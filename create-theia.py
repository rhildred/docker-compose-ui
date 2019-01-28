import os
from scripts.git_repo import git_pull, git_repo, GIT_YML_PATH, git_clone
import hashlib
import sys
import js2py
from json import loads
import requests

def createProject(item):
    m = hashlib.shake_128()
    m.update(item.encode('utf-8'))
    sFolder = m.hexdigest(4) + "-" + item
    nPort = example.crc16(sFolder + "." + oCreds["Site"])
    git_clone("https://github.com/rhildred/theia-remote.git", "./users/" + item + '/' +  sFolder)
    env_file = open("./users/" + item + '/' +  sFolder + "/.env", "w")
    env_file.write("RHPORT=" + str(nPort))
    env_file.close()
    dictToSend = {'type':"CNAME", 'name':sFolder, 'content': oCreds["Site"], 'proxied': True }
    dictHeaders = {"X-Auth-Email":oCreds["EmailID"], "X-Auth-Key":oCreds["SecretKey"]}
    res = requests.post('https://api.cloudflare.com/client/v4/zones/' + oCreds["ZoneID"] + "/dns_records", json=dictToSend, headers=dictHeaders)
    print('response from server:',res.text)

dir_path = os.path.dirname(os.path.realpath(__file__))
eval_result, example = js2py.run_file(dir_path + '/static/scripts/proxyport.js')
with open('cloudflare.json') as json_data_file:
    oCreds = loads(json_data_file.read())

if len(sys.argv) > 1:
	createProject(sys.argv[1])
else:
    for item in os.listdir("users"):
        if os.path.isdir(os.path.join("users", item)):
            createProject(item)
