"""Separate frozen WebGL pixels from independently fading HUD notifications."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os

OUT = Path(os.environ.get("NAIWA_EVIDENCE", "/tmp/naiwa-pause-capture"))
OUT.mkdir(parents=True, exist_ok=True)
STYLE = ".overlay,.hud,.boss-status,.guide,.wave-toast,.storm-note,.controls,#character-status{visibility:hidden!important}"
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page(viewport={"width":1280,"height":800})
    page.goto(os.environ.get("NAIWA_URL","http://localhost:4190"))
    page.wait_for_load_state("networkidle")
    page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
    page.locator("#start").click()
    page.wait_for_timeout(1000)
    page.locator("#pause").click()
    state = page.evaluate("window.__naiwa.snapshot()")
    canvas = page.locator("#game canvas")
    visible_before = canvas.screenshot(path=str(OUT/"界面_前.png"))
    pixels_before = canvas.screenshot(path=str(OUT/"场景_前.png"),style=STYLE)
    page.wait_for_timeout(700)
    visible_after = canvas.screenshot(path=str(OUT/"界面_后.png"))
    pixels_after = canvas.screenshot(path=str(OUT/"场景_后.png"),style=STYLE)
    result = {"state_equal":state==page.evaluate("window.__naiwa.snapshot()"),
              "scene_equal":pixels_before==pixels_after,
              "composited_ui_equal":visible_before==visible_after}
    (OUT/"暂停捕获核验.json").write_text(json.dumps(result,indent=2))
    print(json.dumps(result),flush=True)
    assert result["state_equal"] and result["scene_equal"]
    b.close()
