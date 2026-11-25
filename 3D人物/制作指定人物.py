"""Independent 3D body and rig, with the user's selected illustration as the face texture."""
import bpy, math, json
from mathutils import Vector
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"3D人物"; OUT.mkdir(exist_ok=True)
bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete(use_global=False)
def material(name, color, roughness=.7):
    rgb=[int(color[i:i+2],16)/255 for i in (0,2,4)]
    rgb=[v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4 for v in rgb]
    m=bpy.data.materials.new(name); m.diffuse_color=(*rgb,1); m.use_nodes=True
    bs=m.node_tree.nodes["Principled BSDF"]
    bs.inputs["Base Color"].default_value=(*rgb,1)
    bs.inputs["Roughness"].default_value=roughness
    return m
M={k:material(k,c,r) for k,c,r in [
    ("skin","edc5a6",.8),("hair","292b27",.65),("hairLight","5e4b35",.7),
    ("dress","26282d",.8),("seam","34373e",.8),("white","f4e9d5",.75),
    ("lace","fff4e1",.85),("gold","c8a261",.38),("shoe","24252b",.65)]}
face=bpy.data.materials.new("ReferenceFace"); face.use_nodes=True
face.surface_render_method="DITHERED"
nodes=face.node_tree.nodes; nodes.clear()
output=nodes.new("ShaderNodeOutputMaterial")
emission=nodes.new("ShaderNodeEmission"); transparent=nodes.new("ShaderNodeBsdfTransparent")
mix=nodes.new("ShaderNodeMixShader")
texture=nodes.new("ShaderNodeTexImage")
texture.image=bpy.data.images.load(str(ROOT/"public/textures/hero-face.png"))
texture.image.pack()
uv_node=nodes.new("ShaderNodeUVMap"); uv_node.uv_map="UVMap"
face.node_tree.links.new(uv_node.outputs["UV"],texture.inputs["Vector"])
face.node_tree.links.new(texture.outputs["Color"],emission.inputs["Color"])
face.node_tree.links.new(texture.outputs["Alpha"],mix.inputs[0])
face.node_tree.links.new(transparent.outputs[0],mix.inputs[1])
face.node_tree.links.new(emission.outputs[0],mix.inputs[2])
face.node_tree.links.new(mix.outputs[0],output.inputs[0])
M["face"]=face

arm=bpy.data.armatures.new("Tomato_Reference_Rig")
rig=bpy.data.objects.new("Tomato_Reference_Rig",arm); bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
spec={"Root":((0,0,0),(0,0,.12),None),
      "Pelvis":((0,0,.75),(0,0,.95),"Root"),
      "Spine":((0,0,.95),(0,0,1.47),"Pelvis"),
      "Head":((0,0,1.47),(0,0,1.91),"Spine")}
for s,side in [(-1,"L"),(1,"R")]:
    spec.update({
        f"UpperArm_{side}":((s*.205,0,1.39),(s*.25,0,1.14),"Spine"),
        f"Forearm_{side}":((s*.25,0,1.14),(s*.28,-.015,.91),f"UpperArm_{side}"),
        f"Hand_{side}":((s*.28,-.015,.91),(s*.29,-.02,.82),f"Forearm_{side}"),
        f"Thigh_{side}":((s*.09,0,.76),(s*.09,0,.43),"Pelvis"),
        f"Shin_{side}":((s*.09,0,.43),(s*.09,0,.1),f"Thigh_{side}"),
        f"Foot_{side}":((s*.09,0,.1),(s*.09,-.12,.035),f"Shin_{side}"),
        f"Hair_{side}":((s*.14,.06,1.66),(s*.18,-.04,1.12),"Head"),
        # Keep the six-action rig contract; these bones now animate the bag/chains.
        f"Scarf_{side}":((s*.13,-.12,1.36),(s*.16,-.15,.75),"Spine")})
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
    o=bpy.context.object; o.scale=scale
    return finish(o,name,mat,bone)
def tube(name,points,radius,mat,bone="Spine",radii=None):
    c=bpy.data.curves.new(name,"CURVE"); c.dimensions="3D"; c.resolution_u=4
    c.bevel_depth=radius; c.bevel_resolution=2
    sp=c.splines.new("BEZIER"); sp.bezier_points.add(len(points)-1)
    for i,(b,co) in enumerate(zip(sp.bezier_points,points)):
        b.co=co; b.handle_left_type=b.handle_right_type="AUTO"; b.radius=radii[i] if radii else 1
    o=bpy.data.objects.new(name,c); bpy.context.collection.objects.link(o)
    return finish(o,name,mat,bone)
def garment(name,rings,mat,bone="Spine"):
    n=40; vs=[(rx*math.cos(k*math.tau/n),ry*math.sin(k*math.tau/n),z)
              for z,rx,ry in rings for k in range(n)]
    fs=[(a*n+k,a*n+(k+1)%n,(a+1)*n+(k+1)%n,(a+1)*n+k)
        for a in range(len(rings)-1) for k in range(n)]
    fs.extend([tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))])
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    return finish(o,name,mat,bone)
def limb(name,rings,mat,upper,lower,joint):
    n=20; vs=[(x+rx*math.cos(k*math.tau/n),ry*math.sin(k*math.tau/n),z)
              for z,x,rx,ry in rings for k in range(n)]
    fs=[(a*n+k,a*n+(k+1)%n,(a+1)*n+(k+1)%n,(a+1)*n+k)
        for a in range(len(rings)-1) for k in range(n)]
    fs.extend([tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))])
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); finish(o,name,mat,upper)
    hi=o.vertex_groups[upper]; lo=o.vertex_groups.new(name=lower)
    for v in me.vertices:
        w=min(1,max(0,(joint+.055-v.co.z)/.11))
        hi.add([v.index],1-w,"REPLACE"); lo.add([v.index],w,"REPLACE")
    return o

# Sleeveless fitted black dress, cream lace bib and a long, lightly pleated skirt.
garment("FittedDress",[(.87,.145,.105),(1.03,.15,.104),(1.21,.185,.11),
                      (1.37,.196,.1),(1.44,.122,.073)],"dress")
garment("LongSkirt",[(.20,.29,.19),(.43,.25,.168),(.71,.188,.127),(.96,.145,.10)],"dress","Pelvis")
for i in range(12):
    a=i*math.tau/12
    tube("Pleat",[(.144*math.cos(a),.10*math.sin(a),.93),
                 (.20*math.cos(a),.138*math.sin(a),.66),
                 (.286*math.cos(a),.192*math.sin(a),.22)],.003,"seam","Pelvis")
ell("Neck",(0,0,1.47),(.058,.05,.095),"skin","Head")
ell("LaceBlouse",(0,-.074,1.245),(.156,.068,.204),"white")
for s in [-1,1]:
    tube("SoftCollar",[(s*.008,-.132,1.389),(s*.068,-.091,1.46),(s*.106,-.111,1.40)],
         .020,"lace",radii=[.65,1,.7])
for row in range(7):
    z=1.085+row*.044
    for col in range(5):
        x=(col-2)*.05 + (row%2)*.011
        if abs(x)>.135: continue
        flower=[]
        for j in range(17):
            a=j*math.tau/16
            r=.013+.003*math.cos(4*a)
            flower.append((x+r*math.cos(a),-.145,z+r*math.sin(a)))
        tube("LaceEmbroidery",flower,.0027,"lace")
        ell("LaceCentre",(x,-.146,z),(.003,.002,.003),"lace",segments=8,rings=6)
for s,side in [(-1,"L"),(1,"R")]:
    limb("BareArm",[(.91,s*.28,.036,.038),(1.05,s*.266,.038,.041),
         (1.14,s*.25,.040,.042),(1.28,s*.225,.048,.045),(1.39,s*.205,.052,.05)],
         "skin",f"UpperArm_{side}",f"Forearm_{side}",1.14)
    ell("Hand",(s*.287,-.021,.855),(.034,.026,.063),"skin",f"Hand_{side}")
    for j in range(4):
        ell("Finger",(s*.287+(j-1.5)*.013,-.026,.807),(.007,.013,.031),
            "skin",f"Hand_{side}",12,8)
    ell("Thumb",(s*.254,-.037,.858),(.013,.015,.036),"skin",f"Hand_{side}",16,10)
    limb("Leg",[(.08,s*.09,.038,.044),(.27,s*.09,.042,.046),
         (.43,s*.09,.049,.05),(.61,s*.09,.055,.06),(.78,s*.09,.060,.062)],
         "skin",f"Thigh_{side}",f"Shin_{side}",.43)
    ell("FlatShoe",(s*.09,-.052,.047),(.058,.106,.043),"shoe",f"Foot_{side}")

# The supplied face lies on a gently curved front surface. No substitute eyes or mouth.
ell("HeadBack",(0,.044,1.66),(.128,.07,.14),"hair","Head",36,24)
ell("JawBack",(0,.005,1.599),(.094,.08,.109),"skin","Head",32,20)
n,m=20,24
verts=[]; uvs=[]
for j in range(m+1):
    v=j/m
    for i in range(n+1):
        u=i/n; x=(u-.5)*.44
        verts.append((x,-.137-.028*(1-(2*u-1)**2),1.452+v*.495))
        uvs.append((u,v))
faces=[(j*(n+1)+i,j*(n+1)+i+1,(j+1)*(n+1)+i+1,(j+1)*(n+1)+i)
       for j in range(m) for i in range(n)]
me=bpy.data.meshes.new("OriginalIllustrationFace"); me.from_pydata(verts,[],faces); me.update()
uv=me.uv_layers.new(name="UVMap")
for poly in me.polygons:
    for li in poly.loop_indices: uv.data[li].uv=uvs[me.loops[li].vertex_index]
o=bpy.data.objects.new("OriginalIllustrationFace",me); bpy.context.collection.objects.link(o)
finish(o,"OriginalIllustrationFace","face","Head")
# Low side ponytail falls over the left shoulder, matching the selected illustration.
ell("PonytailTie",(-.135,.07,1.625),(.029,.032,.036),"hair","Head")
for i in range(4):
    d=(i-1.5)*.025
    tube("SidePonytail",[(-.135+d,.065,1.64),(-.18+d,-.028,1.48),
         (-.19+d,-.09,1.28),(-.135+d,-.147,1.13)],.032,"hair","Hair_L",[.8,1.15,1,.06])
for i in [-1,1]:
    tube("PonytailHighlight",[(-.16+i*.027,-.019,1.51),(-.19+i*.027,-.11,1.32),
         (-.14+i*.025,-.166,1.16)],.004,"hairLight","Hair_L",[.1,.8,.05])
ell("CrossbodyBag",(-.19,-.148,.77),(.119,.047,.084),"white","Scarf_L")
tube("BagEdge",[(-.292,-.19,.80),(-.26,-.197,.702),(-.105,-.197,.702),(-.086,-.19,.8)],
     .007,"dress","Scarf_L")
for d in [-.012,.012]:
    tube("ChainStrap",[(.10+d,-.095,1.43),(.132+d,-.154,1.22),(.061+d,-.162,1.0),
         (-.12+d,-.175,.80)],.004,"gold","Scarf_R")
for x in [-.205,-.18]:
    points=[(x+.017*math.cos(a*math.tau/16),-.202,.77+.025*math.sin(a*math.tau/16)) for a in range(17)]
    tube("BagEmblem",points,.003,"gold","Scarf_L")

bpy.ops.object.select_all(action="DESELECT")
for o in surfaces: o.select_set(True)
bpy.context.view_layer.objects.active=surfaces[0]; bpy.ops.object.join()
skin=bpy.context.object; skin.name="Tomato_SelectedIllustration"
skin.data.uv_layers.active_index=0
skin.data.uv_layers[0].active_render=True
mod=skin.modifiers.new("Smooth skeleton","ARMATURE"); mod.object=rig; skin.parent=rig
rig["source_note"]="User-selected illustrated face pixels; independent 3D body and unseen-view completion."
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
            p["Spine"].rotation_euler.x=.014*wave; p["Head"].rotation_euler.z=.017*wave
            p["Pelvis"].location.y=.004*wave
        elif name=="walk":
            p["Pelvis"].location.y=.011*(1-math.cos(t*math.tau*2))/2
            p["Spine"].rotation_euler.z=.027*wave
            for s,side in [(-1,"L"),(1,"R")]:
                stride=s*wave
                p[f"Thigh_{side}"].rotation_euler.x=.30*stride
                p[f"Shin_{side}"].rotation_euler.x=-.40*max(0,-stride)
                p[f"Foot_{side}"].rotation_euler.x=.12*stride
                p[f"UpperArm_{side}"].rotation_euler.x=-.23*stride
                p[f"Forearm_{side}"].rotation_euler.x=-.08-.06*max(0,stride)
        elif name=="attack":
            p["UpperArm_R"].rotation_euler.x=1.1*pulse; p["Forearm_R"].rotation_euler.x=.28*pulse
            p["Spine"].rotation_euler.z=-.08*pulse; p["Head"].rotation_euler.z=.035*pulse
        elif name=="defend":
            p["UpperArm_L"].rotation_euler.x=1.05+.02*wave
            p["Forearm_L"].rotation_euler.x=.75; p["Spine"].rotation_euler.x=-.05
        elif name=="dash":
            p["Spine"].rotation_euler.x=-.20-.04*pulse
            p["Thigh_L"].rotation_euler.x=.50; p["Thigh_R"].rotation_euler.x=-.48
            p["Shin_R"].rotation_euler.x=-.40
            for side in ["L","R"]: p[f"UpperArm_{side}"].rotation_euler.x=-.4
        elif name=="laugh":
            p["Head"].rotation_euler.x=.09*pulse
            p["Spine"].rotation_euler.x=.04*math.sin(t*math.tau*3)*pulse
            for s,side in [(-1,"L"),(1,"R")]:
                p[f"UpperArm_{side}"].rotation_euler.z=-s*.60*pulse
                p[f"Forearm_{side}"].rotation_euler.x=.4*pulse
        for s,side in [(-1,"L"),(1,"R")]:
            p[f"Hair_{side}"].rotation_euler.x=.04*math.sin(t*math.tau-.5) if name in ["idle","walk","defend"] else -.10*pulse
            p[f"Scarf_{side}"].rotation_euler.x=.018*math.sin(t*math.tau-.8) if name in ["idle","walk","defend"] else -.06*pulse
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
bpy.ops.export_scene.gltf(filepath=str(glb),use_selection=True,export_format="GLB",
    export_animations=True,export_animation_mode="NLA_TRACKS",export_skins=True,
    export_force_sampling=True,export_frame_range=False,export_yup=True)
scene.render.engine="CYCLES"; scene.cycles.samples=20; scene.cycles.use_denoising=True
scene.render.resolution_x=768; scene.render.resolution_y=960; scene.render.resolution_percentage=100
scene.render.image_settings.file_format="PNG"; scene.view_settings.view_transform="Standard"
scene.world.use_nodes=True
scene.world.node_tree.nodes["Background"].inputs[0].default_value=(.62,.68,.72,1)
scene.world.node_tree.nodes["Background"].inputs[1].default_value=.4
for name,pos,power,size in [("Key",(-3,-4,5),260,4),("Fill",(3,-2,3),130,3),("Rim",(1,3,4),220,3)]:
    d=bpy.data.lights.new(name,"AREA"); d.energy=power; d.size=size
    o=bpy.data.objects.new(name,d); bpy.context.collection.objects.link(o); o.location=pos
    o.rotation_euler=(Vector((0,0,1))-o.location).to_track_quat("-Z","Y").to_euler()
bpy.ops.mesh.primitive_plane_add(size=200,location=(0,0,-.004))
bpy.context.object.data.materials.append(material("Studio","e9dfcf"))
d=bpy.data.cameras.new("PortraitCamera"); camera=bpy.data.objects.new("PortraitCamera",d)
bpy.context.collection.objects.link(camera); scene.camera=camera; d.type="ORTHO"; d.ortho_scale=2.25
for name,pos in [("正面",(0,-6,1.4)),("三分之四",(2.0,-6,1.55)),("背面",(2.5,6,1.55))]:
    camera.location=pos; camera.rotation_euler=(Vector((0,0,.99))-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(OUT/f"人物_{name}.png"); bpy.ops.render.render(write_still=True)
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"指定人物.blend"))
stats={"vertices":len(skin.data.vertices),"triangles":sum(len(p.vertices)-2 for p in skin.data.polygons),
       "bones":len(arm.bones),"animations":durations,"glb_bytes":glb.stat().st_size,
       "blender":bpy.app.version_string,"style":"User-selected face pixels, slim black dress, lace bib and side ponytail; not a scan"}
(OUT/"模型规格.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2))
print("CHARACTER_COMPLETE",json.dumps(stats,ensure_ascii=False))
