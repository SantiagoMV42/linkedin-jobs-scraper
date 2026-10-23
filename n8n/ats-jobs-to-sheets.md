# n8n: career-site jobs to Google Sheets (experimental)

> **Experimental. Please test it before you rely on it.** The Apify API call and the workflow's job-to-row transformation were tested against the live API on 2026-10-23: one run returned 25 Stripe jobs and mapped them to 25 rows, and one returned no jobs and mapped zero rows. **Importing into n8n, running it in n8n, Google OAuth and writing to Sheets have not been tested.** Treat it as a starting point, not a production or end-to-end tested workflow. Reports of what works and what breaks are welcome in this repo's Issues.

Workflow: [ats-jobs-to-sheets.json](ats-jobs-to-sheets.json) · Actor: [Career Site Jobs](https://apify.com/santiagomv/ats-jobs)

**What it does:** Manual or daily (08:00 UTC) trigger → runs the actor for one job board (up to 25 jobs) → checks the response → upserts one row per job into a `Jobs` tab, matched on `url`.

## Cost

The actor charges **$0.0015 per job returned** ($1.50 / 1,000), plus any Apify platform usage. That is up to $0.0375 in actor fees per run at the 25-job cap. Charges go to your own Apify account. Retries and test runs start new runs, which are charged too.

## Setup

1. **Import.** In n8n: Workflows → Import from file → `ats-jobs-to-sheets.json`. It imports inactive. Check that every node loads. The workflow uses Google Sheets node 4.7, HTTP Request 4.5 and Schedule Trigger 1.4, so older n8n versions may not have them.
2. **Sheet.** Create a spreadsheet with a tab named exactly `Jobs`. Put these ten headers in row 1, exactly as written, one per column:

   | url | title | company | ats | location | isRemote | employmentType | postedAt | applyUrl | scrapedAt |
   |---|---|---|---|---|---|---|---|---|---|

3. **Apify credential.** On **Fetch ATS jobs**, create your own Header Auth credential:
   - Name: `Authorization`
   - Value: `Bearer <your Apify API token>` (from [Console → Settings → API & Integrations](https://console.apify.com/settings/integrations))

   The workflow file has no token in it. Don't put your token in the URL or body.
4. **Job board.** In the same node's JSON body, replace `greenhouse:stripe` with your board, e.g. `lever:palantir`, `ashby:openai` or a Workday careers-site URL. The [actor page](https://apify.com/santiagomv/ats-jobs) lists the supported formats. Keep `"onlyNewJobs": false` (see Limits).
5. **Google Sheets credential.** On **Upsert jobs by URL**, connect your own Google Sheets OAuth2 credential. Replace `REPLACE_WITH_BUYER_SPREADSHEET_ID` with your spreadsheet ID (the part of the sheet URL between `/d/` and `/edit`). Select the `Jobs` tab.
6. **Refresh the columns.** Reload the column list in the Sheets node so it reads your tab. Check that:
   - all ten fields are mapped to the matching header (`{{ $json.url }}` → `url`, and so on);
   - **Column to match on** is `url`;
   - **Options → Cell Format** is **Let n8n format** (stored in the workflow as `RAW`), so scraped text is stored as plain text and never run as a Sheets formula.
7. **Run it manually first.** Click *Execute workflow* from **Manual run**. Check the sheet: one row per job, correct columns, no blank row. Run it again and confirm that existing rows are updated and not duplicated.
8. **Then turn on the schedule.** Only after manual runs write correctly, review the **Daily run** time (08:00, workflow timezone `Etc/UTC`) and activate the workflow.

## Limits

- **Snapshot, not full coverage.** `maxJobs: 25` returns at most 25 jobs per run. The jobs are not guaranteed to be the newest, and boards with more jobs will not be fully covered. Raise the cap only if your runs finish within the 300-second synchronous timeout. Larger or slower boards need an asynchronous run-and-poll setup.
- **Retries, not exactly-once.** With `onlyNewJobs: false`, the actor returns current jobs up to the configured cap each run, so a later run can rewrite rows after a failed Sheets write. Nothing guarantees delivery, though: a job that closes before the next run can be missed.
- **No removals.** Closed jobs stay in the sheet. Nothing marks or deletes them.
- **Duplicates.** Overlapping executions, or `url` values already duplicated in the sheet, can create or keep duplicate rows. Don't run it twice at once, and keep the `url` column unique.
- **Zero or few rows doesn't mean the board is healthy.** If a board fails, the actor records it in the run's key-value store under `FAILURES` and can still return an empty or partial result. Check that record in Apify Console when the counts look wrong.
- **Strict response checks.** The code node stops without writing any rows if the response isn't HTTP 201 with a list of jobs, or if any job lacks a valid `http(s)` URL. A job URL repeated within one run is written once.

Not affiliated with n8n, Google, Apify or any ATS vendor. Make sure your use of job-board data follows the source's terms and applicable law.
