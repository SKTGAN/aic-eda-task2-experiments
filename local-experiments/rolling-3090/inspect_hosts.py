"""Read the two named endpoints and retrieve Claude's original ZIP."""
import getpass
import hashlib
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "remote-client-deps"))
import paramiko

INSPECT = """hostname
nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader
free -h
df -hT -x tmpfs -x devtmpfs -x squashfs | head -45
docker version --format '{{.Server.Version}}'
docker image ls --format '{{.Repository}}:{{.Tag}} {{.ID}}' | head -30
docker ps --format '{{.Names}}' | head -30
ls -A /root | grep -E 'aic|task2|contest|data|code|runtime'
ls -ld /data* /workspace /mnt/* /home/vipuser/* 2>/dev/null | head -55
find /root /data /home/vipuser -maxdepth 5 -type f \\( -name runtime.json -o -name open3dbench-contest-runtime.tar.gz -o -name contest-model.key \\) -print 2>/dev/null | head -45
"""

def connect(address, port, password):
    client = paramiko.SSHClient()
    client.load_host_keys(str(Path.home() / ".ssh" / "known_hosts"))
    client.connect(address, port=port, username="root", password=password,
                   allow_agent=False, look_for_keys=False, timeout=15,
                   auth_timeout=30, banner_timeout=25)
    return client

def get_remote_zip(client):
    remote = "/root/code/claude-rolling-ablation-review.zip"
    dest = HERE.parents[1] / "exports" / "claude-rolling-ablation-review.zip"
    with client.open_sftp() as sftp, sftp.open(remote, "rb") as inp:
        payload = inp.read(32 * 1024 * 1024 + 1)
        if len(payload) > 32 * 1024 * 1024 or not payload.startswith(b"PK"):
            raise ValueError("Archive size or signature unexpected")
    if dest.exists() and dest.read_bytes() != payload:
        raise FileExistsError("Different archive already present")
    dest.write_bytes(payload)
    print("Fetched ZIP:", len(payload), hashlib.sha256(payload).hexdigest())

if __name__ == "__main__":
    mode = sys.argv[1]
    address, port = {"source": ("23.27.141.126", 22),
                     "machine": ("180.127.11.167", 30924)}[mode]
    password = getpass.getpass("SSH password for " + mode + ": ")
    try:
        client = connect(address, port, password)
    except paramiko.AuthenticationException:
        if mode != "source" or not password.endswith(chr(92)):
            raise
        client = connect(address, port, password[:-1])
    with client:
        if mode == "source":
            get_remote_zip(client)
        else:
            _, out, err = client.exec_command(INSPECT, timeout=60)
            print(out.read().decode(errors="replace"), err.read().decode(errors="replace"))
