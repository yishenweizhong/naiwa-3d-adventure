"""Supplemental combat checks with real keyboard and button input."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import json
import time
import os

out = Path(__file__).resolve().parents[1] / "验收"
out.mkdir(exist_ok=True)
checks = []

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": 1280, "height": 800})
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(os.environ.get("NAIWA_URL", "http://localhost:4188"))
    page.wait_for_load_state("networkidle")
    page.locator("#practice").click()
    page.keyboard.down("KeyD")
    page.wait_for_function("window.__naiwa.snapshot().tutorialStep === 1")
    page.keyboard.up("KeyD")
    page.keyboard.press("KeyJ")
    page.keyboard.down("KeyK")
    page.wait_for_function("window.__naiwa.snapshot().tutorialStep === 3")
    page.keyboard.up("KeyK")
    page.get_by_role("button", name="出发守村").click()
    page.keyboard.down("KeyJ")
    page.wait_for_function("window.__naiwa.snapshot().hero.energy === 100")
    page.keyboard.up("KeyJ")
    state = lambda: page.evaluate("window.__naiwa.snapshot()")
    # Approach a living guard before spending laugh energy.
    page.keyboard.down("KeyD")
    page.wait_for_function("""() => {
      const s = window.__naiwa.snapshot();
      return s.enemies.some(e => Math.hypot(e.x-s.hero.x,e.y-s.hero.y) < 190);
    }""")
    page.keyboard.up("KeyD")
    before = state()
    page.locator("#laugh").click()
    page.wait_for_function("window.__naiwa.snapshot().hero.energy < 20")
    after = state()
    assert after["kills"] > before["kills"], "laugh must damage a nearby enemy"
    assert after["hero"]["energy"] == 0, "laugh must consume energy"
    checks.append("点击大笑实际消耗笑能并击退附近敌人")
    page.screenshot(path=str(out / "14_大笑实际释放.png"))
    print("PASS", checks[-1], flush=True)
    page.keyboard.down("KeyK")
    full_hp = state()["hero"]["hp"]
    page.wait_for_function("window.__naiwa.snapshot().hero.hp < 120", timeout=30000)
    blocked = state()
    assert blocked["hero"]["defending"] and 0 < full_hp - blocked["hero"]["hp"] <= 10
    checks.append("长按举盾在真实敌人攻击下减少伤害")
    print("PASS", checks[-1], flush=True)
    page.screenshot(path=str(out / "15_举盾实际减伤.png"))
    page.keyboard.up("KeyK")
    # Collect a real drop using movement keys.
    held = set()
    heal_seen = False
    started = time.monotonic()
    while time.monotonic() - started < 15:
        current = state()
        if current["hero"]["hp"] > blocked["hero"]["hp"]:
            heal_seen = True
            break
        if not current["pickups"]:
            break
        h = current["hero"]
        item = min(current["pickups"], key=lambda i: (i["x"]-h["x"])**2+(i["y"]-h["y"])**2)
        wanted = set()
        dx, dy = item["x"] - h["x"], item["y"] - h["y"]
        if abs(dx) > 12:
            wanted.add("KeyD" if dx > 0 else "KeyA")
        if abs(dy) > 12:
            wanted.add("KeyS" if dy > 0 else "KeyW")
        for k in held - wanted:
            page.keyboard.up(k)
        for k in wanted - held:
            page.keyboard.down(k)
        held = wanted
        page.wait_for_timeout(70)
    for k in held:
        page.keyboard.up(k)
    assert heal_seen, "real pickup must restore health"
    checks.append("移动拾取实际掉落牛奶恢复生命")
    print("PASS", checks[-1], flush=True)
    page.screenshot(path=str(out / "16_拾取牛奶回血.png"))
    assert not errors, errors
    (out / "动作验收.json").write_text(json.dumps({"checks": checks, "errors": errors}, ensure_ascii=False, indent=2))
    context.close()
    browser.close()
