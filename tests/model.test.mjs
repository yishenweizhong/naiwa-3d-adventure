import test from "node:test";
import assert from "node:assert/strict";
import { World, decodeSave } from "../src/model.ts";

test("practice has no enemies and completes movement, attack and defense in order", () => {
  const w = new World();
  w.start(true);
  for (let i = 0; i < 100; i++) w.update(0.02, { x: 1, y: 0 });
  assert.equal(w.phase, "tutorial");
  assert.equal(w.enemies.length, 0);
  assert.equal(w.hero.hp, 120);
  assert.equal(w.tutorialStep, 1);
  w.attack();
  assert.equal(w.tutorialStep, 2);
  w.update(0.6, { x: 0, y: 0, defend: true });
  assert.equal(w.tutorialStep, 3);
  w.beginBattle();
  assert.equal(w.phase, "playing");
  assert.equal(w.wave, 1);
});

test("diagonal movement has the same speed as horizontal movement", () => {
  const a = new World();
  const b = new World();
  a.start(false);
  b.start(false);
  const ay = a.hero.y,
    ax = a.hero.x,
    by = b.hero.y,
    bx = b.hero.x;
  a.update(0.05, { x: 1, y: 0 });
  b.update(0.05, { x: 1, y: 1 });
  assert.ok(
    Math.abs(
      Math.hypot(a.hero.x - ax, a.hero.y - ay) -
        Math.hypot(b.hero.x - bx, b.hero.y - by),
    ) < 0.001,
  );
});

test("pause freezes gameplay time and position", () => {
  const w = new World();
  w.start(false);
  w.pause(true);
  const before = JSON.stringify(w.save());
  w.update(1, { x: 1, y: 1, attack: true });
  assert.equal(JSON.stringify(w.save()), before);
});

test("defense reduces incoming damage and invulnerability blocks repeated hits", () => {
  const w = new World();
  w.start(false);
  w.update(0.02, { x: 0, y: 0, defend: true });
  w.damageHero(20);
  assert.equal(w.hero.hp, 112);
  w.damageHero(20);
  assert.equal(w.hero.hp, 112);
});

test("empty waves advance to the boss and killing the boss wins exactly once", () => {
  const w = new World();
  w.start(false);
  w.enemies = [];
  w.update(0.02, { x: 0, y: 0 });
  w.update(2, { x: 0, y: 0 });
  assert.equal(w.wave, 2);
  w.enemies = [];
  w.update(0.02, { x: 0, y: 0 });
  w.update(2, { x: 0, y: 0 });
  assert.equal(w.wave, 3);
  const boss = w.enemies.find((e) => e.kind === "boss");
  assert.ok(boss);
  w.damageEnemy(boss, boss.hp + 1);
  assert.equal(w.phase, "won");
  assert.equal(w.enemies.length, 0);
});

test("defeat offers an unconditional fresh retry", () => {
  const w = new World();
  w.start(false);
  w.damageHero(500);
  assert.equal(w.phase, "defeat");
  w.retry();
  assert.equal(w.phase, "playing");
  assert.equal(w.hero.hp, 120);
  assert.equal(w.wave, 1);
  assert.equal(w.deaths, 1);
});

test("save restores exact active progress and rejects corrupt or out-of-bounds state", () => {
  const w = new World();
  w.start(false);
  w.update(0.05, { x: 1, y: 0 });
  const encoded = JSON.stringify(w.save());
  const save = decodeSave(encoded);
  assert.ok(save);
  const resumed = new World();
  resumed.restore(save);
  assert.equal(resumed.hero.x, w.hero.x);
  assert.equal(resumed.enemies.length, w.enemies.length);
  assert.equal(resumed.wave, w.wave);
  assert.equal(decodeSave("{broken"), null);
  const bad = JSON.parse(encoded);
  bad.hero.x = 50000;
  assert.equal(decodeSave(JSON.stringify(bad)), null);
});

test("large simulation delta remains stable and full-energy laugh damages enemies", () => {
  const w = new World();
  w.start(false);
  w.enemies[0].x = w.hero.x + 70;
  w.enemies[0].y = w.hero.y;
  w.hero.energy = 100;
  w.laugh();
  assert.equal(w.hero.energy, 0);
  assert.ok(w.enemies.length < 5 || w.enemies[0].hp < w.enemies[0].maxHp);
  w.update(30, { x: 0, y: 0 });
  assert.ok(Number.isFinite(w.hero.hp));
});

test("vertical dash follows the movement direction without horizontal drift", () => {
  const w = new World();
  w.start(false);
  w.update(0.02, { x: 0, y: -1 });
  const beforeX = w.hero.x,
    beforeY = w.hero.y;
  w.dash();
  w.update(0.1, { x: 0, y: 0 });
  assert.equal(w.hero.x, beforeX);
  assert.ok(w.hero.y < beforeY - 60);
});
