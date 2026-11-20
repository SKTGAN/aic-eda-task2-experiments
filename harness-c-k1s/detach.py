"""Install and verify a time-limited, forced-command relay for this single run."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import getpass
import json
from pathlib import Path
import re
import sys
import time

HERE=Path(__file__).resolve().parent
sys.path.insert(0,str(HERE.parent/"harness-c-dual"))
import operate as op

root="/root/aic-c-k1s-fleet"
op.ROOT=root
passwords={p:getpass.getpass(str(p)+" SSH: ") for p in (26016,22120)}
with ThreadPoolExecutor(2) as executor:
    a,b=executor.map(lambda p:op.connect(p,passwords[p]),passwords)
try:
    for host in (a,b):
        with host.open_sftp() as s: op.put(s,"remote_relay.py",(HERE/"remote_relay.py").read_bytes())
    op.cmd(a,"cd "+root+" && (test -s relay_id || ssh-keygen -q -t ed25519 -N '' -C C-K1S-run -f relay_id)")
    public=op.cmd(a,"cat "+root+"/relay_id.pub").strip()
    assert re.fullmatch(r"ssh-ed25519 [A-Za-z0-9+/=]+ C-K1S-run",public)
    expiry=(datetime.now(timezone.utc)+timedelta(days=2)).strftime("%Y%m%d%H%M%SZ")
    entry='restrict,expiry-time="'+expiry+'",command="/usr/bin/python3 -B '+root+'/remote_relay.py" '+public
    op.cmd(b,"umask 077; mkdir -p /root/.ssh; touch /root/.ssh/authorized_keys")
    with b.open_sftp() as s:
        path="/root/.ssh/authorized_keys"
        with s.file(path,"rb") as f: contents=f.read()
        if public.encode() not in contents:
            with s.file(path,"ab") as f:f.write(("\n"+entry+"\n").encode())
    hk=b.get_transport().get_remote_server_key()
    with a.open_sftp() as s:
        op.put(s,"worker_hosts",("c-k1s-worker,[c-k1s-worker]:22120 "+hk.get_name()+" "+hk.get_base64()+"\n").encode())
    args=["/usr/bin/python3","-Bu",root+"/remote_relay.py","master"]
    op.service(a,"aic-k1s-server-relay",args,"server-relay.log")
    for attempt in range(28):
        state=op.cmd(a,"cat "+root+"/server-handoff.json 2>/dev/null || true").strip()
        if state:
            print("Remote handoff",state,flush=True)
            (HERE/"results/server-handoff.json").write_text(state,encoding="utf8")
            break
        if attempt in (3,12):
            probe=op.cmd(a,"cd "+root+" && /usr/bin/python3 -Bc \"from remote_relay import ssh; p=ssh('180.127.11.169','ping');print(p.returncode,p.stdout,p.stderr[-300:])\" || true")
            print("relay probe",probe.strip(),flush=True)
        time.sleep(2)
    else:raise RuntimeError("Cross-host control path not yet verified")
finally:
    a.close();b.close()
