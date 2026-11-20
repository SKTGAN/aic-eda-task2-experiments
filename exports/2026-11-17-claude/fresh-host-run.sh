#!/usr/bin/env bash
set -Eeuo pipefail
umask 077

usage() {
    cat <<'USAGE'
Usage: bash fresh-host-run.sh {ours|claude} [--check-only]
Optional environment:
  EDA_HOME          Task root, default /root/aic-eda-single-20261117
  EDA_INPUTS_DIR    Folder containing the official tarballs and Harness ZIPs
                    Default: $EDA_HOME/incoming
  EDA_RETAINED_ROOT Old dual-GPU task root, used to reuse its archives or
                    extracted official files and the final arms-low Harness
  EDA_GPU_INDEX     Host device index, default 0
  EDA_API_KEY_FILE  Host-only provider key file, required for a live run
USAGE
}

fail() {
    printf '%s\n' "$*" >&2
    exit 1
}

if [[ ${1:-} == --help ]]; then
    usage
    exit 0
fi

arm=${1:-}
case "$arm" in
    ours) agent_zip=ours-harness.zip
          agent_sha=0b449eaed6d6f75d04b611a86e1f5bd65c59aace241863d4bd0d0eab0e6e8ade ;;
    claude) agent_zip=claude-harness-revision.zip
            agent_sha=2d47c449b8c058afc739fc1d92aba8b9d7aba5d0d01238717c953e884c13001a ;;
    *) usage >&2; exit 2 ;;
esac
mode=${2:-run}
[[ $# -le 2 && ( "$mode" == run || "$mode" == --check-only ) ]] || fail "Expected --check-only or no second argument."

home=$(realpath -m -- "${EDA_HOME:-/root/aic-eda-single-20261117}")
[[ "$home" != / ]] || fail "EDA_HOME must be a task directory."
inputs=$(realpath -m -- "${EDA_INPUTS_DIR:-$home/incoming}")
retained=
if [[ -n ${EDA_RETAINED_ROOT:-} ]]; then
    retained=$(realpath -e -- "$EDA_RETAINED_ROOT")
    [[ "$retained" != "$home" ]] || fail "EDA_HOME must differ from EDA_RETAINED_ROOT."
fi
gpu=${EDA_GPU_INDEX:-0}
[[ "$gpu" =~ ^[0-9]+$ ]] || fail "EDA_GPU_INDEX must be a device index."

arm_root="$home/arms/$arm"
official="$home/official"
official_source="$official/contest-source"
data="$official/contest-data/task2"
source="$arm_root/contest-source"
work="$arm_root/work"
runtime="$arm_root/runtime.json"
image=sha256:f2401e978e5504c11cbc048266cc088152f3d5cf0a1a5438d91933175c9b7821
key=
if [[ "$mode" == run ]]; then
    [[ -n ${EDA_API_KEY_FILE:-} ]] || fail "Set EDA_API_KEY_FILE to the host-only key file."
    key=$(realpath -e -- "$EDA_API_KEY_FILE")
    [[ -f "$key" && -r "$key" ]] || fail "The host cannot read the key file."
    case "$key" in
        "$official"|"$official/"*|"$arm_root"|"$arm_root/"*)
            fail "Keep the key file outside the source, data and run directories." ;;
    esac
fi

mkdir -p -- "$arm_root"
exec 9>"$home/bootstrap.lock"
flock -n 9 || fail "Another bootstrap is staging this task root."
[[ ! -e "$work/control/session-start.json" && ! -e "$work/session-result.json" ]] ||
    fail "This work directory has a run record. Use a fresh EDA_HOME for a new run."

docker version --format '{{.Server.Version}}'
nvidia-smi -i "$gpu" --query-gpu=name,memory.free --format=csv,noheader
cpu=$(nproc)
((cpu >= 4)) || fail "The official physical container requests four CPUs."
((cpu <= 8)) || cpu=8

find_archive() {
    local name=$1 candidate
    for candidate in "$inputs/$name" "${retained:+$retained/incoming/mobile/$name}" \
                     "${retained:+$retained/incoming/$name}"; do
        if [[ -n "$candidate" && -f "$candidate" ]]; then
            printf '%s\n' "$candidate"
            return
        fi
    done
    return 1
}

verify_file() {
    local result
    result=$(sha256sum -- "$2")
    [[ ${result%% *} == "$1" ]] || fail "SHA-256 mismatch for $2"
}

if [[ ! -d "$official" ]]; then
    stage=$(mktemp -d "$home/official.stage.XXXXXX")
    if source_tar=$(find_archive contest-source.tar.gz) && data_tar=$(find_archive contest-data.tar.gz); then
        verify_file 7d15114c2a1f6ce174f9407b9b6a4ddce759c2f5e037cc42c5422b0703781ada "$source_tar"
        verify_file 0798d49d101c85cd9d51a4e7cc68d345df1a82de8f462132f14e603627cd7d1c "$data_tar"
        tar --no-same-owner -xzf "$source_tar" -C "$stage"
        tar --no-same-owner -xzf "$data_tar" -C "$stage"
    elif [[ -n "$retained" && -d "$retained/official/contest-source" && -d "$retained/official/contest-data" ]]; then
        cp -a --no-preserve=ownership -- "$retained/official/contest-source" "$retained/official/contest-data" "$stage/"
    else
        fail "Could not find both official source/data tarballs or a retained official tree."
    fi
    [[ -d "$stage/contest-source/AgenticBench/contest2" && -d "$stage/contest-data/task2" ]] ||
        fail "The organizer package layout did not match."
    mv -- "$stage" "$official"
fi

if [[ ! -d "$source" ]]; then
    stage=$(mktemp -d "$arm_root/agent.stage.XXXXXX")
    cp -al -- "$official_source" "$stage/contest-source"
    agent="$stage/contest-source/AgenticBench/agent/loss_decoder"
    mv -- "$agent" "$stage/original-agent"
    previous=${retained:+$retained/arms-low/$arm/contest-source/AgenticBench/agent/loss_decoder}
    if [[ -n "$previous" && -f "$previous/agent.py" && -f "$previous/prompt.md" ]]; then
        cp -a --no-preserve=ownership -- "$previous" "$agent"
    else
        archive=$(find_archive "$agent_zip") || fail "Could not find $agent_zip."
        verify_file "$agent_sha" "$archive"
        /usr/bin/python3 -B - "$archive" "$agent" <<'PY'
from pathlib import Path, PurePosixPath
import sys
from zipfile import ZipFile

archive, destination = sys.argv[1:]
prefix = "AgenticBench/agent/loss_decoder/"
root = Path(destination)
root.mkdir()
with ZipFile(archive) as bundle:
    for member in bundle.infolist():
        if member.is_dir() or not member.filename.startswith(prefix):
            continue
        name = PurePosixPath(member.filename)
        if len(name.parts) != 4 or ".." in name.parts or name.suffix not in {".py", ".md", ".txt"}:
            raise ValueError(f"Unexpected participant file: {name}")
        (root / name.name).write_bytes(bundle.read(member))
PY
    fi
    /usr/bin/python3 -B - "$agent" <<'PY'
from pathlib import Path
import sys

root = Path(sys.argv[1])
prompt = root / "prompt.md"
lead = (
    "The official validator forbids assigning to any function parameter or trusted helper. "
    "Use fresh local variables whose names do not start with an underscore. "
    "Do not use a bare underscore in loops or unpacking. Keep the signature and never assign to array elements. "
    "Give the smallest coherent change. Return exactly the two complete Python functions in one code block, "
    "without surrounding explanation, and keep the untouched function exactly as supplied.\n\n"
)
text = prompt.read_text(encoding="utf-8")
if not text.startswith(lead):
    prompt.write_text(lead + text, encoding="utf-8")

agent = root / "agent.py"
text = agent.read_text(encoding="utf-8")
original = '        "stream": False,\n'
replacement = original + '        "reasoning": {"effort": "low"},\n'
if replacement not in text:
    if text.count(original) != 1:
        raise ValueError("Expected one model request constructor")
    text = text.replace(original, replacement)
compile(text, str(agent), "exec")
agent.write_text(text, encoding="utf-8")
(root / "opening.txt").write_text("decoder_only\n", encoding="utf-8")
PY
    cmp -- "$agent/program.py" "$official_source/AgenticBench/local_tasks/tp_gnn_loss_decoder_timing/initial_program.py" ||
        fail "The Harness program does not match the frozen official initial program."
    mv -- "$stage/contest-source" "$source"
    mv -- "$stage/original-agent" "$arm_root/original-agent"
    rmdir -- "$stage"
fi

resolve_image() {
    PYTHONPATH="$official_source/AgenticBench" /usr/bin/python3 -B -c \
        'from contest2.runtime_images import resolve; import sys; print(resolve(sys.argv[1])["docker_address"])' "$image"
}
if ! address=$(resolve_image 2>/dev/null); then
    archive=$(find_archive open3dbench-contest-runtime.tar.gz) || fail "Could not find the official Docker archive."
    verify_file e023ec28d1399ef15037c0df98ae170f647df3845123a872a5798d20025c893d "$archive"
    docker load -i "$archive"
    address=$(resolve_image)
fi

# Match the physical container's UID and dropped capabilities. Check all nine private-mode files.
docker run --rm --pull=never --network none --read-only --cap-drop ALL \
    --security-opt no-new-privileges --user "$(id -u):$(id -g)" \
    --mount "type=bind,source=$data/loss_decoder/train/references,target=/refs,readonly" \
    --entrypoint /bin/sh "$address" -c '
        set -eu
        for design in bp_fe-ng45 bp-ng45 ariane133-ng45; do
            for seed in 1001 1002 1003; do
                file="/refs/$design/$seed/evaluation_result.json"
                if ! test -r "$file"; then
                    printf "Unreadable official reference %s\n" "$file" >&2
                    exit 1
                fi
            done
        done
    '

/usr/bin/python3 -B - "$runtime" "$image" "$gpu" "$cpu" <<'PY'
from pathlib import Path
import json
import sys

path, image, gpu, cpu = sys.argv[1:]
runtime = {
    "queue": str(Path(path).with_name("queue.sqlite")),
    "host": f"gpu-{gpu}",
    "image": image,
    "capacity": {
        "cpu": int(cpu),
        "memory_gb": 24,
        "storage_gb": 40,
        "gpus": [gpu],
        "build_slots": 0,
    },
}
Path(path).write_text(json.dumps(runtime) + "\n", encoding="utf-8")
PY

# Check the same first-phase host admission rules as the official worker.
PYTHONPATH="$official_source/AgenticBench" /usr/bin/python3 -B - "$arm_root" "$gpu" <<'PY'
import json
import sys
from grt_bench.runtime import admission

print(json.dumps(admission(sys.argv[1], {"storage_gb": 16, "memory_gb": 24}, [sys.argv[2]])))
PY

args=(--baseline loss_decoder --source "$official_source" --data-root "$data"
      --runtime "$runtime" --work-root "$work" --agent-cpu 2 --agent-memory-gb 4)
(
    cd -- "$source/AgenticBench"
    exec /usr/bin/python3 -B -m contest2 check "${args[@]}"
) 2>&1 | tee "$arm_root/check.log"

if [[ "$mode" == --check-only ]]; then
    exit 0
fi

unit_suffix=$(printf '%s' "$home" | sha256sum | cut -c1-8)
unit="aic-eda-single-$arm-$unit_suffix"
systemd-run --unit="$unit" --uid="$(id -u)" --gid="$(id -g)" \
    --working-directory="$source/AgenticBench" \
    --property="StandardOutput=append:$arm_root/runner.log" \
    --property="StandardError=append:$arm_root/runner.log" \
    /usr/bin/python3 -B -m contest2 run "${args[@]}" --api-key-file "$key"
printf 'Unit %s.service\nRun folder %s\n' "$unit" "$arm_root"
