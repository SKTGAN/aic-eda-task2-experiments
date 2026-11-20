#!/bin/bash
set -euo pipefail
umask 077
base=/root/aic-26016
cd "$base"
official=$base/official
arm=$base/two-round
src=$official/contest-source
data=$official/contest-data/task2
mkdir -p "$arm"
test -s credentials/provider.key
echo '2df786e28573a2c7d68c2d8c58d3946b76c69035e4f1eb51938a7f4f92132a2d  harness.zip' | sha256sum -c -
if [[ ! -e "$arm/AgenticBench" ]]; then
  cp -al "$src/AgenticBench" "$arm/AgenticBench"
  mv "$arm/AgenticBench/agent/loss_decoder" "$arm/original-agent"
  mkdir "$arm/AgenticBench/agent/loss_decoder"
  /usr/bin/python3 -B -m zipfile -e harness.zip "$arm/AgenticBench/agent/loss_decoder"
  ln "$src/README.md" "$arm/README.md"
fi
cmp "$arm/AgenticBench/agent/loss_decoder/program.py" "$src/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py"
archive="$official/open3dbench-contest-runtime.tar.gz"
if [[ ! -f "$archive" ]]; then
  echo waiting_for_runtime_image
  until [[ $(stat -c '%s' "$official/runtime.tar.gz.part" 2>/dev/null || true) == 7005779726 ]]; do sleep 8; done
  echo 'e023ec28d1399ef15037c0df98ae170f647df3845123a872a5798d20025c893d  official/runtime.tar.gz.part' | sha256sum -c -
  mv "$official/runtime.tar.gz.part" "$archive"
fi
/usr/bin/python3 -B - "$arm" "$data" "$archive" <<'PY'
import json, sys
from pathlib import Path
arm, data, archive = map(Path, sys.argv[1:])
runtime = json.loads((data / 'runtime.json').read_text())
runtime.update(host='dual-3080-26016', queue=str(arm/'queue.sqlite'), image_archive=str(archive))
runtime['capacity'].update(cpu=16, memory_gb=64, storage_gb=80, gpus=['0','1'], gpu_slots_per_device=1)
(arm / 'runtime.json').write_text(json.dumps(runtime, indent=2))
PY
cd "$arm/AgenticBench"
args=(--baseline loss_decoder --source "$src" --data-root "$data" --runtime "$arm/runtime.json" --work-root "$arm/work" --agent-cpu 2 --agent-memory-gb 4)
echo gpu_preflight
/usr/bin/python3 -B -m contest2 check "${args[@]}" > "$arm/check.log" 2>&1 || { tail -18 "$arm/check.log"; exit 1; }
echo complete_preflight_start_training
exec /usr/bin/python3 -Bu -m contest2 run "${args[@]}" --api-key-file "$base/credentials/provider.key"
