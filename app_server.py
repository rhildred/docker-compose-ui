import bjoern
import os
import signal
import fileinput
import socket

#first write ip address of this server for nginx config

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # doesn't even have to be reachable
        s.connect(('10.255.255.255', 1))
        IP = s.getsockname()[0]
    except:
        IP = '127.0.0.1'
    finally:
        s.close()
    return IP

sIp = get_ip()
oFile = open("nginx.conf", "w")
for line in fileinput.input(['nginx.tmpl.conf']):
    oFile.write(line.replace('dockerhost', sIp))
oFile.close()

#we will want to run docker-compose up equivalent here

#now set up as a web server

from main import app

host = '0.0.0.0'
port = 5001
NUM_WORKERS = 5
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
    for pid in worker_pids:
        os.kill(pid, signal.SIGINT)