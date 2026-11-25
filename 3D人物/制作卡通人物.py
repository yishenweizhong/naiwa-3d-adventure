"""Locally authored chibi portrait: sculpted features, no photographic face mask."""
import bpy, math, json
from mathutils import Vector
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"3D人物"; OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
def material(name,color,roughness=.7):
    rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    m=bpy.data.materials.new(name); m.diffuse_color=(*rgb,1); m.use_nodes=True
    bs=m.node_tree.nodes["Principled BSDF"]; bs.inputs["Base Color"].default_value=(*rgb,1)
    bs.inputs["Roughness"].default_value=roughness
    return m
M={k:material(k,c,r) for k,c,r in [
    ("skin","f3cbb9",.78),("blush","edb6ab",.8),("navy","293346",.78),
    ("trim","435068",.8),("black","242734",.8),("hair","704b3b",.56),
    ("lightHair","91644a",.6),("gold","f0c75b",.8),("white","fff4df",.7),
    ("tie","b94d67",.7),("green","c2df7b",.65),("boots","363446",.55),
    ("iris","684634",.36),("pupil","211f29",.35),("lip","d77687",.7),
    ("eyeWhite","fff8ed",.35)]}
arm=bpy.data.armatures.new("Naiwa_Chibi_Rig")
rig=bpy.data.objects.new("Naiwa_Chibi_Rig",arm); bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
spec={
    "Root":((0,0,0),(0,0,.12),None),
    "Pelvis":((0,0,.55),(0,0,.70),"Root"),
    "Spine":((0,0,.70),(0,0,1.18),"Pelvis"),
    "Head":((0,0,1.18),(0,0,1.69),"Spine")}
for s,side in [(-1,"L"),(1,"R")]:
    spec.update({
        f"UpperArm_{side}":((s*.21,0,1.12),(s*.27,0,.92),"Spine"),
        f"Forearm_{side}":((s*.27,0,.92),(s*.30,-.02,.73),f"UpperArm_{side}"),
        f"Hand_{side}":((s*.30,-.02,.73),(s*.30,-.03,.64),f"Forearm_{side}"),
        f"Thigh_{side}":((s*.10,0,.57),(s*.10,0,.32),"Pelvis"),
        f"Shin_{side}":((s*.10,0,.32),(s*.10,0,.11),f"Thigh_{side}"),
        f"Foot_{side}":((s*.10,0,.11),(s*.10,-.12,.045),f"Shin_{side}"),
        f"Hair_{side}":((s*.23,.04,1.59),(s*.38,.05,1.01),"Head"),
        f"Scarf_{side}":((s*.14,-.16,1.16),(s*.16,-.18,.63),"Spine")})
for name,(head,tail,parent) in spec.items():
    b=arm.edit_bones.new(name); b.head=head; b.tail=tail
    if parent: b.parent=arm.edit_bones[parent]
bpy.ops.object.mode_set(mode="OBJECT"); rig.select_set(False)
surfaces=[]
def finish(o,name,mat,bone):
    o.name=name; o.data.materials.append(M[mat])
    bpy.ops.object.select_all(action="DESELECT"); o.select_set(True); bpy.context.view_layer.objects.active=o
    if o.type=="CURVE": bpy.ops.object.convert(target="MESH"); o=bpy.context.object
    bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    o.vertex_groups.new(name=bone).add(list(range(len(o.data.vertices))),1,"REPLACE")
    for p in o.data.polygons: p.use_smooth=True
    surfaces.append(o); return o
def ell(name,loc,scale,mat,bone="Spine",segments=24,rings=16):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments,ring_count=rings,location=loc)
    o=bpy.context.object; o.scale=scale; return finish(o,name,mat,bone)
def tube(name,points,radius,mat,bone="Spine",radii=None):
    c=bpy.data.curves.new(name,"CURVE"); c.dimensions="3D"; c.resolution_u=5
    c.bevel_depth=radius; c.bevel_resolution=2
    sp=c.splines.new("BEZIER"); sp.bezier_points.add(len(points)-1)
    for i,(b,co) in enumerate(zip(sp.bezier_points,points)):
        b.co=co; b.handle_left_type=b.handle_right_type="AUTO"; b.radius=radii[i] if radii else 1
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o)
    return finish(o,name,mat,bone)
def panel(name,verts,mat,bone="Spine",thick=.006):
    me=bpy.data.meshes.new(name); me.from_pydata(verts,[],[tuple(range(len(verts)))]); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    bpy.context.view_layer.objects.active=o; o.select_set(True)
    m=o.modifiers.new("Cloth thickness","SOLIDIFY"); m.thickness=thick
    bpy.ops.object.modifier_apply(modifier=m.name)
    return finish(o,name,mat,bone)
def garment(name,rings,mat,bone="Spine"):
    n=32; vs=[(rx*math.cos(k*math.tau/n),ry*math.sin(k*math.tau/n),z) for z,rx,ry in rings for k in range(n)]
    fs=[(a*n+k,a*n+(k+1)%n,(a+1)*n+(k+1)%n,(a+1)*n+k) for a in range(len(rings)-1) for k in range(n)]
    fs.extend([tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))])
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    return finish(o,name,mat,bone)
def limb(name,rings,mat,upper,lower,joint):
    n=20; vs=[(x+rx*math.cos(k*math.tau/n),ry*math.sin(k*math.tau/n),z) for z,x,rx,ry in rings for k in range(n)]
    fs=[(a*n+k,a*n+(k+1)%n,(a+1)*n+(k+1)%n,(a+1)*n+k) for a in range(len(rings)-1) for k in range(n)]
    fs.extend([tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))])
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); finish(o,name,mat,upper)
    hi=o.vertex_groups[upper]; lo=o.vertex_groups.new(name=lower)
    for v in me.vertices:
        w=min(1,max(0,(joint+.05-v.co.z)/.10))
        hi.add([v.index],1-w,"REPLACE"); lo.add([v.index],w,"REPLACE")
    return o

# Soft A-line uniform and short, weighted limbs.
garment("Coat",[(.49,.24,.14),(.60,.225,.14),(.82,.175,.13),(1.02,.19,.135),(1.13,.21,.12),(1.18,.14,.09)],"navy")
garment("PleatedSkirt",[(.46,.22,.13),(.66,.17,.12)],"black","Pelvis")
ell("Neck",(0,0,1.22),(.07,.063,.10),"skin","Head")
panel("Shirt",[(-.09,-.142,1.17),(.09,-.142,1.17),(.08,-.149,.91),(-.08,-.149,.91)],"white")
for s,side in [(-1,"L"),(1,"R")]:
    panel("Collar",[(s*.005,-.17,1.19),(s*.11,-.14,1.18),(s*.075,-.18,1.08)],"white")
    panel("Lapel",[(s*.20,-.105,1.13),(s*.13,-.15,1.19),(s*.035,-.18,.87),(s*.16,-.146,.97)],"trim")
    limb("Sleeve",[(.73,s*.30,.065,.065),(.84,s*.28,.073,.073),(.92,s*.27,.079,.076),
        (1.04,s*.23,.085,.08),(1.14,s*.21,.074,.07)],"navy",f"UpperArm_{side}",f"Forearm_{side}",.92)
    ell("Cuff",(s*.30,-.02,.74),(.068,.063,.024),"white",f"Forearm_{side}")
    ell("MittenPalm",(s*.30,-.025,.68),(.061,.044,.065),"skin",f"Hand_{side}")
    ell("Thumb",(s*.25,-.052,.70),(.025,.028,.032),"skin",f"Hand_{side}",16,10)
    limb("Stocking",[(.12,s*.10,.051,.058),(.24,s*.10,.052,.056),(.32,s*.10,.058,.063),(.45,s*.10,.07,.075),(.57,s*.10,.077,.079)],
        "black",f"Thigh_{side}",f"Shin_{side}",.32)
    ell("Boot",(s*.10,-.06,.07),(.077,.13,.067),"boots",f"Foot_{side}")
    ell("BootShaft",(s*.10,0,.13),(.063,.065,.08),"boots",f"Shin_{side}")
    tube("BootSeam",[(s*.10-.06,-.08,.09),(s*.10,-.15,.095),(s*.10+.06,-.08,.09)],.006,"trim",f"Foot_{side}")
panel("Tie",[(-.025,-.182,1.10),(.025,-.182,1.10),(.04,-.184,.90),(0,-.184,.84),(-.04,-.184,.90)],"tie")
ell("TieKnot",(0,-.184,1.12),(.030,.017,.027),"tie")
for z in [.94,1.02]:
    panel("TieDiagonal",[(-.032,-.19,z+.008),(.032,-.19,z-.025),(.032,-.19,z-.041),(-.032,-.19,z-.008)],"gold",thick=.001)
for z in [.71,.81]:
    ell("CoatButton",(0,-.14,z),(.013,.009,.013),"gold",segments=12,rings=8)

# Sculpted head with a narrower jaw. Front = -Y, exported glTF front = +Z.
head=ell("SoftJaw",(0,.012,1.57),(.251,.205,.313),"skin","Head",48,32)
for v in head.data.vertices:
    if v.co.z<1.55:
        t=max(0,min(1,(1.55-v.co.z)/.30))
        v.co.x*=1-.12*t
for s in [-1,1]:
    ell("Ear",(s*.245,.02,1.55),(.036,.025,.054),"skin","Head")
    ell("EarInner",(s*.254,-.001,1.55),(.018,.010,.034),"blush","Head")
    # Almond eye silhouette, dark line above and a restrained brown iris.
    x=s*.103
    ell("AlmondEye",(x,-.181,1.597),(.078,.025,.040),"eyeWhite","Head",32,20)
    ell("BrownIris",(x,-.204,1.595),(.029,.009,.033),"iris","Head",28,18)
    ell("Pupil",(x,-.212,1.596),(.017,.004,.026),"pupil","Head",20,16)
    ell("EyeHighlight",(x-.009,-.218,1.608),(.009,.002,.010),"white","Head",12,8)
    ell("SmallGlint",(x+.011,-.217,1.583),(.004,.002,.005),"white","Head",12,8)
    tube("UpperLid",[(x-s*.073,-.184,1.599),(x-s*.036,-.201,1.632),(x+s*.017,-.200,1.636),(x+s*.077,-.172,1.616)],.006,"hair","Head",[.35,.8,1,.25])
    tube("Lash",[(x+s*.067,-.178,1.619),(x+s*.086,-.168,1.627)],.006,"hair","Head",[1,.1])
    tube("Brow",[(x-s*.054,-.173,1.667),(x-s*.01,-.184,1.685),(x+s*.050,-.162,1.676)],.009,"hair","Head",[.35,.85,.25])
    ell("WarmCheek",(s*.157,-.154,1.509),(.044,.004,.017),"blush","Head",24,12)
ell("NoseBridge",(0,-.189,1.55),(.016,.022,.044),"skin","Head")
ell("SoftNose",(0,-.211,1.524),(.026,.025,.018),"skin","Head")
tube("GentleSmile",[(-.058,-.157,1.455),(-.022,-.178,1.448),(0,-.181,1.446),(.026,-.177,1.453),(.058,-.151,1.471)],.0065,"lip","Head",[.1,.7,.9,.7,.1])
tube("LowerLip",[(-.030,-.166,1.432),(0,-.173,1.430),(.030,-.162,1.438)],.003,"blush","Head",[.1,1,.1])

# Broad tapered hair locks instead of a bundle of thin cylinders.
ell("HairBack",(0,.118,1.652),(.268,.12,.257),"hair","Head",36,24)
for i in range(9):
    x=-.195+i*.049
    end_z=1.72+abs(x)*.10-(.02 if i in [3,5] else 0)
    tube("Bangs",[(x*.74,-.052,1.84),(x*.88,-.139,1.79),(x,-.175+abs(x)*.19,end_z)],.030,"hair","Head",[1.15,1,.05])
for s,side in [(-1,"L"),(1,"R")]:
    tube("FaceFramingLock",[(s*.18,-.09,1.80),(s*.249,-.065,1.65),(s*.244,-.06,1.48)],.028,"hair","Head",[1,1,.05])
    ell("HairTie",(s*.255,.035,1.56),(.038,.04,.05),"gold","Head")
    for i in range(3):
        d=(i-1)*.041
        tube("TwinTail",[(s*(.265+d),.08,1.56),(s*(.32+d),.065,1.39),(s*(.41+d),.019,1.20),
             (s*(.39+d),-.045,1.05+i*.025),(s*(.31+d),-.07,1.00+i*.025)],
             .054,"hair",f"Hair_{side}",[.8,1.1,1,.65,.025])
    for i in [-1,1]:
        tube("HairRibbon",[(s*(.29+i*.026),.018,1.50),(s*(.36+i*.026),-.033,1.29),(s*(.42+i*.026),-.075,1.08)],
             .004,"lightHair",f"Hair_{side}",[.3,1,.1])
ell("HatCrown",(0,.022,1.89),(.284,.22,.16),"black","Head",40,24)
ell("HatBrim",(0,-.028,1.80),(.31,.254,.033),"black","Head",40,16)
for s in [-1,1]:
    tube("PointedHatEar",[(s*.19,.06,1.99),(s*.30,.08,2.13),(s*.32,.09,2.22)],.075,"black","Head",[1.15,.7,.03])
    ell("LimeHatEye",(s*.12,-.170,1.927),(.073,.012,.055),"green","Head")
    ell("HatPupil",(s*.132,-.184,1.922),(.045,.010,.044),"black","Head")
    ell("HatGlint",(s*.106,-.196,1.943),(.012,.004,.012),"white","Head",12,8)
ell("ScarfWrap",(0,0,1.18),(.12,.13,.05),"gold")
for s,side in [(-1,"L"),(1,"R")]:
    x=s*.154; bottom=.56 if s<0 else .62; b=f"Scarf_{side}"
    panel("YellowScarf",[(x-.050,-.169,1.18),(x+.050,-.169,1.18),(x+.057,-.188,bottom),(x-.047,-.188,bottom)],"gold",b,.015)
    for z in [bottom+.04,bottom+.077,bottom+.24,bottom+.277,bottom+.44,bottom+.477]:
        if z<1.16: panel("PairedBlackStripe",[(x-.05,-.198,z),(x+.055,-.198,z),(x+.055,-.198,z+.022),(x-.05,-.198,z+.022)],"black",b,.001)
    for i in range(8):
        xx=x-.042+i*.013
        tube("ScarfFringe",[(xx,-.19,bottom+.005),(xx,-.19,bottom-.03)],.003,"gold",b)

bpy.ops.object.select_all(action="DESELECT")
for o in surfaces: o.select_set(True)
bpy.context.view_layer.objects.active=surfaces[0]; bpy.ops.object.join()
skin=bpy.context.object; skin.name="Naiwa_CutePortrait"
def chibi_z(z): return z*.76 if z<=1.18 else z-1.18*.24
for v in skin.data.vertices: v.co.z=chibi_z(v.co.z)
bpy.ops.object.select_all(action="DESELECT"); rig.select_set(True); bpy.context.view_layer.objects.active=rig
bpy.ops.object.mode_set(mode="EDIT")
for b in arm.edit_bones:
    b.head.z=chibi_z(b.head.z); b.tail.z=chibi_z(b.tail.z)
bpy.ops.object.mode_set(mode="OBJECT")
mod=skin.modifiers.new("Smooth skeleton","ARMATURE"); mod.object=rig; skin.parent=rig
rig["source_note"]="Original local stylization from user's reference photographs; no photo texture and no scan claim."
rig["front"]="Blender -Y / glTF +Z"
def reset():
    for b in rig.pose.bones:
        b.rotation_mode="XYZ"; b.rotation_euler=(0,0,0); b.location=(0,0,0)
durations={"idle":3.2,"walk":.9,"attack":.45,"defend":1.6,"dash":.36,"laugh":1.6}
rig.animation_data_create()
for name,duration in durations.items():
    rig.animation_data.action=None; count=round(duration*30)
    for f in range(count+1):
        reset(); p=rig.pose.bones; t=f/count; wave=math.sin(t*math.tau); pulse=math.sin(math.pi*t)**2
        if name=="idle":
            p["Spine"].rotation_euler.x=.016*wave; p["Head"].rotation_euler.z=.022*wave
            p["Pelvis"].location.y=.004*wave
        elif name=="walk":
            p["Pelvis"].location.y=.013*(1-math.cos(t*math.tau*2))/2
            p["Spine"].rotation_euler.z=.042*wave
            for s,side in [(-1,"L"),(1,"R")]:
                stride=s*wave
                p[f"Thigh_{side}"].rotation_euler.x=.43*stride
                p[f"Shin_{side}"].rotation_euler.x=-.52*max(0,-stride)
                p[f"Foot_{side}"].rotation_euler.x=.14*stride
                p[f"UpperArm_{side}"].rotation_euler.x=-.31*stride
                p[f"Forearm_{side}"].rotation_euler.x=-.10-.08*max(0,stride)
        elif name=="attack":
            p["UpperArm_R"].rotation_euler.x=1.1*pulse; p["Forearm_R"].rotation_euler.x=.28*pulse
            p["Spine"].rotation_euler.z=-.10*pulse; p["Head"].rotation_euler.z=.05*pulse
        elif name=="defend":
            p["UpperArm_L"].rotation_euler.x=1.05+.02*wave
            p["Forearm_L"].rotation_euler.x=.75; p["Spine"].rotation_euler.x=-.07
        elif name=="dash":
            p["Spine"].rotation_euler.x=-.27-.04*pulse
            p["Thigh_L"].rotation_euler.x=.65; p["Thigh_R"].rotation_euler.x=-.62; p["Shin_R"].rotation_euler.x=-.50
            for side in ["L","R"]: p[f"UpperArm_{side}"].rotation_euler.x=-.48
        elif name=="laugh":
            p["Head"].rotation_euler.x=.12*pulse; p["Spine"].rotation_euler.x=.05*math.sin(t*math.tau*3)*pulse
            for s,side in [(-1,"L"),(1,"R")]:
                p[f"UpperArm_{side}"].rotation_euler.z=-s*.68*pulse; p[f"Forearm_{side}"].rotation_euler.x=.4*pulse
        for s,side in [(-1,"L"),(1,"R")]:
            p[f"Hair_{side}"].rotation_euler.x=.045*math.sin(t*math.tau-.5) if name in ["idle","walk","defend"] else -.14*pulse
            p[f"Hair_{side}"].rotation_euler.z=s*.02*wave
            p[f"Scarf_{side}"].rotation_euler.x=.03*math.sin(t*math.tau-.8) if name in ["idle","walk","defend"] else -.10*pulse
        for b in p:
            b.keyframe_insert("rotation_euler",frame=f+1,group=b.name)
            b.keyframe_insert("location",frame=f+1,group=b.name)
    action=rig.animation_data.action; action.name=name
    track=rig.animation_data.nla_tracks.new(); track.name=name; track.strips.new(name,1,action); track.mute=True
rig.animation_data.action=None; reset()
scene=bpy.context.scene; scene.render.fps=30; scene.frame_set(1); scene.frame_end=97
bpy.ops.object.select_all(action="DESELECT"); rig.select_set(True); skin.select_set(True)
bpy.context.view_layer.objects.active=rig
glb=ROOT/"public/models/reference-hero.glb"
bpy.ops.export_scene.gltf(filepath=str(glb),use_selection=True,export_format="GLB",export_animations=True,
    export_animation_mode="NLA_TRACKS",export_skins=True,export_force_sampling=True,export_frame_range=False,export_yup=True)
scene.render.engine="CYCLES"; scene.cycles.samples=24; scene.cycles.use_denoising=True
scene.render.resolution_x=768; scene.render.resolution_y=960; scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"; scene.view_settings.view_transform="AgX"
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.62,.68,.72,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value=.45
for name,pos,power,size in [("Key",(-3,-4,5),350,4),("Fill",(3,-2,3),160,3),("Rim",(1,3,4),300,3)]:
    d=bpy.data.lights.new(name,"AREA"); d.energy=power; d.size=size
    o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o); o.location=pos
    o.rotation_euler=(Vector((0,0,1.1))-o.location).to_track_quat("-Z","Y").to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.004))
bpy.context.object.data.materials.append(material("Studio","e9dfcf"))
d=bpy.data.cameras.new("PortraitCamera"); camera=bpy.data.objects.new("PortraitCamera",d)
bpy.context.collection.objects.link(camera); scene.camera=camera; d.type="ORTHO"; d.ortho_scale=2.35
for name,pos in [("正面",(0,-6,1.65)),("三分之四",(2.5,-6,1.8)),("背面",(2.5,6,1.8))]:
    camera.location=pos; camera.rotation_euler=(Vector((0,0,.96))-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(OUT/f"人物_{name}.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"可爱卡通人物.blend"))
stats={"vertices":len(skin.data.vertices),"triangles":sum(len(p.vertices)-2 for p in skin.data.polygons),
       "bones":len(arm.bones),"animations":durations,"glb_bytes":glb.stat().st_size,"blender":bpy.app.version_string,
       "style":"Locally sculpted cute chibi, recognizable costume and facial features; not a scan"}
(OUT/"模型规格.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2))
print("CHARACTER_COMPLETE",json.dumps(stats,ensure_ascii=False))
