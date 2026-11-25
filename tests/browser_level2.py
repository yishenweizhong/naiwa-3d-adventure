"""Campaign verification through browser buttons, keyboard and CDP touches.

Run with the preview server running: python3 tests/browser_level2.py
Snapshots only observe state. No combat state is injected or modified.
The legacy migration checks use authentic saves produced by the first release.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import math
import os
import time

ROOT = Path(__file__).resolve().parents[1]
BASE = os.environ.get("NAIWA_URL", "http://localhost:4188")
OUT = Path(os.environ.get("NAIWA_EVIDENCE", "/tmp/naiwa-level2-browser"))
OUT.mkdir(parents=True, exist_ok=True)
REPORT = {"url": BASE, "checks": [], "errors": [], "network_failures": []}
SAVE_KEY = "naiwa.campaign.v3"
OLD_KEY = "naiwa.level1.v1"


def check(label, condition):
    assert condition, label
    REPORT["checks"].append(label)
    print("PASS", label, flush=True)


def state(page):
    return page.evaluate("window.__naiwa.snapshot()")


def capture(page, name):
    page.screenshot(path=str(OUT / f"{name}.png"))


def boot(page):
    page.on("pageerror", lambda error: REPORT["errors"].append(str(error)))
    page.on("requestfailed", lambda req: REPORT["network_failures"].append(req.url))
    page.goto(BASE)
    page.wait_for_load_state("networkidle")
    page.wait_for_function("window.__naiwa && document.querySelector('canvas')")
    if page.locator("#character-status").count():
        page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")


def tutorial(page):
    check("首次进入第二关尚未解锁", page.locator("#start-level2").is_disabled())
    page.locator("#practice").click()
    page.keyboard.down("KeyD")
    page.wait_for_function("window.__naiwa.snapshot().tutorialStep === 1")
    page.keyboard.up("KeyD")
    page.keyboard.press("KeyJ")
    page.keyboard.down("KeyK")
    page.wait_for_function("window.__naiwa.snapshot().tutorialStep === 3")
    page.keyboard.up("KeyK")
    page.locator("#guide-ready").click()


def play(page, level):
    if level == 2:
        # Observe each rendered frame: Python polling can miss the short impact
        # interval while screenshots or software rendering are busy.
        page.evaluate("""() => {
          window.hazardDodges=[];
          const pending=new Map();
          function observe(){
            const s=window.__naiwa.snapshot(), h=s.hero;
            for(const hazard of s.hazards){
              if(hazard.windup>0) pending.set(hazard.id,{...hazard,hp:h.hp});
              else if(pending.has(hazard.id)){
                const before=pending.get(hazard.id);
                if(Math.hypot(h.x-hazard.x,h.y-hazard.y)>=hazard.radius && h.hp>=before.hp)
                  hazardDodges.push({id:hazard.id,hpBefore:before.hp,hpAfter:h.hp});
                pending.delete(hazard.id);
              }
            }
            if(s.phase==='playing' && s.level===2) requestAnimationFrame(observe);
          }
          requestAnimationFrame(observe);
        }""")
    page.keyboard.down("KeyJ")
    started = time.monotonic()
    waves, seen = set(), set()
    laughs, dashes = 0, 0
    points = [(180, 320), (540, 320), (540, 590), (180, 590)]
    waypoint = 0
    pressed = set()
    saved_frames = set()
    previous_hazard = None
    dodges = 0
    last_print = 0
    while time.monotonic() - started < 150:
        s = state(page)
        if s["phase"] in ("won", "defeat"):
            break
        waves.add(s["wave"])
        h = s["hero"]
        enemies = s["enemies"]
        if level == 2:
            target = points[waypoint]
            if math.dist((h["x"], h["y"]), target) < 35:
                waypoint = (waypoint + 1) % len(points)
                target = points[waypoint]
            want = set()
            if abs(target[0] - h["x"]) > 16:
                want.add("KeyD" if target[0] > h["x"] else "KeyA")
            if abs(target[1] - h["y"]) > 16:
                want.add("KeyS" if target[1] > h["y"] else "KeyW")
            for key in pressed - want:
                page.keyboard.up(key)
            for key in want - pressed:
                page.keyboard.down(key)
            pressed = want
            danger = any(e["kind"] == "boss" and e["windup"] > 0 and
                         math.dist((h["x"], h["y"]), (e["aimX"], e["aimY"])) < 150
                         for e in enemies)
            if danger and h["dashCooldown"] == 0:
                page.keyboard.press("KeyL")
                dashes += 1
            for e in enemies:
                if e["kind"] == "rusher" and e["chargeTime"] > 0:
                    seen.add("rusher_charge")
                if e["kind"] == "rusher" and e["windup"] > 0:
                    seen.add("rusher_warning")
                    if "斥候冲锋预警" not in saved_frames:
                        capture(page, "04_斥候冲锋预警")
                        saved_frames.add("斥候冲锋预警")
            hazards = s["hazards"]
            if hazards:
                seen.add("lightning")
                current = hazards[0]
                if current["windup"] > 0:
                    previous_hazard = {**current, "hp": h["hp"]}
                    if "落雷" not in saved_frames:
                        capture(page, "05_落雷预警")
                        saved_frames.add("落雷")
                elif previous_hazard and current["id"] == previous_hazard["id"]:
                    if math.dist((h["x"], h["y"]), (current["x"], current["y"])) >= current["radius"] and h["hp"] >= previous_hazard["hp"]:
                        dodges += 1
                    previous_hazard = None
            if s["wave"] == 3 and "第三波" not in saved_frames:
                capture(page, "06_第三波混合敌人")
                saved_frames.add("第三波")
        if h["energy"] == 100 and any(math.dist((h["x"], h["y"]), (e["x"], e["y"])) < 240 for e in enemies):
            page.keyboard.press("Space")
            laughs += 1
        for e in enemies:
            if e["kind"] == "boss":
                if e["windup"] > 0:
                    seen.add("boss_warning")
                    if level == 2 and "首领" not in saved_frames:
                        capture(page, "07_风暴执政官")
                        saved_frames.add("首领")
                if e["enraged"]:
                    seen.add("boss_enraged")
                    if level == 2 and "狂暴" not in saved_frames:
                        capture(page, "08_首领半血狂暴")
                        saved_frames.add("狂暴")
        if time.monotonic() - last_print > 8:
            print(f"PLAY level={level} wave={s['wave']} kills={s['kills']} hp={h['hp']} elapsed={s['elapsed']:.1f}", flush=True)
            last_print = time.monotonic()
        page.wait_for_timeout(140)
    for key in pressed | {"KeyJ"}:
        page.keyboard.up(key)
    end = state(page)
    if level == 2:
        dodges = max(dodges, page.evaluate("window.hazardDodges.length"))
    REPORT[f"level{level}"] = {
        "phase": end["phase"], "kills": end["kills"], "hp": end["hero"]["hp"],
        "battle_seconds": round(end["elapsed"], 2), "waves": sorted(waves),
        "observed": sorted(seen), "laugh_uses": laughs, "dash_uses": dashes,
        "lightning_dodges": dodges,
    }
    capture(page, f"09_第{level}关实际结果")
    check(f"第{level}关通过真实按键完成全部波次与首领",
          end["phase"] == "won" and end["kills"] == (13 if level == 1 else 22) and waves == set(range(1, 4 if level == 1 else 5)))
    check(f"第{level}关首领预警和半血狂暴实际出现", {"boss_warning", "boss_enraged"} <= seen)
    if level == 2:
        check("实际战斗出现斥候蓄力、冲锋和落雷", {"rusher_charge", "rusher_warning", "lightning"} <= seen)
        check("通过实际移动离开黄色圈并避开落雷伤害", dodges > 0)
    return end


def migrate(browser, fixture):
    text = (ROOT / "tests" / "fixtures" / f"legacy-{fixture}.json").read_text()
    expected = json.loads(text)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    context.add_init_script(f"if (!localStorage.getItem({json.dumps(OLD_KEY)})) localStorage.setItem({json.dumps(OLD_KEY)}, {json.dumps(text)})")
    page = context.new_page()
    boot(page)
    check(f"旧版{fixture}存档在首页正确显示解锁状态", page.locator("#start-level2").is_disabled() == (fixture != "won"))
    page.locator("#resume").click()
    s = state(page)
    check(f"旧版{fixture}进度迁移保留第一关、波次、击杀和生命",
          s["level"] == 1 and s["wave"] == expected["wave"] and s["kills"] == expected["kills"] and s["hero"]["hp"] == expected["hero"]["hp"])
    check(f"旧版{fixture}原始存档保持不变且新存档为版本3",
          page.evaluate(f"localStorage.getItem({json.dumps(OLD_KEY)})") == text and
          json.loads(page.evaluate(f"localStorage.getItem({json.dumps(SAVE_KEY)})"))["version"] == 3)
    context.close()


def run():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1280, "height": 800},
                                      record_video_dir=str(OUT / "video"),
                                      record_video_size={"width": 1280, "height": 800})
        page = context.new_page()
        boot(page)
        capture(page, "01_双关首页")
        tutorial(page)
        first = play(page, 1)
        check("第一关真实通关后解锁第二关并显示入口", first["unlockedLevel"] == 2 and page.locator("#next-level").is_visible())
        page.locator("#next-level").click()
        briefing = state(page)
        page.wait_for_timeout(450)
        check("进入第二关说明期间敌人、落雷和时钟全部冻结",
              state(page) == briefing and briefing["level"] == 2 and briefing["paused"])
        capture(page, "02_第二关说明")
        page.locator("#begin-level").click()
        page.wait_for_function("window.__naiwa.snapshot().hazards.some(h => h.windup > .5)")
        page.locator("#pause").click()
        frozen = state(page)
        page.wait_for_timeout(300)
        check("第二关暂停冻结全部战斗状态和落雷倒计时", state(page) == frozen)
        saved = json.loads(page.evaluate(f"localStorage.getItem({json.dumps(SAVE_KEY)})"))
        check("落雷预警和斥候新字段进入真实存档", bool(saved["hazards"]) and all("chargeTime" in e for e in saved["enemies"]))
        page.reload()
        page.wait_for_load_state("networkidle")
        page.locator("#resume").click()
        restored = state(page)
        check("刷新续玩恢复第二关、生命、波次和原落雷位置",
              restored["level"] == saved["level"] == 2 and restored["wave"] == saved["wave"] and
              restored["hero"]["hp"] == saved["hero"]["hp"] and restored["kills"] == saved["kills"] and
              [(h["id"], h["x"], h["y"], h["radius"]) for h in restored["hazards"]] ==
              [(h["id"], h["x"], h["y"], h["radius"]) for h in saved["hazards"]])
        capture(page, "03_第二关暂停恢复")
        page.locator("#continue").click()
        second = play(page, 2)
        check("第二关通关解锁第三关并显示下一关入口", "第三关已解锁" in page.locator("#result-copy").inner_text() and page.locator("#next-level").is_visible())
        campaign_storage = context.storage_state()
        page.locator("#retry").click()
        page.wait_for_function("window.__naiwa.snapshot().phase === 'defeat'", timeout=90000)
        fallen = state(page)
        check("第二关无输入时由真实敌人和落雷造成失败", fallen["hero"]["hp"] == 0 and fallen["level"] == 2)
        capture(page, "10_第二关实际失败")
        page.locator("#retry").click()
        retry = state(page)
        check("第二关免费重来保留解锁，恢复第一波120生命", retry["level"] == 2 and retry["wave"] == 1 and retry["hero"]["hp"] == 120 and retry["kills"] == 0 and retry["unlockedLevel"] == 3)
        page.keyboard.press("Escape")
        page.locator("#back-menu").click()
        check("返回首页仍可直接重返第二关", not page.locator("#start-level2").is_disabled())
        video = page.video
        context.close()
        Path(video.path()).rename(OUT / "真实双关游玩.webm")

        mobile = browser.new_context(viewport={"width": 844, "height": 390},
                                     is_mobile=True, has_touch=True, storage_state=campaign_storage)
        phone = mobile.new_page()
        boot(phone)
        phone.locator("#start-level2").tap()
        capture(phone, "11_手机横屏第二关说明")
        phone.locator("#begin-level").tap()
        cdp = mobile.new_cdp_session(phone)
        joy = phone.locator("#joystick").bounding_box()
        attack = phone.locator("#attack").bounding_box()
        point = lambda r, n: {"x": r["x"] + r["width"] * .8, "y": r["y"] + r["height"] / 2, "id": n, "radiusX": 4, "radiusY": 4, "force": 1}
        before = state(phone)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchStart", "touchPoints": [point(joy, 1), point(attack, 2)]})
        phone.wait_for_timeout(500)
        moving = state(phone)
        check("第二关手机双指摇杆和奶弹同时生效", moving["hero"]["x"] > before["hero"]["x"] + 30 and moving["serial"] > before["serial"] + 1)
        cdp.send("Input.dispatchTouchEvent", {"type": "touchCancel", "touchPoints": []})
        phone.wait_for_timeout(100)
        stopped = state(phone)
        phone.wait_for_timeout(300)
        after = state(phone)
        check("第二关触控取消后停止移动与连发", stopped["hero"]["x"] == after["hero"]["x"] and not any(s["team"] == "hero" and s["id"] > stopped["serial"] for s in after["shots"]))
        capture(phone, "12_手机横屏第二关战斗")
        phone.locator("#pause").tap()
        phone.set_viewport_size({"width": 390, "height": 844})
        phone.locator("#continue").tap()
        capture(phone, "13_手机竖屏第二关")
        check("第二关横竖屏切换保留状态，页面没有横向溢出", state(phone)["level"] == 2 and not phone.evaluate("document.documentElement.scrollWidth > innerWidth"))
        mobile.close()
        migrate(browser, "active")
        migrate(browser, "won")
        check("本轮浏览器无脚本错误和资源加载失败", not REPORT["errors"] and not REPORT["network_failures"])
        browser.close()


if __name__ == "__main__":
    try:
        run()
    finally:
        (OUT / "第二关浏览器验收.json").write_text(json.dumps(REPORT, ensure_ascii=False, indent=2))
