# Enrich a list of LinkedIn companies into a CSV

Got a list of LinkedIn company pages and need website, industry, size, headcount and HQ for each? [`enrich_companies.py`](enrich_companies.py) sends the list to the [LinkedIn Company Scraper](https://apify.com/santiagomv/linkedin-company) on Apify and writes one CSV row per company. It uses only the Python standard library (3.8+). Every new run it starts has a company limit and a hard dollar cap (a resumed run keeps its original limits).

I built and sell the scraper this script calls ($2 per 1,000 companies, paid to Apify). The script itself is free to copy.

## Run it

1. Get an Apify API token from **Settings → API & Integrations** in the [Apify Console](https://console.apify.com).
2. Put one company per line in `companies.txt`, as a LinkedIn company URL or the exact slug from it. Company names and website domains are not looked up: they may be rejected (`Acme Inc`) or point at the wrong page.

   ```text
   https://www.linkedin.com/company/stripe/
   posthog
   ```

3. Run:

   ```bash
   export APIFY_TOKEN=your_token
   python3 enrich_companies.py
   ```

   ```text
   Wrote 2 companies to companies_enriched.csv (run EGOYMagxubXo7eTZO).
   ```

The CSV has these columns: `name, website, industry, companySize, employeesOnLinkedIn, followers, headquarters, founded, type, url, slug, input, scrapedAt`. `input` is the normalized URL the script sent (`https://www.linkedin.com/company/<slug>/`, slug lowercased), so join back to your own sheet on that or on `slug`.

## Limits and cost

- **10 companies and $0.02 per run by default.** A longer list is refused before anything is sent, never cut short silently. Raise the limits for bigger lists, up to 100 companies:

  ```bash
  python3 enrich_companies.py --max-companies 100 --max-charge-usd 0.25
  ```

- `--max-charge-usd` is a hard cap that Apify enforces on the run's charges.
- Duplicates are removed before the run. Personal profiles, school and showcase pages, and non-LinkedIn URLs are rejected before anything is sent.
- `--wait-secs` (default 360) only limits how long the script waits. When it runs out, the script stops waiting; the run keeps going on Apify.
- `python3 enrich_companies.py --help` lists every option.

## When something goes wrong

The exit code and the last line tell you what happened. Details go to `companies_enriched.csv.diagnostics.json`.

| Exit | Meaning | What to do |
|---|---|---|
| `0` | Every company found. | Nothing. |
| `2` | Partial: the CSV holds the companies that worked. | `omissions` in the diagnostics file lists the ones missing, and `failures` gives the scraper's reason where it has one (e.g. page not found). |
| `1` | No new CSV written. An older CSV at the same path is left untouched. | Read `error` in the diagnostics file. |

Problems caught before anything is sent (missing token, a bad input line, a list over the limit) just need fixing and a rerun.

### A run was started but no CSV was saved

If the diagnostics file says `"start_attempted": true` and no CSV was saved, a paid run may exist. The script won't start a new one while that file is there, so a rerun can't pay for the same list twice by accident. Pick up the existing run instead.

**`run_id` is filled in.** Resume that run with the same `companies.txt` (same lines, same order) and the same `--max-companies`, `--output` and `--diagnostics` you used before:

```bash
python3 enrich_companies.py --resume-run-id RUN_ID_FROM_DIAGNOSTICS
```

Resume starts no second run. It checks that the run belongs to this scraper and that its input matches your file, waits up to `--wait-secs`, and writes the CSV if the run succeeded (exit 0 or 2). If the original run is still going, it keeps charging under its original limits. Rows a finished run already saved aren't scraped or charged again; reading them counts as ordinary Apify platform usage.

- Still running when the wait ends (`LOCAL_TIMEOUT`): run the same command again later.
- `RUN_INPUT_MISMATCH`: your file differs from what that run was given. Restore the original list rather than starting a new run.
- `RUN_FAILED`, `RUN_TIMED-OUT` or `RUN_ABORTED`: nothing is exported, even if the run saved some rows. Its charges stand. Look at the run in the Console before deciding to pay for a new one.
- `--max-charge-usd`, `--timeout-secs` and `--memory-mbytes` only apply to new runs. They don't change, or lower, the cap of the run you're resuming.

**`run_id` is empty.** The script can't tell whether Apify created a run (an error such as `API_HTTP_401` usually means it didn't, a dropped connection may not). Open **Runs** in the Apify Console and look for a LinkedIn Company Scraper run started at that time.

- If you find one and its input is your list, resume it. The old diagnostics file doesn't record that ID, so give the resume a new report path:

  ```bash
  python3 enrich_companies.py --resume-run-id RUN_ID_FROM_CONSOLE --diagnostics resume.diagnostics.json
  ```

  Once that saves the CSV, move the old diagnostics file aside so later normal runs aren't blocked.

- If there is no such run, move the old diagnostics file aside (keep it as a record) and run normally.

Use the same `--diagnostics` approach if the default file belongs to some other run (`RESUME_DIAGNOSTICS_MISMATCH`), but only after confirming the run ID in the Console.

## Good to know

- **Spreadsheet safety.** Cells that start with `=`, `+`, `-` or `@` get a leading apostrophe so Excel or Google Sheets won't run them as formulas. Strip it if you load the CSV somewhere else.
- **Your token** goes only in the request header. It is never written to the CSV, the diagnostics file or the screen.
- Values are what LinkedIn shows on the public company page at the time of the run. Counts change over time, and some companies leave fields empty.

> ⚠️ This reads LinkedIn's public, logged-out company pages. LinkedIn's User Agreement restricts automated access, so using it **may break LinkedIn's terms**, and LinkedIn may block IPs or accounts linked to that use. You are responsible for how you use it and the data, including data-protection law (e.g. GDPR). Not affiliated with, endorsed by, or sponsored by LinkedIn.
