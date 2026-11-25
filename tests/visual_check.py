from playwright.sync_api import sync_playwright
from pathlib import Path
import json, os

OUT=Path(os.environ.get("NAIWA_EVIDENCE","/tmp/naiwa-cute-visual"))
OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get("NAIWA_URL","http://localhost:4190")
with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for name,size in [("电脑",{"width":1280,"height":800}),("手机竖屏",{"width":390,"height":844}),("手机横屏",{"width":844,"height":390})]:
        page=browser.new_page(viewport=size,has_touch=name!="电脑")
        page.goto(BASE); page.wait_for_load_state("networkidle")
        page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
        page.screenshot(path=str(OUT/f"{name}_首页.png"),full_page=True)
        boxes={id:page.locator("#"+id).bounding_box() for id in ["start","easy","normal","start-level2","start-level3"]}
        print(name,json.dumps(boxes),flush=True)
        page.locator("#start").click()
        page.wait_for_function("window.__naiwa.snapshot().phase==='playing'")
        page.keyboard.down("KeyJ"); page.wait_for_timeout(1200); page.keyboard.up("KeyJ")
        page.screenshot(path=str(OUT/f"{name}_战斗.png"),full_page=True)
        page.close()
    browser.close()
