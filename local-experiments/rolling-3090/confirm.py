import getpass
from inspect_hosts import connect
from stage import run

with connect("180.127.11.167",30924,getpass.getpass("New GPU SSH password: ")) as client:
    print(run(client, """python3 - <<'PY'
import collections,json,sqlite3,subprocess
from datetime import datetime
from pathlib import Path
p=Path('/root/rolling-3090')
work=p/'feedback/work'
if 'open3dbench-contest-runtime.tar.gz: OK' in (p/'runner.log').read_text() and (p/'official/open3dbench-contest-runtime.tar.gz').stat().st_size==7005779726:
    parts=p/'image-parts'
    freed=0
    for i in range(209):
        q=parts/('p-%04d'%i)
        if q.is_file() and not q.is_symlink():
            freed+=q.stat().st_size
            q.unlink()
    print("Temporary image chunks removed (bytes):",freed)
print(datetime.now().astimezone().isoformat())
print(subprocess.run(['systemctl','is-active','rolling-3090-run'],capture_output=True,text=True).stdout.strip())
db=work/'control/budget.sqlite'
if db.is_file():
    c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
    print('Evaluations:',c.execute('select status,count(*) from evaluations group by status').fetchall())
    print('Model calls:',c.execute('select status,count(*) from model_calls group by status').fetchall())
    c.close()
log=work/'participant-agent/loss_decoder/search.jsonl'
if log.is_file():
    rows=[]
    for line in log.read_text().splitlines():
        try: rows.append(json.loads(line))
        except ValueError: pass
    print('Agent events:',dict(collections.Counter(r.get('event') for r in rows)))
    for r in rows:
        if r.get('event') in {'official_receipt','invalid_proposal','submitted','runtime_capabilities','selected','agent_error','model_error'}:
            print({k:r[k] for k in ('event','search_intent','score','status','reason','numpy','torch','reference_helper','loss_probe','decoder_probe') if k in r})
for d in (work/'evaluations').glob('*'):
    if d.is_dir():
        print('Completed cell files:',[str(x.relative_to(d)) for x in d.glob('cells/*/*/cell.json')])
print(subprocess.run(['docker','ps','--format','{{.Names}}'],capture_output=True,text=True).stdout.strip())
if (work/'session-result.json').is_file():
    s=json.loads((work/'session-result.json').read_text()); print('Session:',{k:s[k] for k in ('status','error_type','message','candidate_id') if k in s})
PY"""))
