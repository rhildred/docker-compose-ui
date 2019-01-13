import requests
import json
import socket

dictCloudFlare = {}
dictCloudFlare["EmailID"] = input("Please enter your email for CloudFlare: ")
dictCloudFlare["SecretKey"] = input("Please enter your secret for CloudFlare: ")
dictCloudFlare["Site"] = input("Please enter the site that you are using on CloudFlare: ")
dictCloudFlare["ZoneID"] = input("Please enter your zoneId for CloudFlare: ")
with open('cloudflare.json', 'w') as fp:
    json.dump(dictCloudFlare, fp)

dictGithub = {}

dictGithub["client_id"] = input("Please enter your client ID for Github: ")
dictGithub["client_secret"] = input("Please enter your client secret for Github: ")
with open('github.json', 'w') as fp:
    json.dump(dictGithub, fp)

sHostname = socket.gethostname()

if(-1 != sHostname.find("internal")):
    sHostname = requests.get("http://169.254.169.254/latest/meta-data/public-hostname").text

print(sHostname)
with open('cloudflare.json') as json_data_file:
    oCreds = json.loads(json_data_file.read())

dictToSend = {'type':"CNAME", 'name':oCreds["Site"], 'content': sHostname, 'proxied': True }
dictHeaders = {"X-Auth-Email":oCreds["EmailID"], "X-Auth-Key":oCreds["SecretKey"]}
res = requests.post('https://api.cloudflare.com/client/v4/zones/' + oCreds["ZoneID"] + "/dns_records", json=dictToSend, headers=dictHeaders)
print('response from server:',res.text)
dictToSend['name'] = "apps"
dictToSend['content'] = oCreds["Site"]
res = requests.post('https://api.cloudflare.com/client/v4/zones/' + oCreds["ZoneID"] + "/dns_records", json=dictToSend, headers=dictHeaders)
print('response from server:',res.text)
dictToSend['name'] = "www"
res = requests.post('https://api.cloudflare.com/client/v4/zones/' + oCreds["ZoneID"] + "/dns_records", json=dictToSend, headers=dictHeaders)
print('response from server:',res.text)



