"""Enrich a list of companies with LinkedIn firmographics.

Input: companies.txt, one LinkedIn company URL or slug per line.
Output: companies_enriched.csv.

pip install apify-client
APIFY_TOKEN=... python enrich_companies.py
"""
import csv
import os

from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])

with open("companies.txt") as f:
    companies = [line.strip() for line in f if line.strip()]

run = client.actor("santiagomv/linkedin-company").call(run_input={
    "companies": companies,
    "includePosts": False,
    "includeSimilarPages": False,
})

fields = ["name", "website", "industry", "companySize", "employeesOnLinkedIn",
          "followers", "headquarters", "founded", "type", "url"]
with open("companies_enriched.csv", "w", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for item in client.dataset(run["defaultDatasetId"]).iterate_items():
        writer.writerow({k: item.get(k) if not isinstance(item.get(k), (dict, list)) else str(item.get(k)) for k in fields})

print("Saved companies_enriched.csv")
