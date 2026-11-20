"""Run the K1S experiment, relay the 3090 shard, and export training and validation results."""
import getpass
import hashlib
import io
import json
from pathlib import Path
import sys
import time
from zipfile import ZIP_DEFLATED, ZipFile

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent
sys.path.insert(0,str(PROJECT/"harness-c-dual"))
import operate as op

ROOT = "/root/aic-c-k1s-fleet"
op.ROOT = ROOT
UNIT = "aic-k1s-fleet"
TRAIN = ROOT + "/k1s-ten"


def setup(dual,single):
    for host in (dual,single):
        op.cmd(host,"umask 077; mkdir -p "+ROOT+"/relay "+ROOT+"/spool")
    if op.cmd(dual,"test -f "+ROOT+"/training.sha256 && echo yes || true").strip()=="yes":
        return
    bundle=io.BytesIO()
    with ZipFile(bundle,"w",ZIP_DEFLATED) as z:
        for f in sorted((HERE/"agent").iterdir()):
            if f.is_file(): z.write(f,f.name)
    sha=hashlib.sha256(bundle.getvalue()).hexdigest()
    (HERE/"harness.zip").write_bytes(bundle.getvalue())
    origin=PROJECT/"local-experiments/three-gpu/three_gpu.py"
    runtime=origin.read_bytes()
    for host in (dual,single):
        with host.open_sftp() as s:op.put(s,"three_gpu.py",runtime)
    routes=json.loads((PROJECT/"harness-c-dual/workers.json").read_bytes())
    for row in routes.values():
        row["command"]=[v.replace("/root/aic-group-c-v1",ROOT) for v in row["command"]]
    gateway=(PROJECT/"diagnose_harness.py").read_text(encoding="utf-8")
    anchor="    def responses_create(self, payload):\n"
    assert gateway.count(anchor)==1
    gateway=gateway.replace(anchor,anchor+'        if getattr(self, "passthrough", False):\n            return self.send(payload, "K1S")[0]\n')
    with dual.open_sftp() as s:
        op.put(s,"diagnose_harness.py",gateway.encode())
        op.put(s,"relay_worker.py",(PROJECT/"harness-c-dual/relay_worker.py").read_bytes())
        op.put(s,"public_validation.py",(HERE/"public_validation.py").read_bytes())
        op.put(s,"workers.json",json.dumps(routes).encode())
        op.put(s,"harness.zip",bundle.getvalue())
    op.cmd(dual,"cd "+ROOT+" && mkdir -p agent && /usr/bin/python3 -B -m zipfile -e harness.zip agent "
           "&& cmp agent/program.py /root/aic-26016/official/contest-source/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py "
           "&& /usr/bin/python3 -B public_validation.py --check")
    shell=("set -eu\ncd "+ROOT+"\n/usr/bin/python3 -Bu three_gpu.py run --official /root/aic-26016/official "
           "--workers workers.json --work-root k1s-ten --rounds 10 --agent-dir agent "
           "--api-key-file /root/aic-26016/credentials/provider.key\n/usr/bin/python3 -Bu public_validation.py\n")
    with dual.open_sftp() as s:op.put(s,"run.sh",shell.encode())
    op.service(dual,UNIT,["/bin/bash",ROOT+"/run.sh"],"fleet.log")
    with dual.open_sftp() as s: op.put(s,"training.sha256",(sha+"  harness.zip\n").encode())


def fetch(s,remote,local):
    if not op.exists(s,remote): return
    if local.is_file() and local.stat().st_size==s.stat(remote).st_size: return
    local.parent.mkdir(parents=True,exist_ok=True)
    tmp=local.with_suffix(".pending")
    s.get(remote,str(tmp));tmp.replace(local)


def main():
    keys={p:getpass.getpass(str(p)+" SSH: ") for p in (26016,22120)}
    sessions={};ready=False;last=None
    dest=HERE/"results"
    while True:
        try:
            for port,key in keys.items():
                if port not in sessions:sessions[port]=op.connect(port,key)
            dual,single=sessions[26016],sessions[22120]
            if not ready:setup(dual,single);ready=True
            op.transfer(dual,single)
            with dual.open_sftp() as s:
                for remote,name in ((ROOT+"/fleet.log","fleet.log"),(TRAIN+"/DIAGNOSTIC_ONLY.json","schedule.json"),
                    (TRAIN+"/diagnostic-result.json","training.json"),(ROOT+"/public-validation/selected.json","frozen.json"),
                    (ROOT+"/public-validation/result.json","public.json")):
                    fetch(s,remote,dest/name)
                path=TRAIN+"/receipts"
                names=s.listdir(path) if op.exists(s,path) else []
                for name in names: fetch(s,path+"/"+name,dest/"receipts"/name)
                if len(names)!=last or (dest/"public.json").exists():
                    fetch(s,TRAIN+"/participant-agent/loss_decoder/search.jsonl",dest/"dialogue.jsonl")
                    print("C completed training matrices:",len(names),flush=True);last=len(names)
                if (dest/"public.json").exists():return
            time.sleep(5)
        except (op.paramiko.SSHException,OSError,EOFError) as exc:
            print(type(exc).__name__,str(exc)[:140],flush=True)
            for c in sessions.values():c.close()
            sessions={};time.sleep(4)

if __name__=="__main__": main()
