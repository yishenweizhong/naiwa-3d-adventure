import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { World, decodeSave, ARENA } from "../src/model.ts";

function third() {
  const w = new World();
  w.unlockedLevel = 3;
  assert.equal(w.start(false, 3), true);
  return w;
}

test("third chapter stays locked until second victory and nextLevel respects phase", () => {
  const w = new World();
  w.unlockedLevel = 2;
  w.start(false, 2);
  assert.equal(w.start(false, 3), false);
  assert.equal(w.nextLevel(), false);
  w.spawnWave(4);
  w.damageEnemy(w.enemies[0], 999);
  assert.equal(w.unlockedLevel, 3);
  assert.equal(w.nextLevel(), true);
  assert.equal(w.level, 3);
  assert.equal(w.hero.hp, 120);
});
test("third chapter progresses through four waves then a 920HP boss", () => {
  const w = third();
  const counts = [];
  for (let wave = 1; wave <= 5; wave++) {
    counts.push(w.enemies.length);
    if (wave === 5) assert.equal(w.enemies[0].maxHp, 920);
    for (const enemy of [...w.enemies]) w.damageEnemy(enemy, 9999);
    if (wave < 5) w.update(1.8, { x: 0, y: 0 });
  }
  assert.deepEqual(counts, [7, 8, 9, 10, 1]);
  assert.equal(w.kills, 35);
  assert.equal(w.phase, "won");
  assert.equal(w.nextLevel(), false);
  assert.ok(decodeSave(JSON.stringify(w.save())));
});
test("third retry resets hazards, HP and kills without losing chapter unlock", () => {
  const w = third();
  w.spawnWave(4);
  w.update(2, { x: 0, y: 0 });
  w.update(1.1, { x: 0, y: 0 });
  w.damageHero(999);
  w.retry();
  assert.equal(w.level, 3);
  assert.equal(w.unlockedLevel, 3);
  assert.equal(w.wave, 1);
  assert.equal(w.hero.hp, 120);
  assert.equal(w.kills, 0);
  assert.deepEqual(w.windWalls, []);
});
function warned() {
  const w = third();
  w.enemies.forEach((e) => (e.stun = 10));
  w.update(2, { x: 0, y: 0 });
  w.update(1.05, { x: 0, y: 0 });
  assert.equal(w.windWalls.length, 1);
  assert.ok(w.windWalls[0].windup > 0);
  assert.equal(w.hero.hp, 120);
  return w;
}
test("wind wall warns without moving, then sweeps from left to right", () => {
  const w = warned();
  const wall = w.windWalls[0];
  const x = wall.x;
  w.update(0.3, { x: 0, y: 0 });
  assert.equal(wall.x, x);
  w.update(1.1, { x: 0, y: 0 });
  assert.ok(wall.x > x + 30);
});
function crossing(defend = false, gap = false, dash = false) {
  const w = warned();
  const wall = w.windWalls[0];
  wall.windup = 0;
  wall.x = w.hero.x - 30;
  w.hero.y = gap ? wall.gapY : ARENA.bottom;
  if (dash) w.hero.invulnerable = 0.3;
  w.update(0.2, { x: 0, y: 0, defend });
  return w;
}
test("wind wall hits outside its gap once, defense reduces damage", () => {
  const w = crossing();
  assert.equal(w.hero.hp, 100);
  w.update(1, { x: 0, y: 0 });
  assert.equal(w.hero.hp, 100);
  assert.equal(crossing(true).hero.hp, 112);
});
test("safe gap and dash invulnerability avoid wind wall damage", () => {
  assert.equal(crossing(false, true).hero.hp, 120);
  assert.equal(crossing(false, false, true).hero.hp, 120);
});
test("pause and v3 save preserve moving wind walls and cadence", () => {
  const w = warned();
  w.pause(true);
  const saved = w.save();
  w.update(2, { x: 1, y: 1, attack: true });
  assert.deepEqual(w.save(), saved);
  assert.equal(saved.version, 3);
  const decoded = decodeSave(JSON.stringify(saved));
  assert.ok(decoded);
  const restored = new World();
  restored.restore(decoded);
  assert.deepEqual(restored.windWalls, w.windWalls);
  assert.equal(restored.windClock, w.windClock);
  assert.equal(restored.windIndex, w.windIndex);
});
test("authentic v2 active save keeps second battle and does not unlock third", () => {
  const old = JSON.parse(
    readFileSync(new URL("./fixtures/legacy-v2-active.json", import.meta.url)),
  );
  const decoded = decodeSave(JSON.stringify(old));
  assert.ok(decoded);
  assert.equal(decoded.version, 3);
  assert.equal(decoded.level, 2);
  assert.equal(decoded.unlockedLevel, 2);
  assert.deepEqual(decoded.hazards, old.hazards);
  assert.deepEqual(decoded.enemies, old.enemies);
  assert.deepEqual(decoded.windWalls, []);
});
test("authentic v2 second victory unlocks third on migration", () => {
  const decoded = decodeSave(
    readFileSync(
      new URL("./fixtures/legacy-v2-won.json", import.meta.url),
      "utf8",
    ),
  );
  assert.ok(decoded);
  assert.equal(decoded.version, 3);
  assert.equal(decoded.level, 2);
  assert.equal(decoded.unlockedLevel, 3);
});
test("corrupt wind gap or wind wall in a previous chapter is rejected", () => {
  const w = warned();
  const bad = w.save();
  bad.windWalls[0].gapHeight = -100;
  assert.equal(decodeSave(JSON.stringify(bad)), null);
  const misplaced = w.save();
  misplaced.level = 2;
  assert.equal(decodeSave(JSON.stringify(misplaced)), null);
});
test("third boss enrages and emits a denser volley", () => {
  const w = third();
  w.spawnWave(5);
  w.windClock = 10;
  const boss = w.enemies[0];
  boss.x = 600;
  boss.y = 470;
  boss.cooldown = 0;
  w.hero.x = 200;
  w.hero.y = 470;
  w.update(0.02, { x: 0, y: 0 });
  w.hero.y = 285;
  w.update(1.2, { x: 0, y: 0 });
  const normal = w.shots.filter((s) => s.team === "enemy").length;
  w.shots = [];
  boss.hp = 450;
  boss.cooldown = 0;
  w.update(0.02, { x: 0, y: 0 });
  w.update(1.2, { x: 0, y: 0 });
  assert.equal(boss.enraged, true);
  assert.equal(normal, 7);
  assert.equal(w.shots.filter((s) => s.team === "enemy").length, 9);
});
