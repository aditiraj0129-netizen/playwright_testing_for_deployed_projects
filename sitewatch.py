"""SiteWatch: checks websites with Playwright and builds a simple health report."""
import datetime
import html
import json
import pathlib
import re
import time

from playwright.sync_api import sync_playwright

from alerts import send_alerts

OUT = pathlib.Path("site")          # this folder gets published as the website
SHOTS = OUT / "screenshots"
MAX_LINKS = 20                      # how many links to check per page
IST = datetime.timezone(datetime.timedelta(hours=5, minutes=30))


def slug(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ---------- Optional user-journey tests ----------
# Each one returns a short message if it works, or raises an error if it fails.
def saucedemo_login(page):
    page.goto("https://www.saucedemo.com")
    page.fill("#user-name", "standard_user")      # public demo login
    page.fill("#password", "secret_sauce")
    page.click("#login-button")
    page.wait_for_url("**/inventory.html", timeout=10000)
    return "Demo user can log in and reach the products page"


FLOWS = {"saucedemo_login": saucedemo_login}


# ---------- Checks ----------
def check_links(page):
    hrefs = page.eval_on_selector_all("a[href]", "els => els.map(e => e.href)")
    links = [h for h in dict.fromkeys(hrefs) if h.startswith("http")][:MAX_LINKS]
    broken = []
    for link in links:
        try:
            r = page.request.get(link, timeout=10000)
            if r.status >= 400:
                broken.append(f"{link} ({r.status})")
        except Exception:
            broken.append(f"{link} (no response)")
    return len(links), broken


def check_site(pw, browser, site):
    name, url = site["name"], site["url"]
    result = {"name": name, "url": url, "checks": [], "shots": []}

    def add(check, ok, detail=""):
        result["checks"].append({"check": check, "ok": bool(ok), "detail": detail})

    # 1) Desktop checks
    ctx = browser.new_context(viewport={"width": 1366, "height": 768})
    page = ctx.new_page()
    console_errors = []
    page.on("console", lambda m: console_errors.append(m.text) if m.type == "error" else None)
    page.on("pageerror", lambda err: console_errors.append(str(err)))  # uncaught JS crashes
    try:
        start = time.time()
        resp = page.goto(url, wait_until="load", timeout=30000)
        secs = round(time.time() - start, 2)
        status = resp.status if resp else "no response"
        add("Page opens", resp is not None and resp.ok, f"HTTP status {status}")
        add("Loads in under 5 seconds", secs < 5, f"Took {secs} seconds")

        # Give React / single-page apps time to finish drawing (up to 8 seconds)
        must = site.get("must_contain")
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        try:
            page.wait_for_function(
                "document.body && document.body.innerText.trim().split(/\\s+/).length >= 5",
                timeout=8000,
            )
            if must:
                page.wait_for_function(
                    "t => document.body.innerText.toLowerCase().includes(t)",
                    arg=must.lower(), timeout=8000,
                )
        except Exception:
            pass  # the checks below will report what's missing

        body = page.inner_text("body")
        words = len(body.split())
        add("Page shows content (not blank)", words >= 5, f"Found {words} words on the page")

        if must:
            add("Important text is visible", must.lower() in body.lower(), f'Looked for "{must}"')

        total, broken = check_links(page)
        detail = f"Checked {total} links"
        if broken:
            detail += ". Broken: " + ", ".join(broken[:5])
        add("No broken links", not broken, detail)

        add("No JavaScript errors", not console_errors,
            "; ".join(console_errors[:3]) or "Browser console is clean")

        shot = SHOTS / f"{slug(name)}-desktop.png"
        page.screenshot(path=shot)
        result["shots"].append(["Desktop", shot.relative_to(OUT).as_posix()])
    except Exception as e:
        add("Page opens", False, f"Could not open page: {str(e)[:150]}")
    finally:
        ctx.close()

    # 2) Mobile check
    device = dict(pw.devices["iPhone 13"])
    device.pop("default_browser_type", None)
    ctx = browser.new_context(**device)
    page = ctx.new_page()
    try:
        page.goto(url, wait_until="load", timeout=30000)
        try:
            page.wait_for_load_state("networkidle", timeout=8000)
        except Exception:
            pass
        overflow = page.evaluate("document.documentElement.scrollWidth > window.innerWidth + 1")
        add("Fits on mobile screen", not overflow, "Tested at iPhone 13 size")
        shot = SHOTS / f"{slug(name)}-mobile.png"
        page.screenshot(path=shot)
        result["shots"].append(["Mobile", shot.relative_to(OUT).as_posix()])
    except Exception as e:
        add("Fits on mobile screen", False, str(e)[:150])
    finally:
        ctx.close()

    # 3) Optional user journey
    flow = site.get("flow")
    if flow in FLOWS:
        ctx = browser.new_context()
        page = ctx.new_page()
        try:
            add("User journey works", True, FLOWS[flow](page))
        except Exception as e:
            add("User journey works", False, f"Failed: {str(e)[:150]}")
        finally:
            ctx.close()

    return result


# ---------- Report ----------
CSS = """
* { box-sizing: border-box; }
body { margin: 0; font-family: system-ui, sans-serif; background: #f5f6f8; color: #1d2330; }
main { max-width: 960px; margin: 0 auto; padding: 24px 16px; }
h1 { margin: 0 0 4px; }
h2 { font-size: 20px; }
.muted { color: #667085; }
.summary { display: flex; gap: 12px; flex-wrap: wrap; margin: 20px 0; }
.stat { background: #fff; border-radius: 10px; padding: 14px 18px; flex: 1; min-width: 150px; }
.stat b { display: block; font-size: 26px; }
.card { background: #fff; border-radius: 10px; padding: 18px; margin-bottom: 18px; }
.badge { padding: 3px 10px; border-radius: 99px; font-size: 13px; font-weight: 600; vertical-align: middle; }
.ok { background: #dcfae6; color: #067647; }
.bad { background: #fee4e2; color: #b42318; }
table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 14px; }
table { table-layout: fixed; }
td:first-child { width: 36px; }
td:nth-child(2) { width: 38%; }
td { padding: 8px 6px; border-top: 1px solid #eaecf0; vertical-align: top; word-break: break-word; }
.shots { display: flex; gap: 12px; flex-wrap: wrap; margin-top: 12px; }
figure { margin: 0; }
img { max-height: 220px; max-width: 100%; border: 1px solid #eaecf0; border-radius: 6px; }
figcaption { font-size: 12px; color: #667085; }
"""


def build_report(results):
    now = datetime.datetime.now(IST).strftime("%d %b %Y, %I:%M %p IST")
    total = sum(len(r["checks"]) for r in results)
    passed = sum(c["ok"] for r in results for c in r["checks"])
    healthy = sum(all(c["ok"] for c in r["checks"]) for r in results)

    cards = []
    for r in results:
        all_ok = all(c["ok"] for c in r["checks"])
        badge = ('<span class="badge ok">Healthy</span>' if all_ok
                 else '<span class="badge bad">Needs attention</span>')
        rows = "".join(
            f'<tr><td>{"✅" if c["ok"] else "❌"}</td>'
            f'<td>{html.escape(c["check"])}</td><td>{html.escape(c["detail"])}</td></tr>'
            for c in r["checks"]
        )
        shots = "".join(
            f'<figure><img src="{p}" alt="{label} screenshot"><figcaption>{label}</figcaption></figure>'
            for label, p in r["shots"]
        )
        cards.append(
            f'<section class="card"><h2>{html.escape(r["name"])} {badge}</h2>'
            f'<a class="muted" href="{html.escape(r["url"])}">{html.escape(r["url"])}</a>'
            f'<table>{rows}</table><div class="shots">{shots}</div></section>'
        )

    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SiteWatch Report</title><style>{CSS}</style></head>
<body><main>
<h1>SiteWatch Report</h1>
<p class="muted">Last checked: {now}</p>
<div class="summary">
  <div class="stat"><b>{healthy}/{len(results)}</b>Sites healthy</div>
  <div class="stat"><b>{passed}/{total}</b>Checks passed</div>
</div>
{''.join(cards)}
<p class="muted">Built with Python + Playwright. Runs daily on GitHub Actions.</p>
</main></body></html>"""

    (OUT / "index.html").write_text(page, encoding="utf-8")
    (OUT / "results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")


def main():
    SHOTS.mkdir(parents=True, exist_ok=True)
    sites = json.loads(pathlib.Path("sites.json").read_text(encoding="utf-8"))
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        results = [check_site(pw, browser, s) for s in sites]
        browser.close()
    build_report(results)
    for r in results:
        ok = sum(c["ok"] for c in r["checks"])
        print(f'{r["name"]}: {ok}/{len(r["checks"])} checks passed')
    print("Report saved to site/index.html")
    send_alerts(results)


if __name__ == "__main__":
    main()
