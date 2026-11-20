from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import getpass
import time
from inspect_hosts import HERE, connect

REMOTE = "/root/rolling-3090"
FILES = ("contest-data.tar.gz", "contest-source.tar.gz", "open3dbench-contest-runtime.tar.gz")

def run(client, cmd):
    _, out, err = client.exec_command(cmd)
    data = out.read().decode(errors="replace") + err.read().decode(errors="replace")
    if out.channel.recv_exit_status():
        raise RuntimeError(data)
    return data

def upload(client, name):
    src = Path("E:/赛题2") / name
    target = REMOTE + "/official/" + name
    with client.open_sftp() as sftp:
        try:
            existing = sftp.stat(target).st_size
        except FileNotFoundError:
            existing = 0
        total = src.stat().st_size
        if existing > total:
            raise ValueError("Unexpected size: " + name)
        if existing == total:
            print(name, "already staged", flush=True)
            return
        with src.open("rb") as inp, sftp.open(target, "ab") as out:
            inp.seek(existing)
            out.set_pipelined(True)
            last = time.monotonic()
            while chunk := inp.read(1024 * 1024):
                out.write(chunk)
                existing += len(chunk)
                if time.monotonic() - last > 35:
                    print(name, existing, "/", total, flush=True)
                    last = time.monotonic()
        print(name, "finished", sftp.stat(target).st_size, flush=True)

if __name__ == "__main__":
    password = getpass.getpass("SSH password for new 3090: ")
    with connect("180.127.11.167", 30924, password) as client:
        client.get_transport().set_keepalive(20)
        run(client, "umask 077; mkdir -p /root/rolling-3090/official")
        with client.open_sftp() as sftp:
            sftp.put(str(HERE / "provision.sh"), REMOTE + "/provision.sh")
        print(run(client, "systemctl is-active --quiet rolling-3090-provision || systemd-run --collect --unit=rolling-3090-provision --property=StandardOutput=append:/root/rolling-3090/provision.log --property=StandardError=append:/root/rolling-3090/provision.log /bin/bash /root/rolling-3090/provision.sh"), flush=True)
        with ThreadPoolExecutor(3) as pool:
            list(pool.map(lambda name: upload(client, name), FILES))
