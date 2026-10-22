# LinkedIn Jobs, Company & Career-Site Scrapers: code examples

Copy-paste examples (Python, Node.js, cURL, n8n) for four job and company data scrapers that run on [Apify](https://apify.com). Each one needs no LinkedIn login or cookies, and you pay only per result saved.

| Scraper | What you get | Price |
|---|---|---|
| [LinkedIn Jobs Scraper](https://apify.com/santiagomv/linkedin-jobs) | Job search results with full descriptions, parsed salary, applicants, seniority, industry | $1 / 1,000 jobs |
| [Career Site Jobs (Greenhouse, Lever, Ashby, Workable +5)](https://apify.com/santiagomv/ats-jobs) | Every open job from company career pages, one schema, through official public job-board APIs | $1.50 / 1,000 jobs |
| [LinkedIn Company Scraper](https://apify.com/santiagomv/linkedin-company) | Website, industry, size, employee and follower counts, HQ, offices, specialties, similar companies | $2 / 1,000 companies |
| [LinkedIn Company Posts Scraper](https://apify.com/santiagomv/linkedin-company-posts) | Recent company page posts: text, date, likes, comments, reposts, images | $1 / 1,000 posts |

All four have an **only-new** mode: schedule them daily and each run returns only the jobs or posts you haven't received yet. Repeats are free.

> ⚠️ The LinkedIn scrapers read LinkedIn's public, logged-out pages. LinkedIn's User Agreement restricts automated access, so using them **may break LinkedIn's terms**, and LinkedIn may block IPs or accounts linked to that use. You are responsible for how you use them and the data, including data-protection law (e.g. GDPR). Not affiliated with, endorsed by, or sponsored by LinkedIn, Greenhouse, Lever, Ashby or Workable.

## Setup

1. Create a free Apify account and copy your API token from [Console → Settings → API & Integrations](https://console.apify.com/settings/integrations).
2. `export APIFY_TOKEN=your_token`

## Examples

| Use case | Python | Node.js |
|---|---|---|
| Daily LinkedIn job alert to CSV (new jobs only) | [python/linkedin_jobs_to_csv.py](python/linkedin_jobs_to_csv.py) | [node/linkedin-jobs.mjs](node/linkedin-jobs.mjs) |
| All open roles at a list of companies (Greenhouse, Lever, Ashby…) | [python/career_site_jobs.py](python/career_site_jobs.py) | [node/career-site-jobs.mjs](node/career-site-jobs.mjs) |
| Enrich a list of companies with LinkedIn firmographics | [python/enrich_companies.py](python/enrich_companies.py) | |
| Track competitors' LinkedIn posts | [python/competitor_posts.py](python/competitor_posts.py) | |
| No code: n8n daily job alert | [n8n/linkedin-jobs-daily.json](n8n/linkedin-jobs-daily.json) | |

### cURL: one call, results back as JSON

```bash
curl -X POST "https://api.apify.com/v2/acts/santiagomv~linkedin-jobs/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"searchQueries":["data engineer"],"location":"United States","datePosted":"day","maxJobsPerSearch":50}'
```

Swap `santiagomv~linkedin-jobs` for `santiagomv~ats-jobs`, `santiagomv~linkedin-company` or `santiagomv~linkedin-company-posts`, with that scraper's input. Synchronous calls time out after 5 minutes; for bigger runs use the client libraries below, which wait for the run to finish.

### Make, Zapier and other tools

Use Apify's official [Make](https://apify.com/integrations/make) or [Zapier](https://apify.com/integrations/zapier) integration: action **Run Actor**, actor ID `santiagomv/linkedin-jobs` (or any above), paste the input JSON from the examples, then map dataset items to Google Sheets, Airtable, Slack or a CRM.

## Sample output (LinkedIn Jobs)

```json
{
  "id": "4475651276",
  "title": "Entry Level Sales Representative",
  "company": "Alleviation Enterprise LLC",
  "location": "Pocatello, ID",
  "postedAt": "2026-10-11",
  "salaryMin": 64000,
  "salaryMax": 89000,
  "salaryCurrency": "USD",
  "salaryPeriod": "year",
  "applicants": "Be among the first 25 applicants",
  "seniorityLevel": "Not Applicable",
  "employmentType": "Full-time",
  "industries": "Insurance",
  "url": "https://www.linkedin.com/jobs/view/4475651276",
  "description": "We are currently in search of an ambitious and self-disciplined individual..."
}
```

Full field lists are on each scraper's page. Questions or a missing field: open an issue here or on the scraper's Issues tab.

### n8n

Import [n8n/linkedin-jobs-daily.json](n8n/linkedin-jobs-daily.json) (Workflows → Import from file), replace `YOUR_APIFY_TOKEN`, and connect the output to a Google Sheets, Slack or email node. Each item is one job.
