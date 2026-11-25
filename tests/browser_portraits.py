"""Verify selected portraits and hit effects through real game input."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import os, json

BASE=os.environ.get("NAIWA_URL","http://localhost:4192")
OUT=Path(os.environ.get("NAIWA_EVIDENCE","/tmp/tomato-portrait-test"))
OUT.mkdir(parents=True,exist_ok=True)
report={"checks":[],"errors":[]}
def check(name,condition):
    assert condition,name
    report["checks"].append(name)
    print("PASS",name,flush=True)
def data(page):
    return page.locator("#stage").evaluate("(el)=>({...el.dataset})")
def snapshot(page):
    return page.evaluate("window.__naiwa.snapshot()")

with sync_playwright() as p:
    browser=p.chromium.launch(headless=True)
    context=browser.new_context(viewport={"width":1280,"height":800},
        record_video_dir=str(OUT/"video"),record_video_size={"width":1280,"height":800})
    page=context.new_page()
    page.on("pageerror",lambda e:report["errors"].append(str(e)))
    page.goto(BASE); page.wait_for_load_state("networkidle")
    page.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
    check("主角原画贴图与小兵照片均已加载",
          data(page).get("heroPortrait")=="selected-illustration" and data(page).get("enemyPortrait")=="ready")
    page.screenshot(path=str(OUT/"01_指定主角首页.png"))
    page.locator("#start").click()
    page.wait_for_function("window.__naiwa.snapshot().phase==='playing'")
    page.wait_for_function("Number(document.querySelector('#stage').dataset.enemyHeads)===window.__naiwa.snapshot().enemies.length")
    check("首波全部小兵都使用指定照片头部",int(data(page)["enemyHeads"])==len(snapshot(page)["enemies"])>0)
    page.screenshot(path=str(OUT/"02_全部小兵照片头像.png"))
    page.evaluate("""window.hitEvidence=[]; window.freezeNextHit=true;
      new MutationObserver(()=>{
        const d=document.querySelector('#stage').dataset;
        hitEvidence.push({id:Number(d.lastHitTarget),s:window.__naiwa.snapshot(),flashes:Number(d.hitFlashes),particles:Number(d.hitParticles)});
        // Click the actual pause control in the observed frame, before screenshot latency.
        if(window.freezeNextHit || (window.freezeNextDefeat && Number(d.enemyDefeats)>0)){
          window.freezeNextHit=false; window.freezeNextDefeat=false;
          document.querySelector('#pause').click();
        }
      }).observe(document.querySelector('#stage'),{attributes:true,attributeFilter:['data-enemy-hits']});
    """)
    before=snapshot(page)
    page.keyboard.down("KeyJ")
    page.wait_for_function("window.__naiwa.snapshot().paused")
    page.keyboard.up("KeyJ")
    check("真实奶弹命中后出现头像闪色与星星",int(data(page)["hitFlashes"])>0 and int(data(page)["hitParticles"])>0)
    hits=page.evaluate("window.hitEvidence")
    check("命中特效记录指向实际扣血的小兵",
          any(any(e["id"]==h["id"] and e["hp"]<e["maxHp"] for e in h["s"]["enemies"]) for h in hits))
    page.screenshot(path=str(OUT/"03_真实受伤闪色星星.png"),style=".overlay{visibility:hidden!important}")
    frozen=data(page); state=snapshot(page)
    style=".overlay,.hud,.boss-status,.guide,.wave-toast,.storm-note,.controls,#character-status{visibility:hidden!important}"
    frame=page.locator("#game canvas").screenshot(style=style)
    page.wait_for_timeout(450)
    check("暂停冻结战斗、头像回弹与粒子",
          state==snapshot(page) and frozen==data(page) and frame==page.locator("#game canvas").screenshot(style=style))
    page.locator("#continue").click()
    page.wait_for_function("Number(document.querySelector('#stage').dataset.hitFlashes)===0 && Number(document.querySelector('#stage').dataset.hitParticles)===0")
    check("恢复后受伤特效正常结束",int(data(page)["hitParticles"])==0)
    page.evaluate("window.freezeNextDefeat=true")
    page.keyboard.down("KeyJ")
    page.wait_for_function("Number(document.querySelector('#stage').dataset.enemyDefeats)>0")
    page.wait_for_function("window.__naiwa.snapshot().paused")
    page.keyboard.up("KeyJ")
    check("实际击退后残留星星继续播放",snapshot(page)["kills"]>0 and int(data(page)["hitParticles"])>0)
    page.screenshot(path=str(OUT/"04_实际击退消散.png"),style=".overlay{visibility:hidden!important}")
    page.locator("#continue").click()
    page.wait_for_function("Number(document.querySelector('#stage').dataset.hitParticles)===0")
    check("击退小兵的头像实例已移除",
          int(data(page)["enemyHeads"])==len(snapshot(page)["enemies"]))
    page.screenshot(path=str(OUT/"05_受伤反馈结束.png"))
    check("实际战斗没有浏览器脚本错误",not report["errors"])
    report["hits"]=page.evaluate("window.hitEvidence")
    video=page.video; context.close(); report["video"]=str(video.path())

    # Exercise both actionable failure paths and retry; no substitution of the old portrait.
    for asset in ["textures/enemy-head.png","models/reference-hero.glb"]:
        bad=browser.new_page()
        bad.route("**/"+asset+"*",lambda route:route.abort())
        bad.goto(BASE); bad.wait_for_load_state("networkidle")
        bad.wait_for_function("document.querySelector('#stage').dataset.heroState==='error'")
        check(asset+"加载失败有可见重试",bad.locator("#character-status").is_visible())
        bad.unroute("**/"+asset+"*")
        bad.get_by_role("button",name="重新加载人物").click()
        bad.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
        check(asset+"重试后加载指定人物",data(bad).get("heroPortrait")=="selected-illustration")
        bad.close()
    # Starting during a slow portrait download must not create white heads.
    slow=browser.new_page()
    pending=[]
    slow.route("**/textures/enemy-head.png*",lambda route:pending.append(route))
    slow.goto(BASE,wait_until="domcontentloaded")
    slow.locator("#start").click()
    slow.wait_for_timeout(400)
    s=snapshot(slow)
    check("头像未下载时提前开始不会受伤或创建空白头像",
          bool(pending) and s["elapsed"]==0 and s["hero"]["hp"]==120 and int(data(slow).get("enemyHeads","0"))==0)
    for route in pending: route.continue_()
    slow.wait_for_function("document.querySelector('#stage').dataset.heroState==='ready'")
    slow.wait_for_function("Number(document.querySelector('#stage').dataset.enemyHeads)===window.__naiwa.snapshot().enemies.length")
    check("慢下载完成后全部小兵显示指定头像",int(data(slow)["enemyHeads"])==len(snapshot(slow)["enemies"])>0)
    slow.close()
    browser.close()
(OUT/"指定人物与受击验证.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
print("COMPLETE",len(report["checks"]),OUT,flush=True)
