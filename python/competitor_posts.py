"""Track competitors' LinkedIn company posts. Run daily; only new posts come back.

pip install apify-client
APIFY_TOKEN=... python competitor_posts.py
"""
import os

from apify_client import ApifyClient

client = ApifyClient(os.environ["APIFY_TOKEN"])

run = client.actor("santiagomv/linkedin-company-posts").call(run_input={
    "companies": ["stripe", "https://www.linkedin.com/company/posthog"],
    "maxPostsPerCompany": 30,
    "onlyNewPosts": True,
    "stateStoreName": "competitor-posts-seen",
})

for post in client.dataset(run["defaultDatasetId"]).iterate_items():
    kind = "repost" if post.get("isRepost") else "post"
    text = (post.get("text") or "").replace("\n", " ")[:120]
    print(f"[{post['companySlug']}] {kind} {post.get('publishedAt') or ''} likes={post.get('likes')} {text}")
    print(f"    {post['url']}")
