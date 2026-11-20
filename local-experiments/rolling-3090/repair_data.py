import getpass
from inspect_hosts import HERE, connect
from stage import run, REMOTE
with connect("180.127.11.167",30924,getpass.getpass("New GPU SSH password: ")) as client:
    with client.open_sftp() as sftp:
        sftp.put(str(HERE / "baseline_probe.py"), REMOTE + "/baseline_probe.py")
    print(run(client, """set -eu
base=/root/rolling-3090
ref=$base/official/contest-data/task2/loss_decoder/train/references/bp_fe-ng45/1001/evaluation_result.json
hash=$(sha256sum "$ref")
stat -c 'Before uid=%u gid=%g mode=%a' "$ref"
for d in "$base/official/contest-data" "$base/official/contest-source"; do
  test "$(realpath "$d")" = "$d"
  find "$d" -xdev ! -uid 0 -exec chown -h root:root {} +
done
test "$hash" = "$(sha256sum "$ref")"
stat -c 'After uid=%u gid=%g mode=%a; content verified unchanged' "$ref"
systemd-run --unit=rolling-3090-baseline --property=StandardOutput=append:/root/rolling-3090/baseline.log --property=StandardError=append:/root/rolling-3090/baseline.log /usr/bin/python3 -Bu /root/rolling-3090/baseline_probe.py
"""))
