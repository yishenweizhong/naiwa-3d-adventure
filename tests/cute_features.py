from playwright.sync_api import sync_playwright
from pathlib import Path
import json,os
OUT=Path(os.environ.get("NAIWA_EVIDENCE","/tmp/naiwa-cute-features")); OUT.mkdir(parents=True,exist_ok=True)
BASE=os.environ.get("NAIWA_URL","http://localhost:4190")
report={"checks":[],"errors":[]}
def check(name,value):
    assert value,name
    report["checks"].append(name); print("PASS",name,flush=True)
with sync_playwright() as p:
    b=p.chromium.launch(headless=True); page=b.new_page(viewport={"width":1280,"height":800})
    page.on("pageerror",lambda e:report["errors"].append(str(e)))
    page.goto(BASE); page.wait_for_load_state("networkidle")
    page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready' && document.querySelector('#stage').dataset.cc0Props==='2'")
    check("卡通GLB和两种Kenney场景模型在浏览器实际加载",not page.locator("#stage").get_attribute("data-prop-error"))
    check("新玩家默认轻松玩",page.locator("#easy").get_attribute("aria-pressed")=="true")
    page.locator("#normal").click()
    check("标准挑战更新选择和说明",page.locator("#normal").get_attribute("aria-pressed")=="true" and "完整战斗" in page.locator("#difficulty-note").inner_text())
    page.locator("#easy").click(); page.locator("#start").click()
    page.wait_for_function("window.__naiwa.snapshot().phase==='playing'")
    page.keyboard.down("KeyJ")
    page.wait_for_function("window.__naiwa.snapshot().kills>0")
    page.keyboard.up("KeyJ"); page.locator("#pause").click()
    state=page.evaluate("window.__naiwa.snapshot()")
    check("轻松模式产生实际击杀并进入存档",state["kills"]>0 and state["difficulty"]=="easy")
    page.reload(); page.wait_for_load_state("networkidle"); page.locator("#resume").click()
    after=page.evaluate("window.__naiwa.snapshot()")
    check("恢复暂停的轻松模式与真实击杀进度",after["paused"] and after["difficulty"]=="easy" and after["kills"]==state["kills"])
    page.locator("#back-menu").click()
    page.screenshot(path=str(OUT/"新功能首页.png"))
    check("无脚本错误",not report["errors"]); b.close()
(OUT/"新功能验证.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
