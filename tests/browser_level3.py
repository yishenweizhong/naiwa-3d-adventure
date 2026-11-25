"""Real 1→2→3 campaign inputs, migration, recovery and touch controls.

Run: python3 tests/browser_level3.py (preview server must be running).
NAIWA_URL / NAIWA_EVIDENCE optionally override URL / temporary evidence path.
No combat state changes or runtime shortcuts are used.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import math
import os
import time
import browser_level2 as base

OUT = Path(os.environ.get("NAIWA_EVIDENCE", "/tmp/naiwa-level3-browser"))
OUT.mkdir(parents=True, exist_ok=True)
REPORT = {"url": base.BASE, "checks": [], "errors": [], "network_failures": []}
base.OUT, base.REPORT = OUT, REPORT
check, state, capture, boot = base.check, base.state, base.capture, base.boot
ROOT = Path(__file__).resolve().parents[1]
SAVE_KEY = "naiwa.campaign.v3"


def play_third(page):
    page.keyboard.down("KeyJ")
    points = [(180, 320), (540, 320), (540, 590), (180, 590)]
    waypoint, laughs, dashes, safe_passes = 0, 0, 0, 0
    pressed, waves, seen, passed = set(), set(), set(), set()
    started, printed = time.monotonic(), 0
    while time.monotonic() - started < 150:
        s = state(page)
        if s["phase"] in ("won", "defeat"):
            break
        h, enemies = s["hero"], s["enemies"]
        waves.add(s["wave"])
        if math.dist((h["x"], h["y"]), points[waypoint]) < 35:
            waypoint = (waypoint + 1) % len(points)
        target = points[waypoint]
        approaching = [w for w in s["windWalls"]
                       if h["x"] - 320 < w["x"] < h["x"] + 22]
        if approaching:
            wall = max(approaching, key=lambda w: w["x"])
            target = (h["x"], wall["gapY"])
        wanted = set()
        if abs(target[0] - h["x"]) > 14:
            wanted.add("KeyD" if target[0] > h["x"] else "KeyA")
        if abs(target[1] - h["y"]) > 14:
            wanted.add("KeyS" if target[1] > h["y"] else "KeyW")
        for key in pressed - wanted:
            page.keyboard.up(key)
        for key in wanted - pressed:
            page.keyboard.down(key)
        pressed = wanted
        if h["energy"] == 100 and any(math.dist((h["x"], h["y"]), (e["x"], e["y"])) < 240 for e in enemies):
            page.keyboard.press("Space")
            laughs += 1
        for enemy in enemies:
            if enemy["kind"] == "boss":
                if enemy["windup"] > 0:
                    if "boss_warning" not in seen:
                        capture(page, "08_长夜钟守预警")
                    seen.add("boss_warning")
                    if math.dist((h["x"], h["y"]), (enemy["aimX"], enemy["aimY"])) < 170 and h["dashCooldown"] == 0:
                        page.keyboard.press("KeyL")
                        dashes += 1
                if enemy["enraged"]:
                    if "boss_enraged" not in seen:
                        capture(page, "09_长夜钟守半血狂暴")
                    seen.add("boss_enraged")
        for wall in s["windWalls"]:
            if wall["windup"] > 0:
                if "wind_warning" not in seen:
                    capture(page, "04_风墙预警与安全缺口")
                seen.add("wind_warning")
            else:
                if "wind_active" not in seen:
                    capture(page, "05_移动风墙")
                seen.add("wind_active")
                if wall["x"] > h["x"] + 22 and wall["id"] not in passed:
                    passed.add(wall["id"])
                    if abs(h["y"] - wall["gapY"]) < wall["gapHeight"] / 2 and not wall["hit"]:
                        safe_passes += 1
                        if safe_passes == 1:
                            capture(page, "06_真实缺口避伤")
        if s["wave"] == 4 and "fourth_wave" not in seen:
            capture(page, "07_第四波混合守卫")
            seen.add("fourth_wave")
        if time.monotonic() - printed > 8:
            print(f"PLAY level=3 wave={s['wave']} hp={h['hp']} kills={s['kills']} elapsed={s['elapsed']:.1f}", flush=True)
            printed = time.monotonic()
        page.wait_for_timeout(130)
    for key in pressed | {"KeyJ"}:
        page.keyboard.up(key)
    end = state(page)
    REPORT["level3"] = {
        "phase": end["phase"], "kills": end["kills"], "hp": end["hero"]["hp"],
        "battle_seconds": round(end["elapsed"], 2), "waves": sorted(waves),
        "observed": sorted(seen), "laugh_uses": laughs, "dash_uses": dashes,
        "safe_gap_passes": safe_passes,
    }
    capture(page, "10_第三关实际结果")
    check("真实按键完成第三关五波和35个敌人", end["phase"] == "won" and end["kills"] == 35 and waves == {1,2,3,4,5})
    check("真实战斗出现风墙蓄力、移动和安全缺口避伤", {"wind_warning","wind_active"} <= seen and safe_passes > 0)
    check("长夜钟守出现红圈预警和半血狂暴", {"boss_warning","boss_enraged"} <= seen)
    return end


def migrate_v2(browser, name):
    text = (ROOT / "tests/fixtures" / f"legacy-v2-{name}.json").read_text()
    expected = json.loads(text)
    context = browser.new_context(viewport={"width":1280,"height":800})
    context.add_init_script(f"localStorage.setItem('naiwa.campaign.v2',{json.dumps(text)})")
    page = context.new_page()
    boot(page)
    check(f"v2 {name}存档解锁状态正确", page.locator("#start-level3").is_disabled() == (name == "active"))
    page.locator("#resume").click()
    restored = state(page)
    check(f"v2 {name}迁移保留第二关波次、生命与击杀", restored["level"] == 2 and restored["wave"] == expected["wave"] and restored["hero"]["hp"] == expected["hero"]["hp"] and restored["kills"] == expected["kills"])
    check(f"v2 {name}原始存档不变，新存档立即写入v3", page.evaluate("localStorage.getItem('naiwa.campaign.v2')") == text and json.loads(page.evaluate(f"localStorage.getItem('{SAVE_KEY}')"))["version"] == 3)
    context.close()


def visible_in_viewport(page, selector):
    r = page.locator(selector).bounding_box()
    size = page.viewport_size
    return r and r["x"] >= 0 and r["y"] >= 0 and r["x"] + r["width"] <= size["width"] and r["y"] + r["height"] <= size["height"]


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width":1280,"height":800},
            record_video_dir=str(OUT/"video"),record_video_size={"width":1280,"height":800})
        page = context.new_page()
        boot(page)
        check("新玩家第三关入口锁定", page.locator("#start-level3").is_disabled())
        capture(page, "01_三关首页")
        base.tutorial(page)
        base.play(page, 1)
        check("第一关通关仍只解锁第二关", state(page)["unlockedLevel"] == 2)
        page.locator("#next-level").click()
        page.locator("#begin-level").click()
        base.play(page, 2)
        check("第二关真实通关解锁第三关并显示前往第三关", state(page)["unlockedLevel"] == 3 and "第三关" in page.locator("#next-level").inner_text())
        page.locator("#next-level").click()
        frozen = state(page)
        page.wait_for_timeout(400)
        check("第三关说明期间全战斗状态冻结", frozen == state(page) and frozen["level"] == 3 and frozen["paused"])
        capture(page, "02_第三关说明")
        page.locator("#begin-level").click()
        page.wait_for_function("window.__naiwa.snapshot().windWalls.some(w=>w.windup>.5)")
        page.locator("#pause").click()
        frozen = state(page)
        page.wait_for_timeout(350)
        check("第三关暂停冻结角色、敌人、风墙与计时", state(page) == frozen)
        saved = json.loads(page.evaluate(f"localStorage.getItem('{SAVE_KEY}')"))
        check("真实v3存档包含风墙缺口、位置与倒计时", saved["level"] == 3 and bool(saved["windWalls"]))
        page.reload()
        page.wait_for_load_state("networkidle")
        page.locator("#resume").click()
        restored = state(page)
        check("第三关刷新恢复原波次、生命和风墙预警", restored["level"] == 3 and restored["wave"] == saved["wave"] and restored["hero"]["hp"] == saved["hero"]["hp"] and
              [(w["id"],w["x"],w["gapY"],w["gapHeight"]) for w in restored["windWalls"]] == [(w["id"],w["x"],w["gapY"],w["gapHeight"]) for w in saved["windWalls"]])
        capture(page, "03_第三关暂停与恢复")
        page.locator("#continue").click()
        play_third(page)
        check("第三关结算显示三关完成且无第四关入口", "三关冒险完成" in page.locator("#result-copy").inner_text() and not page.locator("#next-level").is_visible())
        storage = context.storage_state()
        (OUT/"真实三关通关存档.json").write_text(json.dumps(storage,ensure_ascii=False,indent=2))
        page.locator("#retry").click()
        page.wait_for_function("window.__naiwa.snapshot().phase === 'defeat'", timeout=90000)
        check("第三关真实受击失败", state(page)["hero"]["hp"] == 0 and state(page)["level"] == 3)
        capture(page, "11_第三关实际失败")
        page.locator("#retry").click()
        s = state(page)
        check("第三关免费重来保留解锁并恢复第一波120生命", s["level"] == 3 and s["wave"] == 1 and s["hero"]["hp"] == 120 and s["kills"] == 0 and s["unlockedLevel"] == 3 and not s["windWalls"])
        page.keyboard.press("Escape")
        page.locator("#back-menu").click()
        check("返回首页第三关仍可直接进入", not page.locator("#start-level3").is_disabled())
        video = page.video
        context.close()
        Path(video.path()).rename(OUT/"真实三关游玩.webm")
        mobile = browser.new_context(viewport={"width":844,"height":390},is_mobile=True,has_touch=True,storage_state=storage)
        phone = mobile.new_page()
        boot(phone)
        check("手机横屏三关入口完整可见", all(visible_in_viewport(phone,s) for s in ["#start","#resume","#start-level2","#start-level3"]))
        capture(phone, "12_手机横屏三关首页")
        phone.locator("#start-level3").tap()
        capture(phone, "13_手机横屏第三关说明")
        phone.locator("#begin-level").tap()
        cdp = mobile.new_cdp_session(phone)
        point = lambda r,n: {"x":r["x"]+r["width"]*.8,"y":r["y"]+r["height"]/2,"id":n,"radiusX":4,"radiusY":4,"force":1}
        before = state(phone)
        cdp.send("Input.dispatchTouchEvent",{"type":"touchStart","touchPoints":[point(phone.locator("#joystick").bounding_box(),1),point(phone.locator("#attack").bounding_box(),2)]})
        phone.wait_for_function(
            """(before)=>{
              const s=window.__naiwa.snapshot();
              return !s.paused && s.hero.x>before.hero.x+30 && s.serial>before.serial+1;
            }""",arg=before,timeout=3000)
        moving = state(phone)
        check("第三关双指移动和攻击同时生效", moving["hero"]["x"] > before["hero"]["x"]+30 and moving["serial"] > before["serial"]+1)
        cdp.send("Input.dispatchTouchEvent",{"type":"touchCancel","touchPoints":[]})
        phone.wait_for_timeout(100)
        stopped = state(phone)
        phone.wait_for_timeout(300)
        after = state(phone)
        check("第三关触控取消后停止移动与连发", stopped["hero"]["x"] == after["hero"]["x"] and not any(s["team"]=="hero" and s["id"]>stopped["serial"] for s in after["shots"]))
        phone.locator("#pause").tap()
        phone.set_viewport_size({"width":390,"height":844})
        phone.locator("#continue").tap()
        capture(phone, "14_手机竖屏第三关")
        check("第三关旋转后状态保留且五个触控控件完整可见", state(phone)["level"] == 3 and all(visible_in_viewport(phone,s) for s in ["#joystick","#attack","#defend","#dash","#laugh"]) and not phone.evaluate("document.documentElement.scrollWidth>innerWidth"))
        phone.locator("#pause").tap()
        phone.locator("#back-menu").tap()
        capture(phone, "15_手机竖屏三关首页")
        check("手机竖屏三关入口完整可见", all(visible_in_viewport(phone,s) for s in ["#start","#resume","#start-level2","#start-level3"]))
        mobile.close()
        migrate_v2(browser,"active")
        migrate_v2(browser,"won")
        base.migrate(browser,"active")
        base.migrate(browser,"won")
        check("本轮三关浏览器无脚本错误与资源加载失败", not REPORT["errors"] and not REPORT["network_failures"])
        browser.close()


if __name__ == "__main__":
    try:
        run()
    finally:
        (OUT/"第三关浏览器验收.json").write_text(json.dumps(REPORT,ensure_ascii=False,indent=2))
