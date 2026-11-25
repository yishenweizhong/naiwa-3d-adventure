import test from "node:test";
import assert from "node:assert/strict";
import { World } from "../src/model.ts";

test("hit identifies the damaged enemy, even with two nearby enemies", () => {
  const world = new World();
  world.start(false);
  const [first, second] = world.enemies;
  second.x = first.x + 1;
  second.y = first.y;
  world.events = [];
  world.damageEnemy(second, 18);
  const hit = world.events.find(e => e.kind === "hit");
  assert.equal(hit.targetId, second.id);
  assert.equal(first.hp, first.maxHp);
  assert.equal(second.hp, second.maxHp - 18);
});

test("fatal hit keeps target identity after the actor leaves the world", () => {
  const world = new World();
  world.start(false);
  const enemy = world.enemies[0];
  world.events = [];
  world.damageEnemy(enemy, enemy.hp);
  assert.equal(world.enemies.includes(enemy), false);
  assert.equal(world.events.find(e => e.kind === "hit").targetId, enemy.id);
  const count = world.events.length;
  world.damageEnemy(enemy, 18);
  assert.equal(world.events.length, count);
});
