import test from "node:test";
import assert from "node:assert/strict";
import { World, decodeSave } from "../src/model.ts";
import { starsFor, readRecords, updateRecord } from "../src/progress.ts";

test("easy mode reduces actual damage, improves healing, and persists through retry", () => {
  const w=new World();
  w.difficulty="easy"; w.start(false); w.damageHero(20);
  assert.equal(w.hero.hp,108);
  w.hero.invulnerable=0; w.hero.defending=true; w.damageHero(20);
  assert.equal(w.hero.hp,103);
  w.hero.hp=50; w.spawnWave(2); assert.equal(w.hero.hp,90);
  const saved=decodeSave(JSON.stringify(w.save())); assert.equal(saved.difficulty,"easy");
  const restored=new World(); restored.restore(saved); restored.retry();
  assert.equal(restored.difficulty,"easy");
});
test("legacy saves default to standard, invalid difficulty is rejected", () => {
  const w=new World(); w.start(false); const s=w.save(); delete s.difficulty;
  assert.equal(decodeSave(JSON.stringify(s)).difficulty,"normal");
  s.difficulty="godmode"; assert.equal(decodeSave(JSON.stringify(s)),null);
});
test("stars require victory, and separately reward remaining health and speed", () => {
  assert.equal(starsFor("defeat",120,10,1),0);
  assert.equal(starsFor("won",20,100,1),1);
  assert.equal(starsFor("won",60,100,1),2);
  assert.equal(starsFor("won",60,90,1),3);
});
test("records never downgrade stars and separate easy and standard accomplishments", () => {
  let records=readRecords(null);
  records=updateRecord(records,1,"easy",3,80);
  records=updateRecord(records,1,"easy",1,120);
  records=updateRecord(records,1,"normal",2,95);
  assert.deepEqual(records["easy-1"],{stars:3,time:80});
  assert.deepEqual(records["normal-1"],{stars:2,time:95});
  assert.deepEqual(readRecords(JSON.stringify(records)),records);
  assert.deepEqual(readRecords('{"easy-1":{"stars":99,"time":-1}}'),{});
  assert.deepEqual(readRecords("{broken"),{});
});
