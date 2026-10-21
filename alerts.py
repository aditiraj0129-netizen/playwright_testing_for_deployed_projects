"""Sends a short alert on Telegram and/or email when a site has problems.

Both are optional. An alert is only sent if its settings are filled in
(as environment variables locally, or as GitHub Secrets online).

Telegram needs:  TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
Email needs:     EMAIL_USER, EMAIL_APP_PASSWORD, EMAIL_TO
"""
import json
import os
import smtplib
import urllib.parse
import urllib.request
from email.message import EmailMessage


def build_message(results, report_url=""):
    bad_sites = [r for r in results if not all(c["ok"] for c in r["checks"])]
    if not bad_sites:
        return None

    lines = [f"SiteWatch: {len(bad_sites)} site(s) need attention", ""]
    for r in bad_sites:
        lines.append(f"- {r['name']} ({r['url']})")
        for c in r["checks"]:
            if not c["ok"]:
                lines.append(f"    x {c['check']}: {c['detail'][:120]}")
        lines.append("")
    if report_url:
        lines.append(f"Full report: {report_url}")
    return "\n".join(lines)


def send_telegram(text):
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat_id):
        return "Telegram: skipped (not set up)"

    data = urllib.parse.urlencode({"chat_id": chat_id, "text": text[:4000]}).encode()
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        with urllib.request.urlopen(url, data=data, timeout=15) as resp:
            ok = json.loads(resp.read()).get("ok")
        return "Telegram: sent" if ok else "Telegram: failed"
    except Exception as e:
        return f"Telegram: failed ({e})"


def send_email(text):
    user = os.getenv("EMAIL_USER")
    password = os.getenv("EMAIL_APP_PASSWORD")
    to = os.getenv("EMAIL_TO")
    if not (user and password and to):
        return "Email: skipped (not set up)"

    msg = EmailMessage()
    msg["Subject"] = text.splitlines()[0]
    msg["From"] = user
    msg["To"] = to
    msg.set_content(text)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=20) as smtp:
            smtp.login(user, password)
            smtp.send_message(msg)
        return "Email: sent"
    except Exception as e:
        return f"Email: failed ({e})"


def send_alerts(results):
    text = build_message(results, os.getenv("REPORT_URL", ""))
    if text is None:
        print("All sites healthy. No alert sent.")
        return
    print(send_telegram(text))
    print(send_email(text))
