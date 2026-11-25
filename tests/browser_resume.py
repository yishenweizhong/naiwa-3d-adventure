"""Reproduce restoration with a real third-level save made through UI."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os
root=Path(__file__).resolve().parents[1]
fixture=(root/"tests/fixtures/legacy-v2-won.json").read_text()
out=root/"验收/续玩"; out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
    b=p.chromium.launch(headless=True); c=b.new_context(viewport={"width":1280,"height":800})
    c.add_init_script(f"if(!localStorage.getItem('naiwa.campaign.v3')) localStorage.setItem('naiwa.campaign.v2',{json.dumps(fixture)})")
    page=c.new_page(); page.goto(os.environ.get("NAIWA_URL","http://localhost:4188"))
    page.wait_for_load_state("networkidle")
    page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
    page.locator("#start-level3").click(); page.locator("#begin-level").click()
    page.wait_for_function("window.__naiwa.snapshot().windWalls.some(w=>w.windup>.5)")
    page.locator("#pause").click()
    saved=json.loads(page.evaluate("localStorage.getItem('naiwa.campaign.v3')"))
    page.reload(); page.wait_for_load_state("networkidle")
    page.locator("#resume").click()
    restored=page.evaluate("window.__naiwa.snapshot()")
    report={"saved":saved,"restored":restored}
    (out/"续玩对比.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    for key in ["phase","level","wave","elapsed","hero","windWalls"]:
        print(key, "SAVED", saved[key], "RESTORED",restored[key],flush=True)
        assert saved[key]==restored[key],key
    c.close(); b.close()
