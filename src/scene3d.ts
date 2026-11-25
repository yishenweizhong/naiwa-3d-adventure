import * as T from "three";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { World, ARENA, type Input, type GameEvent, type Enemy } from "./model.ts";
import { heroMotion, type HeroMotion } from "./hero-motion.ts";
import { heroFraming } from "./hero-framing.ts";
import { advanceWorld } from "./clock.ts";
import { RoundedBoxGeometry } from "three/addons/geometries/RoundedBoxGeometry.js";

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
  private decorations = new T.Group();
  private props = new Map<string,T.Group>();
  private hero = new T.Group();
  private figure?: T.Group;
  private shieldHand?: T.Object3D;
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
  private labels: { sprite:T.Sprite; age:number }[] = [];
  private shadowTexture?: T.CanvasTexture;
  private enemyTexture?: T.Texture;
  private portraitError = false;
  private heroError = false;
  private heroLoaded = false;
  private enemyHeads = new Map<number, { sprite: T.Sprite; hitUntil: number }>();
  private starTexture?: T.CanvasTexture;
  private hitParticles: { sprite: T.Sprite; age: number; life: number; velocity: T.Vector3 }[] = [];
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
  private modelUrl = `${import.meta.env.BASE_URL}models/reference-hero.glb?v=tailored-proportions-20261125`;

  constructor(private world: World, private hooks: Hooks) {
    this.renderer = new T.WebGLRenderer({ antialias: true, alpha: false, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = T.PCFSoftShadowMap;
    this.renderer.shadowMap.autoUpdate = false;
    this.renderer.toneMapping = T.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.1;
    this.renderer.outputColorSpace = T.SRGBColorSpace;
    this.renderer.domElement.setAttribute("aria-label", "实时三维游戏场景");
    document.getElementById("game")!.append(this.renderer.domElement);
    this.camera.position.set(0, 18, 23);
    this.camera.lookAt(0, 0, -2);
    this.scene.add(this.environment, this.decorations, this.dynamic, this.hero);
    this.contact(this.hero,.29);
    this.scene.add(new T.HemisphereLight(0xd9efff, 0x7c7559, 2.3));
    this.sun.position.set(-8, 18, 9);
    this.sun.castShadow = true;
    this.sun.shadow.mapSize.set(1024, 1024);
    Object.assign(this.sun.shadow.camera, { left: -18, right: 18, top: 16, bottom: -14, near: .1, far: 60 });
    this.sun.shadow.bias = -.0008;
    this.sun.shadow.normalBias = .03;
    this.scene.add(this.sun);
    const game = document.getElementById("game")!;
    new ResizeObserver(() => {
      this.renderer.setSize(game.clientWidth, game.clientHeight, false);
      const halfHeight=13.5*game.clientHeight/Math.max(1,game.clientWidth);
      this.camera.top=halfHeight; this.camera.bottom=-halfHeight;
      this.camera.updateProjectionMatrix();
      this.dirty = true;
    }).observe(game);
    this.renderer.domElement.addEventListener("webglcontextlost", e => {
      e.preventDefault();
      this.world.pause(true);
      this.status("画面连接中断，刷新页面后可继续已保存的进度。", "error");
    });
    this.loadProps();
    this.loadEnemyPortrait();
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
      button.onclick = () => {
        if (!this.enemyTexture) this.loadEnemyPortrait();
        this.loadHero();
      };
      box.append(button);
    }
  }
  private updateReady() {
    this.ready = this.heroLoaded && !!this.enemyTexture && !this.portraitError && !this.heroError;
    if (this.portraitError) this.status("小兵头像未加载成功，检查网络后重试。", "error");
    else if (this.heroError) this.status("人物未加载成功，检查网络后重试。", "error");
    else this.status(this.ready ? "" : "人物加载中…", this.ready ? "ready" : "loading");
    this.dirty = true;
  }
  private loadEnemyPortrait() {
    this.portraitError = false;
    new T.TextureLoader().load(`${import.meta.env.BASE_URL}textures/enemy-head.png`, texture => {
      texture.colorSpace = T.SRGBColorSpace;
      this.enemyTexture = texture;
      this.stage.dataset.enemyPortrait = "ready";
      this.updateReady();
    }, undefined, () => {
      this.portraitError = true;
      this.stage.dataset.enemyPortrait = "error";
      this.updateReady();
    });
  }
  private loadProps() {
    for (const name of ["cloud","grass"]) {
      this.loader.load(`${import.meta.env.BASE_URL}models/kenney/${name}.glb`, gltf => {
        const bounds=new T.Box3().setFromObject(gltf.scene), size=bounds.getSize(new T.Vector3());
        const center=bounds.getCenter(new T.Vector3());
        gltf.scene.traverse(o=>{
          if (o instanceof T.Mesh) { o.material=this.mat(name==="cloud"?"#fff8ef":"#87b183"); o.castShadow=false; }
        });
        const normalized=new T.Group(); normalized.add(gltf.scene);
        gltf.scene.position.sub(center);
        if (name==="grass") gltf.scene.position.y+=size.y/2;
        normalized.scale.setScalar((name==="cloud"?4:.65)/Math.max(size.x,size.y,size.z));
        this.props.set(name,normalized); this.placeProps(); this.dirty=true;
      },undefined,()=>{ this.stage.dataset.propError=name; });
    }
  }
  private placeProps() {
    this.decorations.clear();
    for (const [name,source] of this.props) {
      const count=name==="cloud"?5:12;
      for (let i=0;i<count;i++) {
        const g=source.clone(true);
        g.position.set(name==="cloud"?-15+i*7:-11+i*2,
          name==="cloud"?6+(i%2)*1.7:.03,name==="cloud"?-14-i%2*2:-4.6);
        if (name==="grass") g.rotation.y=i*1.7;
        this.decorations.add(g);
      }
    }
    this.stage.dataset.cc0Props=String(this.props.size);
  }

  private loadHero() {
    this.ready = false;
    this.heroLoaded = false;
    this.heroError = false;
    this.actions.clear();
    if (this.figure) {
      this.mixer?.stopAllAction();
      this.hero.remove(this.figure);
      this.figure.traverse(o => {
        if (o instanceof T.Mesh) {
          o.geometry.dispose();
          for (const m of Array.isArray(o.material) ? o.material : [o.material]) m.dispose();
        }
      });
    }
    this.status("人物加载中…", "loading");
    this.loader.load(this.modelUrl, gltf => {
      this.figure = gltf.scene;
      let hasPortrait = false;
      this.figure.traverse(o => {
        if (o instanceof T.Mesh) {
          o.castShadow = false; o.receiveShadow = true; o.frustumCulled = false;
          const original = Array.isArray(o.material) ? o.material : [o.material];
          const materials = original.map(m => {
            if (m.name !== "ReferenceFace") return m;
            hasPortrait = true;
            const source = m as T.MeshStandardMaterial;
            // Preserve the selected illustration's colours, without lighting or tone mapping.
            const portrait = new T.MeshBasicMaterial({
              map: source.map ?? source.emissiveMap, transparent: true, alphaTest: .02,
              depthWrite: true, side: T.FrontSide, toneMapped: false,
            });
            portrait.name = "ReferenceFace"; m.dispose();
            return portrait;
          });
          o.material = Array.isArray(o.material) ? materials : materials[0];
        }
      });
      if (!hasPortrait) {
        this.heroError = true;
        this.status("人物资源版本不匹配，请刷新后重新加载。", "error");
        return;
      }
      this.hero.add(this.figure);
      this.shieldHand=this.figure.getObjectByName("Hand_L");
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
        this.heroError = true;
        this.status("人物动作资源不完整，请重新加载。", "error");
        return;
      }
      this.baseAction = this.actions.get("idle")!;
      this.movingAction = this.actions.get("walk")!;
      this.baseAction.play();
      this.movingAction.play().setEffectiveWeight(0);
      this.heroLoaded = true;
      this.motion = undefined;
      this.stage.dataset.heroPortrait = "selected-illustration";
      this.updateReady();
    }, undefined, () => {
      this.heroError = true;
      this.updateReady();
    });
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
      const g = kind === "box" ? new RoundedBoxGeometry(1, 1, 1, 2, .08)
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
  // Inspired by drei's blurred contact shadows; a shared procedural decal avoids per-frame depth passes.
  private contact(parent:T.Object3D,radius:number) {
    if (!this.shadowTexture) {
      const canvas=document.createElement("canvas"); canvas.width=canvas.height=64;
      const ctx=canvas.getContext("2d")!, gradient=ctx.createRadialGradient(32,32,3,32,32,32);
      gradient.addColorStop(0,"rgba(43,58,43,.32)"); gradient.addColorStop(.45,"rgba(43,58,43,.16)");
      gradient.addColorStop(1,"rgba(43,58,43,0)"); ctx.fillStyle=gradient; ctx.fillRect(0,0,64,64);
      this.shadowTexture=new T.CanvasTexture(canvas);
    }
    const m=new T.Mesh(new T.PlaneGeometry(radius*3,radius*2.2),
      new T.MeshBasicMaterial({map:this.shadowTexture,transparent:true,depthWrite:false}));
    m.rotation.x=-Math.PI/2; m.position.y=.085; parent.add(m);
  }

  private house(x: number, z: number, color: string, size = 1) {
    const g = new T.Group(); g.position.set(x, 0, z); g.scale.setScalar(size); this.environment.add(g);
    this.box(g, color, 0, 1.35, 0, 2.8, 2.7, 2.2);
    const roof = this.mesh(g, "cone", "#d78d83", [0, 3.25, 0], [2.3, 1.4, 1.9]);
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
    this.mesh(g, "cylinder", "#ad8865", [0, 1, 0], [.17, 2, .17]);
    for (let i=0; i<3; i++)
      this.mesh(g, "sphere", i === 1 ? "#a4c98a" : "#7fab80",
        [Math.sin(i*2)*.45, 2.1+i*.38, Math.cos(i*2)*.28], [.95, .85, .95]);
  }
  private windmill(x: number, z: number, size = 1) {
    const g = new T.Group(); g.position.set(x, 0, z); g.scale.setScalar(size); this.environment.add(g);
    this.mesh(g, "cylinder", "#c4bca1", [0, 2, 0], [.9, 4, .9]);
    this.mesh(g, "cone", "#b78aa6", [0, 4.3, 0], [1.25, 1.15, 1.25]);
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
    this.scene.background = new T.Color(night ? "#8e99bf" : dusk ? "#ecd0da" : "#c5e2dd");
    this.scene.fog = new T.Fog(this.scene.background, 38, 78);
    this.sun.color.set(night ? "#b0c9ff" : "#ffe2ad");
    const ground = night ? "#b3b7cd" : dusk ? "#c9b6ad" : "#bdd39e";
    this.box(this.environment, "#b8a98b", 0, -.55, -2, 30, 1, 20);
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
      this.mesh(this.environment, "sphere", dusk ? "#acb9aa" : "#a3c3a0", [x, 2.8, z], [5, 2.6+(i%3)*.1, 4]);
    }
    this.placeProps();
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
    for (let i=0;i<25;i++) {
      const x=-11+i*.93, z=-4.55-(i%3)*.14;
      this.mesh(this.environment,"cylinder","#6b9972",[x,.19,z],[.026,.38,.026]);
      for (let j=0;j<4;j++)
        this.mesh(this.environment,"sphere",i%2?"#f5d389":"#eeadbc",
          [x+Math.sin(j*Math.PI/2)*.09,.39,z+Math.cos(j*Math.PI/2)*.09],[.095,.065,.095]);
      this.mesh(this.environment,"sphere","#fff4d7",[x,.43,z],[.052,.04,.052]);
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
      const color=boss ? "#9b8bb7" : mage ? "#b49bcb" : rusher ? "#dea274" : "#93b5a0";
      this.mesh(g,"sphere",color,[0,.69,0],[.39,.49,.31]);
      const portrait = new T.Sprite(new T.SpriteMaterial({
        map: this.enemyTexture, transparent: true, alphaTest: .02,
        toneMapped: false, depthWrite: true,
      }));
      portrait.name = "SelectedEnemyHead";
      portrait.position.set(0,1.43,.06);
      portrait.scale.set(.78,1.15,1);
      g.add(portrait);
      this.enemyHeads.set(e.id,{sprite:portrait,hitUntil:0});
      for (const s of [-1,1]) {
        const arm=this.mesh(g,"sphere",color,[s*.40,.76,.01],[.14,.25,.14]); arm.name=`arm${s}`;
        this.mesh(g,"sphere","#f3dcc0",[s*.43,.55,.025],[.11,.11,.11]);
        const foot=this.mesh(g,"sphere","#655772",[s*.16,.18,.02],[.14,.18,.19]); foot.name=`foot${s}`;
      }
      this.mesh(g,"sphere","#ead096",[0,.75,.31],[.20,.26,.035]);
      if (mage) {
        this.mesh(g,"cylinder","#5f536c",[.52,.8,0],[.04,1.4,.04]);
        this.mesh(g,"sphere","#c0a4de",[.52,1.57,0],[.13,.13,.13]);
      }
      if (boss) {
        g.scale.setScalar(1.75);
        this.box(g,"#a5a8b4",0,.95,-.3,.9,1.1,.16);
        this.ring(g,"#f3d082",.30,1.99);
        for (const x of [-.22,0,.22]) this.mesh(g,"cone","#f3d082",[x,2.10,0],[.10,.24,.10]);
      }
      const bar=new T.Group(); bar.name="health"; bar.position.set(0,boss?2.4:2.2,0); g.add(bar);
      this.box(bar,"#424d59",0,0,0,.7,.07,.05);
      const fill=this.box(bar,"#dce3b9",0,0,.035,.68,.05,.04); fill.name="fill";
      this.contact(g,.35);
    }
    g.position.set(px(e.x),0,pz(e.y));
    g.rotation.y=Math.atan2(this.hero.position.x-g.position.x,this.hero.position.z-g.position.z);
    g.position.y=e.stun>0 ? .06*Math.sin(this.time*14) : .025*Math.sin(this.time*5+e.id);
    const head = this.enemyHeads.get(e.id)!;
    const remaining = Math.max(0, head.hitUntil-this.time);
    const recoil = remaining > 0 ? Math.sin((.42-remaining)*Math.PI/.42) : 0;
    head.sprite.material.color.setRGB(1,1-recoil*.42,1-recoil*.55);
    head.sprite.material.rotation = recoil*.16;
    head.sprite.position.y = 1.43 + recoil*.12;
    head.sprite.scale.set(.78*(1+recoil*.08),1.15*(1-recoil*.06),1);
    for (const s of [-1,1]) {
      g.getObjectByName(`arm${s}`)!.rotation.x=e.windup>0 ? -.6 : s*.24*Math.sin(this.time*6+e.id);
      g.getObjectByName(`foot${s}`)!.position.y=.18+s*.035*Math.sin(this.time*6+e.id);
    }
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
      if (!keep.has(key)) {
        if (key.startsWith("enemy:")) {
          const id = Number(key.slice(6));
          this.enemyHeads.get(id)?.sprite.material.dispose();
          this.enemyHeads.delete(id);
        }
        this.dynamic.remove(o); this.actorMap.delete(key);
      }
    }
    this.stage.dataset.enemyHeads = String(this.enemyHeads.size);
    this.stage.dataset.hitFlashes = String([...this.enemyHeads.values()].filter(h => h.hitUntil>this.time).length);
  }

  private hitFeedback(e: GameEvent) {
    if (e.targetId === undefined) return;
    const head = this.enemyHeads.get(e.targetId);
    if (head) head.hitUntil = this.time + .42;
    const alive = this.world.enemies.some(enemy => enemy.id===e.targetId);
    const actor = this.actorMap.get(`enemy:${e.targetId}`);
    const height = actor?.scale.y===1.75 ? 2.8 : 1.65;
    if (!this.starTexture) {
      const c=document.createElement("canvas"); c.width=c.height=64;
      const ctx=c.getContext("2d")!;
      ctx.beginPath();
      for (let i=0;i<10;i++) {
        const angle=-Math.PI/2+i*Math.PI/5, r=i%2?12:27;
        const x=32+Math.cos(angle)*r, y=32+Math.sin(angle)*r;
        if (i===0) ctx.moveTo(x,y); else ctx.lineTo(x,y);
      }
      ctx.closePath(); ctx.fillStyle="#ffe293"; ctx.fill();
      ctx.lineWidth=3; ctx.strokeStyle="#fff8e4"; ctx.stroke();
      this.starTexture=new T.CanvasTexture(c);
      this.starTexture.colorSpace=T.SRGBColorSpace;
    }
    for (let i=0;i<(alive?5:9);i++) {
      const angle=i*Math.PI*2/(alive?5:9);
      const sprite=new T.Sprite(new T.SpriteMaterial({
        map:this.starTexture,transparent:true,depthWrite:false,toneMapped:false,
        color:alive?0xffffff:0xffc7a0,
      }));
      sprite.position.set(px(e.x),height,pz(e.y));
      sprite.scale.setScalar(alive?.32:.42);
      this.dynamic.add(sprite);
      this.hitParticles.push({sprite,age:0,life:alive?.58:.85,
        velocity:new T.Vector3(Math.cos(angle)*1.6,.6+Math.sin(angle)*1.2,Math.sin(angle)*.35)});
    }
    this.stage.dataset.lastHitTarget=String(e.targetId);
    this.stage.dataset.enemyHits=String(Number(this.stage.dataset.enemyHits??0)+1);
    if (!alive) this.stage.dataset.enemyDefeats=String(Number(this.stage.dataset.enemyDefeats??0)+1);
  }

  private event(e: GameEvent) {
    if (e.kind==="hit") this.hitFeedback(e);
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
    if (e.value && ["hit","hurt","heal","block"].includes(e.kind)) {
      const c=document.createElement("canvas"); c.width=128; c.height=64;
      const ctx=c.getContext("2d")!; ctx.font="bold 36px sans-serif"; ctx.textAlign="center";
      ctx.lineWidth=7; ctx.strokeStyle="#fffaf1";
      const text=`${e.kind==="heal"?"+":"−"}${e.value}`;
      ctx.strokeText(text,64,46); ctx.fillStyle=e.kind==="heal"?"#527d5b":e.kind==="hurt"?"#be5e73":"#947343"; ctx.fillText(text,64,46);
      const sprite=new T.Sprite(new T.SpriteMaterial({map:new T.CanvasTexture(c),depthTest:false,transparent:true}));
      sprite.position.set(px(e.x),2.7,pz(e.y)); sprite.scale.set(1.1,.55,1);
      this.dynamic.add(sprite); this.labels.push({sprite,age:0});
    }
    this.hooks.event(e);
  }

  private animateHero(dt: number, input: Input) {
    const menu=this.world.phase==="menu", h=this.world.hero;
    const mobile=matchMedia("(max-width:650px) and (orientation:portrait)").matches;
    const framing=heroFraming(menu,mobile);
    this.hero.position.set(menu?(mobile?0:6):px(h.x),0,menu?2.8:pz(h.y));
    this.hero.scale.setScalar(framing.scale);
    this.camera.position.lerp(new T.Vector3(0,framing.cameraY,framing.cameraZ),1-Math.exp(-dt*6));
    this.camera.zoom=T.MathUtils.damp(this.camera.zoom, framing.zoom,8,dt);
    this.camera.updateProjectionMatrix();
    this.camera.lookAt(0,framing.lookY,framing.lookZ);
    // Record projected upright endpoints for viewport/camera verification.
    this.camera.updateMatrixWorld();
    const foot=this.hero.position.clone().project(this.camera);
    const head=this.hero.position.clone().add(new T.Vector3(0,1.913*framing.scale,0)).project(this.camera);
    this.stage.dataset.heroProjectedHeight=String(Math.round(Math.abs(head.y-foot.y)*this.renderer.domElement.clientHeight/2));
    this.stage.dataset.heroProjectedTop=String((1-head.y)/2);
    this.stage.dataset.heroProjectedBottom=String((1-foot.y)/2);
    this.stage.dataset.heroScale=String(framing.scale);
    if (!this.ready) return;
    const moving=!menu && Math.hypot(input.x,input.y)>.05;
    const direction=menu ? -.08 : this.world.hero.dashTime>0 || (this.transient.action==="dash" && this.transient.actionTime>0)
      ? Math.atan2(h.dashX,h.dashY)
      : this.transient.action==="attack" && this.world.enemies.length
        ? (() => {
            const e=this.world.enemies.reduce((a,b) => Math.hypot(a.x-h.x,a.y-h.y)<Math.hypot(b.x-h.x,b.y-h.y)?a:b);
            return Math.atan2(e.x-h.x,e.y-h.y);
          })()
        : moving ? Math.atan2(input.x,input.y) : this.angle;
    const target = menu ? direction : Math.sin(direction)*.48;
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
        this.mesh(o,"sphere","#b4daef",[0,0,0],[.56,.68,.10],true);
        const edge=this.ring(o,"#c2e3ef",.58,0); edge.rotation.x=0; edge.scale.y=.70;
        return o;
      });
      this.hero.updateMatrixWorld(true);
      const hand=this.shieldHand?.getWorldPosition(new T.Vector3())
        ?? this.hero.position.clone().add(new T.Vector3(-.5,2.8,.6));
      g.position.copy(hand).add(new T.Vector3(0,-.26,.18).applyAxisAngle(new T.Vector3(0,1,0),this.angle));
      g.rotation.y=this.angle;
      this.stage.dataset.shieldHandDistance=String(g.position.distanceTo(hand));
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
      if (this.ready) this.syncActors();
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
      for (const label of [...this.labels]) {
        label.age+=dt; label.sprite.position.y+=dt*.8; label.sprite.material.opacity=Math.max(0,1-label.age/.75);
        if (label.age>=.75) {
          this.dynamic.remove(label.sprite); label.sprite.material.map!.dispose(); label.sprite.material.dispose();
          this.labels.splice(this.labels.indexOf(label),1);
        }
      }
      for (const particle of [...this.hitParticles]) {
        particle.age+=dt;
        particle.sprite.position.addScaledVector(particle.velocity,dt);
        particle.velocity.y-=dt*2;
        particle.sprite.material.rotation+=dt*2;
        particle.sprite.material.opacity=Math.max(0,1-particle.age/particle.life);
        if (particle.age>=particle.life) {
          this.dynamic.remove(particle.sprite); particle.sprite.material.dispose();
          this.hitParticles.splice(this.hitParticles.indexOf(particle),1);
        }
      }
      this.stage.dataset.hitParticles=String(this.hitParticles.length);
      this.dirty=true;
    }
    this.hooks.frame();
    if (this.dirty) { this.renderer.render(this.scene,this.camera); this.dirty=false; }
  }
}
