import test from "node:test";
import assert from "node:assert/strict";
import { heroMotion } from "../src/hero-motion.ts";

test("dash event still has a visible pose after a slow physics frame", () => {
  assert.equal(heroMotion({phase:"playing",dashTime:0,defending:false,moving:true,action:"dash",actionTime:.22}),"dash");
});

const state = { phase: "playing", dashTime: 0, defending: false, moving: false, action: "", actionTime: 0 };
test("hero follows combat actions before locomotion", () => {
  assert.equal(heroMotion({ ...state, moving: true }), "walk");
  assert.equal(heroMotion({ ...state, moving: true, defending: true }), "defend");
  assert.equal(heroMotion({ ...state, defending: true, dashTime: .1 }), "dash");
  assert.equal(heroMotion({ ...state, action: "laugh", actionTime: .2 }), "laugh");
  assert.equal(heroMotion({ ...state, action: "attack", actionTime: 0 }), "idle");
});
test("menu and finished battles return to idle", () => {
  assert.equal(heroMotion({ ...state, phase: "menu", moving: true }), "idle");
  assert.equal(heroMotion({ ...state, phase: "won", defending: true }), "idle");
  assert.equal(heroMotion({ ...state, phase: "tutorial", moving: true }), "walk");
});
