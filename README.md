# SiteWatch

A daily website health checker built with Python and Playwright.

Every morning it opens your websites in a real browser, checks they work,
takes desktop and mobile screenshots, publishes a simple report, and sends
you a Telegram or email alert if something breaks.

## What it checks

1. Page opens without errors
2. Loads in under 5 seconds
3. Important text is visible
4. No broken links
5. No JavaScript errors
6. Fits on a mobile screen
7. Optional: a full user journey (like login)

## Run it on your laptop

**Mac / Linux / Git Bash:**
```bash
bash run.sh
```

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
python -m playwright install chromium
python sitewatch.py
```

Then open `site/index.html`.

## Add your own sites

Edit `sites.json`. Each site needs a `name` and `url`. `must_contain` and
`flow` are optional.

## Alerts (optional)

Alerts are sent only when a site fails a check.

**Telegram**
1. On Telegram, message `@BotFather`, send `/newbot`, and copy the bot token.
2. Send any message to your new bot.
3. Open `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates` and copy the
   number after `"chat":{"id":`.

**Email (Gmail)**
1. Turn on 2-Step Verification on your Google account.
2. Create an App Password (Google Account > Security > App passwords).
3. Use your Gmail as `EMAIL_USER`, the 16-letter app password as
   `EMAIL_APP_PASSWORD`, and where to send alerts as `EMAIL_TO`.

**Locally:** copy `.env.example` to `.env` and fill it in.
**On GitHub:** add the same names under Settings > Secrets and variables > Actions.

## Put it online (free)

1. Push this folder to a public GitHub repo.
2. Settings > Pages > Source: **GitHub Actions**.
3. Actions > SiteWatch > **Run workflow**.
4. Your report goes live at `https://<username>.github.io/<repo-name>/`
   and updates every day at 8 AM IST.

## Built with

Python, Playwright, GitHub Actions, GitHub Pages.
