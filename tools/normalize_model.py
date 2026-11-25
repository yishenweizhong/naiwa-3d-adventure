from pathlib import Path
import struct, json
path=Path(__file__).resolve().parents[1]/"public/models/reference-hero.glb"
b=path.read_bytes(); n=struct.unpack_from("<I",b,12)[0]; g=json.loads(b[20:20+n])
# Preserve the illustrated face as a portable unlit RGBA material, including
# alpha and front-side culling in model viewers outside this game's adapter.
for material in g.get("materials", []):
    if material.get("name") != "ReferenceFace": continue
    pbr=material.setdefault("pbrMetallicRoughness", {})
    texture=pbr.get("baseColorTexture") or material.get("emissiveTexture")
    assert texture, "Selected illustration texture must be embedded in the GLB"
    pbr["baseColorTexture"]=texture
    pbr["baseColorFactor"]=[1,1,1,1]
    material["alphaMode"]="BLEND"
    material["doubleSided"]=False
    material.pop("emissiveTexture",None)
    material.pop("emissiveFactor",None)
    material.setdefault("extensions", {})["KHR_materials_unlit"]={}
    if "KHR_materials_unlit" not in g.setdefault("extensionsUsed", []):
        g["extensionsUsed"].append("KHR_materials_unlit")
for i,node in enumerate(g["nodes"]):
    if "skin" not in node: continue
    for parent in g["nodes"]:
        if i in parent.get("children",[]):
            assert not any(k in parent for k in ["matrix","translation","rotation","scale"])
            parent["children"].remove(i)
    for scene in g["scenes"]:
        if i not in scene["nodes"]: scene["nodes"].append(i)
assert {x["name"] for x in g["animations"]}=={"idle","walk","attack","defend","dash","laugh"}
data=json.dumps(g,separators=(",",":")).encode(); data+=b" "*((-len(data))%4); binary=b[20+n:]
result=struct.pack("<III",0x46546c67,2,20+len(data)+len(binary))+struct.pack("<II",len(data),0x4e4f534a)+data+binary
path.write_bytes(result)
print("Normalized",len(result),"bytes;",len(g["animations"]),"clips")
