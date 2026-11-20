#!/bin/bash
set -euo pipefail
umask 077
base=/root/aic-26016
arm=$base/development/15332-memory
official=$base/official
source=$official/contest-source
cd "$arm"
sha256sum -c bundle.sha256
if [[ ! -d "$arm/AgenticBench" ]]; then
    cp -al "$source/AgenticBench" "$arm/AgenticBench"
    mv "$arm/AgenticBench/agent/loss_decoder" "$arm/original-agent"
    mkdir "$arm/AgenticBench/agent/loss_decoder"
    /usr/bin/python3 -B -m zipfile -e dev-harness.zip "$arm/AgenticBench/agent/loss_decoder"
    ln "$source/README.md" "$arm/README.md"
fi
cmp "$arm/AgenticBench/agent/loss_decoder/program.py" "$source/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py"
mkdir -p "$arm/work"
echo '{"purpose":"development only","historical_run":"15332-claude-v3","historical_trials":10,"new_trial_limit":2,"eligible_for_contest_submission":false}' > "$arm/work/DEVELOPMENT_ONLY.json"
cd "$arm/AgenticBench"
exec /usr/bin/python3 -Bu -m contest2 run --baseline loss_decoder --source "$source" --data-root "$official/contest-data/task2" --runtime "$base/two-round/runtime.json" --work-root "$arm/work" --agent-cpu 2 --agent-memory-gb 4 --api-key-file "$base/credentials/provider.key"
