#!/bin/bash -i
sudo yum update
sudo amazon-linux-extras install docker python3 python3-devel libev-devel git gcc gcc-c++ make 
sudo service docker start
sudo usermod -a -G docker ec2-user
pip3 install --user docker-compose
git clone https://github.com/rhildred/docker-compose-ui.git
cd docker-compose-ui
pip3 install --user -r requirements.txt
python3 setup.py
curl -o- https://raw.githubusercontent.com/creationix/nvm/v0.32.1/install.sh | bash
bash -c "source ~/.nvm/nvm.sh ; nvm install node; npm install -g pm2; pm2 start app_server.py --interpreter=python3"
