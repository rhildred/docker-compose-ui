#!/bin/bash -i
sudo yum update
sudo yum install python3 python3-devel libev-devel git gcc gcc-c++ make 
sudo amazon-linux-extras install docker 
sudo usermod -a -G docker ec2-user
sudo systemctl enable docker
sudo systemctl start docker
pip3 install --user docker-compose
git clone https://github.com/rhildred/docker-compose-ui.git
cd docker-compose-ui
pip3 install --user -r requirements.txt
python3 setup.py
openssl req -x509 -nodes -days 365 -newkey rsa:2048 -keyout localhost.key -out localhost.crt
sudo cp rhlab.service /lib/systemd/system
sudo systemctl enable rhlab
sudo systemctl start rhlab
