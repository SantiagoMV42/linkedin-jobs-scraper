"""Transcripts or comments for a YouTube playlist or channel, saved as JSON Lines.

Standard library only (Python 3.8+). Uses Apify's synchronous run endpoint, so keep runs
small: it waits at most 5 minutes. --max-cost is sent as the run's maxTotalChargeUsd, so
Apify stops the run once it reaches that many USD of charges.

APIFY_TOKEN=... python channel_to_jsonl.py transcripts https://www.youtube.com/playlist?list=UU...
APIFY_TOKEN=... python channel_to_jsonl.py comments https://www.youtube.com/@GoogleDevelopers --max-videos 10
"""
import argparse
import json
import math
import os
from pathlib import Path
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request

ACTORS = {"transcripts": "santiagomv~youtube-transcripts", "comments": "santiagomv~youtube-comments"}


def int_in(low, high=None):
    def check(text):
        value = int(text)
        if value < low or (high is not None and value > high):
            raise argparse.ArgumentTypeError(f"must be {low}..{high}" if high else f"must be >= {low}")
        return value
    return check


def positive_usd(text):
    value = float(text)
    if not math.isfinite(value) or value <= 0:
        raise argparse.ArgumentTypeError("must be a positive number of USD")
    return value


parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
parser.add_argument("mode", choices=ACTORS)
parser.add_argument("source", help="playlist, youtube.com/@handle or youtube.com/channel/UC... URL")
parser.add_argument("--max-videos", type=int_in(1, 10000), default=20, help="videos in total, 1-10000 (default 20)")
parser.add_argument("--max-pages", type=int_in(1, 100), default=3, help="playlist/channel pages read, 1-100 (default 3)")
parser.add_argument("--max-comments", type=int_in(0), default=50, help="comments per video, comments mode; 0 = unlimited (default 50)")
parser.add_argument("--max-cost", type=positive_usd, default=0.10, help="run cost cap in USD, enforced by Apify (default 0.10)")
parser.add_argument("--language", default="en", help="transcripts mode (default en)")
parser.add_argument("--out", help="output file (default <mode>.jsonl)")
args = parser.parse_args()

run_input = {"sources": [args.source], "maxVideos": args.max_videos, "maxSourcePages": args.max_pages}
if args.mode == "comments":
    run_input["maxComments"] = args.max_comments
else:
    run_input["language"] = args.language

query = urllib.parse.urlencode({"maxTotalChargeUsd": args.max_cost})
url = f"https://api.apify.com/v2/acts/{ACTORS[args.mode]}/run-sync-get-dataset-items?{query}"
request = urllib.request.Request(
    url,
    data=json.dumps(run_input).encode(),
    headers={"Authorization": f"Bearer {os.environ['APIFY_TOKEN']}", "Content-Type": "application/json"},
)
try:
    with urllib.request.urlopen(request, timeout=330) as response:
        items = json.load(response)
except urllib.error.HTTPError as e:
    # 408 = the run is still going after 5 minutes; lower --max-videos or fetch its dataset in Apify Console.
    sys.exit(f"HTTP {e.code}: {e.read().decode(errors='replace')[:500]}")

out = args.out or f"{args.mode}.jsonl"
if not isinstance(items, list) or any(
    not isinstance(item, dict) or not isinstance(item.get("videoId"), str)
    or not item["videoId"] for item in items
):
    raise ValueError

output_path = Path(out)
temporary_path = None
try:
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", dir=output_path.parent,
                                     prefix=".youtube-", suffix=".jsonl", delete=False) as f:
        temporary_path = Path(f.name)
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())
    os.replace(temporary_path, output_path)
finally:
    if temporary_path is not None:
        temporary_path.unlink(missing_ok=True)

videos = {item["videoId"] for item in items}
print(f"{len(items)} rows from {len(videos)} videos -> {out}")
print("Skipped videos and playlist/channel errors aren't rows: see FAILURES and SOURCE_EXPANSION in the run's key-value store.")
