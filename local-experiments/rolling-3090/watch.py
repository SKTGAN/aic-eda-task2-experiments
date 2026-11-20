"""Read the deployment and training status. Print only counters, bounded errors and stage changes."""
import getpass
import json
import time
from inspect_hosts import connect

QUERY = """from pathlib import Path
import collections,json,sqlite3,subprocess
p=Path('/root/rolling-3090')
def tail(path):
    if not path.exists(): return ''
    with path.open('rb') as f:
        f.seek(max(0,path.stat().st_size-1800))
        return '\\n'.join(f.read().decode(errors='replace').splitlines()[-3:])[:600]
def unit(name):
    return subprocess.run(['systemctl','is-active',name],stdout=subprocess.PIPE,text=True).stdout.strip()
state={'service':unit('rolling-3090-run'),'setup':unit('rolling-3090-provision'),
       'setup_tail':tail(p/'provision.log'), 'run_tail':tail(p/'runner.log'),
       'check_tail':tail(p/'feedback/check.log'),
       'docker':Path('/usr/bin/docker').exists(),'nvidia_ctk':Path('/usr/bin/nvidia-ctk').exists()}
db=p/'feedback/work/control/budget.sqlite'
if db.is_file():
    try:
        conn=sqlite3.connect(db.as_uri()+'?mode=ro',uri=True,timeout=3)
        state['evals']=dict(conn.execute('select status,count(*) from evaluations group by status'))
        state['model']=dict(conn.execute('select status,count(*) from model_calls group by status'))
        conn.close()
    except sqlite3.Error: pass
state['cells']=len(list((p/'feedback/work').glob('evaluations/*/cells/*/*/cell.json')))
log=p/'feedback/work/participant-agent/loss_decoder/search.jsonl'
if log.exists():
    events=collections.Counter()
    for line in log.open(encoding='utf-8'):
        try: events[json.loads(line)['event']]+=1
        except (ValueError,KeyError): pass
    state['events']=dict(events)
print(json.dumps(state,sort_keys=True))
"""
if __name__ == "__main__":
    with connect("180.127.11.167",30924,getpass.getpass("New GPU SSH password: ")) as client:
        client.get_transport().set_keepalive(20)
        last=None
        while True:
            stdin,stdout,stderr=client.exec_command("python3 -",timeout=30)
            stdin.write(QUERY)
            stdin.channel.shutdown_write()
            output=stdout.read().decode().strip()
            if not output: raise RuntimeError(stderr.read().decode()[:320])
            state=json.loads(output)
            if state != last:
                print(output,flush=True)
                last=state
            if state['service'] in ('failed','inactive') or state.get('evals'): break
            time.sleep(30)
