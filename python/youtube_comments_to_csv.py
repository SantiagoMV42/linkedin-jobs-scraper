"""Export YouTube comments (newest first) to a CSV, e.g. for sentiment analysis or picking a giveaway winner.

pip install apify-client
APIFY_TOKEN=... python youtube_comments_to_csv.py https://www.youtube.com/watch?v=aircAruvnKk
"""
import csv
import os
import sys

from apify_client import ApifyClient

videos = sys.argv[1:] or ["https://www.youtube.com/watch?v=aircAruvnKk"]
client = ApifyClient(os.environ["APIFY_TOKEN"])
run = client.actor("santiagomv/youtube-comments").call(run_input={
    "videos": videos,
    "maxComments": 500,
    "sortBy": "newest",
})

fields = ["videoTitle", "authorName", "text", "likeCount", "replyCount", "publishedAtApprox", "commentUrl"]
with open("comments.csv", "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    rows = list(client.dataset(run["defaultDatasetId"]).iterate_items())
    writer.writerows(rows)
print(f"comments.csv: {len(rows)} comments")
