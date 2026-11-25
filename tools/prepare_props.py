"""Pack already downloaded CC0 geometry with solid color material instead of external images."""
from pathlib import Path
import struct,json
for path in (Path(__file__).resolve().parents[1]/"public/models/kenney").glob("*.glb"):
    binary=path.read_bytes(); size=struct.unpack_from("<I",binary,12)[0]; gltf=json.loads(binary[20:20+size])
    for mat in gltf.get("materials",[]): mat.get("pbrMetallicRoughness",{}).pop("baseColorTexture",None)
    for key in ["images","textures","samplers"]: gltf.pop(key,None)
    data=json.dumps(gltf,separators=(",",":")).encode(); data+=b" "*((-len(data))%4); tail=binary[20+size:]
    path.write_bytes(struct.pack("<III",0x46546c67,2,20+len(data)+len(tail))+struct.pack("<II",len(data),0x4e4f534a)+data+tail)
    print(path.name, "solid-color CC0 geometry packed")
