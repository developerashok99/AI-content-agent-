# AI Content Agent — Nightly Gaming Reel Script Generator

Every night, this pipeline:
1. Scrapes the latest gaming news from GameSpot, GameRant, PC Gamer, and PCGamesN.
2. Skips anything already seen on a previous run (`state/seen_articles.json`).
3. Asks Groq's LLM to pick the single most "trending / high engagement potential" gaming story for an audience of 19-30 year old gamers in India, the US, and Japan.
4. Asks Groq to write a ~30-45 second Instagram Reels script for that story (hook, beats, outro, caption, hashtags).
5. Sends the script straight to your Telegram.

You then manually film/edit/post — this agent's job stops at the script.

## Why these 4 sources
IGN and WCCFTech were dropped: WCCFTech's Cloudflare protection blocks scraping outright, and both sites' `robots.txt` explicitly prohibit automated/commercial scraping. GameSpot, GameRant, PC Gamer, and PCGamesN all have clean RSS feeds and permissive `robots.txt` for general crawling. If you want a source added back, re-check its `robots.txt` first.

## One-time setup

### 1. Groq API key (free)
Sign up at [console.groq.com](https://console.groq.com), create an API key. Check [console.groq.com/docs/models](https://console.groq.com/docs/models) for the current best free-tier model — the default here is `llama-3.3-70b-versatile`, override it by setting `GROQ_MODEL` if that's been deprecated.

### 2. Telegram bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, follow the prompts. You'll get a **bot token**.
2. Send any message to your new bot (search for it by the username you gave it).
3. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser — find `"chat":{"id": ...}` in the response. That number is your **chat ID**.

### 3. Local test run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
set -a && source .env && set +a
python -m src.pipeline
```
Check your Telegram for the script. Re-running immediately after should report "No new articles tonight" since everything just got marked seen — that's expected.

### 4. Push to GitHub + schedule the nightly run
```bash
git init
git add .
git commit -m "Initial gaming Reel script agent"
gh repo create <your-repo-name> --private --source=. --push
```
Then in the repo on GitHub: **Settings → Secrets and variables → Actions → New repository secret**, add:
- `GROQ_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`

The workflow in `.github/workflows/nightly.yml` runs at 21:30 UTC (~03:00 IST) daily, and can also be triggered manually from the Actions tab (`Run workflow`) to test it in CI before waiting for the schedule.

## Repo layout
- `src/scrapers/` — one module per source, each exposing `fetch()` and (where the RSS feed is a teaser only) `fetch_body(url)`
- `src/ranker.py` — Groq call that picks tonight's story
- `src/scriptwriter.py` — Groq call that writes the Reel script
- `src/telegram.py` — delivers the finished script
- `src/state.py` — dedup store, read/written from `state/seen_articles.json`
- `src/pipeline.py` — orchestrates the whole run, entry point for both local runs and the GitHub Action

## Adjusting the output
- Change tone/length/structure: edit `SCRIPTWRITER_SYSTEM_PROMPT` in `src/scriptwriter.py`.
- Change what counts as "trending": edit `RANKER_SYSTEM_PROMPT` in `src/ranker.py`.
- Change the schedule: edit the `cron` line in `.github/workflows/nightly.yml` ([crontab.guru](https://crontab.guru) helps).
- Add a source: create `src/scrapers/<name>.py` following an existing scraper's shape, register it in `SCRAPER_MODULES` and the `scrape_all()`/`run()` loops in `src/pipeline.py` — but check that site's `robots.txt` for commercial-scraping restrictions first.
