"""Real Chromium smoke test for Streamlit, screenshot, and synthetic exports."""
from __future__ import annotations

import csv
import io
import json
import re
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright


def main() -> None:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": 1440, "height": 950},
            device_scale_factor=1,
            accept_downloads=True,
        )
        page.goto("http://127.0.0.1:8501", wait_until="domcontentloaded", timeout=30000)
        page.get_by_role("button", name="Load synthetic demo (offline)").click()
        page.get_by_text("SYNTHETIC EXAMPLE", exact=False).first.wait_for(timeout=30000)

        screenshot = Path("docs/images/streamlit-demo.png")
        screenshot.parent.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(screenshot), full_page=True, animations="disabled")
        print(f"Real Streamlit screenshot captured: {screenshot}")

        page.get_by_role("tab", name="Export / Methodology").click()
        with tempfile.TemporaryDirectory() as folder:
            with page.expect_download() as event:
                page.get_by_role("button", name=re.compile("Download JSON")).click()
            json_file = Path(folder) / "export.json"
            event.value.save_as(str(json_file))
            payload = json.loads(json_file.read_text(encoding="utf-8"))
            assert payload["domain"] == "example.com" and payload.get("demo") is True

            with page.expect_download() as event:
                page.get_by_role("button", name=re.compile("Download CSV")).click()
            csv_file = Path(folder) / "export.csv"
            event.value.save_as(str(csv_file))
            with csv_file.open(encoding="utf-8-sig", newline="") as fp:
                rows = list(csv.DictReader(fp))
            assert rows and {row["source"] for row in rows} == {"rdap", "dns", "cert"}

        print("Actual browser JSON download: PASS")
        print("Actual browser CSV download: PASS")
        browser.close()


if __name__ == "__main__":
    main()
