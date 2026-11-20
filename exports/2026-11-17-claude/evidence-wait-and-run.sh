#!/usr/bin/env bash
set -Eeuo pipefail
umask 077
[[ $(id -u) == 0 && $# == 2 ]] || exit 2
incoming=$(realpath -e -- "$1")
api_file=$(realpath -e -- "$2")
[[ -s "$api_file" ]] || exit 2
export EDA_HOME=/root/aic-eda-evidence-20261117
export EDA_INPUTS_DIR="$incoming" EDA_API_KEY_FILE="$api_file"

archive_ready() {
    local name=$1 size=$2 file value
    for file in "$incoming/$name" "$incoming/$name.peer.partial" "$incoming/$name.partial"; do
        [[ -f "$file" ]] || continue
        value=$(stat -c '%s' -- "$file")
        [[ "$value" == "$size" ]] || continue
        if [[ "$file" != "$incoming/$name" ]]; then
            mv -n -- "$file" "$incoming/$name"
        fi
        [[ $(stat -c '%s' -- "$incoming/$name") == "$size" ]] && return 0
    done
    return 1
}

for ((n=0; n<360; n++)); do
    if archive_ready contest-source.tar.gz 693074022 &&
       archive_ready contest-data.tar.gz 196359062 &&
       archive_ready open3dbench-contest-runtime.tar.gz 7005779726 &&
       docker info --format '{{.Runtimes}}' 2>/dev/null | grep -q nvidia; then
        printf '%s Inputs and GPU runtime ready; checking the official package.\n' "$(date -Is)"
        exec bash "$incoming/evidence-host-run.sh" evidence
    fi
    if (( n % 8 == 0 )); then
        printf '%s Waiting for signed runtime package assembly and official archive transfers.\n' "$(date -Is)"
    fi
    sleep 15
done
echo 'The prerequisites did not become ready within 90 minutes.' >&2
exit 1
