#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
base=/root/aic-eda-evidence-20261117
src=$base/official/contest-source
data=$base/official/contest-data/task2
runtime=$base/arms/evidence/runtime.json
arm=$base/arms/branching-20261118
framework=$arm/AgenticBench
work=$arm/work
inbox=/home/vipuser/aic-eda-evidence-incoming
key=/home/vipuser/.config/aic-eda/contest-model.key
unit=aic-eda-branching-10820-20261118
watch=aic-eda-branching-public-10820-20261118
digest=4a1e9e85f343448f02adfd022e8fff992379dfa82201451c8a14a877c4c4547e
waiter=$base/arms/evidence/after-training/run-public-validation.py
exec 9>"$base/branching-launch.lock"
flock -n 9
if systemctl is-active --quiet "$unit"; then
    echo 'Training service already active'; exit 0
fi
[[ ! -e "$arm" && -s "$key" && -r "$runtime" && -r "$waiter" ]]
running=$(docker ps --format '{{.Names}}')
if [[ "$running" =~ grt-|o3db-contest-agent- ]] || [[ -n $(nvidia-smi --query-compute-apps=pid --format=csv,noheader) ]]; then
    echo 'Host already has a physical or GPU job; leaving it undisturbed.'; exit 1
fi
df -h "$base"
nvidia-smi --query-gpu=name,memory.free --format=csv,noheader
mkdir "$arm"
install -m 600 "$inbox/branching-harness-4a1e9e85.zip" "$arm/harness.zip"
printf '%s  %s\n' "$digest" "$arm/harness.zip" | sha256sum -c -
cp -al "$src/AgenticBench" "$framework"
agent="$framework/agent/loss_decoder"
mv "$agent" "$arm/original-agent"
mkdir "$agent"
/usr/bin/python3 -B - "$arm/harness.zip" "$agent" <<'PY'
from pathlib import Path
import sys, zipfile
archive, dest = sys.argv[1:]
names = 'agent.py candidate_reply.py decision_evidence.py paired_feedback.py program.py prompt.md search_control.py'.split()
prefix = 'AgenticBench/agent/loss_decoder/'
with zipfile.ZipFile(archive) as z:
    assert sorted(z.namelist()) == sorted(prefix + n for n in names)
    for name in names:
        (Path(dest) / name).write_bytes(z.read(prefix + name))
PY
cmp "$agent/program.py" "$src/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py"
cd "$framework"
args=(--baseline loss_decoder --source "$src" --data-root "$data" --runtime "$runtime" --work-root "$work" --agent-cpu 2 --agent-memory-gb 4)
/usr/bin/python3 -B -m contest2 check "${args[@]}" >"$arm/check.log" 2>&1 || { tail -n 16 "$arm/check.log"; exit 1; }
tail -n 13 "$arm/check.log"
systemd-run --unit="$unit" --working-directory="$framework" -p "StandardOutput=append:$arm/runner.log" -p "StandardError=append:$arm/runner.log" /usr/bin/python3 -B -m contest2 run "${args[@]}" --api-key-file "$key"
mkdir "$arm/after-training"
systemd-run --unit="$watch" --working-directory="$framework" -p "StandardOutput=append:$arm/after-training/pipeline.log" -p "StandardError=append:$arm/after-training/pipeline.log" /usr/bin/python3 -B "$waiter" --unit "$unit" --framework "$framework" --source "$src" --data "$data" --runtime "$runtime" --work "$work" --output "$arm/after-training"
systemctl show "$unit" "$watch" -p Id -p ActiveState -p Result -p MainPID
TZ=Asia/Shanghai date '+%F %T %Z'
