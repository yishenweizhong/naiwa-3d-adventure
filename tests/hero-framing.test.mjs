import test from "node:test";
import assert from "node:assert/strict";
import { heroFraming } from "../src/hero-framing.ts";

test("battle retains at least 90% of an upright character's projected height", () => {
  const f=heroFraming(false,false);
  const elevation=Math.atan2(f.cameraY-f.lookY,f.cameraZ-f.lookZ);
  assert.ok(Math.cos(elevation)>=.9);
  assert.ok(f.scale>=1.9 && f.scale<=2.1);
});

test("menu changes with portrait viewport while battle framing stays stable", () => {
  assert.deepEqual(heroFraming(false,true),heroFraming(false,false));
  assert.ok(heroFraming(true,true).scale<heroFraming(true,false).scale);
  assert.equal(heroFraming(true,false).zoom,1);
  assert.ok(heroFraming(true,true).zoom>1);
});
