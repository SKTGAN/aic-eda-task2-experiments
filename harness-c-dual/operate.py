"""Deploy C, relay only its single-card worker, and retrieve the completed evidence."""
import argparse
import getpass
import json
from pathlib import Path
import shlex
import sys
import time

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0,str(PROJECT / "local-experiments/remote-client-deps"))
import paramiko

ROOT = "/root/aic-group-c-v1"
DUAL = "/root/aic-26016/official"
SINGLE = "/root/aic-eda-fourth/official"
OLD = "/root/aic-eda-fourth/staging/independent-harness-e1e2710/run-01"
HOSTS = {26016:"180.127.11.169",22120:"180.127.11.169"}
CASES = ("ariane133-ng45","bp-ng45","bp_fe-ng45")
AR,BP,FE=CASES


def connect(port, password):
    c=paramiko.SSHClient()
    for f in (PROJECT/"harness-fourth/ssh_known_hosts",PROJECT/"exports/2026-11-18-overnight/ssh_known_hosts_26016"):
        c.load_host_keys(str(f))
    c.connect(HOSTS[port],port=port,username="root",password=password,timeout=14,
              auth_timeout=16,banner_timeout=16,look_for_keys=False,allow_agent=False)
    c.get_transport().set_keepalive(15)
    return c


def cmd(c, command):
    _,o,e=c.exec_command(command,timeout=45)
    data=o.read().decode(errors="replace");err=e.read().decode(errors="replace")
    if o.channel.recv_exit_status():
        raise RuntimeError((err or data)[-800:])
    return data


def put(sftp, name, value):
    path=ROOT+"/"+name
    with sftp.file(path+".pending","wb") as f:f.write(value)
    sftp.posix_rename(path+".pending",path)


def argv(official, gpu, cases, workers, slots, memory):
    args=["/usr/bin/python3","-B",ROOT+"/three_gpu.py","worker","--official",official,"--gpu",str(gpu),
          "--workers",str(workers),"--host-slots",str(slots),"--memory-gib",str(memory)]
    for case in cases:args+=["--case",case]
    return args


def service(c, unit, args, log):
    active=cmd(c,"systemctl is-active "+unit+" || true").strip()
    if active=="active":return
    cmd(c,"systemd-run --unit="+unit+" --property=WorkingDirectory="+ROOT+
        " --property=StandardOutput=append:"+ROOT+"/"+log+" --property=StandardError=append:"+ROOT+"/"+log+" "+shlex.join(args))


def setup(dual,single):
    p=PROJECT/"local-experiments/three-gpu/three_gpu.py"
    for c in (dual,single):
        cmd(c,"umask 077; mkdir -p "+ROOT+"/relay "+ROOT+"/spool")
        raw=p.read_text(encoding="utf-8")
        if c is dual:
            for old,new in (
                ("work.mkdir(parents=True)","work.mkdir(parents=True, exist_ok=True)"),
                ('    atomic(work / "DIAGNOSTIC_ONLY.json",','    if not args.baseline_only: args.rounds = min(args.rounds, 3)\n    atomic(work / "DIAGNOSTIC_ONLY.json",'),
                ("        receipts = {}",'        receipts = {r["request_id"]:r for r in (json.loads(f.read_text()) for f in sorted((work/"receipts").glob("*.json")))}'),
                ("(work / name).mkdir()","(work / name).mkdir(exist_ok=True)")):
                if raw.count(old)!=1:raise ValueError("Unexpected worker entry point")
                raw=raw.replace(old,new)
        with c.open_sftp() as s:put(s,"three_gpu.py",raw.encode())
    a={AR:["1001","1003"]}; b={BP:["1001","1002","1003"],FE:["1003"]}; c={AR:["1002"],FE:["1001","1002"]}
    routes={"26016-0":{"command":argv(DUAL,0,a,2,4,21),"cells":a},
            "26016-1":{"command":argv(DUAL,1,b,2,4,21),"cells":b},
            "22120-0":{"command":["/usr/bin/python3","-B",ROOT+"/relay_worker.py"],"cells":c}}
    with dual.open_sftp() as s:
        put(s,"workers.json",json.dumps(routes,indent=2).encode())
        put(s,"relay_worker.py",(HERE/"relay_worker.py").read_bytes())
        put(s,"diagnose_harness.py",(PROJECT/"diagnose_harness.py").read_bytes())
        put(s,"parent.py",(PROJECT/"exports/2026-11-19-claude-expert-audit/runs/15332-claude-v3/round-04/candidate.py").read_bytes())
    (HERE/"workers.json").write_text(json.dumps(routes,indent=2),encoding="utf-8")
    if cmd(dual,"test -d "+ROOT+"/control-r4 && echo present || true").strip()!="present":
        service(dual,"aic-c-control",["/usr/bin/python3","-Bu",ROOT+"/three_gpu.py","run","--official",DUAL,
                "--workers",ROOT+"/workers.json","--work-root",ROOT+"/control-r4","--baseline-only",
                "--reference-program",ROOT+"/parent.py"],"control.log")


def exists(s,path):
    try:s.stat(path);return True
    except FileNotFoundError:return False


def transfer(dual,single):
    with dual.open_sftp() as a,single.open_sftp() as b:
        for name in sorted(a.listdir(ROOT+"/relay")):
            if not name.endswith(".request"):continue
            stem=name[:-8];base="spool/"+stem
            if exists(a,ROOT+"/relay/"+stem+".reply") or exists(a,ROOT+"/relay/"+stem+".error"):continue
            if exists(b,ROOT+"/"+base+".ok"):
                with b.file(ROOT+"/"+base+".ok","rb") as f:payload=f.read()
                json.loads(payload);put(a,"relay/"+stem+".reply",payload);continue
            if exists(b,ROOT+"/"+base+".failed"):
                with b.file(ROOT+"/"+base+".err","rb") as f:err=f.read()[-900:]
                put(a,"relay/"+stem+".error",err);continue
            if exists(b,ROOT+"/"+base+".request"):continue
            with a.file(ROOT+"/relay/"+name,"rb") as f:payload=f.read()
            request=json.loads(payload);assert request["cells"]=={AR:["1002"],FE:["1001","1002"]}
            args=argv(SINGLE,0,[AR,FE],1,1,24)
            loc=ROOT+"/"+base
            script="cd "+ROOT+"\n"+shlex.join(args)+" < "+loc+".request > "+loc+".tmp 2> "+loc+".err && mv "+loc+".tmp "+loc+".ok || touch "+loc+".failed\n"
            put(b,base+".sh",script.encode());put(b,base+".request",payload)
            service(single,"aic-c-"+stem,["/bin/bash",loc+".sh"],base+".service-log")
            print("22120 accepted",stem,flush=True)


def advance(dual):
    with dual.open_sftp() as s:
        control=ROOT+"/control-r4/receipts/initial.json"
        if not exists(s,control):return False
        local=HERE/"control-r4.json"
        if not local.exists():s.get(control,str(local))
        z=HERE/"group-c-harness.zip"
        if not z.exists():return False
        if not exists(s,ROOT+"/run-c"):
            put(s,"group-c-harness.zip",z.read_bytes())
            cmd(dual,"mkdir -p "+ROOT+"/agent; /usr/bin/python3 -B -m zipfile -e "+ROOT+"/group-c-harness.zip "+ROOT+"/agent")
            service(dual,"aic-c-search",["/usr/bin/python3","-Bu",ROOT+"/three_gpu.py","run","--official",DUAL,
                    "--workers",ROOT+"/workers.json","--work-root",ROOT+"/run-c","--rounds","3",
                    "--agent-dir",ROOT+"/agent","--api-key-file","/root/aic-26016/credentials/provider.key"],"search.log")
        return exists(s,ROOT+"/run-c/diagnostic-result.json")


def main():
    passwords={p:getpass.getpass(str(p)+" SSH: ") for p in HOSTS}
    connected={}
    ready=False
    while True:
        try:
            for p in HOSTS:
                if p not in connected or not connected[p].get_transport().is_active():
                    connected[p]=connect(p,passwords[p])
            dual,single=(connected[p] for p in HOSTS)
            if not ready:
                setup(dual,single);ready=True;print("C calibration started or recovered",flush=True)
            transfer(dual,single)
            if advance(dual):
                print("C complete",flush=True);return
            time.sleep(4)
        except (OSError, EOFError, paramiko.SSHException) as exc:
            print(type(exc).__name__,str(exc)[:130],flush=True)
            for c in connected.values():c.close()
            connected={};time.sleep(5)


if __name__=="__main__":main()
