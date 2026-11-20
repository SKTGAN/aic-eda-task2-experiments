import getpass
import time
from inspect_hosts import HERE, connect
from stage import run, REMOTE
MONITOR="""python3 - <<'PY'
from pathlib import Path
import collections,datetime,json,sqlite3,subprocess
p=Path('/root/rolling-3090')
w=p/'feedback/work-v2'
d=p/'baseline-diagnostic/physical/cells/bp_fe-ng45/1001/cell.json'
state={'retry':subprocess.run(['systemctl','is-active','rolling-3090-run-v2'],capture_output=True,text=True).stdout.strip()}
if d.is_file():
    cell=json.loads(d.read_text())
    state['baseline']={k:cell.get(k) for k in ('status','valid','score','error_message')}
db=w/'control/budget.sqlite'
if db.is_file():
    try:
        c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
        state['evaluations']=dict(c.execute('select status,count(*) from evaluations group by status'))
        state['model_calls']=dict(c.execute('select status,count(*) from model_calls group by status'))
        c.close()
    except sqlite3.Error: pass
cells=[]
for f in sorted(w.glob('evaluations/*/cells/*/*/cell.json')):
    row=json.loads(f.read_text()); cells.append({k:row.get(k) for k in ('case','seed','status','score','error_message')})
state['measured_cells']=cells[:10]
state['containers']=subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True).stdout.splitlines()
if state['retry'] in ('failed','inactive'):
    log=p/'retry.log'
    if log.exists(): state['error']=log.read_text(errors='replace')[-550:]
print(json.dumps(state))
PY"""
with connect("180.127.11.167",30924,getpass.getpass("New GPU SSH password: ")) as client:
    client.get_transport().set_keepalive(20)
    with client.open_sftp() as sftp:
        sftp.put(str(HERE / "retry.sh"), REMOTE + "/retry.sh")
    print(run(client, "systemd-run --unit=rolling-3090-run-v2 --property=StandardOutput=append:/root/rolling-3090/retry.log --property=StandardError=append:/root/rolling-3090/retry.log /bin/bash /root/rolling-3090/retry.sh"),flush=True)
    import json
    last=''
    while True:
        data=run(client,MONITOR).strip()
        if data!=last:
            print(data,flush=True)
            last=data
        state=json.loads(data)
        if state['retry'] in ('failed','inactive') or state.get('measured_cells'): break
        time.sleep(20)
