"""Real character rendering, action transitions, pause and local GLB loading."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os

BASE=os.environ.get("NAIWA_URL","http://localhost:4188")
OUT=Path(os.environ.get("NAIWA_EVIDENCE","/tmp/naiwa-character-browser"))
OUT.mkdir(parents=True,exist_ok=True)
report={"checks":[],"errors":[],"model_loads":[]}

def check(name,ok):
    assert ok,name
    report["checks"].append(name)
    print("PASS",name,flush=True)

def motion(page,name):
    page.wait_for_function(
        "(name)=>document.querySelector('#stage').dataset.heroMotion===name || window.observedMotions?.includes(name)",
        arg=name,timeout=5000)

def canvas_hash(page):
    # Locator screenshots include overlapping DOM; compare the WebGL scene
    # independently of the toast timeout and HUD CSS transitions.
    return page.locator("#game canvas").screenshot(style=
        ".overlay,.hud,.boss-status,.guide,.wave-toast,.storm-note,.controls,#character-status{visibility:hidden!important}")

def run():
    with sync_playwright() as p:
        browser=p.chromium.launch(headless=True)
        context=browser.new_context(viewport={"width":1280,"height":800},
            record_video_dir=str(OUT/"video"),record_video_size={"width":1280,"height":800})
        page=context.new_page()
        page.on("pageerror",lambda e:report["errors"].append(str(e)))
        page.on("response",lambda r:report["model_loads"].append({"status":r.status,"url":r.url}) if "reference-hero.glb" in r.url else None)
        page.goto(BASE); page.wait_for_load_state("networkidle")
        page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
        page.evaluate("""window.observedMotions=[];
          new MutationObserver(()=>observedMotions.push(document.querySelector('#stage').dataset.heroMotion))
          .observe(document.querySelector('#stage'),{attributes:true,attributeFilter:['data-hero-motion']});
        """)
        check("本地GLB实际加载，首页显示新人物",bool(report["model_loads"]) and report["model_loads"][0]["status"]==200)
        page.screenshot(path=str(OUT/"01_新人物首页.png"))
        page.locator("#practice").click(); motion(page,"idle")
        page.keyboard.down("KeyD"); motion(page,"walk")
        page.wait_for_function("window.__naiwa.snapshot().tutorialStep===1")
        page.screenshot(path=str(OUT/"02_行走.png"))
        page.keyboard.up("KeyD"); motion(page,"idle")
        page.keyboard.press("KeyJ"); motion(page,"attack")
        page.screenshot(path=str(OUT/"03_攻击.png"))
        page.keyboard.down("KeyK"); motion(page,"defend")
        page.wait_for_function("window.__naiwa.snapshot().tutorialStep===3")
        page.screenshot(path=str(OUT/"04_举盾.png"))
        page.keyboard.up("KeyK")
        check("真实练习输入驱动行走、攻击与举盾动作",True)
        page.locator("#guide-ready").click()
        page.keyboard.down("KeyA"); motion(page,"walk")
        page.wait_for_timeout(250); left=canvas_hash(page)
        page.keyboard.up("KeyA")
        page.keyboard.down("KeyD"); page.wait_for_timeout(250); right=canvas_hash(page)
        page.keyboard.up("KeyD")
        check("左右实际移动会改变人物画面",left!=right)
        page.keyboard.press("KeyL"); motion(page,"dash")
        page.screenshot(path=str(OUT/"05_冲刺.png"))
        page.wait_for_timeout(650)
        page.locator("#pause").click()
        page.wait_for_timeout(100)
        before=canvas_hash(page); state=page.evaluate("window.__naiwa.snapshot()")
        page.wait_for_timeout(500)
        after=canvas_hash(page)
        (OUT/"暂停场景_前.png").write_bytes(before)
        (OUT/"暂停场景_后.png").write_bytes(after)
        check("暂停冻结游戏状态",state==page.evaluate("window.__naiwa.snapshot()"))
        check("暂停冻结3D画面",after==before)
        page.locator("#continue").click()
        page.keyboard.down("KeyK")
        page.wait_for_function("window.__naiwa.snapshot().hero.energy===100",timeout=40000)
        page.keyboard.up("KeyK"); page.keyboard.press("Space"); motion(page,"laugh")
        page.screenshot(path=str(OUT/"06_真实大笑动作.png"))
        check("实际积满笑能并触发大笑骨骼动作",page.evaluate("window.__naiwa.snapshot().hero.energy")<100)
        report["motions"]=page.evaluate("window.observedMotions")
        page.locator("#pause").click()
        page.reload(); page.wait_for_load_state("networkidle")
        page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
        page.locator("#resume").click()
        check("刷新恢复存档后仍加载新人物",page.locator("#stage").get_attribute("data-hero-state")=="ready")
        check("人物验证无浏览器脚本错误",not report["errors"])
        video=page.video
        context.close()
        report["video"]=str(video.path())
        # Failure is explicit and actionable; no old frog is silently substituted.
        bad=browser.new_page()
        bad.route("**/models/reference-hero.glb*",lambda r:r.abort())
        bad.goto(BASE); bad.wait_for_load_state("networkidle")
        bad.wait_for_function("document.querySelector('#stage').dataset.heroState==='error'")
        check("资源失败时给出可见重试提示",bad.locator("#character-status").is_visible())
        bad.close()
        browser.close()
    (OUT/"人物验证.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
    print("COMPLETE",len(report["checks"]),str(OUT),flush=True)

if __name__=="__main__":
    run()
