import { LEVELS, type LevelId, type EnemyKind } from "./levels.ts";

export const WIDTH = 1280;
export const HEIGHT = 720;
export const ARENA = { left: 68, right: 1212, top: 272, bottom: 628 };
export const RUSHER = { speed: 540, duration: 0.42, radius: 44, windup: 0.75 };
export const WIND = { halfWidth: 22, windup: 1.15, speed: 240, damage: 20 };

export type Phase = "menu" | "tutorial" | "playing" | "defeat" | "won";
export type Input = {
  x: number;
  y: number;
  attack?: boolean;
  defend?: boolean;
};
export type Hero = {
  x: number;
  y: number;
  hp: number;
  energy: number;
  facing: number;
  invulnerable: number;
  attackCooldown: number;
  dashCooldown: number;
  dashTime: number;
  dashX: number;
  dashY: number;
  defending: boolean;
};
export type Enemy = {
  id: number;
  kind: EnemyKind;
  x: number;
  y: number;
  hp: number;
  maxHp: number;
  speed: number;
  cooldown: number;
  windup: number;
  aimX: number;
  aimY: number;
  stun: number;
  enraged: boolean;
  chargeTime: number;
  chargeX: number;
  chargeY: number;
};
export type Shot = {
  id: number;
  team: "hero" | "enemy";
  x: number;
  y: number;
  vx: number;
  vy: number;
  life: number;
  damage: number;
};
export type Pickup = { id: number; x: number; y: number; life: number };
export type Hazard = {
  id: number;
  x: number;
  y: number;
  radius: number;
  windup: number;
  life: number;
  damage: number;
};
export type WindWall = {
  id: number;
  x: number;
  gapY: number;
  gapHeight: number;
  windup: number;
  life: number;
  speed: number;
  damage: number;
  hit: boolean;
};
export type GameEvent = {
  kind:
    | "shot"
    | "hit"
    | "hurt"
    | "block"
    | "dash"
    | "laugh"
    | "heal"
    | "wave"
    | "thunder"
    | "win"
    | "defeat";
  x: number;
  y: number;
  value?: number;
};
export type Save = {
  version: 3;
  level: LevelId;
  unlockedLevel: LevelId;
  hazards: Hazard[];
  hazardClock: number;
  movement: { x: number; y: number };
  windWalls: WindWall[];
  windClock: number;
  windIndex: number;
  phase: Phase;
  wave: number;
  elapsed: number;
  kills: number;
  deaths: number;
  serial: number;
  transition: number;
  tutorialStep: number;
  tutorialDistance: number;
  tutorialDefense: number;
  hero: Hero;
  enemies: Enemy[];
  shots: Shot[];
  pickups: Pickup[];
};

const clamp = (v: number, min: number, max: number) =>
  Math.max(min, Math.min(max, v));
const distance = (a: { x: number; y: number }, b: { x: number; y: number }) =>
  Math.hypot(a.x - b.x, a.y - b.y);
const direction = (x: number, y: number) => {
  const n = Math.hypot(x, y);
  return n > 0 ? { x: x / n, y: y / n } : { x: 0, y: 0 };
};
const freshHero = (): Hero => ({
  x: 280,
  y: 470,
  hp: 120,
  energy: 30,
  facing: 1,
  invulnerable: 0,
  attackCooldown: 0,
  dashCooldown: 0,
  dashTime: 0,
  dashX: 1,
  dashY: 0,
  defending: false,
});

export class World {
  level: LevelId = 1;
  unlockedLevel: LevelId = 1;
  phase: Phase = "menu";
  paused = false;
  hero = freshHero();
  enemies: Enemy[] = [];
  shots: Shot[] = [];
  pickups: Pickup[] = [];
  hazards: Hazard[] = [];
  hazardClock = 3.5;
  events: GameEvent[] = [];
  wave = 0;
  elapsed = 0;
  kills = 0;
  deaths = 0;
  serial = 0;
  transition = 0;
  tutorialStep = 0;
  tutorialDistance = 0;
  tutorialDefense = 0;
  movement = { x: 1, y: 0 };
  windWalls: WindWall[] = [];
  windClock = 3;
  windIndex = 0;

  start(practice = true, level: LevelId = 1) {
    if (!LEVELS[level] || level > this.unlockedLevel) return false;
    this.level = level;
    this.hero = freshHero();
    this.enemies = [];
    this.shots = [];
    this.pickups = [];
    this.hazards = [];
    this.hazardClock = 3.5;
    this.movement = { x: 1, y: 0 };
    this.windWalls = [];
    this.windClock = 3;
    this.windIndex = 0;
    this.events = [];
    this.elapsed = 0;
    this.kills = 0;
    this.wave = 0;
    this.serial = 0;
    this.transition = 0;
    this.tutorialStep = 0;
    this.tutorialDistance = 0;
    this.tutorialDefense = 0;
    this.paused = false;
    this.phase = practice && level === 1 ? "tutorial" : "playing";
    if (this.phase === "playing") this.spawnWave(1);
    return true;
  }

  beginBattle(skipPractice = false) {
    if (this.phase !== "tutorial" || (!skipPractice && this.tutorialStep < 3)) return;
    this.phase = "playing";
    this.hero = freshHero();
    this.shots = [];
    this.spawnWave(1);
  }

  retry() {
    this.deaths++;
    this.start(false, this.level);
  }
  nextLevel() {
    if (this.level >= 3 || this.phase !== "won") return false;
    return this.start(false, (this.level + 1) as LevelId);
  }
  pause(value: boolean) {
    this.paused = value;
    this.hero.defending = false;
  }
  private active() {
    return (
      !this.paused && (this.phase === "playing" || this.phase === "tutorial")
    );
  }

  attack() {
    if (!this.active() || this.hero.attackCooldown > 0 || this.hero.defending)
      return;
    if (this.phase === "tutorial" && this.tutorialStep === 1)
      this.tutorialStep = 2;
    const target = this.enemies.reduce<Enemy | undefined>(
      (a, e) => (!a || distance(this.hero, e) < distance(this.hero, a) ? e : a),
      undefined,
    );
    const aim = target
      ? direction(target.x - this.hero.x, target.y - this.hero.y)
      : { x: this.hero.facing, y: 0 };
    this.hero.facing = aim.x < 0 ? -1 : 1;
    this.hero.attackCooldown = 0.24;
    this.shots.push({
      id: ++this.serial,
      team: "hero",
      x: this.hero.x + aim.x * 28,
      y: this.hero.y + aim.y * 28,
      vx: aim.x * 650,
      vy: aim.y * 650,
      life: 1.8,
      damage: 18,
    });
    this.events.push({ kind: "shot", x: this.hero.x, y: this.hero.y });
  }

  dash() {
    if (
      !this.active() ||
      this.phase === "tutorial" ||
      this.hero.dashCooldown > 0
    )
      return;
    const aim =
      Math.hypot(this.movement.x, this.movement.y) > 0
        ? direction(this.movement.x, this.movement.y)
        : { x: this.hero.facing, y: 0 };
    this.hero.dashX = aim.x;
    this.hero.dashY = aim.y;
    this.hero.dashTime = 0.18;
    this.hero.dashCooldown = 2.5;
    this.hero.invulnerable = Math.max(this.hero.invulnerable, 0.3);
    this.events.push({ kind: "dash", x: this.hero.x, y: this.hero.y });
  }

  laugh() {
    if (!this.active() || this.phase === "tutorial" || this.hero.energy < 100)
      return;
    this.hero.energy = 0;
    this.hero.invulnerable = 0.9;
    this.events.push({ kind: "laugh", x: this.hero.x, y: this.hero.y });
    for (const e of [...this.enemies])
      if (distance(e, this.hero) < 245) {
        this.damageEnemy(e, e.kind === "boss" ? 90 : 80);
        e.stun = 1.5;
      }
    this.hero.energy = 0;
    this.shots = this.shots.filter((s) => s.team === "hero");
  }

  damageHero(amount: number) {
    if (
      this.phase !== "playing" ||
      this.hero.invulnerable > 0 ||
      !Number.isFinite(amount) ||
      amount <= 0
    )
      return;
    const damage = this.hero.defending ? Math.ceil(amount * 0.4) : amount;
    this.hero.hp = Math.max(0, this.hero.hp - damage);
    this.hero.invulnerable = 0.75;
    if (this.hero.defending)
      this.hero.energy = Math.min(100, this.hero.energy + 6);
    this.events.push({
      kind: this.hero.defending ? "block" : "hurt",
      x: this.hero.x,
      y: this.hero.y,
      value: damage,
    });
    if (!this.hero.hp) {
      this.phase = "defeat";
      this.hero.defending = false;
      this.events.push({ kind: "defeat", x: this.hero.x, y: this.hero.y });
    }
  }

  damageEnemy(enemy: Enemy, damage: number) {
    if (!this.enemies.includes(enemy) || this.phase !== "playing") return;
    enemy.hp -= damage;
    this.hero.energy = Math.min(100, this.hero.energy + 8);
    this.events.push({ kind: "hit", x: enemy.x, y: enemy.y, value: damage });
    if (enemy.hp <= 0) {
      this.kills++;
      this.enemies = this.enemies.filter((e) => e !== enemy);
      if (enemy.kind === "boss") {
        this.phase = "won";
        this.enemies = [];
        this.shots = [];
        this.hazards = [];
        this.windWalls = [];
        this.unlockedLevel = Math.max(
          this.unlockedLevel,
          Math.min(3, this.level + 1),
        ) as LevelId;
        this.events.push({ kind: "win", x: enemy.x, y: enemy.y });
      } else if (this.kills % 3 === 0) {
        this.pickups.push({
          id: ++this.serial,
          x: enemy.x,
          y: enemy.y,
          life: 18,
        });
      }
    }
  }

  spawnWave(wave: number) {
    const config = LEVELS[this.level];
    const kinds = config.waves[wave - 1];
    if (!kinds) return;
    this.wave = wave;
    this.transition = 0;
    this.shots = [];
    this.hazards = [];
    this.hazardClock = 3.5;
    this.windWalls = [];
    this.windClock = 3;
    this.enemies = kinds.map((kind, i) => {
      const maxHp =
        kind === "boss"
          ? config.bossHp
          : this.level >= 2
            ? kind === "rusher"
              ? this.level === 3
                ? 78
                : 66
              : kind === "mage"
                ? this.level === 3
                  ? 72
                  : 64
                : this.level === 3
                  ? 60
                  : 54
            : kind === "mage"
              ? 48
              : 44;
      return {
        id: ++this.serial,
        kind,
        x: kind === "boss" ? 1010 : 890 + (i % 3) * 95,
        y: kind === "boss" ? 445 : 310 + Math.floor(i / 3) * 104 + (i % 3) * 28,
        hp: maxHp,
        maxHp,
        speed:
          kind === "boss"
            ? this.level === 3
              ? 88
              : this.level === 2
                ? 80
                : 72
            : kind === "rusher"
              ? this.level === 3
                ? 96
                : 88
              : kind === "mage"
                ? this.level === 3
                  ? 55
                  : this.level === 2
                    ? 48
                    : 42
                : 64 +
                  i * 3 +
                  (this.level === 3 ? 15 : this.level === 2 ? 9 : 0),
        cooldown: 0.9 + i * 0.25,
        windup: 0,
        aimX: 0,
        aimY: 0,
        stun: 0,
        enraged: false,
        chargeTime: 0,
        chargeX: 0,
        chargeY: 0,
      } as Enemy;
    });
    if (wave > 1) this.hero.hp = Math.min(120, this.hero.hp + 25);
    this.events.push({ kind: "wave", x: 640, y: 360, value: wave });
  }

  update(delta: number, input: Input) {
    if (!this.active() || !Number.isFinite(delta) || delta <= 0) return;
    // Fixed substeps preserve collision checks after frame stalls; excess background time is discarded.
    let left = Math.min(delta, 2);
    while (left > 0.00001 && this.active()) {
      const dt = Math.min(left, 0.04);
      left -= dt;
      this.step(dt, input);
    }
  }

  private step(dt: number, input: Input) {
    const h = this.hero;
    const dx = Number.isFinite(input.x) ? clamp(input.x, -1, 1) : 0;
    const dy = Number.isFinite(input.y) ? clamp(input.y, -1, 1) : 0;
    const move = direction(dx, dy);
    h.defending = !!input.defend && h.dashTime <= 0;
    h.invulnerable = Math.max(0, h.invulnerable - dt);
    h.attackCooldown = Math.max(0, h.attackCooldown - dt);
    h.dashCooldown = Math.max(0, h.dashCooldown - dt);
    const before = { x: h.x, y: h.y };
    if (h.dashTime > 0) {
      h.x += h.dashX * 810 * dt;
      h.y += h.dashY * 810 * dt;
      h.dashTime = Math.max(0, h.dashTime - dt);
    } else {
      const speed = h.defending ? 110 : 230;
      h.x += move.x * speed * dt;
      h.y += move.y * speed * dt;
      if (dx || dy) {
        this.movement = move;
        if (dx) h.facing = dx < 0 ? -1 : 1;
      }
    }
    h.x = clamp(h.x, ARENA.left, ARENA.right);
    h.y = clamp(h.y, ARENA.top, ARENA.bottom);
    if (input.attack) this.attack();
    if (this.phase === "tutorial") {
      if (this.tutorialStep === 0) {
        this.tutorialDistance += distance(before, h);
        if (this.tutorialDistance >= 80) this.tutorialStep = 1;
      }
      if (this.tutorialStep === 2 && h.defending) {
        this.tutorialDefense += dt;
        if (this.tutorialDefense >= 0.45) this.tutorialStep = 3;
      }
    } else {
      this.elapsed += dt;
      if (!this.enemies.length) {
        if (!this.transition) this.transition = 1.5;
        this.transition -= dt;
        if (this.transition <= 0) this.spawnWave(this.wave + 1);
      }
      for (const e of [...this.enemies]) this.updateEnemy(e, dt);
      if (this.level === 2 && this.phase === "playing" && this.enemies.length) {
        this.updateHazards(dt);
      }
      if (this.level === 3 && this.phase === "playing" && this.enemies.length) {
        this.updateWind(dt);
      }
    }
    this.updateShots(dt);
    for (const item of this.pickups) {
      item.life -= dt;
      if (distance(h, item) < 46 && h.hp < 120) {
        h.hp = Math.min(120, h.hp + 28);
        item.life = 0;
        this.events.push({ kind: "heal", x: h.x, y: h.y, value: 28 });
      }
    }
    this.pickups = this.pickups.filter((p) => p.life > 0);
  }

  private updateEnemy(e: Enemy, dt: number) {
    if (this.phase !== "playing") return;
    e.cooldown = Math.max(-2, e.cooldown - dt);
    if (e.stun > 0) {
      e.stun -= dt;
      return;
    }
    if (e.chargeTime > 0) {
      e.x = clamp(e.x + e.chargeX * RUSHER.speed * dt, ARENA.left, ARENA.right);
      e.y = clamp(e.y + e.chargeY * RUSHER.speed * dt, ARENA.top, ARENA.bottom);
      e.chargeTime = Math.max(0, e.chargeTime - dt);
      if (distance(e, this.hero) < RUSHER.radius) {
        this.damageHero(16);
        e.chargeTime = 0;
      }
      return;
    }
    const d = distance(e, this.hero);
    const boss = e.kind === "boss";
    e.enraged = boss && e.hp < e.maxHp / 2;
    if (e.windup > 0) {
      e.windup -= dt;
      if (e.windup <= 0) {
        if (e.kind === "mage") this.enemyShot(e, 1);
        else if (e.kind === "rusher") {
          const aim = direction(e.aimX - e.x, e.aimY - e.y);
          e.chargeX = aim.x;
          e.chargeY = aim.y;
          e.chargeTime = RUSHER.duration;
        } else if (boss) {
          if (
            distance(this.hero, { x: e.aimX, y: e.aimY }) <
            LEVELS[this.level].bossRadius
          )
            this.damageHero(LEVELS[this.level].bossDamage[Number(e.enraged)]);
          this.events.push({ kind: "hit", x: e.aimX, y: e.aimY });
          this.enemyShot(e, LEVELS[this.level].bossShots[Number(e.enraged)]);
        } else if (distance(e, this.hero) < 64) this.damageHero(10);
        e.cooldown =
          e.kind === "rusher"
            ? 2.4
            : boss
              ? LEVELS[this.level].bossCooldown[Number(e.enraged)]
              : e.kind === "mage"
                ? 2.1
                : 1.25;
      }
      return;
    }
    const desired = boss
      ? 165
      : e.kind === "mage"
        ? 270
        : e.kind === "rusher"
          ? 155
          : 40;
    if (d > desired) {
      const v = direction(this.hero.x - e.x, this.hero.y - e.y);
      e.x += v.x * e.speed * dt;
      e.y += v.y * e.speed * dt;
    }
    if (
      e.cooldown <= 0 &&
      d <
        (boss ? 640 : e.kind === "mage" ? 550 : e.kind === "rusher" ? 410 : 55)
    ) {
      e.windup = boss
        ? LEVELS[this.level].bossWindup
        : e.kind === "rusher"
          ? RUSHER.windup
          : e.kind === "mage"
            ? 0.65
            : 0.6;
      e.aimX = this.hero.x;
      e.aimY = this.hero.y;
    }
    for (const other of this.enemies) {
      if (other.id <= e.id) continue;
      const sep = distance(e, other);
      const min = boss || other.kind === "boss" ? 70 : 42;
      if (sep < min && sep > 0) {
        const v = direction(e.x - other.x, e.y - other.y);
        const push = (min - sep) * 0.5;
        e.x += v.x * push;
        e.y += v.y * push;
        other.x -= v.x * push;
        other.y -= v.y * push;
      }
    }
    e.x = clamp(e.x, ARENA.left, ARENA.right);
    e.y = clamp(e.y, ARENA.top, ARENA.bottom);
  }

  private enemyShot(e: Enemy, count: number) {
    const speed = this.level === 3 ? 260 : this.level === 2 ? 240 : 210;
    const angle = Math.atan2(this.hero.y - e.y, this.hero.x - e.x);
    for (let i = 0; i < count; i++) {
      const a = angle + (i - (count - 1) / 2) * 0.23;
      this.shots.push({
        id: ++this.serial,
        team: "enemy",
        x: e.x,
        y: e.y,
        vx: Math.cos(a) * speed,
        vy: Math.sin(a) * speed,
        life: 4.5,
        damage:
          e.kind === "boss"
            ? this.level === 3
              ? 18
              : this.level === 2
                ? 16
                : 14
            : 9,
      });
    }
  }

  private updateHazards(dt: number) {
    this.hazardClock -= dt;
    if (this.hazardClock <= 0) {
      this.hazardClock = Math.max(4, 7 - this.wave);
      this.hazards.push({
        id: ++this.serial,
        x: this.hero.x,
        y: this.hero.y,
        radius: 78,
        windup: 1.1,
        life: 1.4,
        damage: 18,
      });
    }
    for (const hazard of this.hazards) {
      hazard.life -= dt;
      if (hazard.windup > 0) {
        hazard.windup = Math.max(0, hazard.windup - dt);
        if (hazard.windup === 0) {
          if (distance(hazard, this.hero) < hazard.radius)
            this.damageHero(hazard.damage);
          this.events.push({ kind: "thunder", x: hazard.x, y: hazard.y });
        }
      }
    }
    this.hazards = this.hazards.filter((h) => h.life > 0);
  }

  private updateWind(dt: number) {
    const enraged = this.enemies.some((e) => e.kind === "boss" && e.enraged);
    this.windClock -= dt;
    if (this.windClock <= 0) {
      this.windClock = enraged ? 5.5 : this.wave === 5 ? 6.8 : 8;
      this.windWalls.push({
        id: ++this.serial,
        x: ARENA.left,
        gapY: this.windIndex++ % 2 ? 536 : 352,
        gapHeight: enraged ? 112 : 136,
        windup: WIND.windup,
        life: 7,
        speed: enraged ? 280 : WIND.speed,
        damage: WIND.damage,
        hit: false,
      });
    }
    for (const wall of this.windWalls) {
      wall.life -= dt;
      if (wall.windup > 0) {
        wall.windup = Math.max(0, wall.windup - dt);
        continue;
      }
      const before = wall.x;
      wall.x += wall.speed * dt;
      const crossing =
        this.hero.x >= before - WIND.halfWidth &&
        this.hero.x <= wall.x + WIND.halfWidth;
      if (
        !wall.hit &&
        crossing &&
        Math.abs(this.hero.y - wall.gapY) >= wall.gapHeight / 2
      ) {
        wall.hit = true;
        this.damageHero(wall.damage);
      }
    }
    this.windWalls = this.windWalls.filter(
      (wall) => wall.life > 0 && wall.x <= ARENA.right + WIND.halfWidth,
    );
  }

  private updateShots(dt: number) {
    for (const s of [...this.shots]) {
      const before = { x: s.x, y: s.y };
      s.x += s.vx * dt;
      s.y += s.vy * dt;
      s.life -= dt;
      const targets = s.team === "hero" ? this.enemies : [this.hero];
      for (const target of [...targets]) {
        const radius = "kind" in target && target.kind === "boss" ? 42 : 24;
        const segmentX = s.x - before.x,
          segmentY = s.y - before.y;
        const len = segmentX ** 2 + segmentY ** 2;
        const t = len
          ? clamp(
              ((target.x - before.x) * segmentX +
                (target.y - before.y) * segmentY) /
                len,
              0,
              1,
            )
          : 0;
        if (
          Math.hypot(
            target.x - before.x - segmentX * t,
            target.y - before.y - segmentY * t,
          ) < radius
        ) {
          if (s.team === "hero") this.damageEnemy(target as Enemy, s.damage);
          else this.damageHero(s.damage);
          s.life = 0;
          break;
        }
      }
    }
    this.shots = this.shots.filter(
      (s) =>
        s.life > 0 &&
        s.x > -30 &&
        s.x < WIDTH + 30 &&
        s.y > 180 &&
        s.y < HEIGHT,
    );
  }

  save(): Save {
    return structuredClone({
      version: 3,
      level: this.level,
      unlockedLevel: this.unlockedLevel,
      hazards: this.hazards,
      hazardClock: this.hazardClock,
      movement: this.movement,
      windWalls: this.windWalls,
      windClock: this.windClock,
      windIndex: this.windIndex,
      phase: this.phase,
      wave: this.wave,
      elapsed: this.elapsed,
      kills: this.kills,
      deaths: this.deaths,
      serial: this.serial,
      transition: this.transition,
      tutorialStep: this.tutorialStep,
      tutorialDistance: this.tutorialDistance,
      tutorialDefense: this.tutorialDefense,
      hero: this.hero,
      enemies: this.enemies,
      shots: this.shots,
      pickups: this.pickups,
    });
  }

  restore(save: Save) {
    const copy = structuredClone(save);
    Object.assign(this, copy);
    this.paused = false;
    this.events = [];
    this.hero.defending = false;
  }
}

export function decodeSave(text: string | null): Save | null {
  if (!text || text.length > 250000) return null;
  try {
    const s = JSON.parse(text);
    if (s?.version === 1) {
      s.version = 2;
      s.level = 1;
      s.unlockedLevel = s.phase === "won" ? 2 : 1;
      s.hazards = [];
      s.hazardClock = 3.5;
      s.movement = { x: s.hero?.facing, y: 0 };
      if (Array.isArray(s.enemies))
        for (const e of s.enemies) {
          if (e && typeof e === "object")
            Object.assign(e, { chargeTime: 0, chargeX: 0, chargeY: 0 });
        }
    }
    if (s?.version === 2) {
      if (
        ![1, 2].includes(s.level) ||
        ![1, 2].includes(s.unlockedLevel) ||
        s.level > s.unlockedLevel
      )
        return null;
      s.version = 3;
      if (s.phase === "won" && s.level === 2) s.unlockedLevel = 3;
      s.windWalls = [];
      s.windClock = 3;
      s.windIndex = 0;
    }
    const num = (n: unknown, min: number, max: number): boolean =>
      typeof n === "number" && Number.isFinite(n) && n >= min && n <= max;
    const position = (p: any) =>
      p &&
      num(p.x, ARENA.left, ARENA.right) &&
      num(p.y, ARENA.top, ARENA.bottom);
    const integer = (n: unknown, min: number, max: number) =>
      num(n, min, max) && Number.isInteger(n);
    if (
      s.version !== 3 ||
      ![1, 2, 3].includes(s.level) ||
      ![1, 2, 3].includes(s.unlockedLevel) ||
      s.level > s.unlockedLevel ||
      !["tutorial", "playing", "defeat", "won"].includes(s.phase) ||
      !integer(s.wave, 0, LEVELS[s.level as LevelId].waves.length) ||
      !num(s.elapsed, 0, 86400) ||
      !integer(s.kills, 0, 10000) ||
      !integer(s.deaths, 0, 10000) ||
      !integer(s.serial, 0, 1000000) ||
      !num(s.transition, -1, 2) ||
      !integer(s.tutorialStep, 0, 3) ||
      !num(s.tutorialDistance, 0, 10000) ||
      !num(s.tutorialDefense, 0, 10000) ||
      !position(s.hero) ||
      !num(s.hero.hp, 0, 120) ||
      !num(s.hero.energy, 0, 100) ||
      ![-1, 1].includes(s.hero.facing) ||
      typeof s.hero.defending !== "boolean" ||
      !Array.isArray(s.enemies) ||
      s.enemies.length > 20 ||
      !Array.isArray(s.shots) ||
      s.shots.length > 100 ||
      !Array.isArray(s.pickups) ||
      s.pickups.length > 20
    )
      return null;
    if (
      !num(s.hazardClock, 0, 10) ||
      !s.movement ||
      !num(s.movement.x, -1, 1) ||
      !num(s.movement.y, -1, 1) ||
      !Array.isArray(s.hazards) ||
      s.hazards.length > 10 ||
      (s.level !== 2 && s.hazards.length) ||
      !Array.isArray(s.windWalls) ||
      s.windWalls.length > 4 ||
      (s.level !== 3 && s.windWalls.length) ||
      !num(s.windClock, 0, 12) ||
      !integer(s.windIndex, 0, 1000000)
    )
      return null;
    for (const k of [
      "invulnerable",
      "attackCooldown",
      "dashCooldown",
      "dashTime",
    ])
      if (!num(s.hero[k], 0, 10)) return null;
    if (!num(s.hero.dashX, -1, 1) || !num(s.hero.dashY, -1, 1)) return null;
    for (const e of s.enemies) {
      if (
        !position(e) ||
        !integer(e.id, 1, s.serial) ||
        !["guard", "mage", "rusher", "boss"].includes(e.kind) ||
        (s.level === 1 && e.kind === "rusher") ||
        !num(e.hp, 0.001, 1000) ||
        !num(e.maxHp, e.hp, 1000) ||
        !num(e.speed, 0, 300) ||
        !num(e.cooldown, -10, 10) ||
        !num(e.windup, -0.1, 3) ||
        !num(e.stun, -0.1, 10) ||
        !num(e.aimX, 0, WIDTH) ||
        !num(e.aimY, 0, HEIGHT) ||
        typeof e.enraged !== "boolean"
      )
        return null;
      if (
        !num(e.chargeTime, 0, 1) ||
        !num(e.chargeX, -1, 1) ||
        !num(e.chargeY, -1, 1)
      )
        return null;
    }
    for (const shot of s.shots)
      if (
        !integer(shot.id, 1, s.serial) ||
        !["hero", "enemy"].includes(shot.team) ||
        !num(shot.x, -30, WIDTH + 30) ||
        !num(shot.y, 180, HEIGHT) ||
        !num(shot.vx, -1000, 1000) ||
        !num(shot.vy, -1000, 1000) ||
        !num(shot.life, 0, 6) ||
        !num(shot.damage, 0, 100)
      )
        return null;
    for (const p of s.pickups)
      if (!position(p) || !integer(p.id, 1, s.serial) || !num(p.life, 0, 30))
        return null;
    for (const h of s.hazards)
      if (
        !position(h) ||
        !integer(h.id, 1, s.serial) ||
        !num(h.radius, 1, 136) ||
        !num(h.windup, 0, 1.2) ||
        !num(h.life, 0, 1.5) ||
        !num(h.damage, 1, 50)
      )
        return null;
    for (const wall of s.windWalls)
      if (
        !wall ||
        !integer(wall.id, 1, s.serial) ||
        !num(wall.x, ARENA.left, ARENA.right + WIND.halfWidth) ||
        !num(wall.gapY, ARENA.top + 80, ARENA.bottom - 80) ||
        !num(wall.gapHeight, 96, 160) ||
        !num(wall.windup, 0, WIND.windup) ||
        !num(wall.life, 0, 7) ||
        !num(wall.speed, 180, 320) ||
        !num(wall.damage, 1, 50) ||
        typeof wall.hit !== "boolean"
      )
        return null;
    if (s.phase === "playing" && (!s.hero.hp || !s.wave)) return null;
    if (s.phase === "defeat" && s.hero.hp !== 0) return null;
    if (s.phase === "tutorial" && (s.level !== 1 || s.wave || s.enemies.length))
      return null;
    if (
      s.phase === "won" &&
      (s.wave !== LEVELS[s.level as LevelId].waves.length || s.enemies.length)
    )
      return null;
    if (s.phase === "won" && s.unlockedLevel < Math.min(3, s.level + 1))
      return null;
    return s as Save;
  } catch {
    return null;
  }
}
