"""Hand the single-card shard to the authenticated local C coordinator."""
import json
from pathlib import Path
import re
import sys
import time

root = Path(__file__).resolve().parent / "relay"
root.mkdir(exist_ok=True)
request = json.load(sys.stdin)
if not all(re.fullmatch(r"[a-zA-Z0-9_-]{1,96}", request[k]) for k in ("run","request")):
    raise ValueError("Invalid job name")
base = root / (request["run"] + "_" + request["request"])
pending = base.with_suffix(".tmp")
pending.write_text(json.dumps(request))
pending.replace(base.with_suffix(".request"))
while not base.with_suffix(".reply").exists():
    if base.with_suffix(".error").exists():
        raise RuntimeError(base.with_suffix(".error").read_text()[-1200:])
    time.sleep(3)
print(base.with_suffix(".reply").read_text())
