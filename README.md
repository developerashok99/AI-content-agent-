# AI Content Agent — Nightly Gaming Reel Script Generator

Every night, this pipeline:
1. Checks Telegram for replies to past scripts (feedback) and files them against that night's history entry.
2. Scrapes the latest gaming news from GameSpot, GameRant, PC Gamer, and PCGamesN.
3. Skips anything already seen on a previous run (`state/seen_articles.json`).
4. Pulls today's trending gaming videos on YouTube for India, the US, and Japan — a real signal of what the audience is actually watching, not just what a news site published.
5. Asks Groq's LLM to pick the single most "trending / high engagement potential" gaming story, using the news articles + trend signals + recently-covered topics (to avoid repeats) + past feedback as context.
6. Asks Groq to write **2 different script variants** (different hook/angle) for a ~30-45 second Instagram Reels video — hook, beats, outro, filming/visual notes, caption, hashtags.
7. Sends a lead message (topic + reasoning + trend signals used) and one message per variant straight to your Telegram.
8. Records the whole night — topic, variants, trend context, delivery, any feedback — to `docs/data/history.json`, which powers a status dashboard.
9. If anything fails at any step, sends a distinct "⚠️ run failed" Telegram message and still logs a `failed` entry to history, instead of failing silently.

You then manually film/edit/post — this agent's job stops at the script.

## Dashboard
`docs/index.html` is a single self-contained static page (no build step) that reads `docs/data/history.json` and shows: last run time/result, next scheduled run (computed from the cron schedule), and a browsable list of every past night — chosen story, reasoning, trend signals used, both script variants, filming notes, and any feedback you replied with. Hosted free via GitHub Pages (see setup below) — this requires the repo to be **public** (GitHub Pages on a private repo needs a paid GitHub plan). Nothing sensitive lives in the repo itself; all credentials are GitHub Actions Secrets, never committed.

## Why these 4 news sources
IGN and WCCFTech were dropped: WCCFTech's Cloudflare protection blocks scraping outright, and both sites' `robots.txt` explicitly prohibit automated/commercial scraping. GameSpot, GameRant, PC Gamer, and PCGamesN all have clean RSS feeds and permissive `robots.txt` for general crawling. If you want a source added back, re-check its `robots.txt` first.

## Feedback loop
Reply directly (Telegram "reply", not a new message) to any script message the bot sent you — e.g. "this one flopped" or "variant B did really well, more like this." On the next nightly run, the pipeline polls for new replies, matches them to the script they replied to via Telegram's `reply_to_message`, and feeds a summary of recent feedback into the next ranking prompt so it can lean toward what's worked and away from what hasn't. Anyone on the `TELEGRAM_CHAT_IDS` list can give feedback this way — matching works per-person since each recipient's copy of a script is tracked separately.

## One-time setup

### 1. Groq API key (free)
Sign up at [console.groq.com](https://console.groq.com), create an API key. Check [console.groq.com/docs/models](https://console.groq.com/docs/models) for the current best free-tier model — the default here is `llama-3.3-70b-versatile`, override it by setting `GROQ_MODEL` if that's been deprecated.

### 2. Telegram bot
1. Message [@BotFather](https://t.me/BotFather) on Telegram, send `/newbot`, follow the prompts. You'll get a **bot token**.
2. Have everyone who should receive the nightly script message the bot at least once (bots can't message someone who hasn't started a conversation with them first).
3. Visit `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` in a browser — each message shows a `"chat":{"id": ...}` — collect one chat_id per recipient. **Double-check each name/username you don't recognize** — the bot's username is public, so anyone who finds it can message it and show up here too; only add chat_ids you've confirmed belong to someone you actually want receiving these scripts.
4. Set `TELEGRAM_CHAT_IDS` to a comma-separated list of all the chat_ids you want to include (e.g. `976137998,906438317`). To add or remove a recipient later, just edit this value — no code changes needed.

### 3. YouTube Data API key (free)
1. Go to the [Google Cloud Console](https://console.cloud.google.com/), create a project (or use an existing one).
2. **APIs & Services → Library** → search "YouTube Data API v3" → Enable.
3. **APIs & Services → Credentials → Create Credentials → API key**. Copy it.
4. Free quota is 10,000 units/day; this pipeline uses about 3/night (one call per region), so there's no realistic risk of hitting the limit.

### 4. Local test run
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in GROQ_API_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS, YOUTUBE_API_KEY
set -a && source .env && set +a
python -m src.pipeline
```
Check your Telegram for the lead message + 2 script variants, and check `docs/data/history.json` for the new entry. Re-running immediately after should report "No new articles tonight" since everything just got marked seen — that's expected.

### 5. Push to GitHub + schedule the nightly run
```bash
git init
git add .
git commit -m "Initial gaming Reel script agent"
gh repo create <your-repo-name> --public --source=. --push
```
Then in the repo on GitHub: **Settings → Secrets and variables → Actions → New repository secret**, add:
- `GROQ_API_KEY`
- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_IDS`
- `YOUTUBE_API_KEY`

The workflow in `.github/workflows/nightly.yml` runs at 21:30 UTC (~03:00 IST) daily, and can also be triggered manually from the Actions tab (`Run workflow`) to test it in CI before waiting for the schedule.

### 6. Enable the dashboard
**Settings → Pages → Source: Deploy from a branch → Branch: `main`, folder: `/docs` → Save.** GitHub will give you a URL like `https://<username>.github.io/<repo>/` — that's your status dashboard.

## Repo layout
- `src/scrapers/` — one module per news source, each exposing `fetch()` and (where the RSS feed is a teaser only) `fetch_body(url)`
- `src/trends.py` — YouTube Data API call for today's trending gaming videos per region
- `src/ranker.py` — Groq call that picks tonight's story, using articles + trends + recent-topics + feedback as context
- `src/scriptwriter.py` — Groq call that writes the 2 Reel script variants
- `src/telegram.py` — sends messages to every recipient in `TELEGRAM_CHAT_IDS` and polls `getUpdates` for replies
- `src/feedback.py` — matches Telegram replies back to the script they responded to
- `src/history.py` — read/write/prune `docs/data/history.json`, the dashboard's data source
- `src/state.py` — dedup store, read/written from `state/seen_articles.json`
- `src/pipeline.py` — orchestrates the whole run, entry point for both local runs and the GitHub Action
- `docs/index.html` — the status dashboard (GitHub Pages serves this folder)

## Adjusting the output
- Change tone/length/structure/number of variants: edit `SCRIPTWRITER_SYSTEM_PROMPT` / `NUM_VARIANTS` in `src/scriptwriter.py`.
- Change what counts as "trending": edit `RANKER_SYSTEM_PROMPT` in `src/ranker.py`.
- Change the schedule: edit the `cron` line in `.github/workflows/nightly.yml` ([crontab.guru](https://crontab.guru) helps) — also update `CRON_HOUR_UTC`/`CRON_MINUTE_UTC` at the top of `docs/index.html`'s script so the dashboard's "next run" countdown stays accurate.
- Add a news source: create `src/scrapers/<name>.py` following an existing scraper's shape, register it in `SCRAPER_MODULES` and the `scrape_all()` loop in `src/pipeline.py` — but check that site's `robots.txt` for commercial-scraping restrictions first.
- How much history to keep: `RETENTION_DAYS` in `src/history.py` (dashboard) and `src/state.py` (dedup window).
