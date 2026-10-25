"""Bounded LinkedIn company enrichment. Python standard library only."""
import argparse
import csv
import io
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

BASE = 'https://api.apify.com/v2'
ACTOR = 'santiagomv~linkedin-company'
MAX_COMPANIES = 100
FIELDS = ['name', 'website', 'industry', 'companySize', 'employeesOnLinkedIn',
          'followers', 'headquarters', 'founded', 'type', 'url', 'slug', 'input', 'scrapedAt']
TERMINAL = {'SUCCEEDED', 'FAILED', 'TIMED-OUT', 'ABORTED'}
ACTIVE = {'READY', 'RUNNING', 'TIMING-OUT', 'ABORTING'}
ID = re.compile(r'^[A-Za-z0-9_-]+$')


class Error(Exception):
    pass


def bounded_int(low, high):
    def parse(value):
        try:
            number = int(value)
        except ValueError:
            raise argparse.ArgumentTypeError('INVALID_INTEGER') from None
        if not low <= number <= high:
            raise argparse.ArgumentTypeError(f'RANGE_{low}_{high}')
        return number
    return parse


def charge(value):
    try:
        number = float(value)
    except ValueError:
        raise argparse.ArgumentTypeError('INVALID_CHARGE') from None
    if not math.isfinite(number) or not 0 < number <= 100:
        raise argparse.ArgumentTypeError('CHARGE_RANGE_0_EXCLUSIVE_100')
    return number


def parser():
    p = argparse.ArgumentParser(description='Enrich a list of LinkedIn companies into a CSV with the santiagomv/linkedin-company '
                                'Apify actor. Needs APIFY_TOKEN. Exit 0 = all rows, 2 = partial CSV, 1 = nothing written.')
    p.add_argument('--input', default='companies.txt',
                   help='one LinkedIn company URL or slug per line; names and domains are not looked up (default: %(default)s)')
    p.add_argument('--output', default='companies_enriched.csv', help='CSV to write (default: %(default)s)')
    p.add_argument('--diagnostics', help='run report JSON (default: <output>.diagnostics.json)')
    p.add_argument('--resume-run-id', metavar='RUN_ID',
                   help='start nothing; re-check an existing run of this actor whose input matches --input '
                        '(same lines, same order) and write its CSV if it succeeded')
    p.add_argument('--max-charge-usd', type=charge, default=0.02,
                   help='hard cost cap in USD for a new run; does not change an existing run (default: %(default)s)')
    p.add_argument('--max-companies', type=bounded_int(1, MAX_COMPANIES), default=10,
                   help='refuse inputs with more distinct companies than this, 1-100; also applies on resume (default: %(default)s)')
    p.add_argument('--timeout-secs', type=bounded_int(1, 3600), default=300, help='timeout for a new actor run (default: %(default)s)')
    p.add_argument('--wait-secs', type=bounded_int(1, 3900), default=360,
                   help='how long this script waits; the Apify run is not stopped when it expires (default: %(default)s)')
    p.add_argument('--http-timeout-secs', type=bounded_int(1, 120), default=30, help='per-request timeout (default: %(default)s)')
    p.add_argument('--poll-secs', type=bounded_int(1, 30), default=2, help='status poll interval (default: %(default)s)')
    p.add_argument('--memory-mbytes', type=int, choices=[128, 256, 512, 1024], default=256, help='memory for a new actor run (default: %(default)s)')
    return p


def canonical(value):
    value = value.strip()
    if not value or len(value) > 2048:
        raise Error('INVALID_COMPANY')
    if '://' in value or '/' in value:
        url = urllib.parse.urlsplit(value if '://' in value else 'https://' + value)
        if (url.scheme not in ('http', 'https') or url.username or url.password
                or url.port is not None or not url.hostname
                or not re.fullmatch(r'(?:www\.|[a-z]{2}\.)?linkedin\.com', url.hostname.lower())):
            raise Error('INVALID_COMPANY_URL')
        match = re.fullmatch(r'/company/([^/]+)(?:/(?:about)?/?)?', url.path)
        if not match:
            raise Error('INVALID_COMPANY_PATH')
        value = match[1]
    if re.search(r'%(?![0-9a-fA-F]{2})', value):
        raise Error('INVALID_COMPANY_ENCODING')
    try:
        slug = urllib.parse.unquote(value, errors='strict').lower()
    except UnicodeError:
        raise Error('INVALID_COMPANY_ENCODING') from None
    if not re.fullmatch(r"[\w&'-]+(?:[.][\w&'-]+)*", slug, re.UNICODE) or len(slug) > 200:
        raise Error('INVALID_COMPANY_SLUG')
    return 'https://www.linkedin.com/company/' + urllib.parse.quote(slug, safe='') + '/'


def read_companies(path, limit):
    # Bound bytes and lines as well as distinct companies, before any network call.
    with open(path, 'rb') as source:
        raw = source.read(1024 * 1024 + 1)
    if len(raw) > 1024 * 1024:
        raise Error('INPUT_TOO_LARGE')
    values = list(dict.fromkeys(canonical(line) for line in raw.decode('utf-8-sig').splitlines() if line.strip()))
    if not values:
        raise Error('EMPTY_INPUT')
    if len(values) > limit:
        raise Error('MAX_COMPANIES_EXCEEDED')
    return values


def atomic_write(path, content):
    path = Path(path)
    name = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', newline='',
                                         dir=path.parent, prefix='.' + path.name + '.', delete=False) as f:
            name = f.name
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(name, path)
    finally:
        if name and os.path.exists(name):
            os.unlink(name)


def redact(value, token):
    if isinstance(value, str):
        return value.replace(token, '[REDACTED]') if token else value
    if isinstance(value, list):
        return [redact(v, token) for v in value]
    if isinstance(value, dict):
        return {redact(k, token): redact(v, token) for k, v in value.items()}
    return value


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise Error('API_REDIRECT_REJECTED')


class Client:
    def __init__(self, token, http_timeout, deadline, opener=None, read_only=False):
        self.token, self.http_timeout, self.deadline = token, http_timeout, deadline
        self.opener = opener or urllib.request.build_opener(NoRedirect()).open
        self.read_only = read_only

    def request(self, path, data=None, query=None):
        if self.read_only and data is not None:
            raise Error('RESUME_START_FORBIDDEN')
        remaining = self.deadline - time.monotonic()
        if remaining <= 0:
            raise Error('LOCAL_TIMEOUT')
        url = BASE + path + ('?' + urllib.parse.urlencode(query) if query else '')
        request = urllib.request.Request(url, data=None if data is None else json.dumps(data).encode(),
                                         headers={'Authorization': 'Bearer ' + self.token,
                                                  'Content-Type': 'application/json'})
        try:
            with self.opener(request, timeout=min(self.http_timeout, remaining)) as response:
                payload = response.read(8 * 1024 * 1024 + 1)
                if len(payload) > 8 * 1024 * 1024:
                    raise Error('API_RESPONSE_TOO_LARGE')
                return json.loads(payload)
        except urllib.error.HTTPError as e:
            raise Error(f'API_HTTP_{e.code}') from None
        except (urllib.error.URLError, TimeoutError, OSError):
            raise Error('API_TRANSPORT_ERROR') from None
        except (ValueError, UnicodeError):
            raise Error('API_INVALID_JSON') from None


def object_data(payload):
    if not isinstance(payload, dict) or not isinstance(payload.get('data'), dict):
        raise Error('API_INVALID_DATA')
    return payload['data']


def identifier(value):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise Error('API_INVALID_ID')
    return value


def verify_run(run, run_id, actor_id=None):
    if run.get('id') != run_id:
        raise Error('RUN_ID_MISMATCH')
    if actor_id is not None and run.get('actId') != actor_id:
        raise Error('RUN_ACTOR_MISMATCH')


def resume_run(client, run_id, companies):
    run = object_data(client.request('/actor-runs/' + run_id))
    verify_run(run, run_id)
    actor_id = identifier(object_data(client.request('/acts/' + ACTOR)).get('id'))
    verify_run(run, run_id, actor_id)
    store = identifier(run.get('defaultKeyValueStoreId'))
    stored = client.request(f'/key-value-stores/{store}/records/INPUT')
    values = stored.get('companies') if isinstance(stored, dict) else None
    if (not isinstance(values, list) or len(values) != len(companies)
            or any(not isinstance(value, str) for value in values)):
        raise Error('RUN_INPUT_MISMATCH')
    try:
        matches = [canonical(value) for value in values] == companies
    except (Error, ValueError):
        matches = False
    if not matches:
        raise Error('RUN_INPUT_MISMATCH')
    return run, actor_id


def csv_cell(value):
    if value is None:
        return ''
    text = json.dumps(value, ensure_ascii=False, sort_keys=True) if isinstance(value, (dict, list)) else str(value)
    # Spreadsheet importers can ignore leading whitespace/control characters.
    probe = re.sub(r'^[\s\x00-\x1f\x7f\ufeff]*', '', text)
    if probe.startswith(('=', '+', '-', '@')) or text.startswith(('\t', '\r', '\n')):
        text = "'" + text
    return text


def download(client, run, companies, diagnostics):
    dataset = identifier(run.get('defaultDatasetId'))
    store = identifier(run.get('defaultKeyValueStoreId'))
    failures = client.request(f'/key-value-stores/{store}/records/FAILURES')
    if not isinstance(failures, list) or len(failures) > len(companies):
        raise Error('INVALID_FAILURES')
    diagnostics['failures'] = failures
    failed = set()
    for failure in failures:
        if (not isinstance(failure, dict) or not isinstance(failure.get('error'), str)
                or canonical(failure.get('input', '')) not in companies):
            raise Error('INVALID_FAILURES')
        company = canonical(failure['input'])
        if company in failed:
            raise Error('INVALID_FAILURES')
        failed.add(company)
    count = object_data(client.request(f'/datasets/{dataset}')).get('itemCount')
    if type(count) is not int or not 0 <= count <= len(companies):
        raise Error('INVALID_DATASET_COUNT')
    diagnostics['dataset_count'] = count
    rows, seen = [], set()
    while True:
        # Dataset metadata is eventually consistent immediately after a run.
        # Read items even when itemCount is zero; request one extra to detect overflow.
        limit = min(100, len(companies) + 1 - len(rows))
        page = client.request(f'/datasets/{dataset}/items', query={
            'format': 'json', 'offset': len(rows), 'limit': limit, 'clean': 'false'})
        if not isinstance(page, list) or len(rows) + len(page) > len(companies):
            raise Error('INVALID_DATASET_PAGE')
        if not page:
            if len(rows) < count:
                raise Error('INVALID_DATASET_PAGE')
            break
        for row in page:
            if not isinstance(row, dict) or not isinstance(row.get('name'), str) or not row['name'].strip():
                raise Error('INVALID_COMPANY_RESULT')
            company = canonical(row.get('input', ''))
            if company not in companies or company in seen or company in failed or canonical(row.get('slug', '')) != company:
                raise Error('UNEXPECTED_COMPANY_RESULT')
            seen.add(company)
            rows.append(row)
            diagnostics['count'] = len(rows)
            diagnostics['omissions'] = [c for c in companies if c not in seen]
        if len(page) < limit and len(rows) >= count:
            break
    diagnostics['omissions'] = [c for c in companies if c not in seen]
    if not rows:
        raise Error('EMPTY_DATASET')
    return rows


def execute(args, opener=None):
    token = os.environ.get('APIFY_TOKEN', '').strip()
    resume_id = getattr(args, 'resume_run_id', None)
    if resume_id is not None:
        try:
            resume_id = identifier(resume_id)
        except Error:
            print('INVALID_RUN_ID: --resume-run-id takes the run ID from the diagnostics file or the Apify '
                  'Console (letters, digits, - and _ only). Nothing was sent.', file=sys.stderr)
            args.blocked = True
            raise
    diag_path = args.diagnostics or args.output + '.diagnostics.json'
    paths = [Path(p).resolve() for p in (args.input, args.output, diag_path)]
    if len(set(paths)) != 3:
        print('PATH_COLLISION: --input, --output and the diagnostics file must be three different files. '
              'Nothing was sent.', file=sys.stderr)
        args.blocked = True
        raise Error('PATH_COLLISION')
    previous = None
    if Path(diag_path).exists():
        try:
            previous = json.loads(Path(diag_path).read_text(encoding='utf-8'))
        except (OSError, ValueError):
            print(f'INVALID_DIAGNOSTICS: {diag_path} is not a readable diagnostics file and may describe a paid run. '
                  'Nothing was sent. Check it and Apify Console > Runs before moving it aside.', file=sys.stderr)
            args.blocked = True
            return 1
        if resume_id is not None:
            if not isinstance(previous, dict) or previous.get('run_id') != resume_id:
                print(f'RESUME_DIAGNOSTICS_MISMATCH: {diag_path} does not record this run ID. Nothing was sent. '
                      'Confirm the ID in Apify Console > Runs; if it is right, pass a new --diagnostics path.',
                      file=sys.stderr)
                args.blocked = True
                return 1
        elif not isinstance(previous, dict) or ((previous.get('start_attempted') or previous.get('resume_attempted'))
                                               and not previous.get('output_committed')):
            # Keep the original run evidence; an operator must reconcile/archive it.
            print(f'Not starting a new run: {diag_path} records a run whose results were never saved. '
                  'If it has a run_id, rerun with --resume-run-id <run_id> and the same input file. '
                  'If run_id is empty, check Apify Console > Runs first. See the README.', file=sys.stderr)
            args.blocked = True
            return 1
    diagnostics = {'run_id': None, 'status': 'INPUT_VALIDATION', 'count': 0,
                   'failures': [], 'charged_event_counts': {}, 'omissions': [],
                   'start_attempted': False, 'output_committed': False}
    if resume_id is not None:
        if previous is not None:
            diagnostics.update(previous)
        diagnostics.update(run_id=resume_id, resume_attempted=True,
                           resume_verified=False)
        # Keep the original start/budget/charge evidence, even if verification fails.
        if 'error' in diagnostics:
            diagnostics.setdefault('previous_error', diagnostics.pop('error'))

    def save():
        atomic_write(diag_path, json.dumps(redact(diagnostics, token), ensure_ascii=False, indent=2) + '\n')

    try:
        companies = read_companies(args.input, args.max_companies)
        if resume_id is None:
            diagnostics.update(input_count=len(companies), omissions=companies,
                               max_charge_usd=args.max_charge_usd)
        if not token or any(ord(c) < 33 or ord(c) > 126 for c in token):
            raise Error('MISSING_OR_INVALID_APIFY_TOKEN')
        # Check destinations before creating a billable run.
        save()
        with tempfile.TemporaryFile(dir=Path(args.output).parent):
            pass
        client = Client(token, args.http_timeout_secs, time.monotonic() + args.wait_secs,
                        opener, read_only=resume_id is not None)
        actor_id = None
        if resume_id is not None:
            run, actor_id = resume_run(client, resume_id, companies)
            diagnostics.update(resume_verified=True, input_count=len(companies),
                               omissions=companies, count=0, failures=[], output_committed=False)
            if 'options' in run:
                diagnostics['run_options'] = run['options']
            if 'maxTotalChargeUsd' in run:
                diagnostics['run_max_total_charge_usd'] = run['maxTotalChargeUsd']
        else:
            diagnostics.update(status='START_UNCONFIRMED', start_attempted=True)
            save()
            run = object_data(client.request(f'/acts/{ACTOR}/runs', data={
                'companies': companies, 'includePosts': False, 'includeSimilarPages': False,
            }, query={'timeout': args.timeout_secs, 'memory': args.memory_mbytes,
                      'maxTotalChargeUsd': args.max_charge_usd}))
            # Persist the ID before interpreting any other response fields.
            diagnostics['run_id'] = identifier(run.get('id'))
        save()
        while True:
            status = run.get('status')
            diagnostics['status'] = status
            diagnostics['charged_event_counts'] = run.get('chargedEventCounts', diagnostics['charged_event_counts'])
            diagnostics['usage_total_usd'] = run.get('usageTotalUsd', diagnostics.get('usage_total_usd'))
            save()
            if status in TERMINAL:
                break
            if status not in ACTIVE:
                raise Error('INVALID_RUN_STATUS')
            remaining = client.deadline - time.monotonic()
            if remaining <= 0:
                raise Error('LOCAL_TIMEOUT')
            time.sleep(min(args.poll_secs, remaining))
            run = object_data(client.request('/actor-runs/' + diagnostics['run_id']))
            verify_run(run, diagnostics['run_id'], actor_id)
        if status != 'SUCCEEDED':
            store = run.get('defaultKeyValueStoreId')
            if isinstance(store, str) and ID.fullmatch(store):
                try:
                    failures = client.request(f'/key-value-stores/{store}/records/FAILURES')
                    if isinstance(failures, list):
                        diagnostics['failures'] = failures
                except Error as failure_error:
                    diagnostics['failures_error'] = str(failure_error)
            raise Error('RUN_' + status)
        rows = download(client, run, companies, diagnostics)
        stream = io.StringIO(newline='')
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: csv_cell(redact(row.get(k), token)) for k in FIELDS})
        diagnostics['partial'] = bool(diagnostics['omissions'] or diagnostics['failures'])
        save()
        atomic_write(args.output, stream.getvalue())
        diagnostics['output_committed'] = True
        save()
        return 2 if diagnostics['partial'] else 0
    except (Error, OSError, ValueError, TypeError, AttributeError, KeyboardInterrupt) as e:
        # Never expose server bodies, URLs, headers, arbitrary exception strings or credentials.
        diagnostics['error'] = str(e) if isinstance(e, Error) else 'LOCAL_OR_SCHEMA_ERROR'
        save()
        return 1


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        code = execute(args)
    except (Error, OSError, ValueError):
        code = 1
    if not getattr(args, 'blocked', False):
        summarize(code, args.diagnostics or args.output + '.diagnostics.json', args.output)
    return code


def summarize(code, diag_path, output):
    """One stderr line so the exit code isn't the only feedback."""
    try:
        with open(diag_path, encoding='utf-8') as f:
            d = json.load(f)
    except (OSError, ValueError):
        d = {}
    if not isinstance(d, dict):
        d = {}
    run = f" (run {d['run_id']})" if d.get('run_id') else ''
    if code == 0:
        msg = f"Wrote {d.get('count', '?')} companies to {output}{run}."
    elif code == 2:
        msg = (f"Partial: wrote {d.get('count', '?')} companies to {output}; "
               f"{len(d.get('omissions') or [])} missing{run}. See {diag_path}.")
    else:
        msg = f"No CSV written: {d.get('error', 'see diagnostics')}{run}. See {diag_path}."
    print(msg, file=sys.stderr)


if __name__ == '__main__':
    sys.exit(main())
