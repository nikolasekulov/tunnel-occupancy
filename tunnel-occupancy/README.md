# Tunnel Occupancy Dashboard

Independent dashboard for NonStop Gym Lausanne Tunnel. A GitHub Actions collector runs every five minutes; Supabase stores actual readings; GitHub Pages serves seven weekday overlays. The browser never pretends to have fetched live data if the database is empty or stale.

## Setup (GitHub + Supabase)

1. Create a free Supabase project at https://supabase.com/dashboard. Open **SQL Editor**, paste `supabase/schema.sql`, and run it.
2. In Supabase **Project settings > API keys**, locate the project URL, publishable/anon key, and **service_role/secret** key. Keep the service key secret. Only the publishable/anon key belongs in the public website.
3. Edit `site/config.js` to set the Supabase URL and anon/publishable key. (For new `sb_publishable_` keys, Supabase REST supports the `apikey` header. If authorization using that key fails, use the project legacy anon JWT key.)
4. Create a **public** GitHub repository, upload all files (including `.github`), and set its default branch to `main`. A public repo allows GitHub Pages free hosting; your history will be readable by anyone who knows the URL.
5. In GitHub repo **Settings > Secrets and variables > Actions**, create repository secrets `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`. **Never** put the service role key in `site/config.js` or commit it.
6. In **Settings > Pages**, set Build and deployment source to **GitHub Actions**. Run workflow **Deploy dashboard** once if necessary. Your public URL will be `https://YOUR_USERNAME.github.io/YOUR_REPO/`.
7. In **Actions > Capture Tunnel occupancy**, choose **Run workflow** and check the log. If the live reading couldn't be extracted, download the `collector-diagnostics` artifact. Then adjust `collector/scrape.py` for the page's actual rendered markup or network response. Do **not** start trusting collected results until you compare the reading with the official page at the same time.
8. After validating the first reading, scheduled checks run every five minutes **approximately**. GitHub Actions schedule can be delayed or skipped under load; network and source issues can cause gaps. Database preserves prior readings. For tighter scheduling, use an always-on worker or managed cron.

## Limits

- Source site may require region selection, JS rendering, and may change its implementation; extractor has **not been live-tested** in the authoring environment. It saves readings only if it can match one unambiguous percentage to Tunnel.
- The collector does **not** use the website's *average occupancy* chart and cannot reconstruct historical measurements from before activation.
- Supabase free-tier projects may pause when inactive, and GitHub's free usage, schedules and Pages terms may change. Monitor service usage. Chromium installation on each scheduled GitHub Actions run consumes significant runner minutes and may exceed free quotas; using a direct API endpoint discovered from diagnostic captures would be much cheaper.
- The dashboard queries up to 105,000 samples; for years of storage, add a server-side date-range filter and pagination.
- Review the source website's terms and robots/access expectations before enabling persistent scraping.

## Run collector locally

```bash
pip install -r collector/requirements.txt
python -m playwright install chromium
python collector/scrape.py --dry-run
```

If detection fails, inspect `collector-diagnostic.json` and `collector-diagnostic.png`. If it succeeds, set `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY` to save the observation.
