"""Search Workday careers sites by keyword and filter, and export jobs with salary to CSV.

Works with any *.myworkdayjobs.com careers site. Filters use the names shown in the
site's own filter menu (e.g. "Remote", "United States", "Engineering"). Each run saves
every filter value a site offers to AVAILABLE_FILTERS in the run's key-value store.

pip install apify-client
APIFY_TOKEN=... python workday_jobs_salary.py
"""
import csv
import os

from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])

run_input = {
    "sites": [
        "https://nvidia.wd5.myworkdayjobs.com/NVIDIAExternalCareerSite",
        "https://adobe.wd5.myworkdayjobs.com/external_experienced",
        "https://salesforce.wd12.myworkdayjobs.com/External_Career_Site",
    ],
    "searchQueries": ["machine learning", "data engineer"],
    # Filter names differ per site (NVIDIA: "Remote"; Adobe: "Remote California"), so add
    # "filters" per site after checking AVAILABLE_FILTERS from a first run.
    "excludeTitleKeywords": ["intern"],
    "postedWithinDays": 14,
    "descriptionFormat": "none",
}

run = client.actor("santiagomv/workday-jobs").call(run_input=run_input)
fields = ["company", "title", "location", "country", "postedAt", "salaryMin", "salaryMax", "salaryCurrency", "salaryPeriod", "url"]
with open("workday_jobs.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for job in client.dataset(run["defaultDatasetId"]).iterate_items():
        writer.writerow(job)
print("Saved workday_jobs.csv")
