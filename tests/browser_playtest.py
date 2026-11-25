"""Real browser inputs only. The game exposes a read-only snapshot for assertions.

Run after starting `npm run preview`: python3 tests/browser_playtest.py
Requires: python3 -m pip install playwright; python3 -m playwright install chromium
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import time
import os

BASE = os.environ.get("NAIWA_URL", "http://localhost:4188")
OUT = Path(__file__).resolve().parents[1] / "验收"
OUT.mkdir(exist_ok=True)
report = {"url": BASE, "checks": [], "errors": [], "network_failures": []}


def check(label, condition):
    assert condition, label
    report["checks"].append(label)
    print("PASS", label, flush=True)


def snapshot(page):
    return page.evaluate("window.__naiwa.snapshot()")


def boot(page):
    page.on("pageerror", lambda error: report["errors"].append(str(error)))
    page.on("requestfailed", lambda req: report["network_failures"].append(req.url))
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    page.wait_for_function("window.__naiwa && document.querySelector('canvas')")


def tutorial(page):
    page.locator("#practice").click()
    page.keyboard.down("KeyD")
    page.wait_for_function("window.__naiwa.snapshot().tutorialStep === 1")
    page.keyboard.up("KeyD")
    page.keyboard.press("KeyJ")
    page.wait_for_function("window.__naiwa.snapshot().tutorialStep === 2")
    page.keyboard.down("KeyK")
    page.wait_for_function("window.__naiwa.snapshot().tutorialStep === 3")
    page.keyboard.up("KeyK")
    page.wait_for_function("!window.__naiwa.snapshot().hero.defending")
    check("安全练习无敌人、无伤害，移动/轻点攻击/长按防御均有效", snapshot(page)["hero"]["hp"] == 120 and not snapshot(page)["enemies"])
    page.get_by_role("button", name="出发守村").click()
    page.wait_for_function("window.__naiwa.snapshot().phase === 'playing'")


with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800}, record_video_dir=str(OUT / "录像源"), record_video_size={"width": 1280, "height": 800})
    page = context.new_page()
    boot(page)
    page.screenshot(path=str(OUT / "01_首页.png"))
    tutorial(page)
    page.screenshot(path=str(OUT / "02_练习完成.png"))
    # Hold attack and release it; no new projectile IDs should appear afterward.
    attack = page.locator("#attack")
    box = attack.bounding_box()
    page.mouse.move(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
    page.mouse.down()
    page.wait_for_timeout(500)
    page.mouse.up()
    serial = snapshot(page)["serial"]
    page.wait_for_timeout(450)
    check("奶弹松手后停止连发", snapshot(page)["serial"] == serial)
    page.keyboard.down("KeyW")
    page.wait_for_function("window.__naiwa.snapshot().hero.y < 450")
    page.keyboard.press("KeyL")
    page.keyboard.up("KeyW")
    page.wait_for_function("window.__naiwa.snapshot().hero.dashCooldown > 0")
    check("冲刺实际位移并进入冷却", snapshot(page)["hero"]["y"] < 450)
    page.get_by_role("button", name="暂停游戏").click()
    before = snapshot(page)
    page.keyboard.down("KeyD")
    page.wait_for_timeout(400)
    page.keyboard.up("KeyD")
    check("暂停时位置、敌人、弹幕和战斗时钟全部冻结", snapshot(page) == before)
    encoded = page.evaluate("localStorage.getItem('naiwa.campaign.v3')")
    saved = json.loads(encoded)
    page.reload()
    page.wait_for_load_state("networkidle")
    page.get_by_role("button", name="继续上次冒险").click()
    restored = snapshot(page)
    check("刷新后恢复真实波次、击杀、生命和位置", restored["wave"] == saved["wave"] and restored["kills"] == saved["kills"] and restored["hero"]["hp"] == saved["hero"]["hp"] and abs(restored["hero"]["x"] - saved["hero"]["x"]) < 1)
    page.get_by_role("button", name="继续冒险").click()
    page.get_by_role("button", name="操作说明").click()
    check("查看操作说明时战斗暂停", snapshot(page)["paused"])
    page.get_by_role("button", name="知道了").click()
    check("关闭说明后恢复战斗", not snapshot(page)["paused"])
    page.get_by_role("button", name="关闭声音").click()
    check("声音按钮可切换", page.get_by_role("button", name="开启声音").count() == 1)
    page.get_by_role("button", name="开启声音").click()
    # Complete all waves with actual key events, not state edits.
    page.keyboard.down("KeyJ")
    seen_waves = {1}
    laughter = 0
    boss_warning = False
    boss_enraged = False
    started = time.monotonic()
    while time.monotonic() - started < 65:
        state = snapshot(page)
        if state["phase"] in ("defeat", "won"):
            break
        seen_waves.add(state["wave"])
        hero = state["hero"]
        if hero["energy"] == 100 and any(((e["x"] - hero["x"]) ** 2 + (e["y"] - hero["y"]) ** 2) ** 0.5 < 240 for e in state["enemies"]):
            page.keyboard.press("Space")
            laughter += 1
        bosses = [e for e in state["enemies"] if e["kind"] == "boss"]
        if bosses:
            boss = bosses[0]
            boss_enraged |= boss["enraged"]
            if boss["windup"] > 0 and not boss_warning:
                page.screenshot(path=str(OUT / "08_首领攻击预警.png"))
                boss_warning = True
        if state["wave"] == 2 and not (OUT / "09_第二波战斗.png").exists():
            page.screenshot(path=str(OUT / "09_第二波战斗.png"))
        page.wait_for_timeout(150)
    page.keyboard.up("KeyJ")
    end = snapshot(page)
    check("实际打完两波敌人及首领，击退全部 13 个敌人", end["phase"] == "won" and end["kills"] == 13 and seen_waves == {1, 2, 3})
    check("首领出现攻击预警并进入半血狂暴阶段", boss_warning and boss_enraged)
    page.screenshot(path=str(OUT / "10_实际通关.png"))
    report["victory"] = {"wave": end["wave"], "hp": end["hero"]["hp"], "kills": end["kills"], "battle_seconds": round(end["elapsed"], 2), "laugh_uses": laughter}
    page.wait_for_timeout(900)
    page.get_by_role("button", name="再玩一回").click()
    # No inputs: let actual enemy attacks cause defeat.
    page.wait_for_function("window.__naiwa.snapshot().phase === 'defeat'", timeout=70000)
    fallen = snapshot(page)
    check("敌人实际攻击导致失败并显示免费重来", fallen["hero"]["hp"] == 0 and page.get_by_role("button", name="免费重来").is_visible())
    page.screenshot(path=str(OUT / "11_实际失败.png"))
    page.get_by_role("button", name="免费重来").click()
    retry = snapshot(page)
    check("失败后无条件重开第一波，生命和击杀重置", retry["phase"] == "playing" and retry["wave"] == 1 and retry["hero"]["hp"] == 120 and retry["kills"] == 0)
    # Blur uses the same real browser event as switching away.
    page.evaluate("window.dispatchEvent(new Event('blur'))")
    check("失去窗口焦点自动暂停", snapshot(page)["paused"])
    page.get_by_role("button", name="返回首页").click()
    video = page.video
    context.close()
    video_path = Path(video.path())
    video_path.rename(OUT / "实际游玩.webm")
    # Mobile emulation: two simultaneous real CDP touches, then cancellation.
    mobile = browser.new_context(viewport={"width": 844, "height": 390}, is_mobile=True, has_touch=True)
    phone = mobile.new_page()
    boot(phone)
    phone.get_by_role("button", name="开始冒险").tap()
    cdp = mobile.new_cdp_session(phone)
    joy = phone.locator("#joystick").bounding_box()
    attack_box = phone.locator("#attack").bounding_box()
    point = lambda r, n: {"x": r["x"] + r["width"] * 0.8, "y": r["y"] + r["height"] / 2, "id": n, "radiusX": 4, "radiusY": 4, "force": 1}
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point(joy, 1), point(attack_box, 2)]})
    phone.wait_for_function("window.__naiwa.snapshot().tutorialDistance >= 80")
    moving = snapshot(phone)
    check("手机同时摇杆移动和奶弹连发", moving["hero"]["x"] > 350 and moving["serial"] > 1)
    cdp.send("Input.dispatchTouchEvent", {"type": "touchCancel", "touchPoints": []})
    # A neutral frame clears held input before taking the comparison state.
    phone.wait_for_timeout(150)
    stopped = snapshot(phone)
    phone.wait_for_timeout(350)
    after = snapshot(phone)
    check("触控取消后不继续移动或射击", stopped["hero"]["x"] == after["hero"]["x"] and stopped["serial"] == after["serial"])
    phone.locator("#attack").tap()
    defend = phone.locator("#defend").bounding_box()
    cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point(defend, 3)]})
    phone.wait_for_function("window.__naiwa.snapshot().tutorialStep === 3")
    cdp.send("Input.dispatchTouchEvent", {"type": "touchEnd", "touchPoints": []})
    phone.get_by_role("button", name="出发守村").tap()
    phone.screenshot(path=str(OUT / "12_手机横屏战斗.png"))
    check("手机触控可完成练习并进入真实战斗", snapshot(phone)["phase"] == "playing")
    phone.set_viewport_size({"width": 390, "height": 844})
    phone.wait_for_timeout(200)
    phone.screenshot(path=str(OUT / "13_手机竖屏战斗.png"))
    check("横竖屏切换不丢失关卡，页面无横向溢出", snapshot(phone)["wave"] == 1 and not phone.evaluate("document.documentElement.scrollWidth > innerWidth"))
    mobile.close()
    check("浏览器无脚本错误或资源加载失败", not report["errors"] and not report["network_failures"])
    browser.close()
    (OUT / "浏览器验收.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
