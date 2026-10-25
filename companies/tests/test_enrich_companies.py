"""Offline contract tests: no credentials or live Apify calls."""
import contextlib
import csv
import importlib.util
import io
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit

SOURCE = Path(__file__).resolve().parents[1] / 'enrich_companies.py'
spec = importlib.util.spec_from_file_location('enrich_companies', SOURCE)
app = importlib.util.module_from_spec(spec)
spec.loader.exec_module(app)
COMPANIES = [app.canonical('stripe'), app.canonical('posthog')]


class API:
    def __init__(self):
        self.calls = []
        self.run = {'id': 'run123', 'actId': 'actor123', 'status': 'SUCCEEDED',
                    'defaultDatasetId': 'dataset123', 'defaultKeyValueStoreId': 'store123',
                    'chargedEventCounts': {'company': 2}, 'usageTotalUsd': 0.004,
                    'options': {'maxTotalChargeUsd': 0.02}}
        self.actor = {'id': 'actor123'}
        self.stored = {'companies': COMPANIES.copy(), 'includePosts': False,
                       'includeSimilarPages': False}
        self.rows = [{'name': 'Stripe', 'input': COMPANIES[0], 'slug': 'stripe'},
                     {'name': 'PostHog', 'input': COMPANIES[1], 'slug': 'posthog'}]
        self.failures = []
        self.runs = []

    def __call__(self, request, timeout):
        url = urlsplit(request.full_url)
        path = url.path[len('/v2'):]
        self.calls.append((request.get_method(), path, parse_qs(url.query), request.data, timeout))
        if path == '/acts/' + app.ACTOR + '/runs':
            assert request.get_method() == 'POST'
            payload = {'data': self.run}
        elif path == '/actor-runs/run123':
            payload = {'data': self.runs.pop(0) if self.runs else self.run}
        elif path == '/acts/' + app.ACTOR:
            payload = {'data': self.actor}
        elif path == '/key-value-stores/store123/records/INPUT':
            payload = self.stored
        elif path == '/key-value-stores/store123/records/FAILURES':
            payload = self.failures
        elif path == '/datasets/dataset123':
            payload = {'data': {'itemCount': len(self.rows)}}
        elif path == '/datasets/dataset123/items':
            query = parse_qs(url.query)
            offset, limit = int(query['offset'][0]), int(query['limit'][0])
            payload = self.rows[offset:offset + limit]
        else:
            raise AssertionError('Unexpected offline request: ' + path)
        return io.BytesIO(json.dumps(payload).encode())


class ResumeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=Path(__file__).parent)
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.source, self.output, self.diag = root / 'input.txt', root / 'out.csv', root / 'diag.json'
        self.source.write_text('stripe\nposthog\n')
        self.output.write_text('previous CSV\n')
        self.api = API()
        self.env = patch.dict(os.environ, {'APIFY_TOKEN': 'offline-test-token'})
        self.env.start()
        self.addCleanup(self.env.stop)

    def args(self, resume=True, extra=()):
        argv = ['--input', str(self.source), '--output', str(self.output),
                '--diagnostics', str(self.diag), '--wait-secs', '3', '--poll-secs', '1']
        if resume:
            argv += ['--resume-run-id', 'run123']
        return app.parser().parse_args(argv + list(extra))

    def execute(self, resume=True, extra=()):
        with contextlib.redirect_stderr(io.StringIO()):
            result = app.execute(self.args(resume, extra), self.api)
        if resume:
            self.assertTrue(all(call[0] == 'GET' for call in self.api.calls))
            self.assertFalse(any(call[1].endswith('/runs') for call in self.api.calls))
        return result

    def report(self):
        return json.loads(self.diag.read_text())

    def previous(self, **updates):
        data = {'run_id': 'run123', 'start_attempted': True, 'output_committed': False,
                'status': 'RUNNING', 'error': 'LOCAL_TIMEOUT', 'max_charge_usd': 0.07,
                'charged_event_counts': {'company': 1}, 'usage_total_usd': 0.002,
                'operator_note': 'preserve this evidence'}
        data.update(updates)
        self.diag.write_text(json.dumps(data))
        return self.diag.read_bytes()

    def assert_preserved(self):
        self.assertEqual(self.output.read_text(), 'previous CSV\n')

    def test_resume_success_retains_original_budget_and_evidence(self):
        self.previous()
        self.assertEqual(self.execute(extra=['--max-charge-usd', '0.01']), 0)
        report = self.report()
        self.assertTrue(report['resume_verified'])
        self.assertTrue(report['start_attempted'])
        self.assertTrue(report['output_committed'])
        self.assertEqual(report['max_charge_usd'], 0.07)
        self.assertEqual(report['previous_error'], 'LOCAL_TIMEOUT')
        self.assertEqual(report['operator_note'], 'preserve this evidence')
        self.assertEqual(report['usage_total_usd'], 0.004)
        self.assertNotIn('error', report)
        with self.output.open() as f:
            self.assertEqual([r['name'] for r in csv.DictReader(f)], ['Stripe', 'PostHog'])
        self.assertEqual([c[1] for c in self.api.calls[:3]],
                         ['/actor-runs/run123', '/acts/' + app.ACTOR,
                          '/key-value-stores/store123/records/INPUT'])

    def test_fresh_resume_does_not_claim_new_cost_cap_or_start(self):
        self.api.run['maxTotalChargeUsd'] = 0.09
        self.assertEqual(self.execute(), 0)
        report = self.report()
        self.assertFalse(report['start_attempted'])
        self.assertNotIn('max_charge_usd', report)
        self.assertEqual(report['run_options'], self.api.run['options'])
        self.assertEqual(report['run_max_total_charge_usd'], 0.09)

    def test_missing_charge_fields_do_not_erase_prior_paid_evidence(self):
        self.previous()
        del self.api.run['chargedEventCounts']
        del self.api.run['usageTotalUsd']
        self.assertEqual(self.execute(), 0)
        self.assertEqual(self.report()['charged_event_counts'], {'company': 1})
        self.assertEqual(self.report()['usage_total_usd'], 0.002)

    def test_canonical_stored_input_matches(self):
        self.api.stored['companies'] = ['https://linkedin.com/company/STRIPE/about', 'posthog']
        self.assertEqual(self.execute(), 0)

    def test_bad_identity_actor_and_input_refuse_download(self):
        cases = [('id', 'another-run', 'RUN_ID_MISMATCH'),
                 ('actId', 'other-actor', 'RUN_ACTOR_MISMATCH'),
                 ('actId', None, 'RUN_ACTOR_MISMATCH')]
        for field, value, error in cases:
            with self.subTest(field=field, value=value):
                self.api = API()
                self.api.run[field] = value
                self.assertEqual(self.execute(), 1)
                self.assertEqual(self.report()['error'], error)
                self.assertFalse(self.report()['resume_verified'])
                self.assertFalse(any('/datasets/' in c[1] for c in self.api.calls))
                self.assert_preserved()

    def test_input_mismatch_and_malformed_input(self):
        for stored in ({'companies': ['stripe', 'other']}, {'companies': ['posthog', 'stripe']},
                       {'companies': ['stripe', 'stripe']}, {'companies': ['stripe']},
                       {'companies': [None, 'posthog']}, {'companies': ['http://bad', 'posthog']},
                       [], {}, {'companies': 'stripe'}):
            with self.subTest(stored=stored):
                self.api = API()
                self.api.stored = stored
                self.assertEqual(self.execute(), 1)
                self.assertEqual(self.report()['error'], 'RUN_INPUT_MISMATCH')
                self.assertFalse(any('/datasets/' in c[1] for c in self.api.calls))
                self.assert_preserved()

    def test_unrelated_or_ambiguous_diagnostics_are_untouched(self):
        for prior in ({'run_id': 'other-run'}, {'run_id': None, 'start_attempted': True},
                      {'status': 'INPUT_VALIDATION'}, [], 'invalid json'):
            with self.subTest(prior=prior):
                self.diag.write_text(prior if isinstance(prior, str) else json.dumps(prior))
                original = self.diag.read_bytes()
                self.assertEqual(self.execute(), 1)
                self.assertEqual(self.diag.read_bytes(), original)
                self.assertFalse(self.api.calls)
                self.assert_preserved()

    def test_failed_terminal_run_retains_charges_and_failures(self):
        for status in ('FAILED', 'TIMED-OUT', 'ABORTED'):
            with self.subTest(status=status):
                self.api = API()
                self.api.run['status'] = status
                self.api.failures = [{'input': 'stripe', 'error': 'offline failure'}]
                self.assertEqual(self.execute(), 1)
                report = self.report()
                self.assertEqual(report['error'], 'RUN_' + status)
                self.assertEqual(report['usage_total_usd'], 0.004)
                self.assertEqual(report['failures'], self.api.failures)
                self.assertFalse(any('/datasets/' in c[1] for c in self.api.calls))
                self.assert_preserved()

    def test_local_timeout_bounded_and_fresh_resume_blocks_normal_start(self):
        self.api.run['status'] = 'RUNNING'
        clock = [0.0]
        def sleep(seconds):
            clock[0] += seconds
        with patch.object(app.time, 'monotonic', side_effect=lambda: clock[0]), \
                patch.object(app.time, 'sleep', side_effect=sleep):
            self.assertEqual(self.execute(), 1)
        self.assertEqual(clock[0], 3)
        self.assertEqual(self.report()['error'], 'LOCAL_TIMEOUT')
        self.assertEqual(self.report()['run_id'], 'run123')
        self.assertTrue(all(0 < c[4] <= 3 for c in self.api.calls))
        self.assert_preserved()
        self.api.calls.clear()
        self.assertEqual(self.execute(resume=False), 1)
        self.assertFalse(self.api.calls)

    def test_resume_polls_to_success_and_rechecks_identity_and_actor(self):
        for changed, expected in (({}, 0), ({'id': 'other'}, 1), ({'actId': 'other'}, 1)):
            with self.subTest(changed=changed):
                self.api = API()
                active = dict(self.api.run, status='RUNNING')
                terminal = dict(self.api.run, **changed)
                self.api.runs = [active, terminal]
                with patch.object(app.time, 'sleep'):
                    self.assertEqual(self.execute(), expected)
                if expected:
                    self.assertIn(self.report()['error'], ('RUN_ID_MISMATCH', 'RUN_ACTOR_MISMATCH'))

    def test_strict_download_rejects_unrelated_rows_and_keeps_output(self):
        self.api.rows[0]['input'] = app.canonical('other')
        self.assertEqual(self.execute(), 1)
        self.assertEqual(self.report()['error'], 'UNEXPECTED_COMPANY_RESULT')
        self.assert_preserved()

    def test_partial_export_and_spreadsheet_safety(self):
        self.api.rows = [dict(self.api.rows[0], name='=unsafe')]
        self.api.failures = [{'input': 'posthog', 'error': 'not found'}]
        self.assertEqual(self.execute(), 2)
        self.assertEqual(self.report()['omissions'], [COMPANIES[1]])
        self.assertIn("'=unsafe", self.output.read_text())

    def test_atomic_write_failure_then_resume_succeeds_without_post(self):
        original_replace = app.os.replace
        def fail_output(src, dst):
            if Path(dst) == self.output:
                raise OSError('offline write failure')
            return original_replace(src, dst)
        with patch.object(app.os, 'replace', side_effect=fail_output):
            self.assertEqual(self.execute(resume=False), 1)
        self.assert_preserved()
        report = self.report()
        self.assertEqual(report['run_id'], 'run123')
        self.assertFalse(report['output_committed'])
        self.assertEqual(report['usage_total_usd'], 0.004)
        self.assertEqual(len(list(self.output.parent.glob('.out.csv.*'))), 0)
        self.api.calls.clear()
        self.assertEqual(self.execute(), 0)
        self.assertTrue(self.report()['output_committed'])

    def test_resume_output_failure_retains_existing_csv_and_run(self):
        self.previous()
        original_replace = app.os.replace
        def fail_output(src, dst):
            if Path(dst) == self.output:
                raise OSError('offline write failure')
            return original_replace(src, dst)
        with patch.object(app.os, 'replace', side_effect=fail_output):
            self.assertEqual(self.execute(), 1)
        self.assert_preserved()
        self.assertEqual(self.report()['run_id'], 'run123')
        self.assertEqual(self.report()['max_charge_usd'], 0.07)
        self.assertFalse(self.report()['output_committed'])
        self.assertEqual(len(list(self.output.parent.glob('.out.csv.*'))), 0)

    def test_invalid_resume_id_cannot_summarize_an_unrelated_previous_run(self):
        original = self.previous(run_id='other-run')
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr), patch.object(app.Client, 'request') as request:
            args = ['--input', str(self.source), '--output', str(self.output),
                    '--diagnostics', str(self.diag), '--resume-run-id', '../bad']
            self.assertEqual(app.main(args), 1)
            request.assert_not_called()
        self.assertNotIn('other-run', stderr.getvalue())
        self.assertEqual(original, self.diag.read_bytes())

    def test_read_only_client_rejects_post_before_transport(self):
        client = app.Client('offline-test-token', 1, float('inf'), self.api, read_only=True)
        with self.assertRaisesRegex(app.Error, 'RESUME_START_FORBIDDEN'):
            client.request('/acts/' + app.ACTOR + '/runs', data={})
        self.assertFalse(self.api.calls)

    def test_normal_flow_still_posts_once_with_original_settings(self):
        self.assertEqual(self.execute(resume=False), 0)
        posts = [call for call in self.api.calls if call[0] == 'POST']
        self.assertEqual(len(posts), 1)
        self.assertEqual(json.loads(posts[0][3]), self.api.stored)
        self.assertEqual(posts[0][2], {'timeout': ['300'], 'memory': ['256'],
                                      'maxTotalChargeUsd': ['0.02']})
        self.assertFalse(any(c[1].endswith('/INPUT') for c in self.api.calls))
        self.assertTrue(self.report()['start_attempted'])
        self.assertTrue(self.report()['output_committed'])

    def test_normal_flow_still_blocks_unexported_start(self):
        before = self.previous()
        self.assertEqual(self.execute(resume=False), 1)
        self.assertFalse(self.api.calls)
        self.assertEqual(before, self.diag.read_bytes())


if __name__ == '__main__':
    unittest.main()
