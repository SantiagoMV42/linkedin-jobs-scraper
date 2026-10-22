"""Daily LinkedIn job alert: new jobs only, appended to a CSV.

pip install apify-client
APIFY_TOKEN=... python linkedin_jobs_to_csv.py
Schedule it with cron; with onlyNewJobs on, each run returns only jobs you haven't seen yet.
"""
import csv
import os

from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])

run_input = {
    "searchQueries": ["data engineer", "analytics engineer"],
    "location": "United States",
    "datePosted": "day",
    "workplaceTypes": ["2"],  # 1 = on-site, 2 = remote, 3 = hybrid
    "maxJobsPerSearch": 200,
    "onlyNewJobs": True,
}

run = client.actor("santiagomv/linkedin-jobs").call(run_input=run_input)
jobs = list(client.dataset(run["defaultDatasetId"]).iterate_items())

fields = ["postedAt", "title", "company", "location", "salaryMin", "salaryMax",
          "salaryCurrency", "employmentType", "seniorityLevel", "applicants", "url"]
path = "linkedin_jobs.csv"
new_file = not os.path.exists(path)
with open(path, "a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    if new_file:
        writer.writeheader()
    writer.writerows(jobs)

print(f"{len(jobs)} new jobs added to {path}")
