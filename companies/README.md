# Enrich a list of companies from LinkedIn into a CSV

Got a list of company names or LinkedIn URLs and need website, industry, size, headcount and HQ for each? [`enrich_companies.py`](enrich_companies.py) sends the list to the [LinkedIn Company Scraper](https://apify.com/santiagomv/linkedin-company) on Apify and writes one CSV row per company. It uses only the Python standard library (3.8+), and it's capped so a typo can't run up a bill.

I built and sell the scraper this script calls ($2 per 1,000 companies, paid to Apify). The script itself is free to copy.

## Run it

1. Get an Apify API token from **Settings → API & Integrations** in the [Apify Console](https://console.apify.com).
2. Put one company per line in `companies.txt`. Use the LinkedIn URL or the slug from it:

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

The CSV has these columns: `name, website, industry, companySize, employeesOnLinkedIn, followers, headquarters, founded, type, url, slug, input, scrapedAt`. `input` is the line you gave, so you can join the results back to your own sheet.

## Limits and cost

- **10 companies and $0.02 per run by default.** A longer list is refused up front, never cut short silently. Raise the limits for bigger lists, up to 100 companies:

  ```bash
  python3 enrich_companies.py --max-companies 100 --max-charge-usd 0.25
  ```

- `--max-charge-usd` is a hard cap that Apify enforces. If it's reached, the run stops and you get the rows saved up to that point.
- Duplicates are removed before the run. Personal profiles, school and showcase pages, and non-LinkedIn URLs are rejected before anything is sent.
- `python3 enrich_companies.py --help` lists every option.

## When something goes wrong

The exit code and the last line tell you what happened. Details go to `companies_enriched.csv.diagnostics.json`.

| Exit | Meaning | What to do |
|---|---|---|
| `0` | Every company found. | Nothing. |
| `2` | Partial: the CSV holds the companies that worked. | `omissions` in the diagnostics file lists the ones missing, and `failures` gives the scraper's reason where it has one (e.g. page not found). |
| `1` | No new CSV written. An older CSV at the same path is left untouched. | Read `error` in the diagnostics file. |

**After an exit 1, check before you rerun.** Once the script has asked Apify to start a run, that run may still be going, or may have finished after the script stopped waiting, and you may already have paid for its results. So if the diagnostics file says `"start_attempted": true`, the script won't start another run until you've checked:

1. If there's a `run_id`, open the run in the Apify Console (**Runs**) and download its dataset if it has the rows you need. If `run_id` is empty, the start request itself failed (e.g. `API_HTTP_401` for a wrong token); check **Runs** for a run started at that time, which there usually isn't.
2. Then move or delete the diagnostics file, or pass a different `--diagnostics` path, and rerun.

Problems caught before anything is sent (missing token, a bad input line, a list over the limit) don't need this: fix them and rerun.

## Good to know

- **Spreadsheet safety.** Cells that start with `=`, `+`, `-` or `@` get a leading apostrophe so Excel or Google Sheets won't run them as formulas. Strip it if you load the CSV somewhere else.
- **Your token** goes only in the request header. It is never written to the CSV, the diagnostics file or the screen.
- Values are what LinkedIn shows on the public company page at the time of the run. Counts change over time, and some companies leave fields empty.

> ⚠️ This reads LinkedIn's public, logged-out company pages. LinkedIn's User Agreement restricts automated access, so using it **may break LinkedIn's terms**, and LinkedIn may block IPs or accounts linked to that use. You are responsible for how you use it and the data, including data-protection law (e.g. GDPR). Not affiliated with, endorsed by, or sponsored by LinkedIn.
