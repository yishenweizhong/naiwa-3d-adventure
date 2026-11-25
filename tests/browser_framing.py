"""Actual browser framing: portrait, landscape, resize and model cache version."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json, os

URL=os.environ.get("NAIWA_URL","http://localhost:4192/")
OUT=Path(os.environ.get("NAIWA_EVIDENCE","/tmp/tomato-framing"))
OUT.mkdir(parents=True,exist_ok=True)
report={"checks":[],"viewports":[],"errors":[]}
def check(name,ok):
    assert ok,name
    report["checks"].append(name); print("PASS",name,flush=True)

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    for name,w,h in [("桌面",1280,800),("手机竖屏",390,844),("手机横屏",844,390),("窄屏",320,700)]:
        context=browser.new_context(viewport={"width":w,"height":h},device_scale_factor=1)
        page=context.new_page()
        page.on("pageerror",lambda e:report["errors"].append(str(e)))
        models=[]; page.on("response",lambda r:models.append(r.url) if "reference-hero.glb" in r.url else None)
        page.goto(URL); page.wait_for_load_state("networkidle")
        page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
        page.wait_for_timeout(1000)
        def frame():
            s=page.locator("#stage").evaluate("(s)=>({...s.dataset})")
            return {"height":int(s["heroProjectedHeight"]),"top":float(s["heroProjectedTop"]),
                    "bottom":float(s["heroProjectedBottom"]),"scale":float(s["heroScale"])}
        menu=frame()
        check(f"{name}菜单完整显示头脚",menu["top"]>.025 and menu["bottom"]<.97)
        check(f"{name}菜单人物具有足够尺寸",menu["height"]>=140)
        check(f"{name}新模型使用更新缓存版本",any("tailored-proportions" in u for u in models))
        page.screenshot(path=str(OUT/f"{name}_菜单.png"),full_page=True)
        page.locator("#practice").click(); page.wait_for_timeout(1200)
        practice=frame()
        check(f"{name}战斗人物等比缩放",practice["scale"]==2)
        check(f"{name}战斗人物未裁切",practice["top"]>0 and practice["bottom"]<1)
        if w<=650 and h>w:
            guide=page.locator("#guide").bounding_box()
            canvas=page.locator("#game").bounding_box()
            check(f"{name}练习提示不遮挡人物",guide["y"]>=canvas["y"]+canvas["height"])
        page.screenshot(path=str(OUT/f"{name}_练习.png"),full_page=True)
        if name=="手机竖屏":
            page.set_viewport_size({"width":844,"height":390}); page.wait_for_timeout(800)
            turned=frame()
            check("练习中手机旋转保持人物比例",turned["scale"]==2 and turned["top"]>0 and turned["bottom"]<1)
            page.screenshot(path=str(OUT/"手机旋转后.png"),full_page=True)
        report["viewports"].append({"name":name,"size":[w,h],"menu":menu,"practice":practice})
        context.close()
    check("响应式适配没有脚本错误",not report["errors"])
    browser.close()
(OUT/"适配检查.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
print("COMPLETE",len(report["checks"]),flush=True)
