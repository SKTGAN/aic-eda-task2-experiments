"""Send as-yet unstarted tail chunks of the same archive over a second set of streams."""
from concurrent.futures import ThreadPoolExecutor
import getpass
import time
from faststage import BLOCK, COUNT, PARTS, SRC, TOTAL, FINAL
from inspect_hosts import connect
from stage import run

if __name__ == "__main__":
    pw = getpass.getpass("New GPU SSH password: ")
    def worker(lane):
        time.sleep(lane * 0.35)
        with connect("180.127.11.167", 30924, pw) as client, SRC.open("rb") as inp:
            client.get_transport().set_keepalive(20)
            for index in range(COUNT - 1 - lane, 0, -8):
                name = "%s/p-%04d" % (PARTS, index)
                length = min(BLOCK, TOTAL - index * BLOCK)
                state = run(client, "if test -f %s -o -f %s.part || test $(stat -c %%s %s) -ge %d; then echo reached; fi" % (name, name, FINAL, (index + 1) * BLOCK))
                if state.strip():
                    break
                ch = client.get_transport().open_session(timeout=30)
                ch.settimeout(150)
                ch.exec_command("umask 077; cat > %s.boost && mv %s.boost %s" % (name, name, name))
                try:
                    inp.seek(index * BLOCK)
                    left = length
                    while left:
                        data = inp.read(min(left, 1048576))
                        if not data:
                            raise EOFError("Local file shortened")
                        ch.sendall(data)
                        left -= len(data)
                    ch.shutdown_write()
                    if ch.recv_exit_status():
                        raise RuntimeError("Chunk upload failed")
                finally:
                    ch.close()
                if lane == 0: print("Tail confirmed through chunk", index, "of", COUNT, flush=True)
    with ThreadPoolExecutor(8) as pool:
        list(pool.map(worker, range(8)))
