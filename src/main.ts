import "./cute.css";
import {
  World,
  decodeSave,
  type Input,
  type GameEvent,
} from "./model.ts";
import { GameScene3D } from "./scene3d.ts";
import { GameAudio } from "./audio.ts";
import { LEVELS } from "./levels.ts";
import { readRecords, updateRecord, starsFor, type Difficulty } from "./progress.ts";

const el = <T extends HTMLElement = HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const world = new World();
const audio = new GameAudio();
const SAVE_KEY = "naiwa.campaign.v3";
const PREVIOUS_KEY = "naiwa.campaign.v2";
const LEGACY_KEY = "naiwa.level1.v1";
const keys = new Set<string>();
const held = { attack: new Set<number>(), defend: new Set<number>() };
let joystick = { x: 0, y: 0 },
  joyId: number | null = null;
let shownPhase = "",
  shownStep = -1,
  helpWasPaused = false,
  saveClock = 0;
let saved = readSave();
world.unlockedLevel = saved?.unlockedLevel ?? 1;
world.difficulty = saved?.difficulty ?? "easy";
let records = readRecords((() => { try { return localStorage.getItem("naiwa.stars.v1"); } catch { return null; } })());
function updateMenuProgress() {
  for (const level of [1,2,3] as const) {
    const score = records[`${world.difficulty}-${level}`]?.stars ?? 0;
    el(`stars-${level}`).textContent = "★".repeat(score) + "☆".repeat(3-score);
  }
  for (const mode of ["easy","normal"] as const)
    el(mode).setAttribute("aria-pressed", String(world.difficulty === mode));
  el("difficulty-note").textContent = world.difficulty === "easy"
    ? "伤害更低，补给更多，适合第一次玩。" : "完整战斗强度，试试三星通关。";
}
function setDifficulty(mode: Difficulty) {
  if (world.phase !== "menu") return;
  world.difficulty = mode; updateMenuProgress();
}
let toastTimer: ReturnType<typeof setTimeout>;

function readSave() {
  try {
    return (
      decodeSave(localStorage.getItem(SAVE_KEY)) ??
      decodeSave(localStorage.getItem(PREVIOUS_KEY)) ??
      decodeSave(localStorage.getItem(LEGACY_KEY))
    );
  } catch {
    return null;
  }
}
function saveProgress() {
  if (world.phase === "menu") return;
  try {
    const save = world.save();
    localStorage.setItem(SAVE_KEY, JSON.stringify(save));
    saved = save;
    el("save-note").textContent = "进度已保存在本机";
  } catch {
    el("save-note").textContent = "浏览器未允许存档，本次仍可游玩";
  }
}
function clearInput() {
  keys.clear();
  held.attack.clear();
  held.defend.clear();
  joyId = null;
  joystick = { x: 0, y: 0 };
  el("stick").style.transform = "";
  for (const id of ["attack", "defend"]) el(id).classList.remove("pressed");
}
function input(): Input {
  return {
    x: Math.max(
      -1,
      Math.min(
        1,
        joystick.x +
          Number(keys.has("KeyD") || keys.has("ArrowRight")) -
          Number(keys.has("KeyA") || keys.has("ArrowLeft")),
      ),
    ),
    y: Math.max(
      -1,
      Math.min(
        1,
        joystick.y +
          Number(keys.has("KeyS") || keys.has("ArrowDown")) -
          Number(keys.has("KeyW") || keys.has("ArrowUp")),
      ),
    ),
    attack: held.attack.size > 0 || keys.has("KeyJ"),
    defend: held.defend.size > 0 || keys.has("KeyK"),
  };
}
function pause(value: boolean) {
  clearInput();
  world.pause(value);
  el("pause-overlay").hidden = !value;
  el("pause-title").textContent = "已暂停";
  el("pause-copy").textContent = "当前进度会保存在这台设备上。回来时，从这里继续。";
  if (value) saveProgress();
}
function goMenu() {
  saveProgress();
  clearInput();
  world.pause(false);
  world.phase = "menu";
  el("pause-overlay").hidden = true;
  el("help-overlay").hidden = true;
  el("level-briefing").hidden = true;
  shownPhase = "";
  frame();
}
function start(practice = false) {
  clearInput();
  world.start(practice);
  el("level-briefing").hidden = true;
  audio.unlock();
  shownPhase = "";
  shownStep = -1;
  saveProgress();
  frame();
}
function resume() {
  const save = readSave();
  if (!save) {
    start();
    return;
  }
  world.restore(save);
  const restoringBattle = world.phase === "playing" || world.phase === "tutorial";
  if (restoringBattle) {
    pause(true);
    el("pause-title").textContent = "进度已恢复";
    el("pause-copy").textContent = "关卡、生命和预警已恢复。点击继续冒险，从这里开打。";
  }
  el("level-briefing").hidden = true;
  clearInput();
  shownPhase = "";
  shownStep = -1;
  audio.unlock();
  saveProgress();
  frame();
}
const briefings = {
  2: {
    title: "风停之前，把笑声送回来。",
    intro: "三波守卫之后，风暴执政官正在等你。",
    rules: [
      ["突袭斥候", "蓄力时会锁定冲锋路线，横向躲开。"],
      ["落雷预警", "黄色圆圈出现后有 1.1 秒躲避时间。"],
      ["风暴首领", "躲开红圈；半血后的弹幕更密。"],
    ],
  },
  3: {
    title: "钟声响起，天就亮了。",
    intro: "四波守卫之后，击败长夜钟守，让晨光照进广场。",
    rules: [
      ["移动风墙", "紫色风墙向右推进，从绿色缺口穿过。"],
      ["冲刺避伤", "来不及进缺口时，用冲刺的短暂无敌越过风墙。"],
      ["长夜钟守", "躲开红圈；半血后弹幕更密，风墙更快。"],
    ],
  },
};
function enterLevel(level: 2 | 3, fromVictory = false) {
  if (!(fromVictory ? world.nextLevel() : world.start(false, level))) return;
  const config = LEVELS[level],
    briefing = briefings[level];
  el("level-briefing").setAttribute("aria-label", `${config.chapter}说明`);
  el("briefing-eyebrow").textContent = `${config.chapter} · ${config.title}`;
  el("briefing-title").textContent = briefing.title;
  el("briefing-intro").textContent = briefing.intro;
  const rows = document.querySelectorAll(".briefing-rules p");
  rows.forEach((row, i) => {
    row.querySelector("b")!.textContent = briefing.rules[i][0];
    row.querySelector("span")!.textContent = briefing.rules[i][1];
  });
  el("briefing-tip").textContent =
    `操作保持不变。失败只重开${config.chapter}，不用重打前面的关卡。`;
  el("begin-level").textContent = `进入${config.place} →`;
  clearInput();
  world.pause(true);
  audio.unlock();
  el("pause-overlay").hidden = true;
  el("level-briefing").hidden = false;
  shownPhase = "";
  saveProgress();
  frame();
}
function help() {
  helpWasPaused = world.paused;
  world.pause(true);
  clearInput();
  el("help-overlay").hidden = false;
}
function closeHelp() {
  el("help-overlay").hidden = true;
  world.pause(helpWasPaused);
  clearInput();
}
function toast(text: string) {
  clearTimeout(toastTimer);
  el("wave-toast").textContent = text;
  el("wave-toast").classList.add("visible");
  toastTimer = setTimeout(
    () => el("wave-toast").classList.remove("visible"),
    1800,
  );
}
function event(e: GameEvent) {
  audio.play(e.kind);
  if (e.kind === "wave")
    toast(
      e.value === LEVELS[world.level].waves.length
        ? `最后一战 · ${LEVELS[world.level].bossName}`
        : `第 ${e.value} 波 · ${world.level === 3 ? "钟楼守卫" : world.level === 2 ? (e.value === 1 ? "斥候来袭" : "风谷守卫") : e.value === 1 ? "冷面卫兵" : "援军来了"}`,
    );
  if (e.kind === "win" || e.kind === "defeat") {
    if (e.kind === "win") {
      records = updateRecord(records, world.level, world.difficulty,
        starsFor(world.phase,world.hero.hp,world.elapsed,world.level), world.elapsed);
      try { localStorage.setItem("naiwa.stars.v1", JSON.stringify(records)); } catch { /* Current result remains visible. */ }
    }
    clearInput();
    saveProgress();
  }
}
const clock = (seconds: number) =>
  `${Math.floor(seconds / 60)}:${String(Math.floor(seconds % 60)).padStart(2, "0")}`;
const guides = [
  ["先活动一下", "拖动左侧摇杆，或用 WASD / 方向键移动。"],
  ["试试奶弹", "按住「奶弹」或 J，松开就停止。自动瞄准，无需鼠标。"],
  ["把盾举起来", "按住「举盾」或 K。举盾时减伤，但移动会慢一些。"],
  ["准备好了！", "战斗中用冲刺躲红圈，笑能满后释放大笑。"],
];
function frame() {
  const w = world;
  const config = LEVELS[w.level];
  el("stage").dataset.chapter = w.phase === "menu" ? "menu" : String(w.level);
  const chapterLabel = document.querySelector(".chapter-label")!;
  chapterLabel.textContent =
    w.phase === "menu"
      ? "奶笑村 → 风车谷 → 晨光钟楼"
      : `${config.chapter} · ${config.title}`;
  el("place-note").textContent =
    w.phase === "menu" ? "奶笑村 · 晴" : `${config.place} · ${config.weather}`;
  if (shownPhase !== w.phase) {
    shownPhase = w.phase;
    const active = w.phase === "tutorial" || w.phase === "playing";
    el("menu").hidden = w.phase !== "menu";
    el("hud").hidden = !active;
    el("controls").hidden = !active;
    el("result").hidden = w.phase !== "defeat" && w.phase !== "won";
    el("guide").hidden = w.phase !== "tutorial";
    if (w.phase === "menu") {
      updateMenuProgress();
      const second = el<HTMLButtonElement>("start-level2");
      second.disabled = w.unlockedLevel < 2;
      second.querySelector(".chapter-action")!.textContent = second.disabled
        ? "通关第一章解锁" : "重返风车谷 →";
      const third = el<HTMLButtonElement>("start-level3");
      third.disabled = w.unlockedLevel < 3;
      third.querySelector(".chapter-action")!.textContent = third.disabled
        ? "通关第二章解锁" : "重返钟楼 →";
      el("resume").hidden = !saved;
      el("resume").textContent =
        saved?.phase === "won"
          ? "查看上次通关"
          : saved?.phase === "defeat"
            ? "继续 · 再试一次"
            : "继续上次冒险";
    }
    if (w.phase === "won" || w.phase === "defeat") {
      const won = w.phase === "won";
      const stars = starsFor(w.phase,w.hero.hp,w.elapsed,w.level);
      el("result-stars").textContent = "★".repeat(stars)+"☆".repeat(3-stars);
      el("result-stars").setAttribute("aria-label",`本关 ${stars} 星，共 3 星`);
      el("star-detail").textContent = won
        ? `${w.difficulty === "easy" ? "轻松玩" : "标准挑战"} · 通关得一星，生命≥60与限时通关各加一星。`
        : "每一关都可以重新挑战，已解锁的关卡会保留。";
      el("result-seal").textContent = won ? "☺" : "☂";
      el("result-eyebrow").textContent = won
        ? `${config.chapter} · 已完成`
        : `${config.chapter} · 跌倒也没关系`;
      el("result-title").textContent = won
        ? w.level === 3
          ? "钟声里，天亮了。"
          : w.level === 2
            ? "风车，又转起来了。"
            : "奶笑村，笑了。"
        : "再给快乐一次机会";
      el("result-copy").textContent = won
        ? w.level === 3
          ? "长夜散去，晨光照进广场。三关冒险完成！"
          : w.level === 2
            ? "风暴散去，风车又转起来了。第三关已解锁，去晨光钟楼继续冒险！"
            : "奶笑村恢复了好心情。第二关已解锁，去风车谷继续冒险！"
        : w.level === 3
          ? "从绿色缺口穿过风墙，留意钟守的红圈。免费重来，只重开第三关。"
          : w.level === 2
            ? "横向躲开斥候，离开落雷圆圈。免费重来，只重开第二关。"
            : "躲开红圈，举盾挡住来不及闪避的攻击。免费重来，从第一波重新出发。";
      el("result-kills").textContent = String(w.kills);
      el("result-time").textContent = clock(w.elapsed);
      el("retry").textContent = won ? "再玩一回 →" : "免费重来 →";
      const hasNext = won && w.level < 3;
      el("next-level").hidden = !hasNext;
      el("next-level").textContent = `前往第${w.level === 1 ? "二" : "三"}关 →`;
      el("retry").classList.toggle("secondary", hasNext);
      el("retry").classList.toggle("primary", !hasNext);
    }
  }
  const active = w.phase === "tutorial" || w.phase === "playing";
  if (!active) {
    el("boss-status").hidden = true;
    el("storm-note").hidden = true;
    return;
  }
  el("hp-fill").style.transform = `scaleX(${w.hero.hp / 120})`;
  el("hp-text").textContent = `${w.hero.hp} / 120`;
  el("hp-meter").setAttribute("aria-valuenow", String(w.hero.hp));
  el("energy-fill").style.transform = `scaleX(${w.hero.energy / 100})`;
  el("energy-text").textContent = `${w.hero.energy}%`;
  el("energy-meter").setAttribute("aria-valuenow", String(w.hero.energy));
  el("wave-title").textContent =
    w.phase === "tutorial"
      ? "安全练习"
      : w.wave === config.waves.length
        ? "最后一战"
        : `第 ${w.wave} 波 / 共 ${config.waves.length} 波`;
  el("wave-detail").textContent =
    w.phase === "tutorial"
      ? "先练习，再出发"
      : w.wave === config.waves.length
        ? config.bossName
        : w.enemies.length
          ? `剩余 ${w.enemies.length} 个敌人`
          : "恢复生命 · 下一波将至";
  if (el("wave-dots").children.length !== config.waves.length) {
    el("wave-dots").replaceChildren(
      ...config.waves.map(() => document.createElement("i")),
    );
  }
  el("wave-dots")
    .querySelectorAll("i")
    .forEach((dot, i) => dot.classList.toggle("active", w.wave >= i + 1));
  const boss = w.enemies.find((e) => e.kind === "boss");
  el("boss-status").hidden = !boss;
  if (boss) {
    el("boss-name").textContent = config.bossName;
    el("boss-fill").style.transform = `scaleX(${boss.hp / boss.maxHp})`;
    el("boss-label").textContent = boss.enraged
      ? "狂暴中 · 留意弹幕"
      : "看清红圈，再出手";
  }
  const warned =
    w.level === 3
      ? w.windWalls.length > 0
      : w.hazards.some((h) => h.windup > 0);
  el("storm-note").hidden = !warned || w.paused;
  const warning =
    w.level === 3 ? "风墙右移 · 走绿色缺口" : "落雷将至 · 离开黄色圈";
  if (el("storm-note").textContent !== warning)
    el("storm-note").textContent = warning;
  const dash = el<HTMLButtonElement>("dash"),
    laugh = el<HTMLButtonElement>("laugh");
  dash.disabled = w.phase === "tutorial" || w.hero.dashCooldown > 0;
  el("dash-label").textContent =
    w.phase === "tutorial"
      ? "战斗中解锁"
      : w.hero.dashCooldown > 0
        ? `${w.hero.dashCooldown.toFixed(1)}s 冷却`
        : "L · 躲开攻击";
  laugh.disabled = w.phase === "tutorial" || w.hero.energy < 100;
  laugh.classList.toggle("ready", !laugh.disabled);
  el("laugh-label").textContent =
    w.phase === "tutorial"
      ? "战斗中解锁"
      : w.hero.energy < 100
        ? `笑能 ${w.hero.energy}%`
        : "空格 · 释放大笑";
  if (w.phase === "tutorial" && shownStep !== w.tutorialStep) {
    shownStep = w.tutorialStep;
    el("guide-number").textContent = shownStep < 3 ? `0${shownStep + 1}` : "✓";
    el("guide-title").textContent = guides[shownStep][0];
    el("guide-copy").textContent = guides[shownStep][1];
    el("guide-ready").hidden = shownStep < 3;
  }
  const now = performance.now();
  if (now - saveClock > 2000) {
    saveClock = now;
    saveProgress();
  }
}
el("start").addEventListener("click", () => start());
el("start-level1").addEventListener("click", () => start());
el("easy").addEventListener("click", () => setDifficulty("easy"));
el("normal").addEventListener("click", () => setDifficulty("normal"));
el("practice").addEventListener("click", () => start(true));
el("skip-practice").addEventListener("click", () => {
  clearInput();
  world.beginBattle(true);
  audio.unlock();
  saveProgress();
});
el("start-level2").addEventListener("click", () => enterLevel(2));
el("start-level3").addEventListener("click", () => enterLevel(3));
el("next-level").addEventListener("click", () =>
  enterLevel((world.level + 1) as 2 | 3, true),
);
el("begin-level").addEventListener("click", () => {
  el("level-briefing").hidden = true;
  world.pause(false);
  clearInput();
  audio.unlock();
  saveProgress();
});
el("resume").addEventListener("click", resume);
el("guide-ready").addEventListener("click", () => {
  clearInput();
  world.beginBattle();
  audio.unlock();
  saveProgress();
});
el("pause").addEventListener("click", () => pause(true));
el("continue").addEventListener("click", () => {
  audio.unlock();
  pause(false);
});
el("back-menu").addEventListener("click", goMenu);
el("result-menu").addEventListener("click", goMenu);
el("retry").addEventListener("click", () => {
  clearInput();
  world.retry();
  audio.unlock();
  saveProgress();
});
el("help").addEventListener("click", help);
el("menu-help").addEventListener("click", help);
el("close-help").addEventListener("click", closeHelp);
el("sound").addEventListener("click", () => {
  audio.enabled = !audio.enabled;
  if (audio.enabled) audio.unlock();
  else audio.suspend();
  el("sound").textContent = audio.enabled ? "♪" : "♩";
  el("sound").setAttribute(
    "aria-label",
    audio.enabled ? "关闭声音" : "开启声音",
  );
  el("sound").setAttribute("aria-pressed", String(!audio.enabled));
});
el("fullscreen").addEventListener("click", async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else if (el("stage").requestFullscreen)
      await el("stage").requestFullscreen();
    else toast("当前浏览器不支持全屏，横屏即可游玩");
  } catch {
    toast("当前浏览器未允许全屏");
  }
});
document.addEventListener("fullscreenchange", () =>
  el("fullscreen").setAttribute(
    "aria-label",
    document.fullscreenElement ? "退出全屏" : "进入全屏",
  ),
);
for (const name of ["attack", "defend"] as const) {
  const button = el<HTMLButtonElement>(name);
  button.addEventListener("pointerdown", (e) => {
    if (world.paused || button.disabled) return;
    e.preventDefault();
    button.setPointerCapture(e.pointerId);
    held[name].add(e.pointerId);
    button.classList.add("pressed");
    audio.unlock();
    if (name === "attack") world.attack();
  });
  const release = (e: PointerEvent) => {
    held[name].delete(e.pointerId);
    if (!held[name].size) button.classList.remove("pressed");
  };
  button.addEventListener("pointerup", release);
  button.addEventListener("pointercancel", release);
  button.addEventListener("lostpointercapture", release);
  button.addEventListener("click", (e) => {
    if (e.detail !== 0 || world.paused) return;
    audio.unlock();
    if (name === "attack") world.attack();
    else toast("按住 K 或触控按钮持续举盾");
  });
}
el("dash").addEventListener("click", () => {
  audio.unlock();
  world.dash();
});
el("laugh").addEventListener("click", () => {
  audio.unlock();
  world.laugh();
});
const joy = el("joystick");
function moveStick(e: PointerEvent) {
  const r = joy.getBoundingClientRect(),
    radius = r.width * 0.32;
  let x = e.clientX - r.left - r.width / 2,
    y = e.clientY - r.top - r.height / 2;
  const d = Math.hypot(x, y);
  if (d > radius) {
    x *= radius / d;
    y *= radius / d;
  }
  joystick = { x: x / radius, y: y / radius };
  el("stick").style.transform = `translate(${x}px,${y}px)`;
}
joy.addEventListener("pointerdown", (e) => {
  if (joyId !== null || world.paused) return;
  e.preventDefault();
  joyId = e.pointerId;
  joy.setPointerCapture(e.pointerId);
  moveStick(e);
  audio.unlock();
});
joy.addEventListener("pointermove", (e) => {
  if (e.pointerId === joyId) moveStick(e);
});
const endStick = (e: PointerEvent) => {
  if (e.pointerId === joyId) {
    joyId = null;
    joystick = { x: 0, y: 0 };
    el("stick").style.transform = "";
  }
};
joy.addEventListener("pointerup", endStick);
joy.addEventListener("pointercancel", endStick);
joy.addEventListener("lostpointercapture", endStick);
const gameKeys = [
  "KeyW",
  "KeyA",
  "KeyS",
  "KeyD",
  "ArrowUp",
  "ArrowLeft",
  "ArrowDown",
  "ArrowRight",
  "KeyJ",
  "KeyK",
  "KeyL",
  "Space",
];
document.addEventListener("keydown", (e) => {
  if (
    e.code === "Escape" &&
    (world.phase === "playing" || world.phase === "tutorial")
  ) {
    if (e.repeat) return;
    if (!el("level-briefing").hidden) return;
    if (!el("help-overlay").hidden) closeHelp();
    else pause(!world.paused);
    return;
  }
  if (!gameKeys.includes(e.code) || world.phase === "menu" || world.paused)
    return;
  e.preventDefault();
  keys.add(e.code);
  audio.unlock();
  if (!e.repeat && e.code === "KeyJ") world.attack();
  if (!e.repeat && e.code === "KeyL") world.dash();
  if (!e.repeat && e.code === "Space") world.laugh();
});
document.addEventListener("keyup", (e) => keys.delete(e.code));
function background() {
  clearInput();
  saveProgress();
  if (
    (world.phase === "tutorial" || world.phase === "playing") &&
    !world.paused
  )
    pause(true);
}
window.addEventListener("blur", background);
document.addEventListener("visibilitychange", () => {
  if (document.hidden) background();
});
window.addEventListener("pagehide", saveProgress);

// Read-only observation for playtests. No mutation or shortcuts to complete a level.
Object.defineProperty(window, "__naiwa", {
  value: Object.freeze({
    snapshot: () => ({ ...world.save(), paused: world.paused }),
  }),
  writable: false,
});
new GameScene3D(world, { input, frame, event });
frame();
