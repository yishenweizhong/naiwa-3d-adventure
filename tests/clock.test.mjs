import test from "node:test";
import assert from "node:assert/strict";
import { World } from "../src/model.ts";
import { advanceWorld } from "../src/clock.ts";

test("low render frame rate preserves battle time and collision steps", () => {
  const fast=new World(), slow=new World();
  fast.start(false); slow.start(false);
  for (let i=0;i<120;i++) advanceWorld(fast,1/60,{x:1,y:0,attack:true});
  for (let i=0;i<10;i++) advanceWorld(slow,.2,{x:1,y:0,attack:true});
  assert.ok(Math.abs(fast.elapsed-slow.elapsed)<.0001);
  assert.ok(Math.abs(fast.hero.x-slow.hero.x)<.0001);
  assert.ok(Math.abs(fast.hero.hp-slow.hero.hp)<=18);
});

test("pause and background delays do not advance hidden combat", () => {
  const w=new World(); w.start(false); w.pause(true);
  advanceWorld(w,.2,{x:1,y:0});
  assert.equal(w.elapsed,0);
});
