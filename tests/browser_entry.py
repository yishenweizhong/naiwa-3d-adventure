"""Public/local smoke test: new visitor, optional practice, actual battle and persistence."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os

BASE=os.environ.get("NAIWA_URL","http://localhost:4188")
OUT=Path(os.environ.get("NAIWA_EVIDENCE","/tmp/naiwa-entry-browser"))
OUT.mkdir(parents=True,exist_ok=True)
report={"url":BASE,"checks":[],"errors":[]}
def check(name,ok):
    assert ok,name
    report["checks"].append(name); print("PASS",name,flush=True)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    ctx=browser.new_context(viewport={"width":1280,"height":800},record_video_dir=str(OUT/"video"))
    page=ctx.new_page(); page.on("pageerror",lambda e:report["errors"].append(str(e)))
    page.goto(BASE); page.wait_for_load_state("networkidle")
    page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
    page.screenshot(path=str(OUT/"01_首页.png"))
    check("首页实际加载全三维场景和六动作人物",page.locator("#stage").get_attribute("data-render-mode")=="full-3d")
    page.locator("#start").click()
    s=page.evaluate("window.__naiwa.snapshot()")
    check("新访客点击主按钮立即进入第一关战斗",s["phase"]=="playing" and s["wave"]==1 and len(s["enemies"])>0 and not page.locator("#guide").is_visible())
    page.keyboard.down("KeyD"); page.keyboard.down("KeyJ")
    page.wait_for_function("(s)=>{let w=window.__naiwa.snapshot(); return w.hero.x>s.hero.x+40 && w.serial>s.serial+2}",arg=s)
    page.screenshot(path=str(OUT/"02_直接战斗.png"))
    page.keyboard.up("KeyD"); page.keyboard.up("KeyJ")
    check("实际按键移动并发射三维弹幕",True)
    page.locator("#pause").click()
    frozen=page.evaluate("window.__naiwa.snapshot()")
    screenshot_style=".overlay,.hud,.boss-status,.guide,.wave-toast,.storm-note,.controls,#character-status{visibility:hidden!important}"
    image=page.locator("#game canvas").screenshot(style=screenshot_style)
    page.wait_for_timeout(500)
    check("暂停冻结战斗及三维骨骼画面",frozen==page.evaluate("window.__naiwa.snapshot()") and image==page.locator("#game canvas").screenshot(style=screenshot_style))
    page.reload(); page.wait_for_load_state("networkidle")
    page.locator("#resume").click()
    check("刷新后可继续原战斗",page.evaluate("window.__naiwa.snapshot().wave")==1)
    page.locator("#back-menu").click(); page.locator("#practice").click()
    check("练习独立可选",page.evaluate("window.__naiwa.snapshot().phase")=="tutorial")
    page.locator("#skip-practice").click()
    check("练习第一步就能直接开打",page.evaluate("window.__naiwa.snapshot().phase")=="playing")
    check("浏览器无脚本异常",not report["errors"])
    video=page.video; ctx.close(); report["video"]=str(video.path())
    browser.close()
(OUT/"入口验收.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
