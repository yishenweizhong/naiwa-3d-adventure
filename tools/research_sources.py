"""Read public GitHub source records; preserve provenance without account metadata."""
import base64, json, subprocess, struct
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/"参考项目"
OUT.mkdir(exist_ok=True)
repos=[
    ("mrdoob/three.js","examples/webgl_animation_skinning_blending.html"),
    ("donmccurdy/glTF-Transform","README.md"),
    ("KhronosGroup/glTF-Validator","README.md"),
    ("KenneyNL/Starter-Kit-3D-Platformer","README.md"),
    ("pmndrs/drei","src/core/ContactShadows.tsx"),
    ("Arminando/ActionPoser","README.md"),
]
def api(path):
    r=subprocess.run(["gh","api",path],capture_output=True,text=True,check=True)
    return json.loads(r.stdout)
records=[]
for repo,path in repos:
    meta=api("repos/"+repo)
    directory=OUT/repo.replace("/","_"); directory.mkdir(exist_ok=True)
    readme=api("repos/"+repo+"/readme")
    (directory/"README.md").write_bytes(base64.b64decode(readme["content"]))
    content=api("repos/"+repo+"/contents/"+path)
    assert content.get("encoding")=="base64", (repo,path)
    (directory/Path(path).name).write_bytes(base64.b64decode(content["content"]))
    license=api("repos/"+repo+"/license")
    (directory/"LICENSE").write_bytes(base64.b64decode(license["content"]))
    commit=api("repos/"+repo+"/commits/"+meta["default_branch"])
    record={"repository":repo,"url":meta["html_url"],"license":(meta.get("license") or {}).get("spdx_id"),
            "branch":meta["default_branch"],"commit":commit["sha"],"read":path}
    records.append(record)
    print(json.dumps(record,ensure_ascii=False))
(OUT/"核实记录.json").write_text(json.dumps(records,ensure_ascii=False,indent=2))
assets=ROOT/"public/models/kenney"; assets.mkdir(exist_ok=True)
for name in ["cloud.glb","grass.glb"]:
    content=api("repos/KenneyNL/Starter-Kit-3D-Platformer/contents/models/"+name)
    binary=base64.b64decode(content["content"])
    size=struct.unpack_from("<I",binary,12)[0]; gltf=json.loads(binary[20:20+size])
    # Geometry reuse with our own solid-color materials; no external colormap download.
    for mat in gltf.get("materials",[]):
        mat.get("pbrMetallicRoughness",{}).pop("baseColorTexture",None)
    for key in ["images","textures","samplers"]: gltf.pop(key,None)
    data=json.dumps(gltf,separators=(",",":")).encode(); data+=b" "*((-len(data))%4)
    tail=binary[20+size:]
    packed=struct.pack("<III",0x46546c67,2,20+len(data)+len(tail))+struct.pack("<II",len(data),0x4e4f534a)+data+tail
    (assets/name).write_bytes(packed)
    print("CC0 model downloaded:",name)
for name in ["scripts/hud.gd","scripts/player.gd","objects/coin.gd"]:
    content=api("repos/KenneyNL/Starter-Kit-3D-Platformer/contents/"+name)
    (OUT/"KenneyNL_Starter-Kit-3D-Platformer"/Path(name).name).write_bytes(base64.b64decode(content["content"]))
