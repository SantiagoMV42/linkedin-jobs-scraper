# LinkedIn Jobs, Company & Career-Site Scrapers: code examples

Copy-paste examples (Python, Node.js, cURL, n8n) for five job and company data scrapers that run on [Apify](https://apify.com). Each one needs no LinkedIn login or cookies, and you pay only per result saved.

| Scraper | What you get | Price |
|---|---|---|
| [LinkedIn Jobs Scraper](https://apify.com/santiagomv/linkedin-jobs) | Job search results with full descriptions, parsed salary, applicants, seniority, industry | $1 / 1,000 jobs |
| [Career Site Jobs (Workday, Greenhouse, Lever, Ashby +6)](https://apify.com/santiagomv/ats-jobs) | Every open job from company career pages, one schema, through official public job-board APIs | $1.50 / 1,000 jobs |
| [Workday Jobs Scraper](https://apify.com/santiagomv/workday-jobs) | Any myworkdayjobs.com site: keyword search, Workday's own country/category filters by name, exact dates, parsed salary | $1 / 1,000 jobs |
| [LinkedIn Company Scraper](https://apify.com/santiagomv/linkedin-company) | Website, industry, size, employee and follower counts, HQ, offices, specialties, similar companies | $2 / 1,000 companies |
| [LinkedIn Company Posts Scraper](https://apify.com/santiagomv/linkedin-company-posts) | Recent company page posts: text, date, likes, comments, reposts, images | $1 / 1,000 posts |

The four job and post scrapers have an **only-new** mode: schedule them daily and each run returns only the jobs or posts you haven't received yet. Repeats aren't saved, so they aren't charged as results. (Company Posts needs a state store name for this.) The Company Scraper has no only-new mode.

> ⚠️ The LinkedIn scrapers read LinkedIn's public, logged-out pages. LinkedIn's User Agreement restricts automated access, so using them **may break LinkedIn's terms**, and LinkedIn may block IPs or accounts linked to that use. You are responsible for how you use them and the data, including data-protection law (e.g. GDPR). Not affiliated with, endorsed by, or sponsored by LinkedIn, Greenhouse, Lever, Ashby, Workable or Workday.

## Setup

1. Create a free Apify account and copy your API token from [Console → Settings → API & Integrations](https://console.apify.com/settings/integrations).
2. `export APIFY_TOKEN=your_token`

## Examples

| Use case | Python | Node.js |
|---|---|---|
| Daily LinkedIn job alert to CSV (new jobs only) | [python/linkedin_jobs_to_csv.py](python/linkedin_jobs_to_csv.py) | [node/linkedin-jobs.mjs](node/linkedin-jobs.mjs) |
| All open roles at a list of companies (Workday, Greenhouse, Lever, Ashby…) | [python/career_site_jobs.py](python/career_site_jobs.py) | [node/career-site-jobs.mjs](node/career-site-jobs.mjs) |
| Workday jobs by keyword and country, with salary, to CSV | [python/workday_jobs_salary.py](python/workday_jobs_salary.py) | |
| Enrich a list of companies with LinkedIn firmographics | [python/enrich_companies.py](python/enrich_companies.py) | |
| Track competitors' LinkedIn posts | [python/competitor_posts.py](python/competitor_posts.py) | |
| No code: n8n daily job alert | [n8n/linkedin-jobs-daily.json](n8n/linkedin-jobs-daily.json) | |
| No code, **experimental** (n8n/Sheets steps untested): n8n career-site jobs to Google Sheets | [n8n/ats-jobs-to-sheets.md](n8n/ats-jobs-to-sheets.md) | |

### Also: YouTube transcripts

[YouTube Transcript Scraper](https://apify.com/santiagomv/youtube-transcripts) returns the transcript of any video, Short or live replay as plain text, timestamped lines or timed segments, plus title, channel, views and duration. $4 / 1,000 transcripts; videos without captions are free. Example: [python/youtube_transcripts_to_markdown.py](python/youtube_transcripts_to_markdown.py) saves each transcript as a Markdown file.

```bash
curl -X POST "https://api.apify.com/v2/acts/santiagomv~youtube-transcripts/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"videos":["https://www.youtube.com/watch?v=aircAruvnKk"],"language":"en"}'
```

> ⚠️ Automated access may be against YouTube's Terms of Service, and transcripts are their creators' copyrighted work; you're responsible for how you use them. Not affiliated with YouTube or Google.

### Also: YouTube comments

[YouTube Comments Scraper](https://apify.com/santiagomv/youtube-comments) returns comments and replies from any video with author, likes, reply count, creator hearts and date, sorted by top or newest. $0.50 / 1,000 comments. Example: [python/youtube_comments_to_csv.py](python/youtube_comments_to_csv.py) exports the newest 500 comments to a CSV.

```bash
curl -X POST "https://api.apify.com/v2/acts/santiagomv~youtube-comments/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"videos":["https://www.youtube.com/watch?v=aircAruvnKk"],"maxComments":50,"sortBy":"newest"}'
```

> ⚠️ Automated access may be against YouTube's Terms of Service, and comments are personal data of their authors; you're responsible for how you use them (including GDPR). Not affiliated with YouTube or Google.

### Also: YouTube playlists and channels

[youtube/](youtube/) is a dependency-free Python script and short tutorial for getting the transcripts or comments of a playlist's or channel's videos, with caps on videos and pages.

### Also: enrich a company list into a CSV

[companies/](companies/) is a dependency-free Python script that turns a list of LinkedIn company URLs or slugs into a CSV with website, industry, size, headcount and HQ, with a default cap of 10 companies and $0.02 per run.

### cURL: one call, results back as JSON

```bash
curl -X POST "https://api.apify.com/v2/acts/santiagomv~linkedin-jobs/run-sync-get-dataset-items?token=$APIFY_TOKEN" \
  -H 'Content-Type: application/json' \
  -d '{"searchQueries":["data engineer"],"location":"United States","datePosted":"day","maxJobsPerSearch":50}'
```

Swap `santiagomv~linkedin-jobs` for `santiagomv~ats-jobs`, `santiagomv~workday-jobs`, `santiagomv~linkedin-company` or `santiagomv~linkedin-company-posts`, with that scraper's input. Synchronous calls time out after 5 minutes; for bigger runs use the client libraries below, which wait for the run to finish.

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
