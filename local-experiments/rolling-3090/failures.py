import getpass
from inspect_hosts import connect
from stage import run

with connect("180.127.11.167",30924,getpass.getpass("New GPU SSH password: ")) as client:
    print(run(client, """python3 - <<'PY'
from pathlib import Path
import sqlite3,json,collections
w=Path('/root/rolling-3090/feedback/work')
samples={}
counts=collections.Counter()
for p in sorted((w/'evaluations').glob('*/cells/*/*/cell.json')):
    r=json.loads(p.read_text())
    m=(r.get('error_type'),r.get('error_message','')[:600])
    counts[m]+=1
    samples.setdefault(m,p)
print('Cell statuses:',len(counts),'failure patterns')
for m,n in counts.most_common(4):
    p=samples[m]; r=json.loads(p.read_text())
    print(n,m, str(p))
    for a in (r.get('native_failure_diagnostics') or [])[:2]:
        print(str(a)[:1800])
    print('Other evidence files:',[str(x.relative_to(p.parent)) for x in (p.parent/'result').glob('*')][:20])
for q in sorted(w.glob('evaluations/*/evaluation_result.json'))[:1]:
    r=json.loads(q.read_text()); print({k:r.get(k) for k in ('status','reason','error_type','error_message')})
    print(str(r.get('artifacts'))[:900])
db=w/'control/budget.sqlite'
c=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True)
print('Evaluations',c.execute('select status,count(*) from evaluations group by status').fetchall())
print('Cost/Status',c.execute('select status,count(*),sum(cost_rmb) from model_calls group by status').fetchall())
print('Session',str(json.loads((w/'session-result.json').read_text()).get('message'))[:600] if (w/'session-result.json').exists() else 'open')
PY"""))
