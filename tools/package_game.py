"""Package the actual production build and editable local model."""
from pathlib import Path
from PIL import Image
import json, zipfile, hashlib, shutil

root=Path(__file__).resolve().parents[1]
docs=root/"docs"
docs.mkdir(exist_ok=True)
for old in docs.iterdir():
    if old.is_dir(): shutil.rmtree(old)
    else: old.unlink()
shutil.copytree(root/"dist",docs,dirs_exist_ok=True,ignore=shutil.ignore_patterns(".DS_Store"))
(docs/".nojekyll").touch()

portraits=[Image.open(root/"3D人物"/f"人物_{name}.png").convert("RGB") for name in ["正面","三分之四","背面"]]
montage=Image.new("RGB",(768*3,960))
for i,im in enumerate(portraits): montage.paste(im,(768*i,0))
montage.save(root/"3D人物/人物三视图.png")
stats_path=root/"3D人物/模型规格.json"
stats=json.loads(stats_path.read_text())
stats["raw_glb_bytes"]=stats.get("raw_glb_bytes",stats["glb_bytes"])
stats["glb_bytes"]=(root/"public/models/reference-hero.glb").stat().st_size
stats["optimization"]="glTF Transform 4.2.1 dedup/resample/prune; scene-root identity skin; validator zero errors/warnings"
stats_path.write_text(json.dumps(stats,ensure_ascii=False,indent=2))

def archive(name,entries):
    path=root/name
    with zipfile.ZipFile(path,"w",zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for disk,rel in entries:
            if disk.is_file(): z.write(disk,str(rel))
    with zipfile.ZipFile(path) as z:
        assert z.testzip() is None
    return {"file":name,"bytes":path.stat().st_size,"sha256":hashlib.sha256(path.read_bytes()).hexdigest()}

deploy=[(f,f.relative_to(root/"dist")) for f in (root/"dist").rglob("*") if f.is_file() and f.name!=".DS_Store"]
source=[]
for name in ["src","public","tests","tools","3D人物"]:
    for f in (root/name).rglob("*"):
        if f.is_file() and f.name!=".DS_Store" and "__pycache__" not in f.parts and not f.name.endswith((".pyc",".blend1")):
            source.append((f,f.relative_to(root)))
for name in ["package.json","package-lock.json","tsconfig.json","vite.config.ts","index.html","README.md",".gitignore","优化说明.md"]:
    f=root/name
    if f.exists(): source.append((f,Path(name)))
model=[(f,f.relative_to(root/"3D人物")) for f in (root/"3D人物").iterdir()
       if f.is_file() and f.name!=".DS_Store" and not f.name.endswith(".blend1")]
model.append((root/"public/models/reference-hero.glb",Path("reference-hero.glb")))
manifest=[
    archive("奶蛙全3D版_部署包.zip",deploy),
    archive("奶蛙全3D版_完整源码与Blender.zip",source),
    archive("人物模型与六组动作.zip",model),
]
(root/"交付清单.json").write_text(json.dumps(manifest,ensure_ascii=False,indent=2))
print(json.dumps(manifest,ensure_ascii=False,indent=2))
