import test from "node:test";
import assert from "node:assert/strict";
import { World } from "../src/model.ts";

test("practice can be skipped at every step without bypassing level locks", () => {
  for (const step of [0, 1, 2, 3]) {
    const w = new World();
    w.start(true);
    w.tutorialStep = step;
    w.beginBattle(true);
    assert.equal(w.phase, "playing");
    assert.equal(w.wave, 1);
    assert.equal(w.hero.hp, 120);
    assert.ok(w.enemies.length);
    assert.equal(w.unlockedLevel, 1);
    assert.equal(w.start(false, 3), false);
  }
});

test("normal tutorial completion remains gated", () => {
  const w = new World();
  w.start(true);
  w.beginBattle();
  assert.equal(w.phase, "tutorial");
});
