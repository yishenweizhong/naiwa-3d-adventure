"""Wait for the GitHub Pages build that belongs to the current local commit."""
import json
import subprocess
import time

repo = "yishenweizhong/naiwa-3d-adventure"
commit = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
started, previous = time.monotonic(), None
while time.monotonic()-started < 300:
    run = subprocess.run(["gh","api",f"repos/{repo}/pages/builds/latest"],
                         text=True,capture_output=True)
    if run.returncode:
        raise RuntimeError(run.stderr)
    build = json.loads(run.stdout)
    status = (build.get("commit"),build.get("status"))
    if status != previous:
        print(json.dumps({"commit":status[0],"status":status[1]},ensure_ascii=False),flush=True)
        previous = status
    if status[0] == commit:
        if status[1] == "built":
            print("PAGES_BUILT",commit,flush=True)
            break
        if status[1] == "errored":
            raise RuntimeError(build.get("error"))
    time.sleep(5)
else:
    raise TimeoutError(f"Pages build not confirmed for {commit}")
