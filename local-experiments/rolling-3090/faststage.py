"""Stream the remaining official image in independent chunks to the same target."""
from concurrent.futures import ThreadPoolExecutor
import getpass
from pathlib import Path
import threading
import time
from inspect_hosts import HERE, connect
from stage import run, REMOTE

NAME = "open3dbench-contest-runtime.tar.gz"
SRC = Path("E:/赛题2") / NAME
PARTS = REMOTE + "/image-parts"
FINAL = REMOTE + "/official/" + NAME
BLOCK = 32 * 1024 * 1024
TOTAL = SRC.stat().st_size
COUNT = (TOTAL + BLOCK - 1) // BLOCK

if __name__ == "__main__":
    password = getpass.getpass("New GPU SSH password: ")
    def open_client():
        client = connect("180.127.11.167", 30924, password)
        client.get_transport().set_keepalive(20)
        return client
    with open_client() as main:
        with main.open_sftp() as sftp:
            sftp.put(str(HERE / "provision.sh"), REMOTE + "/provision.sh")
        print(run(main, "systemctl is-active --quiet rolling-3090-provision || systemd-run --collect --unit=rolling-3090-provision --property=StandardOutput=append:/root/rolling-3090/provision.log --property=StandardError=append:/root/rolling-3090/provision.log /bin/bash /root/rolling-3090/provision.sh"), flush=True)
        run(main, "umask 077; mkdir -p " + PARTS)
        old_size = int(run(main, "stat -c %s " + FINAL).strip())
        already = min(old_size // BLOCK, COUNT - 1)
        print("Starting at", already * BLOCK, "of", TOTAL, flush=True)
        start = time.monotonic()
        progress = [already * BLOCK]
        lock = threading.Lock()
        def worker(lane):
            with open_client() as client, SRC.open("rb") as src:
                for index in range(already + lane, COUNT, 8):
                    dest = "%s/p-%04d" % (PARTS, index)
                    length = min(BLOCK, TOTAL - index * BLOCK)
                    exists = run(client, "stat -c %s " + dest + " 2>/dev/null || echo missing").strip()
                    if exists != str(length):
                        src.seek(index * BLOCK)
                        channel = client.get_transport().open_session(timeout=30)
                        channel.settimeout(150)
                        channel.exec_command("umask 077; cat > " + dest + ".part && mv " + dest + ".part " + dest)
                        try:
                            left = length
                            while left:
                                buf = src.read(min(left, 1024 * 1024))
                                if not buf:
                                    raise EOFError("Local archive shortened")
                                channel.sendall(buf)
                                left -= len(buf)
                            channel.shutdown_write()
                            if channel.recv_exit_status():
                                raise RuntimeError("Target refused an image chunk")
                        finally:
                            channel.close()
                    with lock:
                        progress[0] += length
                        if index % 8 == 0 or progress[0] >= TOTAL:
                            speed = (progress[0] - already * BLOCK) / max(1, time.monotonic() - start) / 1e6
                            print("Image", round(progress[0] / 1e9, 2), "/", round(TOTAL / 1e9, 2), "GB;", round(speed, 2), "MB/s", flush=True)
        with ThreadPoolExecutor(8) as pool:
            list(pool.map(worker, range(8)))
        print("Checking image SHA-256 on the new GPU host", flush=True)
        names = " ".join("%s/p-%04d" % (PARTS, i) for i in range(already, COUNT))
        build = PARTS + "/assembled"
        cmd = ("set -e; umask 077; head -c %d %s > %s; cat %s >> %s; "
               "echo 'e023ec28d1399ef15037c0df98ae170f647df3845123a872a5798d20025c893d  %s' | sha256sum -c -; "
               "mv %s %s" % (already * BLOCK, FINAL, build, names, build, build, build, FINAL))
        print(run(main, cmd), flush=True)
