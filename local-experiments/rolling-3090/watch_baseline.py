import getpass
import time
from inspect_hosts import connect
from stage import run
with connect("180.127.11.167",30924,getpass.getpass("New GPU SSH password: ")) as client:
    client.get_transport().set_keepalive(20)
    previous=None
    while True:
        status=run(client, """p=/root/rolling-3090
        systemctl is-active rolling-3090-baseline
        tail -c 1000 "$p/baseline.log"
        docker ps --format '{{.Names}}'
        cell="$p/baseline-diagnostic/physical/cells/bp_fe-ng45/1001/cell.json"
        if test -s "$cell"; then
          python3 -c 'import json,sys;v=json.load(open(sys.argv[1]));print({k:v.get(k) for k in ("valid","status","score","error_message")})' "$cell"
        fi
        exit 0
        """)
        if status!=previous:
            print(status,flush=True)
            previous=status
        if not status.startswith("active\n"):
            break
        time.sleep(25)
