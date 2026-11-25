import test from "node:test";
import assert from "node:assert/strict";
import { World, decodeSave } from "../src/model.ts";

function second() {
  const w = new World();
  w.unlockedLevel = 2;
  w.start(false, 2);
  assert.equal(w.level, 2);
  return w;
}

test("second level stays locked until the first boss is defeated", () => {
  const w = new World();
  w.start(false);
  assert.equal(w.start(false, 2), false);
  assert.equal(w.level, 1);
  assert.equal(w.nextLevel(), false);
  w.spawnWave(3);
  w.damageEnemy(w.enemies[0], 999);
  assert.equal(w.unlockedLevel, 2);
  assert.equal(w.nextLevel(), true);
  assert.equal(w.level, 2);
  assert.equal(w.wave, 1);
  assert.equal(w.hero.hp, 120);
});

test("second chapter has four distinct waves and completes after its boss", () => {
  const w = second();
  const counts = [];
  for (let wave = 1; wave <= 4; wave++) {
    counts.push(w.enemies.length);
    if (wave < 4) {
      for (const e of [...w.enemies]) w.damageEnemy(e, 999);
      w.update(1.8, { x: 0, y: 0 });
      assert.equal(w.wave, wave + 1);
    }
  }
  assert.deepEqual(counts, [6, 7, 8, 1]);
  assert.equal(w.enemies[0].maxHp, 640);
  w.damageEnemy(w.enemies[0], 999);
  assert.equal(w.phase, "won");
  assert.equal(w.kills, 22);
  assert.equal(w.unlockedLevel, 3);
  assert.equal(w.nextLevel(), true);
  assert.equal(w.level, 3);
});

test("retry resets the second chapter instead of sending the player to chapter one", () => {
  const w = second();
  w.spawnWave(3);
  w.update(4, { x: 0, y: 0 });
  w.hero.invulnerable = 0;
  w.damageHero(999);
  w.retry();
  assert.equal(w.level, 2);
  assert.equal(w.wave, 1);
  assert.equal(w.hero.hp, 120);
  assert.equal(w.kills, 0);
  assert.equal(w.hazards.length, 0);
  assert.equal(w.unlockedLevel, 2);
  w.start(true);
  assert.equal(w.unlockedLevel, 2);
});

test("rusher telegraphs and charges toward the old locked position", () => {
  const w = second();
  const e = w.enemies.find((e) => e.kind === "rusher");
  assert.ok(e);
  w.enemies = [e];
  e.x = 500;
  e.y = 470;
  e.cooldown = 0;
  w.update(0.02, { x: 0, y: 0 });
  assert.ok(e.windup > 0);
  assert.equal(e.aimX, 280);
  w.hero.x = 150;
  w.hero.y = 350;
  w.update(0.8, { x: 0, y: 0 });
  assert.ok(e.chargeTime > 0);
  assert.equal(e.chargeX, -1);
  assert.equal(e.chargeY, 0);
  const beforeX = e.x;
  w.update(0.1, { x: 0, y: 0 });
  assert.ok(e.x < beforeX - 40);
  assert.equal(w.hero.hp, 120);
});

function warned() {
  const w = second();
  w.enemies.forEach((e) => (e.stun = 10));
  w.update(2, { x: 0, y: 0 });
  w.update(1.55, { x: 0, y: 0 });
  assert.equal(w.hazards.length, 1);
  assert.ok(w.hazards[0].windup > 0);
  assert.equal(w.hero.hp, 120);
  return w;
}
test("lightning warns before impact, then damages a hero who stays inside", () => {
  const w = warned();
  w.update(1.2, { x: 0, y: 0 });
  assert.equal(w.hero.hp, 102);
});
test("leaving the lightning radius avoids damage; defense reduces its impact", () => {
  const dodged = warned();
  dodged.hero.x += dodged.hazards[0].radius + 10;
  dodged.update(1.2, { x: 0, y: 0 });
  assert.equal(dodged.hero.hp, 120);
  const defended = warned();
  defended.update(1.2, { x: 0, y: 0, defend: true });
  assert.equal(defended.hero.hp, 112);
});
test("pause freezes lightning and rusher state and v2 save restores them", () => {
  const w = warned();
  w.pause(true);
  const encoded = JSON.stringify(w.save());
  w.update(1, { x: 1, y: 0, attack: true });
  assert.equal(JSON.stringify(w.save()), encoded);
  const restored = new World();
  const decoded = decodeSave(encoded);
  assert.ok(decoded);
  restored.restore(decoded);
  assert.equal(restored.level, 2);
  assert.equal(restored.unlockedLevel, 2);
  assert.deepEqual(restored.hazards, w.hazards);
  assert.deepEqual(restored.enemies, w.enemies);
});
test("legacy first-chapter saves migrate and completed saves unlock chapter two", () => {
  const w = new World();
  w.start(false);
  w.spawnWave(3);
  w.damageEnemy(w.enemies[0], 999);
  const legacy = w.save();
  legacy.version = 1;
  for (const key of [
    "level",
    "unlockedLevel",
    "hazards",
    "hazardClock",
    "movement",
  ])
    delete legacy[key];
  for (const enemy of legacy.enemies) {
    for (const key of ["chargeTime", "chargeX", "chargeY"]) delete enemy[key];
  }
  const migrated = decodeSave(JSON.stringify(legacy));
  assert.ok(migrated);
  assert.equal(migrated.version, 3);
  assert.equal(migrated.level, 1);
  assert.equal(migrated.unlockedLevel, 2);
  assert.deepEqual(migrated.hazards, []);
});
test("v2 rejects a forged locked chapter and corrupt lightning radius", () => {
  const w = warned();
  const forged = w.save();
  forged.unlockedLevel = 1;
  assert.equal(decodeSave(JSON.stringify(forged)), null);
  const corrupt = w.save();
  corrupt.hazards[0].radius = 9999;
  assert.equal(decodeSave(JSON.stringify(corrupt)), null);
});
