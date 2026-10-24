# YouTube playlist or channel → transcripts or comments

Get the transcripts, or the comments, of the videos in a YouTube playlist or channel with one Python script and no dependencies.

> **Disclosure:** I built and sell both actors used here, [YouTube Transcript Scraper](https://apify.com/santiagomv/youtube-transcripts) and [YouTube Comments Scraper](https://apify.com/santiagomv/youtube-comments). They run on Apify and you pay per row saved.

## Cost

| Actor | Price | Free |
|---|---|---|
| YouTube Transcript Scraper | $4 / 1,000 transcripts (one per video) | Listing playlist/channel videos; videos without captions; failed links |
| YouTube Comments Scraper | $0.50 / 1,000 comments (replies too) | Listing playlist/channel videos; videos with comments off; failed links |

The script sends `--max-cost` (default **$0.10**) as the run's `maxTotalChargeUsd` query parameter, and Apify stops the run when charges reach it. With the defaults (20 videos, 50 comments each), transcripts cost at most $0.08. Comments could reach 1,000 rows ($0.50), but the $0.10 cap stops the run at about 200 comments. Raise `--max-cost` to get more.

## Run it

1. Create an Apify account and copy your API token from [Console → Settings → API & Integrations](https://console.apify.com/settings/integrations).
2. Run:

```bash
export APIFY_TOKEN=your_token

# Transcripts of up to 20 videos in a playlist
python3 channel_to_jsonl.py transcripts "https://www.youtube.com/playlist?list=UU_x5XG1OV2P6uZZ5FSM9Ttw"

# Comments from up to 10 videos on a channel's Videos tab, 50 each, capped at $0.10
python3 channel_to_jsonl.py comments "https://www.youtube.com/@GoogleDevelopers" --max-videos 10
```

Each run writes `transcripts.jsonl` or `comments.jsonl`, one JSON object per line. Options: `--max-videos` (1–10000), `--max-pages` (1–100), `--max-comments` (0 = unlimited), `--max-cost` (USD, default 0.10), `--language`, `--out`.

The same call with cURL. The `maxTotalChargeUsd` query parameter is what enforces the budget:

```bash
curl -X POST "https://api.apify.com/v2/acts/santiagomv~youtube-transcripts/run-sync-get-dataset-items?maxTotalChargeUsd=0.10" \
  -H "Authorization: Bearer $APIFY_TOKEN" -H 'Content-Type: application/json' \
  -d '{"sources":["https://www.youtube.com/playlist?list=UU_x5XG1OV2P6uZZ5FSM9Ttw"],"maxVideos":20,"maxSourcePages":3}'
```

## What it accepts

- **Playlists**: `youtube.com/playlist?list=…`.
- **Channels**: `youtube.com/@handle` (or `/@handle/videos`) and `youtube.com/channel/UC…`, Videos tab only (no Shorts or live tabs). Handle lookup is free and gets up to 4 tries; if it fails, the channel shows up in `FAILURES`, so paste its `/channel/UC…` link instead. Old `/c/` and `/user/` links aren't supported.
- Single videos go in the actors' `videos` field instead; see each actor's page.

Two caps bound every run: `maxVideos` (unique videos in total) and `maxSourcePages` (YouTube listing pages read in total; a playlist page holds up to about 100 videos, a channel page about 30). The actors read what YouTube lists; they don't promise every video of a large channel or any particular order.

## What you won't see in the output

The synchronous endpoint returns dataset rows only. Videos that failed (no captions, comments off, private or removed) and playlists or channels that couldn't be read produce **no rows**. To see why, open the run in [Apify Console](https://console.apify.com/actors/runs) → Storage → Key-value store:

- `FAILURES`: each failed video, link, playlist or channel, with the error.
- `SOURCE_EXPANSION`: per playlist or channel, the pages read, videos added, whether a cap stopped it, and any notice from YouTube.

The endpoint waits at most 5 minutes. If it times out (HTTP 408) the run keeps going in Apify; collect its dataset from the Console, or lower `--max-videos`.

## Troubleshooting

- **`0 rows`**: check the run's key-value store. `FAILURES` gives the recorded reason for each failed video, which may be missing captions, comments off, or blocking and temporary fetch errors. `SOURCE_EXPANSION` shows whether each playlist or channel was read and how many videos it added; if it added none, check that it's a playlist, `@handle` or `/channel/UC…` URL.
- **`HTTP 408`**: the endpoint stopped waiting; this alone doesn't tell you how the run went. Check the run's status in [Apify Console](https://console.apify.com/actors/runs) and collect its dataset when it's ready. Starting it again may incur another charge.
- **Comments from fewer videos than `--max-videos`**: the `--max-cost` cap probably stopped the run (about 200 comments at $0.10), or some videos have comments off (see `FAILURES`). Raise `--max-cost` or lower `--max-comments`.

## Before you use it

Automated access may be against YouTube's Terms of Service, and YouTube may block or rate-limit the IP addresses or accounts involved. Transcripts are their creators' copyrighted work, and comments are personal data of their authors. You are responsible for how you use these actors and the data, including copyright, privacy law (such as GDPR) and YouTube's terms. Not affiliated with, endorsed by or sponsored by YouTube or Google LLC.
