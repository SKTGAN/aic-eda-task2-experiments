#!/bin/bash
set -euo pipefail
umask 077
base=/root/rolling-3090
arm=$base/feedback
cd "$base"
sha256sum -c harness.sha256
test -s "$arm/work/session-result.json"
test ! -e "$arm/work-v2"
if systemctl is-active --quiet rolling-3090-run; then exit 1; fi
while systemctl is-active --quiet rolling-3090-baseline; do sleep 10; done
python3 - <<'PY'
from pathlib import Path
import json,math,sys
cell=Path('/root/rolling-3090/baseline-diagnostic/physical/cells/bp_fe-ng45/1001/cell.json')
row=json.loads(cell.read_text())
metrics=row.get('metrics') or {}
if not(row.get('valid') is True and row.get('status')=='succeeded' and
       all(isinstance(metrics.get(k),(float,int)) and math.isfinite(metrics[k])
           for k in ('final_global_wns_setup_ns','final_global_tns_setup_ns'))):
    sys.exit('Baseline did not qualify for a paid retry')
print('Validated official baseline cell',row['case'],row['seed'],row['score'],flush=True)
PY
src=$base/official/contest-source
framework=$arm/AgenticBench
cd "$framework"
cmp "$framework/agent/loss_decoder/program.py" "$src/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py"
exec /usr/bin/python3 -Bu -m contest2 run --baseline loss_decoder --source "$src" --data-root "$base/official/contest-data/task2" --work-root "$arm/work-v2" --agent-cpu 2 --agent-memory-gb 4 --api-key-file "$base/credentials/provider.key"
