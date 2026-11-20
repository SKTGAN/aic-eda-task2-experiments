import getpass
from inspect_hosts import connect
from stage import run

with connect("180.127.11.167",30924,getpass.getpass("New GPU SSH password: ")) as client:
    print(run(client, """date -Is
    stat -c '%s %y %n' /var/cache/apt/archives/partial/* 2>/dev/null | tail -6
    systemctl show rolling-3090-provision -p ActiveState -p Result
    ps -C apt-get,http,https -o etime,stat,comm
    tail -n 12 /root/rolling-3090/provision.log
    command -v nvidia-ctk || true
    du -sh /root/rolling-3090/image-parts
    find /root/rolling-3090/image-parts -maxdepth 1 -name 'p-????' -type f -printf '%s\\n' | awk '{n++;b+=$1} END {print n,"complete segments;",b,"bytes"}'
    find /root/rolling-3090/image-parts -maxdepth 1 -type f \\( -name '*.part' -o -name '*.boost' \\) -printf '%f %s\\n' | head -20
    curl --connect-timeout 6 --max-time 12 -sSfL https://nvidia.github.io/libnvidia-container/gpgkey -o /dev/null && echo NVIDIA-repository-reachable
    exit 0
    """))
