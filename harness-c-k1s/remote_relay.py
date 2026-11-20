"""Run-scoped server-to-server C shard dispatch. Both hosts retain completed receipts."""
import fcntl
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parent
PANEL = {"ariane133-ng45":["1002"],"bp_fe-ng45":["1001","1002"]}

def serve():
    text = sys.stdin.read(40000)
    if text.strip()=="ping":
        print("c-k1s-ready"); return
    assert len(text)<40000
    req = json.loads(text)
    rid = req["request"]
    assert req["run"]=="k1s-ten" and re.fullmatch(r"[er]-[0-9a-f]{60}",rid) and req["cells"]==PANEL
    stem = "k1s-ten_"+rid
    spool = ROOT/"spool"
    wire = spool/(stem+".request")
    unit = "aic-c-"+stem
    reply = ROOT/"workers/ariane133-ng45+bp_fe-ng45-gpu0/k1s-ten"/rid/"reply.json"
    with (spool/"dispatch.lock").open("a") as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        if wire.exists():
            assert json.loads(wire.read_bytes())==req
        else:
            assert len(list(spool.glob("k1s-ten_*.request")))<10
            wire.write_text(text)
        if reply.exists(): print(json.dumps({"reply":json.loads(reply.read_bytes())})); return
        active=subprocess.run(["systemctl","is-active","--quiet",unit]).returncode==0
        if not active:
            if reply.exists(): print(json.dumps({"reply":json.loads(reply.read_bytes())})); return
            if reply.parent.exists():raise RuntimeError("Previously started worker needs inspection")
            subprocess.run(["systemd-run","--quiet","--unit="+unit,"--property=WorkingDirectory="+str(ROOT),
                "--property=StandardInput=file:"+str(wire),"--property=StandardOutput=null",
                "--property=StandardError=append:"+str(spool/(stem+".err")),
                "/usr/bin/python3","-B",str(ROOT/"three_gpu.py"),"worker","--official","/root/aic-eda-fourth/official",
                "--gpu","0","--workers","1","--host-slots","1","--memory-gib","24",
                "--case","ariane133-ng45","--case","bp_fe-ng45"],check=True)
        print('{"running":true}')

def ssh(addr,data):
    return subprocess.run(["ssh","-T","-F","/dev/null","-i",str(ROOT/"relay_id"),"-p","22120",
        "-o","BatchMode=yes","-o","IdentitiesOnly=yes","-o","StrictHostKeyChecking=yes","-o","HostKeyAlias=c-k1s-worker",
        "-o","UserKnownHostsFile="+str(ROOT/"worker_hosts"),"-o","ConnectTimeout=5","root@"+addr],
        input=data,text=True,capture_output=True,timeout=20)

def master():
    hosts=["180.127.11.169","223.109.239.11"]
    relay=ROOT/"relay"
    while not (ROOT/"k1s-ten/diagnostic-result.json").exists():
        for f in sorted(relay.glob("k1s-ten_*.request")):
            out=f.with_suffix(".reply")
            if out.exists():continue
            for addr in hosts:
                try:
                    p=ssh(addr,f.read_text())
                    if p.returncode:continue
                    msg=json.loads(p.stdout)
                    if "reply" in msg:
                        target=out.with_suffix(".server-tmp")
                        target.write_text(json.dumps(msg["reply"])); target.replace(out)
                    (ROOT/"server-handoff.json").write_text(json.dumps({"request":f.stem,"worker":addr,
                        "status":"returned" if "reply" in msg else "accepted","time":time.time()}))
                    hosts=[addr]+[i for i in hosts if i!=addr]
                    break
                except (ValueError,OSError,subprocess.TimeoutExpired):continue
        time.sleep(5)

if __name__=="__main__":
    os.umask(0o077)
    if sys.argv[1:] == ["master"]: master()
    else: serve()
