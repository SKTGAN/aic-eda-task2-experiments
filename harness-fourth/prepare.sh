#!/usr/bin/env bash
set -euo pipefail
umask 077
root=/root/aic-eda-fourth
official=$root/official/contest-source
data=$root/official/contest-data/task2
arm=$root/arm
src=$arm/contest-source
work=$arm/work
key=/root/.config/aic-eda/deepseek.key
image=sha256:f2401e978e5504c11cbc048266cc088152f3d5cf0a1a5438d91933175c9b7821
archive=$root/incoming/open3dbench-contest-runtime.tar.gz
cd "$root"
exec 9>"$root/prepare.lock"
flock -n 9
test -s "$key"
test -e setup.ok
until test -e extracted.ok; do sleep 5; done
test -s "$official/AgenticBench/contest2/runner.py"
test -s "$data/loss_decoder/train/qualified_matrix.json"
mkdir -p "$arm"
if ! test -e "$src"; then
  stage=$(mktemp -d "$arm/stage.XXXXXX")
  cp -al "$official" "$stage/contest-source"
  agent="$stage/contest-source/AgenticBench/agent/loss_decoder"
  mv "$agent" "$stage/stock-agent"
  cp -a "$root/harness/next-harness/AgenticBench/agent/loss_decoder" "$agent"
  cmp "$agent/program.py" "$official/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py"
  mv "$stage/contest-source" "$src"
fi
cmp "$src/AgenticBench/agent/loss_decoder/agent.py" "$root/harness/next-harness/AgenticBench/agent/loss_decoder/agent.py"
cd "$src/AgenticBench"
resolve_image() {
  /usr/bin/python3 -B -c 'import sys; from contest2.runtime_images import resolve; print(resolve(sys.argv[1])["docker_address"])' "$image"
}
if ! resolve_image >/dev/null 2>&1; then
  echo "Waiting for the runtime archive"
  until test "$(stat -c %s "$archive" 2>/dev/null || true)" = 7005779726; do sleep 10; done
  printf '%s  %s\n' e023ec28d1399ef15037c0df98ae170f647df3845123a872a5798d20025c893d "$archive" | sha256sum -c -
  docker load -i "$archive"
fi
resolve_image
/usr/bin/python3 -B - "$arm" "$image" <<'PY'
import json
import os
import sys
from pathlib import Path
from grt_bench.runtime import admission

arm, image = Path(sys.argv[1]), sys.argv[2]
capacity = dict(cpu=min(8, len(os.sched_getaffinity(0))), memory_gb=24, storage_gb=40, gpus=["0"], build_slots=0)
value = dict(queue=str(arm / "queue.sqlite"), host="fourth-3090", image=image, capacity=capacity)
(arm / "runtime.json").write_text(json.dumps(value) + "\n", encoding="utf-8")
print(json.dumps(admission(str(arm), {"storage_gb": 16, "memory_gb": 24}, ["0"])))
PY
args=(--baseline loss_decoder --source "$official" --data-root "$data" --runtime "$arm/runtime.json" --work-root "$work" --agent-cpu 2 --agent-memory-gb 4)
/usr/bin/python3 -B -m contest2 check "${args[@]}" 2>&1 | tee "$arm/check.log"
touch "$root/preflight.ok"
test ! -e "$work/control/session-start.json"
test ! -e "$work/session-result.json"
exec /usr/bin/python3 -Bu -m contest2 run "${args[@]}" --api-key-file "$key" >> "$arm/runner.log" 2>&1
