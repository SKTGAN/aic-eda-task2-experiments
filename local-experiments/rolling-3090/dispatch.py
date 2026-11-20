"""Install our tested agent and queue one official run on the new, named GPU."""
import getpass
import hashlib
import sys
from inspect_hosts import HERE, connect
from stage import REMOTE, run

STATUS = """date -Is
systemctl show rolling-3090-run rolling-3090-provision -p Id -p ActiveState -p Result
stat -c '%s %n' /root/rolling-3090/official/*.tar.gz 2>/dev/null
tail -n 7 /root/rolling-3090/provision.log /root/rolling-3090/runner.log /root/rolling-3090/feedback/check.log 2>/dev/null
docker ps --format '{{.Names}}' 2>/dev/null
df -h / | tail -1
"""
HASHES = """0798d49d101c85cd9d51a4e7cc68d345df1a82de8f462132f14e603627cd7d1c  contest-data.tar.gz
7d15114c2a1f6ce174f9407b9b6a4ddce759c2f5e037cc42c5422b0703781ada  contest-source.tar.gz
e023ec28d1399ef15037c0df98ae170f647df3845123a872a5798d20025c893d  open3dbench-contest-runtime.tar.gz
"""

def deploy(client):
    archive = HERE.parents[1] / "exports" / "claude-rolling-3090-feedback.zip"
    key = getpass.getpass("Official model API key for the new run: ").strip()
    if not key or any(c.isspace() for c in key):
        raise ValueError("Empty or malformed provider key")
    run(client, "umask 077; install -d -m 700 /root/rolling-3090/credentials")
    with client.open_sftp() as sftp:
        files = {"credentials/provider.key": key.encode(), "harness.zip": archive.read_bytes(),
                 "official.sha256": HASHES.encode(), "launch.sh": (HERE / "launch.sh").read_bytes().replace(b"\r\n", b"\n")}
        files["harness.sha256"] = (hashlib.sha256(files["harness.zip"]).hexdigest() + "  harness.zip\n").encode()
        for name, data in files.items():
            with sftp.file(REMOTE + "/" + name, "wb") as out:
                out.chmod(0o600)
                out.write(data)
    print(run(client, "systemctl is-active --quiet rolling-3090-run || systemd-run --unit=rolling-3090-run --property=StandardOutput=append:/root/rolling-3090/runner.log --property=StandardError=append:/root/rolling-3090/runner.log /bin/bash /root/rolling-3090/launch.sh"))

if __name__ == "__main__":
    mode = sys.argv[1]
    assert mode in ("stage", "status")
    with connect("180.127.11.167", 30924, getpass.getpass("New GPU SSH password: ")) as client:
        if mode == "stage":
            deploy(client)
        print(run(client, STATUS))
