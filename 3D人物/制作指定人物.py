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
face.use_backface_culling=True
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
geometry=nodes.new("ShaderNodeNewGeometry")
front=nodes.new("ShaderNodeMath"); front.operation="SUBTRACT"; front.inputs[0].default_value=1
alpha=nodes.new("ShaderNodeMath"); alpha.operation="MULTIPLY"
face.node_tree.links.new(geometry.outputs["Backfacing"],front.inputs[1])
face.node_tree.links.new(front.outputs[0],alpha.inputs[0])
face.node_tree.links.new(texture.outputs["Alpha"],alpha.inputs[1])
face.node_tree.links.new(alpha.outputs[0],mix.inputs[0])
face.node_tree.links.new(transparent.outputs[0],mix.inputs[1])
face.node_tree.links.new(emission.outputs[0],mix.inputs[2])
face.node_tree.links.new(mix.outputs[0],output.inputs[0])
M["face"]=face
lace=bpy.data.materials.new("ReferenceLace"); lace.use_nodes=True
lace.surface_render_method="DITHERED"; lace.use_backface_culling=True
bs=lace.node_tree.nodes["Principled BSDF"]; bs.inputs["Roughness"].default_value=.92
tex=lace.node_tree.nodes.new("ShaderNodeTexImage")
tex.image=bpy.data.images.load(str(ROOT/"public/textures/lace-fabric.png")); tex.image.pack()
lace.node_tree.links.new(tex.outputs["Color"],bs.inputs["Base Color"])
lace.node_tree.links.new(tex.outputs["Alpha"],bs.inputs["Alpha"])
M["referenceLace"]=lace

arm=bpy.data.armatures.new("Tomato_Reference_Rig")
rig=bpy.data.objects.new("Tomato_Reference_Rig",arm); bpy.context.collection.objects.link(rig)
bpy.context.view_layer.objects.active=rig; rig.select_set(True)
bpy.ops.object.mode_set(mode="EDIT")
spec={"Root":((0,0,0),(0,0,.12),None),
      "Pelvis":((0,0,.87),(0,0,1.06),"Root"),
      "Spine":((0,0,1.06),(0,0,1.54),"Pelvis"),
      "Head":((0,0,1.54),(0,0,1.91),"Spine")}
for s,side in [(-1,"L"),(1,"R")]:
    spec.update({
        f"UpperArm_{side}":((s*.194,0,1.51),(s*.253,-.01,1.19),"Spine"),
        f"Forearm_{side}":((s*.253,-.01,1.19),(s*.287,-.025,.945),f"UpperArm_{side}"),
        f"Hand_{side}":((s*.287,-.025,.945),(s*.296,-.03,.85),f"Forearm_{side}"),
        f"Thigh_{side}":((s*.09,0,.88),(s*.09,0,.50),"Pelvis"),
        f"Shin_{side}":((s*.09,0,.50),(s*.09,0,.1),f"Thigh_{side}"),
        f"Foot_{side}":((s*.09,0,.1),(s*.09,-.12,.035),f"Shin_{side}"),
        f"Hair_{side}":((s*.11,.035,1.69),(s*.16,-.04,1.23),"Head"),
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
def garment(name,rings,mat,bone="Spine",folds=False):
    n=64; vs=[]
    for z,rx,ry in rings:
        for k in range(n):
            a=k*math.tau/n
            f=(.009*math.cos(11*a+.2)+.004*math.cos(17*a-.6))*max(0,(1.07-z)/.9) if folds else 0
            vs.append(((rx+f)*math.cos(a),(ry+f)*math.sin(a),z))
    fs=[(a*n+k,a*n+(k+1)%n,(a+1)*n+(k+1)%n,(a+1)*n+k)
        for a in range(len(rings)-1) for k in range(n)]
    fs.extend([tuple(reversed(range(n))),tuple(range((len(rings)-1)*n,len(rings)*n))])
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.update()
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    return finish(o,name,mat,bone)
def textured_surface(name,width,bottom,height,material,bone,front,depth):
    n,m=(64,64) if material=="face" else (32,40)
    vs=[]; uvs=[]
    for j in range(m+1):
        v=j/m
        for i in range(n+1):
            u=i/n
            x=(u-.5)*width; z=bottom+v*height
            y=front-depth*math.sqrt(max(0,1-(2*u-1)**2))
            if material=="face":
                x+=.0135
                jaw=.60+.40*min(1,max(0,(z-1.61)/.15))
                q=max(0,1-(x/(.120*jaw))**2-((z-1.760)/.153)**2)
                nose=.015*math.exp(-((x/.016)**2+((z-1.709)/.024)**2))
                y=.017-.103*math.sqrt(q)-.002-nose
            vs.append((x,y,z))
            uvs.append((u,v))
    fs=[(j*(n+1)+i,j*(n+1)+i+1,(j+1)*(n+1)+i+1,(j+1)*(n+1)+i) for j in range(m) for i in range(n)]
    me=bpy.data.meshes.new(name); me.from_pydata(vs,[],fs); me.update()
    uv=me.uv_layers.new(name="UVMap")
    for poly in me.polygons:
        for li in poly.loop_indices: uv.data[li].uv=uvs[me.loops[li].vertex_index]
    o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    return finish(o,name,material,bone)
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

# A fitted waist and a curved hip transition, rather than two capped cones.
dress=garment("TailoredDress",[(.185,.246,.156),(.28,.237,.151),(.44,.217,.145),
    (.61,.198,.133),(.79,.182,.125),(.92,.172,.115),(1.025,.153,.100),
    (1.10,.138,.090),(1.20,.152,.102),(1.31,.178,.123),(1.40,.184,.105),
    (1.49,.174,.080),(1.545,.058,.045)],"dress","Pelvis",folds=True)
spine=dress.vertex_groups.new(name="Spine")
skirt_thigh={s:dress.vertex_groups.new(name=f"Thigh_{s}") for s in ["L","R"]}
for v in dress.data.vertices:
    w=max(0,min(1,(v.co.z-1.045)/.14))
    sway=.32*max(0,min(1,(.96-v.co.z)/.60))
    right=max(0,min(1,.5+v.co.x/.22))
    dress.vertex_groups["Pelvis"].add([v.index],1-w-sway,"REPLACE"); spine.add([v.index],w,"REPLACE")
    skirt_thigh["L"].add([v.index],sway*(1-right),"REPLACE")
    skirt_thigh["R"].add([v.index],sway*right,"REPLACE")
ell("Neck",(0,-.003,1.565),(.044,.042,.065),"skin","Head")
def blouse():
    levels=[(1.103,.130,.105),(1.15,.146,.110),(1.25,.166,.128),
            (1.35,.175,.141),(1.44,.165,.119),(1.50,.103,.083),(1.54,.048,.055)]
    n=32; vs=[]; uvs=[]
    for j,(z,width,depth) in enumerate(levels):
        for k in range(n+1):
            a=math.pi*k/n
            vs.append((-width*math.cos(a),-.028-depth*math.sin(a),
                       z+(.005*math.cos(k*math.tau/4) if j==0 else 0)))
            uvs.append((k/n*2,j/(len(levels)-1)*2))
    fs=[(j*(n+1)+k,j*(n+1)+k+1,(j+1)*(n+1)+k+1,(j+1)*(n+1)+k) for j in range(len(levels)-1) for k in range(n)]
    me=bpy.data.meshes.new("LaceBlouse"); me.from_pydata(vs,[],fs); me.update()
    uv=me.uv_layers.new(name="UVMap")
    for p in me.polygons:
        for li in p.loop_indices: uv.data[li].uv=uvs[me.loops[li].vertex_index]
    o=bpy.data.objects.new("LaceBlouse",me); bpy.context.collection.objects.link(o)
    return finish(o,"LaceBlouse","referenceLace","Spine")
blouse()
for s in [-1,1]:
    pts=[(s*.003,-.123,1.487),(s*.046,-.06,1.554),(s*.100,-.078,1.513),
         (s*.066,-.145,1.444),(s*.032,-.152,1.471)]
    me=bpy.data.meshes.new("FoldedCollar"); me.from_pydata(pts,[],[(0,1,2),(0,2,4),(2,3,4)]); me.update()
    o=bpy.data.objects.new("FoldedCollar",me); bpy.context.collection.objects.link(o)
    finish(o,"FoldedCollar","lace","Spine")
for s in [-1,1]:
    tube("ShoulderDressStrap",[(s*.085,0,1.543),(s*.156,-.036,1.51),
         (s*.171,-.074,1.395)],.015,"dress",radii=[1,1,.7])
for s,side in [(-1,"L"),(1,"R")]:
    arm_start=len(surfaces)
    shoulder=ell("RoundedShoulder",(s*.182,0,1.48),(.061,.061,.072),"skin",f"UpperArm_{side}")
    # Shoulder tops blend with the torso, while lower deltoid follows the arm.
    group=shoulder.vertex_groups.new(name="Spine")
    for v in shoulder.data.vertices:
        w=max(0,min(.75,(1.48-v.co.z)/-.085))
        shoulder.vertex_groups[f"UpperArm_{side}"].add([v.index],1-w,"REPLACE")
        group.add([v.index],w,"REPLACE")
    limb("BareArm",[(.93,s*.287,.025,.029),(.99,s*.281,.029,.030),
         (1.075,s*.269,.038,.036),(1.19,s*.253,.034,.035),
         (1.30,s*.229,.044,.047),(1.405,s*.203,.052,.056),(1.50,s*.184,.047,.049)],
         "skin",f"UpperArm_{side}",f"Forearm_{side}",1.19)
    hand=ell("Hand",(s*.293,-.022,.902),(.030,.024,.056),"skin",f"Hand_{side}")
    wrist=hand.vertex_groups.new(name=f"Forearm_{side}")
    for v in hand.data.vertices:
        w=min(1,max(0,(v.co.z-.922)/.028))
        hand.vertex_groups[f"Hand_{side}"].add([v.index],1-w,"REPLACE")
        wrist.add([v.index],w,"REPLACE")
    for j in range(4):
        ell("Finger",(s*.293+(j-1.5)*.012,-.024,.852+(j%3)*.003),(.0065,.011,.033),
            "skin",f"Hand_{side}",12,8)
    ell("Thumb",(s*.269,-.042,.903),(.011,.015,.032),"skin",f"Hand_{side}",16,10)
    # Voxel union removes the sphere/cylinder caps and wrist seams.
    parts=surfaces[arm_start:]
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts: o.select_set(True)
    bpy.context.view_layer.objects.active=parts[0]; bpy.ops.object.join()
    whole=bpy.context.object; whole.name=f"ContinuousArm_{side}"
    remesh=whole.modifiers.new("Continuous skin","REMESH"); remesh.mode="VOXEL"; remesh.voxel_size=.007
    bpy.ops.object.modifier_apply(modifier=remesh.name)
    smooth=whole.modifiers.new("Skin smoothing","SMOOTH"); smooth.factor=.6; smooth.iterations=3
    bpy.ops.object.modifier_apply(modifier=smooth.name)
    whole.vertex_groups.clear()
    groups={n:whole.vertex_groups.new(name=n) for n in ["Spine",f"UpperArm_{side}",f"Forearm_{side}",f"Hand_{side}"]}
    for v in whole.data.vertices:
        z=v.co.z
        hand=max(0,min(1,(.96-z)/.05))
        fore=max(0,min(1,(1.24-z)/.10))*(1-hand)
        upper=1-hand-fore
        torso=max(0,min(.8,(z-1.50)/.06))*upper
        for n,w in zip(groups,[torso,upper-torso,fore,hand]):
            if w>0: groups[n].add([v.index],w,"REPLACE")
    for p in whole.data.polygons: p.use_smooth=True
    surfaces[arm_start:]=[whole]
    # Remove body faces covered by the long skirt, a standard clothed-character mesh.
    # The full thigh/shin skeleton remains; visible ankles still follow locomotion.
    limb("VisibleAnkle",[(.075,s*.09,.030,.036),(.13,s*.09,.034,.039),
         (.176,s*.09,.036,.040)],
         "skin",f"Thigh_{side}",f"Shin_{side}",.50)
    ell("FlatShoe",(s*.09,-.054,.046),(.048,.098,.035),"shoe",f"Foot_{side}")

# The supplied face lies on a gently curved front surface. No substitute eyes or mouth.
head=ell("VolumetricHead",(0,.017,1.760),(.120,.103,.153),"hair","Head",64,48)
for v in head.data.vertices:
    v.co.x*=.60+.40*min(1,max(0,(v.co.z-1.61)/.15))
head.data.materials.append(M["skin"])
for p in head.data.polygons:
    center=sum((head.data.vertices[i].co for i in p.vertices),Vector())/len(p.vertices)
    if center.y<.017 and center.z<1.786: p.material_index=1
textured_surface("OriginalIllustrationFace",.3124,1.583,.35145,"face","Head",.005,.133)
# Low side ponytail falls over the left shoulder, matching the selected illustration.
ell("PonytailTie",(-.091,.04,1.68),(.024,.027,.030),"hair","Head")
for i in range(7):
    d=(i-3)*.012
    tube("SidePonytail",[(-.094+d,.030,1.695),(-.142+d,-.042,1.53),
         (-.15+d,-.097,1.36),(-.104+d,-.162,1.235)],.021,"hair","Hair_L",[.75,1.05,.9,.035])
for i in range(5):
    d=(i-2)*.012
    tube("PonytailHighlight",[(-.119+d,-.055,1.60),(-.16+d,-.12,1.40),
         (-.113+d,-.18,1.25)],.0018,"hairLight","Hair_L",[.1,.7,.025])
def rounded_box(name,loc,scale,mat,bone,bevel):
    bpy.ops.mesh.primitive_cube_add(size=1,location=loc)
    o=bpy.context.object; o.scale=scale
    bpy.ops.object.transform_apply(location=False,rotation=False,scale=True)
    mod=o.modifiers.new("Rounded corners","BEVEL"); mod.width=bevel; mod.segments=5
    bpy.context.view_layer.objects.active=o; bpy.ops.object.modifier_apply(modifier=mod.name)
    return finish(o,name,mat,bone)
rounded_box("CrossbodyBag",(-.193,-.174,.84),(.218,.066,.146),"white","Scarf_L",.019)
rounded_box("BagFlap",(-.193,-.212,.867),(.213,.011,.092),"lace","Scarf_L",.011)
tube("BagPiping",[(-.30,-.216,.902),(-.295,-.222,.854),(-.25,-.224,.821),
     (-.144,-.224,.821),(-.091,-.216,.872),(-.085,-.213,.899)],.0035,"dress","Scarf_L")
# The original panel contains the upper gold chain; only continue it below the lace.
tube("ChainStrap",[(.12,-.076,1.49),(.12,.040,1.52),(-.18,.112,1.19),
     (-.271,.067,.926),(-.281,-.15,.912)],.003,"gold","Spine")
tube("ChainFront",[(.092,-.082,1.522),(.126,-.163,1.36),(.119,-.175,1.18),
     (.035,-.157,1.042),(-.115,-.203,.915)],
     .0033,"gold","Scarf_R")
for i in range(5):
    x=-.270+i*.038
    tube("BagQuilt",[(x,-.224,.790),(x+.072,-.224,.858)],.0012,"white","Scarf_L")
for x in [-.205,-.18]:
    points=[(x+.012*math.cos(a*math.tau/16),-.232,.857+.019*math.sin(a*math.tau/16)) for a in range(17)]
    tube("BagEmblem",points,.0025,"gold","Scarf_L")

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
                p[f"Thigh_{side}"].rotation_euler.x=.18*stride
                p[f"Shin_{side}"].rotation_euler.x=-.24*max(0,-stride)
                p[f"Foot_{side}"].rotation_euler.x=.12*stride
                p[f"UpperArm_{side}"].rotation_euler.x=-.23*stride
                p[f"Forearm_{side}"].rotation_euler.x=-.08-.06*max(0,stride)
        elif name=="attack":
            p["UpperArm_R"].rotation_euler.x=-1.1*pulse; p["Forearm_R"].rotation_euler.x=-.28*pulse
            p["Spine"].rotation_euler.z=-.08*pulse; p["Head"].rotation_euler.z=.035*pulse
        elif name=="defend":
            p["UpperArm_L"].rotation_euler.x=-1.05-.02*wave
            p["Forearm_L"].rotation_euler.x=-.75; p["Spine"].rotation_euler.x=.05
        elif name=="dash":
            p["Spine"].rotation_euler.x=.20+.04*pulse
            p["Thigh_L"].rotation_euler.x=.26; p["Thigh_R"].rotation_euler.x=-.26
            p["Shin_R"].rotation_euler.x=-.22
            for side in ["L","R"]: p[f"UpperArm_{side}"].rotation_euler.x=.4
        elif name=="laugh":
            p["Head"].rotation_euler.x=.09*pulse
            p["Spine"].rotation_euler.x=.04*math.sin(t*math.tau*3)*pulse
            for s,side in [(-1,"L"),(1,"R")]:
                p[f"UpperArm_{side}"].rotation_euler.z=-s*.60*pulse
                p[f"Forearm_{side}"].rotation_euler.x=-.4*pulse
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
scene.render.engine="CYCLES"; scene.cycles.samples=16; scene.cycles.use_denoising=True
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
for name,pos in [("正面",(0,-6,1.05)),("三分之四",(2.0,-6,1.2)),("背面",(2.5,6,1.2)),("侧面",(6,0,1.05))]:
    camera.location=pos; camera.rotation_euler=(Vector((0,0,.99))-camera.location).to_track_quat("-Z","Y").to_euler()
    scene.render.filepath=str(OUT/f"人物_{name}.png"); bpy.ops.render.render(write_still=True)
camera.location=(1.3,-6,1.25)
camera.rotation_euler=(Vector((0,0,.99))-camera.location).to_track_quat("-Z","Y").to_euler()
pose_bounds={}
for name in durations:
    rig.animation_data.action=bpy.data.actions[name]
    scene.frame_set(1+round(durations[name]*30*(.25 if name=="walk" else .5)))
    evaluated=skin.evaluated_get(bpy.context.evaluated_depsgraph_get())
    mesh=evaluated.to_mesh()
    positions=[evaluated.matrix_world@v.co for v in mesh.vertices]
    minimum=[min(p[i] for p in positions) for i in range(3)]
    maximum=[max(p[i] for p in positions) for i in range(3)]
    assert all(math.isfinite(v) for v in minimum+maximum), name
    pose_bounds[name]={"min":minimum,"max":maximum}
    evaluated.to_mesh_clear()
    if name in ["walk","attack","defend","dash"]:
        scene.render.filepath=str(OUT/f"动作_{name}.png"); bpy.ops.render.render(write_still=True)
rig.animation_data.action=None; reset(); scene.frame_set(1)
for v in skin.data.vertices:
    assert abs(sum(g.weight for g in v.groups)-1)<1e-4, f"Unnormalized rig weights at {v.index}"
bpy.ops.wm.save_as_mainfile(filepath=str(OUT/"指定人物.blend"))
stats={"vertices":len(skin.data.vertices),"triangles":sum(len(p.vertices)-2 for p in skin.data.polygons),
       "bones":len(arm.bones),"animations":durations,"glb_bytes":glb.stat().st_size,
       "blender":bpy.app.version_string,"style":"Selected face and lace pixels; rounded shoulders, continuous wrists, tailored dress and folded skirt; not a scan",
       "proportions":{"visible_head_height":.35145*389/456,"height":1.913,"heads_tall":1.913/(.35145*389/456)},
       "pose_bounds":pose_bounds,
       "limits":"Face is an illustration mapped to a curved surface; unseen back and shoes independently completed."}
(OUT/"模型规格.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2))
print("CHARACTER_COMPLETE",json.dumps(stats,ensure_ascii=False))
