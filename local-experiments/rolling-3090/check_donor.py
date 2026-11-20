"""Locate the official immutable archive files on the team's existing evaluator, read only."""
from inspect_hosts import connect
import getpass

with connect("180.127.11.167", 15332, getpass.getpass("Existing evaluator SSH password: ")) as client:
    cmd = """ls -d /root/aic* /home/vipuser/aic* /data /mnt/* 2>/dev/null
    find /root /home/vipuser /opt /mnt /data -maxdepth 7 -type f \\( -name open3dbench-contest-runtime.tar.gz -o -name contest-source.tar.gz -o -name contest-data.tar.gz -o -name 'libnvidia-container*.deb' -o -name 'nvidia-container-toolkit*.deb' \\) -printf '%s %p\\n' 2>/dev/null | head -60
    command -v ssh
    """
    _, out, err = client.exec_command(cmd, timeout=60)
    print(out.read().decode(errors="replace"), err.read().decode(errors="replace"))
