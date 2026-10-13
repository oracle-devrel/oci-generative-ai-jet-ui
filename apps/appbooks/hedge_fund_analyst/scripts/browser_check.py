"""Real Chromium checks against localhost, including UI streaming and persona isolation."""
import json
import os
from pathlib import Path

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent
BASE = os.environ.get("HF_BASE_URL", "http://127.0.0.1:8061")
with sync_playwright() as p:
    browser = p.chromium.launch(
        headless=True, executable_path=os.environ.get("HF_BROWSER_EXECUTABLE") or None
    )
    page = browser.new_page(viewport={"width": 1440, "height": 1050})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(BASE)
    page.wait_for_function(
        "document.querySelector('#connection').textContent.includes('connected')", timeout=30000
    )
    default = page.evaluate("fetch('/api/health').then(r=>r.json()).then(h=>h.default_model)")
    assert page.locator("#model").input_value() == default, (
        page.locator("#model").input_value(),
        default,
    )
    assert (
        "graph isolation" in page.locator("#components").inner_text()
        and "verified" in page.locator("#components").inner_text()
    )
    assert (
        page.locator("#reset-memory").is_visible()
        and page.locator("[data-new-session]").count() == 1
    )
    assert page.locator("#model option[value=privateai]").evaluate(
        "(el)=>el.disabled"
    ), page.locator("#model").inner_html()
    for view in ["graph", "vectors", "semantics", "memory", "sql", "golden", "tables"]:
        page.locator(f'[data-view="{view}"]').click()
        page.wait_for_function(
            "!document.querySelector('#data-content').textContent.includes('Reading Oracle')",
            timeout=60000,
        )
        assert not page.locator("#data-content .error").count(), (
            view,
            page.locator("#data-content").inner_text(),
        )
    page.locator('[data-view="tables"]').click()
    page.wait_for_timeout(300)
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(ROOT / "var/desktop.png"), full_page=True)
    page.set_viewport_size({"width": 390, "height": 844})
    page.evaluate("window.scrollTo(0,0)")
    page.screenshot(path=str(ROOT / "var/mobile.png"), full_page=True)
    assert page.evaluate("document.documentElement.scrollWidth<=window.innerWidth")
    page.set_viewport_size({"width": 1440, "height": 1050})
    page.locator("#question").fill("What's our net exposure to Acme group?")
    page.locator("#send").click()
    page.wait_for_function("document.querySelector('#send').disabled===false", timeout=300000)
    assert page.locator("#plane-chat .answer").count() == 1, page.locator("#status").inner_text()
    assert page.locator("#naive-chat .answer").count() == 1, page.locator("#status").inner_text()
    page.locator("#plane-chat summary").click()
    page.locator("#plane-chat .inspect-tabs button", has_text="Entities").click()
    assert "HF002CE18CF92C432A31" in page.locator("#plane-chat .inspect-panel").inner_text()
    page.locator("#plane-chat .inspect-tabs button", has_text="Audit").click()
    page.wait_for_timeout(1000)
    page.screenshot(path=str(ROOT / "var/comparison.png"), full_page=True)
    assert (
        page.locator("#latency-chart svg").count() == 1
        and page.locator("#latency-chart rect[data-tip]").count() == 2
    )
    assert page.locator("#accuracy-chart .col rect[data-tip]").count() == 1
    page.locator("#latency-chart rect[data-tip]").first.hover()
    assert page.locator(".tip").is_visible()
    # Two-step reset arms first and does not delete on a single click.
    page.locator("#reset-memory").click()
    assert "Confirm" in page.locator("#reset-memory").inner_text()
    page.locator("#persona").select_option("Markets")
    page.locator('[data-view="tables"]').click()
    page.wait_for_function(
        "document.querySelector('#data-content').textContent.includes('Markets')", timeout=30000
    )
    assert "Credit" not in page.locator("#data-content").inner_text()
    assert not errors, errors
    version = browser.version
    browser.close()
    (ROOT / "var/browser-report.json").write_text(
        json.dumps(
            {
                "passed": True,
                "browser": "Chromium " + version,
                "checks": [
                    "default model",
                    "graph isolation chip",
                    "chart tooltips",
                    "two-step memory reset",
                    "desktop/mobile rendering",
                    "no horizontal mobile overflow",
                    "all data surfaces",
                    "real streamed model answers",
                    "inspector and charts",
                    "Markets data isolation",
                ],
                "javascript_errors": errors,
            },
            indent=2,
        )
    )
    print("Browser end-to-end checks passed", flush=True)
