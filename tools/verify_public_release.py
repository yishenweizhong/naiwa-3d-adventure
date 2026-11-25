"""Verify that the public site serves every byte of this production build."""
from pathlib import Path
from playwright.sync_api import sync_playwright
import hashlib
import json
import os
import subprocess

ROOT=Path(__file__).resolve().parents[1]
BASE=os.environ.get("NAIWA_URL","https://yishenweizhong.github.io/naiwa-3d-adventure/").rstrip("/")+"/"
OUT=Path(os.environ.get("NAIWA_EVIDENCE",ROOT/"验收/公网"))
OUT.mkdir(parents=True,exist_ok=True)
commit=subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()
report={"url":BASE,"commit":commit,"assets":[]}
with sync_playwright() as p:
    request=p.request.new_context()
    for path in sorted((ROOT/"dist").rglob("*")):
        if not path.is_file(): continue
        rel=path.relative_to(ROOT/"dist").as_posix()
        response=request.get(BASE+rel+"?release="+commit,timeout=60000)
        assert response.ok,f"{rel}: HTTP {response.status}"
        local=hashlib.sha256(path.read_bytes()).hexdigest()
        public=hashlib.sha256(response.body()).hexdigest()
        assert local==public,f"Stale or different public asset: {rel}"
        report["assets"].append({"path":rel,"sha256":public,"status":response.status})
        print("MATCH",rel,flush=True)
    request.dispose()
(OUT/"公网资源一致性.json").write_text(json.dumps(report,ensure_ascii=False,indent=2))
print("PUBLIC_ASSETS_MATCH",len(report["assets"]),commit,flush=True)
