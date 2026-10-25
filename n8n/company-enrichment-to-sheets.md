# n8n: LinkedIn company list to Google Sheets (experimental)

> **Experimental. Please test it before you rely on it.** On 2026-10-25 one live API call with the workflow's own settings and its two sample companies (Stripe, PostHog) returned HTTP 201 and two company rows that passed the workflow's checks. The workflow's two Code nodes were also run outside n8n against mock responses. **Importing into n8n, running it in n8n, Google OAuth and writing to Sheets have not been tested.** Nothing here has been tested end to end. Treat it as a starting point, not a production workflow. Reports of what works and what breaks are welcome in this repo's Issues.

Workflow: [company-enrichment-to-sheets.json](company-enrichment-to-sheets.json) · Actor: [LinkedIn Company Scraper](https://apify.com/santiagomv/linkedin-company)

**What it does:** Manual trigger → **Config** checks your company list → **Apify** runs the actor once → **Rows** checks the whole response and maps one row per company → **Sheets** upserts the rows into a `Companies` tab, matched on `url`.

It only collects company-page facts (website, industry, size, HQ, follower and employee counts). It doesn't look up people, employees' profiles or contact details, posts or similar companies.

> ⚠️ The actor reads LinkedIn's public, logged-out company pages. LinkedIn's User Agreement restricts automated access, so using it **may break LinkedIn's terms**, and LinkedIn may block IPs or accounts linked to that use. You are responsible for how you use it and the data, including data-protection law (e.g. GDPR). Not affiliated with, endorsed by, or sponsored by LinkedIn, n8n, Google or Apify.

## Cost

The actor charges **$0.002 per company returned** ($2 / 1,000), plus any Apify platform usage, to your own Apify account. The two sample companies cost $0.004 in actor fees.

`maxTotalChargeUsd` (default and maximum `0.02`) is sent to Apify as a cap on the **actor's charges** for one run. It is not an all-in budget: platform usage is billed separately. At $0.002 per company, $0.02 covers at most 10 companies (see Limits).

Every execution of the workflow starts a new paid run, including test runs and re-runs.

## Setup

1. **Import.** In n8n: Workflows → Import from file → `company-enrichment-to-sheets.json`. It imports inactive. Check that every node loads. It uses HTTP Request 4.5, Code 2 and Google Sheets 4.7, so older n8n versions may not have them.
2. **Sheet.** Create a spreadsheet with a tab named exactly `Companies`. Put these ten headers in row 1, exactly as written, one per column:

   | url | name | website | industry | companySize | headquarters | description | followers | employeesOnLinkedIn | scrapedAt |
   |---|---|---|---|---|---|---|---|---|---|

3. **Apify credential.** On the **Apify** node, create your own Header Auth credential:
   - Name: `Authorization`
   - Value: `Bearer <your Apify API token>` (from [Console → Settings → API & Integrations](https://console.apify.com/settings/integrations))

   The workflow file has no token in it. Don't put your token in the URL, query or body.
4. **Companies.** Open the **Config** node and edit the three values at the bottom of the code:

   ```js
   companies: ['https://www.linkedin.com/company/stripe', 'https://www.linkedin.com/company/posthog'],
   maxCompanies: 2,
   maxTotalChargeUsd: 0.02
   ```

   - `companies`: LinkedIn company URLs (`linkedin.com/company/<slug>`, optionally ending in `/about/`) or bare slugs like `stripe`. Duplicates are removed. Other URLs stop the workflow before anything is charged.
   - `maxCompanies`: whole number from 1 to 100. The workflow stops before the API call if your list has more distinct companies than this.
   - `maxTotalChargeUsd`: above 0 and at most `0.02`.

   Leave the rest of the code as it is.
5. **Google Sheets credential.** On the **Sheets** node, connect your own Google Sheets OAuth2 credential. Set **Document** to *By ID* and replace `REPLACE_WITH_BUYER_SPREADSHEET_ID` with your spreadsheet ID (the part of the sheet URL between `/d/` and `/edit`). Set **Sheet** to *By Name*: `Companies`.
6. **Refresh the columns.** Reload the column list in the Sheets node so it reads your tab. Check that:
   - all ten fields are mapped to the matching header (`{{ $json.url }}` → `url`, and so on);
   - **Column to match on** is `url`;
   - **Options → Cell Format** is **Let n8n format** (stored in the workflow as `RAW`), so scraped text is stored as plain text and never run as a Sheets formula.
7. **Run it manually.** Click *Execute workflow*. Check the sheet: one row per company, correct columns, no blank row. Running it again (a new paid run) should update the same rows, not add new ones.

There is no schedule. The workflow only runs when you start it.

## The `url` key

Each row's `url` is a canonical form of the company you asked for: `https://www.linkedin.com/company/<slug>/`, lowercased, with a trailing slash. It stays the same across runs, so re-runs update rows in place.

If your tab already has rows, their `url` values must use exactly this format and must be unique. Rows in another format won't match and you'll get duplicates; rows already duplicated stay duplicated. Clean them up before the first run, and don't start two executions at once.

## Limits

- **10 companies per run in practice.** `maxCompanies` accepts up to 100, but the $0.02 actor cap pays for 10 companies at most. If the cap stops the run early, some companies are missing and **Rows** rejects the whole batch (next point), after you've paid for the ones it did get. Keep lists to 10 or fewer.
- **All or nothing before Sheets.** **Rows** writes nothing unless the response is HTTP 201 with a result for every company you asked for, and no others. A missing company, an error row, a company you didn't ask for, an invalid timestamp or an unsafe cell stops the whole batch.
- **Timeouts.** Apify stops the run after 240 seconds and n8n waits up to 300. A timeout or other failed response writes nothing, but Apify may still have created and charged a run. Check Runs in Apify Console before trying again. The workflow never retries the paid call by itself.
- **Cells.** Empty fields become empty cells. Zero stays `0`. Lists and objects (e.g. multiple websites) are stored as JSON text in one cell. Text starting with `=`, `+`, `-` or `@` gets a leading apostrophe so Sheets shows it as text. `description` may be empty; it hasn't been confirmed in live output.
- **No removals.** Companies you drop from the list stay in the sheet.

## If the Sheets step fails

Google Sheets writes aren't all-or-nothing, so some rows may already be written when the node fails. Because rows are matched on `url`, writing the same rows again is safe.

1. Fix the cause (credential, sharing, tab name, headers).
2. Re-send the **same saved rows** from the failed execution. Don't re-run the whole workflow: that starts another paid scrape. Two ways, depending on your n8n version:
   - In **Executions**, open the failed execution and retry it. First check that your n8n version's retry starts from the failed node with the saved data and doesn't re-run the **Apify** node.
   - Or open the failed execution, copy or pin the **Rows** output into the editor, and execute only the **Sheets** node.
3. If n8n no longer has the execution data, find the original run and its dataset in Apify Console before deciding whether to run again.
