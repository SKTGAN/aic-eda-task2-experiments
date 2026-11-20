#!/bin/bash
set -euo pipefail
umask 077
base=/root/rolling-3090
official=$base/official
cd "$official"
ready() { [[ $(stat -c %s "$1" 2>/dev/null || true) == "$2" ]]; }
for item in 'contest-data.tar.gz 196359062' 'contest-source.tar.gz 693074022' 'open3dbench-contest-runtime.tar.gz 7005779726'; do
  read -r name size <<<"$item"
  echo "Waiting for $name"
  until ready "$name" "$size"; do sleep 15; done
  echo "Verifying $name"
  grep -F "  $name" "$base/official.sha256" | sha256sum -c -
  if [[ "$name" != open3dbench-contest-runtime.tar.gz && ! -d "${name%.tar.gz}" ]]; then tar -xzf "$name"; fi
done
echo "Waiting for the GPU runtime"
until docker info --format '{{json .Runtimes}}' 2>/dev/null | grep -q '"nvidia"'; do sleep 15; done
if ! /usr/bin/python3 -c 'import yaml' 2>/dev/null; then
  DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends python3-yaml
fi
cd "$base"
sha256sum -c harness.sha256
src="$official/contest-source"
arm="$base/feedback"
framework="$arm/AgenticBench"
if [[ ! -d "$framework" ]]; then
  mkdir -p "$arm"
  cp -al "$src/AgenticBench" "$framework"
  mv "$framework/agent/loss_decoder" "$arm/organizer-agent"
  mkdir "$framework/agent/loss_decoder"
  /usr/bin/python3 -m zipfile -e "$base/harness.zip" "$framework/agent/loss_decoder"
fi
cmp "$framework/agent/loss_decoder/program.py" "$src/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py"
cd "$framework"
args=(--baseline loss_decoder --source "$src" --data-root "$official/contest-data/task2" --work-root "$arm/work" --agent-cpu 2 --agent-memory-gb 4)
/usr/bin/python3 -B -m contest2 check "${args[@]}" >"$arm/check.log" 2>&1 || { tail -25 "$arm/check.log"; exit 1; }
echo "Official preflight passed"
if [[ -s "$arm/work/run.json" ]]; then
  if /usr/bin/python3 -c 'import json,sys; sys.exit(json.load(open(sys.argv[1])).get("status")!="succeeded")' "$arm/work/run.json"; then exit 0; fi
fi
exec /usr/bin/python3 -Bu -m contest2 run "${args[@]}" --api-key-file "$base/credentials/provider.key"
