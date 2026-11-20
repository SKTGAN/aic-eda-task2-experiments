"""Fetch only the C role transcript, proposals and scored receipts into the local development archive."""
import getpass
import hashlib
import json
from pathlib import Path
import time
from operate import HERE,ROOT,connect
import paramiko

def download(s,src,dst):
    try:
        stat=s.stat(src)
    except FileNotFoundError:return
    if dst.exists() and dst.stat().st_size==stat.st_size:return
    dst.parent.mkdir(parents=True,exist_ok=True)
    tmp=dst.with_suffix(".fetching")
    s.get(src,str(tmp));tmp.replace(dst)

def main():
    key=getpass.getpass("26016 SSH: ")
    dest=HERE/"results";last=""
    while True:
        c=None
        try:
            c=connect(26016,key)
            with c.open_sftp() as s:
                while True:
                    download(s,ROOT+"/control-r4/receipts/initial.json",dest/"control.json")
                    for n in range(13,16):
                        folder="round-%02d"%n
                        for name in ("proposal.json","paired-result.json"):
                            download(s,ROOT+"/run-c/"+folder+"/"+name,dest/folder/name)
                    for name in ("search.log","control.log"):
                        download(s,ROOT+"/"+name,dest/name)
                    for name in ("c-summary.json","diagnostic-result.json","DIAGNOSTIC_ONLY.json"):
                        download(s,ROOT+"/run-c/"+name,dest/name)
                    remote=ROOT+"/run-c/receipts"
                    try: names=s.listdir(remote)
                    except FileNotFoundError:names=[]
                    for name in names:
                        if name.endswith(".json"):download(s,remote+"/"+name,dest/"receipts"/name)
                    summary=dest/"diagnostic-result.json"
                    if summary.exists():
                        download(s,ROOT+"/run-c/participant-agent/loss_decoder/search.jsonl",dest/"conversation.jsonl")
                        assert len(list((dest/"receipts").glob("*.json")))==3
                        print("three C development receipts and dialogue exported",flush=True);return
                    state=(len(list(dest.glob("round-*/proposal.json"))),len(list(dest.glob("receipts/*.json"))))
                    if state!=last:print("C proposals and results:",state,flush=True);last=state
                    time.sleep(12)
        except paramiko.AuthenticationException:raise
        except (EOFError,OSError,paramiko.SSHException) as err:
            print(type(err).__name__,str(err)[:140],flush=True);time.sleep(5)
        finally:
            if c:c.close()

if __name__=="__main__":main()
