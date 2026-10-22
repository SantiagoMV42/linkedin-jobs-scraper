"""All open roles at a list of companies, straight from their career sites.

Works with Workday, Greenhouse, Lever, Ashby, Workable, SmartRecruiters, Recruitee,
Personio, Breezy and Rippling boards. Paste careers-page URLs or ATS board URLs.

pip install apify-client
APIFY_TOKEN=... python career_site_jobs.py
"""
import os

from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])

run_input = {
    "companies": [
        "https://boards.greenhouse.io/stripe",
        "https://jobs.ashbyhq.com/openai",
        "https://jobs.lever.co/palantir",
        "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
    ],
    "titleKeywords": ["engineer"],
    "remoteOnly": False,
    "postedWithinDays": 30,
}

run = client.actor("santiagomv/ats-jobs").call(run_input=run_input)
for job in client.dataset(run["defaultDatasetId"]).iterate_items():
    pay = f" ({job['salaryMin']}-{job['salaryMax']} {job['salaryCurrency']})" if job.get("salaryMin") else ""
    print(f"{job['company']}: {job['title']} | {job.get('location')}{pay} | {job['url']}")
