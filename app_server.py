import bjoern
import os
import signal
import socket


from main import app

host = '0.0.0.0'
port = 5001
NUM_WORKERS = 2
worker_pids = []


bjoern.listen(app, host, port)
for _ in range(NUM_WORKERS):
    pid = os.fork()
    if pid > 0:
        # in master
        worker_pids.append(pid)
    elif pid == 0:
        # in worker
        try:
            bjoern.run()
        except KeyboardInterrupt:
            pass
        exit()

try:
    for _ in range(NUM_WORKERS):
        os.wait()
except KeyboardInterrupt:
    get_project(sPath).down(remove_image_type=False, include_volumes=None)
    for pid in worker_pids:
        os.kill(pid, signal.SIGINT)
