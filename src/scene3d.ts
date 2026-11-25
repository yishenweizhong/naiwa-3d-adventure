import * as T from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { World, ARENA, type Input, type GameEvent, type Enemy } from "./model.ts";
import { heroMotion, type HeroMotion } from "./hero-motion.ts";
import { advanceWorld } from "./clock.ts";

const px = (x: number) => (x - 640) / 50;
const pz = (y: number) => (y - 450) / 50;
type Hooks = { input: () => Input; frame: () => void; event: (e: GameEvent) => void };

/** Render adapter. All combat, hitboxes and progression remain in World. */
export class GameScene3D {
  private scene = new T.Scene();
  private camera = new T.OrthographicCamera(-13.5, 13.5, 7.594, -7.594, .1, 100);
  private renderer: T.WebGLRenderer;
  private environment = new T.Group();
  private dynamic = new T.Group();
  private hero = new T.Group();
  private figure?: T.Group;
  private mixer?: T.AnimationMixer;
  private actions = new Map<HeroMotion, T.AnimationAction>();
  private motion?: HeroMotion;
  private baseAction?: T.AnimationAction;
  private movingAction?: T.AnimationAction;
  private idleUpper?: T.AnimationAction;
  private walkUpper?: T.AnimationAction;
  private actorMap = new Map<string, T.Group>();
  private mats = new Map<string, T.MeshStandardMaterial>();
  private geos = new Map<string, T.BufferGeometry>();
  private windmills: T.Group[] = [];
  private effects: { mesh: T.Mesh; age: number; life: number }[] = [];
  private transient = { action: "", actionTime: 0 };
  private time = 0;
  private last = 0;
  private level = 0;
  private dirty = true;
  private ready = false;
  private angle = 0;
  private stage = document.getElementById("stage")!;
  private sun = new T.DirectionalLight(0xffe5b1, 3);
  private loader = new GLTFLoader();
  private modelUrl = `${import.meta.env.BASE_URL}models/reference-hero.glb`;

  constructor(private world: World, private hooks: Hooks) {
    this.renderer = new T.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = T.PCFSoftShadowMap;
    this.renderer.shadowMap.autoUpdate = false;
    this.renderer.toneMapping = T.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.25;
    this.renderer.outputColorSpace = T.SRGBColorSpace;
    this.renderer.domElement.setAttribute("aria-label", "实时三维游戏场景");
    document.getElementById("game")!.append(this.renderer.domElement);
    this.camera.position.set(0, 18, 23);
    this.camera.lookAt(0, 0, -2);
    this.scene.add(this.environment, this.dynamic, this.hero);
    const contact=this.mesh(this.hero,"cylinder","#53604e",[0,.012,0],[.20,.018,.13],true);
    contact.castShadow=false;
    this.scene.add(new T.HemisphereLight(0xd9efff, 0x7c7559, 2.3));
    this.sun.position.set(-8, 18, 9);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(1024, 1024);
    Object.assign(this.sun.shadow.camera, { left: -18, right: 18, top: 16, bottom: -14, near: .1, far: 60 });
    this.sun.shadow.bias = -.0008;
    this.sun.shadow.normalBias = .03;
    this.scene.add(this.sun);
    new ResizeObserver(() => {
      this.renderer.setSize(this.stage.clientWidth, this.stage.clientHeight, false);
      this.dirty = true;
    }).observe(this.stage);
    this.renderer.domElement.addEventListener("webglcontextlost", e => {
      e.preventDefault();
      this.world.pause(true);
      this.status("画面连接中断，刷新页面后可继续已保存的进度。", "error");
    });
    this.loadHero();
    this.renderer.setAnimationLoop(now => this.tick(now));
  }

  private status(text: string, state: string) {
    const box = document.getElementById("character-status")!;
    box.replaceChildren(document.createTextNode(text));
    box.hidden = state === "ready";
    this.stage.dataset.heroState = state;
    if (state === "error") {
      const button = document.createElement("button");
      button.textContent = "重新加载人物";
      button.className = "text-button";
      button.onclick = () => this.loadHero();
      box.append(button);
    }
  }

  private loadHero() {
    this.status("人物加载中…", "loading");
    this.loader.load(this.modelUrl, gltf => {
      this.figure = gltf.scene;
      this.figure.traverse(o => {
        if (o instanceof T.Mesh) { o.castShadow = false; o.receiveShadow = true; o.frustumCulled = false; }
      });
      this.hero.add(this.figure);
      this.mixer = new T.AnimationMixer(this.figure);
      // Base idle/walk remain active under upper-body actions, preserving locomotion.
      const upper = /Spine|Head|UpperArm|Forearm|Hand|Hair|Scarf/;
      for (const clip of gltf.animations) {
        const name = clip.name as HeroMotion;
        let tracks = clip.tracks;
        if (name === "idle" || name === "walk") {
          const upperAction=this.mixer.clipAction(new T.AnimationClip(`${name}-upper`,clip.duration,tracks.filter(t=>upper.test(t.name))));
          upperAction.play().setEffectiveWeight(name === "idle" ? 1 : 0);
          if (name === "idle") this.idleUpper=upperAction;
          else this.walkUpper=upperAction;
          tracks=tracks.filter(t=>!upper.test(t.name));
        }
        if (["attack", "defend", "laugh"].includes(name))
          tracks = tracks.filter(t => upper.test(t.name));
        this.actions.set(name, this.mixer.clipAction(new T.AnimationClip(name, clip.duration, tracks)));
      }
      if (this.actions.size !== 6) {
        this.hero.remove(this.figure);
        this.status("人物动作资源不完整，请重新加载。", "error");
        return;
      }
      this.baseAction = this.actions.get("idle")!;
      this.movingAction = this.actions.get("walk")!;
      this.baseAction.play();
      this.movingAction.play().setEffectiveWeight(0);
      this.ready = true;
      this.status("", "ready");
      this.dirty = true;
    }, undefined, () => this.status("人物未加载成功，检查网络后重试。", "error"));
  }

  private mat(color: string, transparent = false) {
    const key = `${color}/${transparent}`;
    if (!this.mats.has(key))
      this.mats.set(key, new T.MeshStandardMaterial({
        color, roughness: .78, transparent, opacity: transparent ? .36 : 1,
        depthWrite: !transparent, side: transparent ? T.DoubleSide : T.FrontSide,
      }));
    return this.mats.get(key)!;
  }
  private geometry(kind: string) {
    if (!this.geos.has(kind)) {
      const g = kind === "box" ? new T.BoxGeometry(1, 1, 1)
        : kind === "sphere" ? new T.SphereGeometry(1, 16, 12)
        : kind === "cone" ? new T.ConeGeometry(1, 1, 6)
        : kind === "ring" ? new T.TorusGeometry(1, .035, 6, 48)
        : new T.CylinderGeometry(1, 1, 1, 20);
      this.geos.set(kind, g);
    }
    return this.geos.get(kind)!;
  }
  private mesh(parent: T.Object3D, kind: string, color: string,
    pos: [number, number, number], size: [number, number, number], transparent = false) {
    const m = new T.Mesh(this.geometry(kind), this.mat(color, transparent));
    m.position.set(...pos); m.scale.set(...size);
    m.castShadow = false;
    m.receiveShadow = !transparent;
    parent.add(m);
    return m;
  }
  private box(parent: T.Object3D, color: string, x: number, y: number, z: number, a: number, b: number, c: number) {
    return this.mesh(parent, "box", color, [x, y, z], [a, b, c]);
  }
  private ring(parent: T.Object3D, color: string, radius: number, y = .05) {
    const m = this.mesh(parent, "ring", color, [0, y, 0], [radius, radius, radius]);
    m.rotation.x = -Math.PI / 2; m.castShadow = false;
    return m;
  }

  private house(x: number, z: number, color: string, size = 1) {
    const g = new T.Group(); g.position.set(x, 0, z); g.scale.setScalar(size); this.environment.add(g);
    this.box(g, color, 0, 1.35, 0, 2.8, 2.7, 2.2);
    const roof = this.mesh(g, "cone", "#71644d", [0, 3.25, 0], [2.3, 1.4, 1.9]);
    roof.rotation.y = Math.PI / 6;
    this.box(g, "#5b5b4f", 0, .8, 1.13, .6, 1.6, .08);
    for (const s of [-1, 1]) {
      this.box(g, "#95b8bc", s*.85, 1.6, 1.14, .55, .75, .08);
      this.box(g, "#eee1ba", s*.85, 1.6, 1.2, .06, .8, .08);
    }
    this.box(g, "#918975", .85, 3.1, -.2, .4, 1.6, .45);
  }
  private tree(x: number, z: number, size = 1) {
    const g = new T.Group(); g.position.set(x, 0, z); g.scale.setScalar(size); this.environment.add(g);
    this.mesh(g, "cylinder", "#756343", [0, 1, 0], [.17, 2, .17]);
    for (let i=0; i<3; i++)
      this.mesh(g, "sphere", i === 1 ? "#81975c" : "#657b4e",
        [Math.sin(i*2)*.45, 2.1+i*.38, Math.cos(i*2)*.28], [.95, .85, .95]);
  }
  private windmill(x: number, z: number, size = 1) {
    const g = new T.Group(); g.position.set(x, 0, z); g.scale.setScalar(size); this.environment.add(g);
    this.mesh(g, "cylinder", "#c4bca1", [0, 2, 0], [.9, 4, .9]);
    this.mesh(g, "cone", "#67566d", [0, 4.3, 0], [1.25, 1.15, 1.25]);
    const blades = new T.Group(); blades.position.set(0, 3.15, .97); g.add(blades);
    for (let i=0; i<4; i++) {
      const b = this.box(blades, "#e8d8b1", 0, 1.0, 0, .28, 2.1, .08);
      const pivot = new T.Group(); pivot.rotation.z=i*Math.PI/2; blades.remove(b); pivot.add(b); blades.add(pivot);
    }
    this.mesh(blades, "sphere", "#655644", [0, 0, .04], [.18, .18, .13]);
    this.windmills.push(blades);
  }

  private buildEnvironment(level: number) {
    this.environment.traverse(o => { if (o instanceof T.InstancedMesh) o.dispose(); });
    this.environment.clear(); this.windmills = [];
    const dusk = level === 2, night = level === 3 && this.world.phase !== "won";
    this.scene.background = new T.Color(night ? "#7884a5" : dusk ? "#d1b7c4" : "#d8e3d8");
    this.scene.fog = new T.Fog(this.scene.background, 38, 78);
    this.sun.color.set(night ? "#b0c9ff" : "#ffe2ad");
    const ground = night ? "#7b8291" : dusk ? "#998987" : "#acb493";
    this.box(this.environment, "#787a67", 0, -.55, -2, 30, 1, 20);
    this.box(this.environment, ground, 0, -.06, 0, 23.5, .16, 8.3);
    // Continuous stone edges mark the actual combat boundary.
    for (const x of [-11.7, 11.7]) this.box(this.environment, "#d7cbb4", x, .06, 0, .12, .18, 8.3);
    for (const z of [-4.1, 4.1]) this.box(this.environment, "#d7cbb4", 0, .06, z, 23.5, .18, .12);
    for (let x=-10; x<=10; x+=2) {
      this.box(this.environment, night ? "#969bad" : "#c9bea0", x, .035, .8, 1.75, .07, 1.0);
      this.box(this.environment, night ? "#9399a7" : "#c8bc9d", x+1, .035, -.3, 1.75, .07, 1.0);
    }
    for (let i=0; i<9; i++) {
      const x=-19+i*4.7, z=-15-Math.sin(i)*2;
      this.mesh(this.environment, "sphere", dusk ? "#7f8f86" : "#879b87", [x, .3, z], [5, 3.8+(i%3), 4]);
    }
    if (level === 1) {
      this.house(-8, -7.4, "#e0ceb1", 1.1);
      this.house(-3.8, -8.8, "#d8c3a7", .86);
      this.house(7.4, -8, "#e7d5b5", 1.15);
      this.house(3.3, -10, "#c8c6aa", .8);
      this.tree(-12.5, -5, 1.2); this.tree(11.9, -5.4, 1.1); this.tree(.4, -9, 1.1);
      const well = new T.Group(); well.position.set(0, 0, -5.9); this.environment.add(well);
      this.mesh(well,"cylinder","#b5ae96",[0,.5,0],[.65,1,.65]);
      this.mesh(well,"cylinder","#517e87",[0,1.01,0],[.48,.05,.48]);
      for (const x of [-.63,.63]) this.box(well,"#756144",x,1.35,0,.12,1.3,.12);
      this.box(well,"#73624b",0,2.03,0,1.6,.18,1.2);
    } else if (level === 2) {
      this.windmill(-8, -7.5, 1.1); this.windmill(7.7, -8, 1.3); this.windmill(-2.9, -11, .8);
      this.box(this.environment, "#6f999f", 1.1, -.04, -7, 2.6, .07, 12);
      this.box(this.environment, "#a99574", 1.1, .15, -5.8, 3.5, .23, 2.0);
      for (const z of [-6.7, -4.9]) this.box(this.environment, "#6e6553", 1.1, .72, z, 3.4, .13, .12);
      for (const x of [-.55, 2.75]) this.box(this.environment, "#6e6553", x, .4, -5.8, .13, 1.3, 2.0);
      this.tree(-12.2, -4.8, 1); this.tree(12.3, -4.5, 1);
    } else {
      this.box(this.environment, "#c0bbb5", 0, 3.4, -8.6, 2.9, 6.8, 2.8);
      this.box(this.environment, "#797d91", 0, 7, -8.6, 3.3, .4, 3.3);
      this.mesh(this.environment,"cone","#536176",[0,8.1,-8.6],[2.5,2.0,2.5]);
      const clock = this.mesh(this.environment,"cylinder","#eee2bf",[0,5.45,-7.14],[1.0,.1,1.0]);
      clock.rotation.x=Math.PI/2;
      this.box(this.environment,"#586173",0,5.7,-7.06,.07,.55,.07);
      const hand=this.box(this.environment,"#586173",.23,5.46,-7.03,.48,.06,.07); hand.rotation.z=.2;
      this.house(-7.4, -8.4, "#aaa8b0", 1.1); this.house(7.5, -8.3, "#c0b7b7", 1.1);
      for (const x of [-10, -4, 4, 10]) {
        this.mesh(this.environment,"cylinder","#586072",[x,1.35,-4.9],[.065,2.7,.065]);
        this.mesh(this.environment,"sphere","#ffd88f",[x,2.8,-4.9],[.23,.32,.23]);
      }
    }
    // Physical banners, flowers and rocks live outside hitboxes.
    for (const x of [-10.7, 10.7]) {
      this.mesh(this.environment,"cylinder","#76654c",[x,1.5,-4.7],[.045,3,.045]);
      this.box(this.environment,"#e7c76a",x+.35,2.42,-4.7,.65,.9,.04);
    }
    for (let i=0; i<14; i++) {
      const x=-12.2+(i%2)*24.4, z=-3.4+Math.floor(i/2)*1.2;
      this.mesh(this.environment,"sphere","#909588",[x,.15,z],[.28,.2,.34]);
    }
    this.stage.dataset.renderMode = "full-3d";
    this.batchEnvironment();
    this.renderer.shadowMap.needsUpdate=true;
    this.level = level;
  }

  private batchEnvironment() {
    this.environment.updateMatrixWorld(true);
    const batches=new Map<string,T.Mesh[]>();
    this.environment.traverse(o=>{
      if (!(o instanceof T.Mesh)) return;
      for (let p: T.Object3D | null=o.parent;p;p=p.parent)
        if (this.windmills.includes(p as T.Group)) return;
      const key=`${o.geometry.uuid}/${(o.material as T.Material).uuid}`;
      const list=batches.get(key)??[]; list.push(o); batches.set(key,list);
    });
    for (const list of batches.values()) {
      const group=new T.InstancedMesh(list[0].geometry,list[0].material,list.length);
      group.castShadow=true; group.receiveShadow=true;
      list.forEach((m,i)=>{ group.setMatrixAt(i,m.matrixWorld); m.parent!.remove(m); });
      this.environment.add(group);
    }
  }

  private enemy(e: Enemy) {
    const key=`enemy:${e.id}`;
    let g=this.actorMap.get(key);
    if (!g) {
      g=new T.Group(); this.actorMap.set(key,g); this.dynamic.add(g);
      const boss=e.kind==="boss", mage=e.kind==="mage", rusher=e.kind==="rusher";
      const color=boss ? "#616b83" : mage ? "#817099" : rusher ? "#927868" : "#7b8a82";
      this.mesh(g,"cylinder",color,[0,.8,0],[.34,1.1,.28]);
      this.mesh(g,"sphere","#b8b6a5",[0,1.53,0],[.3,.33,.29]);
      this.mesh(g,"cone",color,[0,1.88,0],[.36,.4,.34]);
      for (const s of [-1,1]) {
        this.mesh(g,"sphere",color,[s*.42,1.03,0],[.14,.4,.14]);
        this.mesh(g,"sphere","#515969",[s*.15,.22,0],[.13,.27,.16]);
        this.mesh(g,"sphere",boss ? "#eed584" : "#333c4b",[s*.095,1.57,.266],[.04,.047,.025]);
      }
      if (mage) {
        this.mesh(g,"cylinder","#5f536c",[.52,.8,0],[.04,1.4,.04]);
        this.mesh(g,"sphere","#c0a4de",[.52,1.57,0],[.13,.13,.13]);
      }
      if (boss) {
        g.scale.setScalar(1.85);
        this.box(g,"#a5a8b4",0,.95,-.3,.9,1.1,.16);
        this.ring(g,"#e9c880",.44,1.97);
      }
      const bar=new T.Group(); bar.name="health"; bar.position.set(0,boss?2.4:2.2,0); g.add(bar);
      this.box(bar,"#424d59",0,0,0,.7,.07,.05);
      const fill=this.box(bar,"#dce3b9",0,0,.035,.68,.05,.04); fill.name="fill";
      this.mesh(g,"cylinder","#53604e",[0,.012,0],[.34,.018,.22],true);
    }
    g.position.set(px(e.x),0,pz(e.y));
    g.rotation.y=Math.atan2(this.hero.position.x-g.position.x,this.hero.position.z-g.position.z);
    g.position.y=e.stun>0 ? .06*Math.sin(this.time*14) : .025*Math.sin(this.time*5+e.id);
    g.getObjectByName("fill")!.scale.x=.68*Math.max(0,e.hp/e.maxHp);
    if (e.windup>0) {
      const warning=this.item(`warning:${e.id}`,() => {
        const v=new T.Group();
        if (e.kind === "rusher") {
          this.mesh(v,"box","#e95d53",[0,.055,2.27],[1.76,.04,4.54],true);
          this.box(v,"#efaf72",0,.09,2.27,.06,.03,4.54);
        } else {
          this.ring(v,"#e95d53",e.kind==="boss"?2.7:.9);
          this.mesh(v,"cylinder","#e95d53",[0,.015,0],[e.kind==="boss"?2.7:.9,.03,e.kind==="boss"?2.7:.9],true);
        }
        return v;
      });
      if (e.kind === "rusher") {
        warning.position.set(px(e.x),.02,pz(e.y));
        warning.rotation.y=Math.atan2(e.aimX-e.x,e.aimY-e.y);
      } else warning.position.set(px(e.aimX),.02,pz(e.aimY));
      warning.scale.setScalar(.94+.06*Math.sin(this.time*9));
    }
    return key;
  }
  private item(key: string, create: () => T.Group) {
    let o=this.actorMap.get(key);
    if (!o) { o=create(); this.actorMap.set(key,o); this.dynamic.add(o); }
    return o;
  }

  private syncActors() {
    const keep=new Set<string>();
    if (this.world.hero.defending) keep.add("hero:shield");
    for (const e of this.world.enemies) {
      keep.add(this.enemy(e));
      if (e.windup>0) keep.add(`warning:${e.id}`);
    }
    for (const s of this.world.shots) {
      const key=`shot:${s.id}`; keep.add(key);
      const g=this.item(key,() => {
        const o=new T.Group();
        this.mesh(o,"sphere",s.team==="hero"?"#fff8da":"#db96a6",[0,0,0],[.16,.16,.16]);
        this.mesh(o,"sphere",s.team==="hero"?"#fff8da":"#db96a6",[0,0,-.23],[.10,.10,.3],true);
        return o;
      });
      g.position.set(px(s.x),1.08,pz(s.y));
      g.rotation.y=Math.atan2(s.vx,s.vy);
    }
    for (const p of this.world.pickups) {
      const key=`pickup:${p.id}`; keep.add(key);
      const g=this.item(key,() => {
        const o=new T.Group();
        this.mesh(o,"cylinder","#f7ebcd",[0,.3,0],[.17,.5,.17]);
        this.mesh(o,"cylinder","#dbb857",[0,.61,0],[.12,.09,.12]);
        this.ring(o,"#efc456",.36,.04); return o;
      });
      g.position.set(px(p.x),.08*Math.sin(this.time*3),pz(p.y)); g.rotation.y=this.time;
    }
    for (const h of this.world.hazards) {
      const key=`hazard:${h.id}`; keep.add(key);
      const g=this.item(key,() => {
        const o=new T.Group();
        this.ring(o,"#ffce69",h.radius/50);
        const bolt=this.mesh(o,"cylinder","#ffe6aa",[0,2.5,0],[.09,5,.09]); bolt.name="bolt";
        this.mesh(o,"cylinder","#f8bd59",[0,.025,0],[h.radius/50,.04,h.radius/50],true);
        return o;
      });
      g.position.set(px(h.x),0,pz(h.y));
      g.getObjectByName("bolt")!.visible=h.windup<=0;
    }
    for (const w of this.world.windWalls) {
      const key=`wind:${w.id}`; keep.add(key);
      const g=this.item(key,() => {
        const o=new T.Group();
        for (const [a,b] of [[ARENA.top,w.gapY-w.gapHeight/2],[w.gapY+w.gapHeight/2,ARENA.bottom]]) {
          const z=(pz(a)+pz(b))/2, len=(b-a)/50;
          this.mesh(o,"box","#ae86cb",[0,1.0,z],[.7,2,len],true);
          this.box(o,"#c5abe4",0,.08,z,.8,.08,len);
          this.box(o,"#d0b5eb",0,1.8,z,.05,.06,len);
        }
        this.box(o,"#94d5aa",0,.065,pz(w.gapY),.8,.08,w.gapHeight/50);
        for (const y of [w.gapY-w.gapHeight/2,w.gapY+w.gapHeight/2])
          this.box(o,"#abe5b8",0,.7,pz(y),.08,1.4,.08);
        return o;
      });
      g.position.x=px(w.x);
      g.scale.y=w.windup>0 ? .22 : 1;
    }
    for (const [key,o] of this.actorMap) {
      if (!keep.has(key)) { this.dynamic.remove(o); this.actorMap.delete(key); }
    }
  }

  private event(e: GameEvent) {
    if (e.kind==="dash") this.transient={action:"dash",actionTime:.22};
    if (e.kind==="shot") this.transient={action:"attack",actionTime:.34};
    if (e.kind==="laugh") this.transient={action:"laugh",actionTime:1.5};
    if (["hit","hurt","laugh","heal","dash"].includes(e.kind)) {
      const m=new T.Mesh(this.geometry("ring"),new T.MeshBasicMaterial({
        color:e.kind==="hurt"?"#dc7070":e.kind==="laugh"?"#f9df8c":"#f3f0ca",transparent:true,opacity:.8,depthWrite:false,
      }));
      m.rotation.x=-Math.PI/2; m.position.set(px(e.x),.1,pz(e.y)); m.scale.setScalar(.2);
      this.dynamic.add(m); this.effects.push({mesh:m,age:0,life:e.kind==="laugh"?.85:.35});
    }
    this.hooks.event(e);
  }

  private animateHero(dt: number, input: Input) {
    const menu=this.world.phase==="menu", h=this.world.hero;
    this.hero.position.set(menu?5.2:px(h.x),0,menu?3.0:pz(h.y));
    this.hero.scale.setScalar(menu?4.8:1.3);
    if (!this.ready) return;
    const moving=!menu && Math.hypot(input.x,input.y)>.05;
    const target=menu ? -.08 : this.world.hero.dashTime>0 || (this.transient.action==="dash" && this.transient.actionTime>0)
      ? Math.atan2(h.dashX,h.dashY)
      : this.transient.action==="attack" && this.world.enemies.length
        ? (() => {
            const e=this.world.enemies.reduce((a,b) => Math.hypot(a.x-h.x,a.y-h.y)<Math.hypot(b.x-h.x,b.y-h.y)?a:b);
            return Math.atan2(e.x-h.x,e.y-h.y);
          })()
        : moving ? Math.atan2(input.x,input.y) : this.angle;
    const delta=Math.atan2(Math.sin(target-this.angle),Math.cos(target-this.angle));
    this.angle+=delta*(1-Math.exp(-dt*12)); this.hero.rotation.y=this.angle;
    const next=heroMotion({
      phase:this.world.phase,dashTime:h.dashTime,defending:h.defending,moving,
      action:this.transient.action,actionTime:this.transient.actionTime,
    });
    if (next!==this.motion) {
      if (this.motion && !["idle","walk"].includes(this.motion))
        this.actions.get(this.motion)!.fadeOut(.13);
      if (!["idle","walk"].includes(next))
        this.actions.get(next)!.reset().setEffectiveWeight(1).fadeIn(next==="dash"?.05:.14).play();
      this.motion=next;
      this.stage.dataset.heroMotion=next;
    }
    const targetWalk=moving && next!=="dash" ? 1 : 0;
    const weight=T.MathUtils.damp(this.movingAction!.getEffectiveWeight(),targetWalk,10,dt);
    this.movingAction!.setEffectiveWeight(weight);
    this.movingAction!.setEffectiveTimeScale(h.defending?.58:1);
    this.baseAction!.setEffectiveWeight(next==="dash"?0:1-weight);
    const upperFree=next==="idle" || next==="walk";
    this.idleUpper!.setEffectiveWeight(T.MathUtils.damp(this.idleUpper!.getEffectiveWeight(),upperFree?1-weight:0,14,dt));
    this.walkUpper!.setEffectiveWeight(T.MathUtils.damp(this.walkUpper!.getEffectiveWeight(),upperFree?weight:0,14,dt));
    this.walkUpper!.setEffectiveTimeScale(h.defending?.58:1);
    this.mixer!.update(dt);
    this.transient.actionTime=Math.max(0,this.transient.actionTime-dt);
    const shieldKey="hero:shield";
    if (h.defending) {
      const g=this.item(shieldKey,() => {
        const o=new T.Group();
        this.mesh(o,"sphere","#b4daef",[0,1.25,.55],[.75,.94,.11],true);
        const edge=this.ring(o,"#c2e3ef",.78,1.25); edge.rotation.x=0; edge.position.z=.55;
        return o;
      });
      g.position.copy(this.hero.position); g.rotation.y=this.angle;
    } else {
      const o=this.actorMap.get(shieldKey);
      if (o) { this.dynamic.remove(o); this.actorMap.delete(shieldKey); }
    }
  }

  private tick(now: number) {
    const dt=Math.min(.25,this.last ? (now-this.last)/1000 : .016);
    this.last=now;
    const dawn=this.world.phase==="won" && this.world.level===3;
    if (this.level!==this.world.level || (this.world.level===3 && (this.stage.dataset.dawn==="yes")!==dawn)) {
      this.buildEnvironment(this.world.level);
      this.stage.dataset.dawn=dawn?"yes":"no";
      this.dirty=true;
    }
    const input=this.hooks.input();
    if (!this.world.paused) {
      // Don't let enemies attack a player whose character is still downloading.
      if (this.ready) advanceWorld(this.world,dt,input);
      for (const e of this.world.events.splice(0)) this.event(e);
      this.time+=dt;
      this.syncActors();
      this.animateHero(dt,input);
      for (const blades of this.windmills) blades.rotation.z=this.time*.38;
      for (const fx of [...this.effects]) {
        fx.age+=dt; fx.mesh.scale.setScalar(.2+fx.age*(fx.life>.5?6:2));
        (fx.mesh.material as T.MeshBasicMaterial).opacity=.8*(1-fx.age/fx.life);
        if (fx.age>=fx.life) {
          this.dynamic.remove(fx.mesh); (fx.mesh.material as T.Material).dispose();
          this.effects.splice(this.effects.indexOf(fx),1);
        }
      }
      this.dirty=true;
    }
    this.hooks.frame();
    if (this.dirty) { this.renderer.render(this.scene,this.camera); this.dirty=false; }
  }
}
