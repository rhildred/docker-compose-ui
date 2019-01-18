"""
Docker Compose UI, flask based application
"""

from json import loads
import logging
import os
import traceback
from shutil import rmtree
from compose.service import ImageType, BuildAction
import docker
import requests
from flask import Flask, jsonify, request, abort, session, redirect, url_for, render_template
from scripts.git_repo import git_pull, git_repo, GIT_YML_PATH, git_clone
from scripts.bridge import ps_, get_project, get_container_from_id, get_yml_path, containers, project_config, info
from scripts.find_files import find_yml_files, get_readme_file, get_logo_file
from scripts.requires_auth import requires_auth, authentication_enabled, \
  disable_authentication, set_authentication
from scripts.manage_project import manage
import uuid


# Flask Application
API_V1 = '/api/v1/'
COMPOSE_REGISTRY = os.getenv('DOCKER_COMPOSE_REGISTRY')

logging.basicConfig(level=logging.INFO)
app = Flask(__name__, static_url_path='')
jinja_options = app.jinja_options.copy()

jinja_options.update(dict(
    block_start_string='<%',
    block_end_string='%>',
    variable_start_string='%%',
    variable_end_string='%%',
    comment_start_string='<#',
    comment_end_string='#>'
))
app.jinja_options = jinja_options

app.secret_key = str(uuid.uuid4())
def load_projects(sPath):
    """
    load project definitions (docker-compose.yml files)
    """
    projects = {}

    if git_repo:
        git_pull()
        projects = find_yml_files(GIT_YML_PATH)
    else:
        projects = find_yml_files(sPath)

    logging.info(projects)
    return projects




def get_project_with_name(path, name):
    """
    get docker compose project given a project name
    """
    projects = load_projects(path)
    path = projects[name]
    return get_project(path)

# REST endpoints
@app.route(API_V1 + "projects", methods=['GET'])
def list_projects():
    """
    List docker compose projects
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        projects = load_projects(YML_PATH)
        active = [container['Labels']['com.docker.compose.project'] \
            if 'com.docker.compose.project' in container['Labels'] \
            else [] for container in containers()]
        return jsonify(projects=projects, active=active)
    else:
        return "unauthorized", 403

@app.route(API_V1 + "remove/<name>", methods=['DELETE'])
@requires_auth
def rm_(name):
    """
    remove previous cached containers. docker-compose rm -f
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        project = get_project_with_name(YML_PATH, name)
        project.remove_stopped()
        return jsonify(command='rm')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "projects/<name>", methods=['GET'])
def project_containers(name):
    """
    get project details
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        project = get_project_with_name(YML_PATH, name)
        return jsonify(containers=ps_(project))
    else:
        return "unauthorized", 403

@app.route(API_V1 + "projects/<project>/<service_id>", methods=['POST'])
@requires_auth
def run_service(project, service_id):
    """
    docker-compose run service
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        json = loads(request.data)
        service = get_project_with_name(YML_PATH, project).get_service(service_id)

        command = json["command"] if 'command' in json else service.options.get('command')

        container = service \
            .create_container(one_off=True, command=command)
        container.start()

        return jsonify(\
            command='run %s/%s' % (project, service_id), \
            name=container.name, \
            id=container.id \
            )
    else:
        return "unauthorized", 403

@app.route(API_V1 + "projects/yml/<name>", methods=['GET'])
def project_yml(name):
    """
    get yml content
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        projects = load_projects(YML_PATH)
        folder_path = projects[name]
        path = get_yml_path(folder_path)
        config = project_config(folder_path)

        with open(path) as data_file:
            env = None
            if os.path.isfile(folder_path + '/.env'):
                with open(folder_path + '/.env') as env_file:
                    env = env_file.read()

            return jsonify(yml=data_file.read(), env=env, config=config._replace(version=config.version.__str__()))
    else:
        return "unauthorized", 403


@app.route(API_V1 + "projects/readme/<name>", methods=['GET'])
def get_project_readme(name):
    """
    get README.md or readme.md if available
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        projects = load_projects(YML_PATH)
        path = projects[name]
        return jsonify(readme=get_readme_file(path))
    else:
        return "unauthorized", 403

@app.route(API_V1 + "projects/logo/<name>", methods=['GET'])
def get_project_logo(name):
    """
    get logo.png if available
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        projects = load_projects(YML_PATH)
        path = projects[name]
        logo = get_logo_file(path)
        if logo is None:
            abort(404)
        return logo
    else:
        abort(403)


@app.route(API_V1 + "projects/<name>/<container_id>", methods=['GET'])
def project_container(name, container_id):
    """
    get container details
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        project = get_project_with_name(YML_PATH, name)
        container = get_container_from_id(project.client, container_id)
        return jsonify(
            id=container.id,
            short_id=container.short_id,
            human_readable_command=container.human_readable_command,
            name=container.name,
            name_without_project=container.name_without_project,
            number=container.number,
            ports=container.ports,
            ip=container.get('NetworkSettings.IPAddress'),
            labels=container.labels,
            log_config=container.log_config,
            image=container.image,
            environment=container.environment,
            started_at=container.get('State.StartedAt'),
            repo_tags=container.image_config['RepoTags']
            )
    else:
        return "unauthorized", 403

@app.route(API_V1 + "projects/<name>", methods=['DELETE'])
@requires_auth
def kill(name):
    """
    docker-compose kill
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        get_project_with_name(YML_PATH, name).kill()
        return jsonify(command='kill')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "projects", methods=['PUT'])
@requires_auth
def pull():
    """
    docker-compose pull
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        name = loads(request.data)["id"]
        get_project_with_name(YML_PATH, name).pull()
        return jsonify(command='pull')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "services", methods=['PUT'])
@requires_auth
def scale():
    """
    docker-compose scale
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        req = loads(request.data)
        name = request['project']
        service_name = req['service']
        num = req['num']

        project = get_project_with_name(YML_PATH, name)
        project.get_service(service_name).scale(desired_num=int(num))
        return jsonify(command='scale')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "projects", methods=['POST'])
@requires_auth
def up_():
    """
    docker-compose up
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        req = loads(request.data)
        name = req["id"]
        service_names = req.get('service_names', None)
        do_build = BuildAction.force if req.get('do_build', False) else BuildAction.none
        
        nUid = os.getuid()
        os.environ["CURRENT_UID"] = str(nUid)
        container_list = get_project_with_name(YML_PATH, name).up(
            service_names=service_names,
            do_build=do_build)

        return jsonify(
            {
                'command': 'up',
                'containers': [container.name for container in container_list]
            })
    else:
        return "unauthorized", 403

@app.route(API_V1 + "build", methods=['POST'])
@requires_auth
def build():
    """
    docker-compose build
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        json = loads(request.data)
        name = json["id"]

        dic = dict(no_cache=json["no_cache"] if "no_cache" in json \
        else None, pull=json["pull"] if "pull" in json else None)

        get_project_with_name(YML_PATH, name).build(**dic)

        return jsonify(command='build')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "create-project", methods=['POST'])
@app.route(API_V1 + "create", methods=['POST'])
@requires_auth
def create_project():
    """
    create new project
    """
    if("username" in session):
        sUserName = session["username"]
        YML_PATH = "./users/" + sUserName

        data = loads(request.data)
        sName = data["name"]
        file_path = git_clone(data["repoName"], YML_PATH + '/' +  sName)

        if 'env' in data and data["env"]:
            env_file = open(YML_PATH + '/' + sName + "/.env", "w")
            env_file.write(data["env"])
            env_file.close()

        with open('cloudflare.json') as json_data_file:
            oCreds = loads(json_data_file.read())

        dictToSend = {'type':"CNAME", 'name':sName, 'content': oCreds["Site"], 'proxied': True }
        dictHeaders = {"X-Auth-Email":oCreds["EmailID"], "X-Auth-Key":oCreds["SecretKey"]}
        res = requests.post('https://api.cloudflare.com/client/v4/zones/' + oCreds["ZoneID"] + "/dns_records", json=dictToSend, headers=dictHeaders)
        print('response from server:',res.text)


        load_projects(YML_PATH)

        return jsonify(path=file_path)
    else:
        return "unauthorized", 403

@app.route(API_V1 + "update-project", methods=['PUT'])
@requires_auth
def update_project():
    """
    update project
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        data = loads(request.data)
        file_path = manage(YML_PATH + '/' +  data["name"], data["yml"], True)

        if 'env' in data and data["env"]:
            env_file = open(YML_PATH + '/' + data["name"] + "/.env", "w")
            env_file.write(data["env"])
            env_file.close()

        return jsonify(path=file_path)
    else:
        return "unauthorized", 403

@app.route(API_V1 + "remove-project/<name>", methods=['DELETE'])
@requires_auth
def remove_project(name):
    """
    remove project
    """
    if('username' in session):
        sUserName = session["username"]
        YML_PATH = "./users/" + sUserName
        directory = YML_PATH + '/' + name
        rmtree(directory)

        with open('cloudflare.json') as json_data_file:
            oCreds = loads(json_data_file.read())
        dictHeaders = {"X-Auth-Email":oCreds["EmailID"], "X-Auth-Key":oCreds["SecretKey"]}
        res = requests.get('https://api.cloudflare.com/client/v4/zones/' + oCreds["ZoneID"] + "/dns_records?name=" + name + "-" + sUserName + "." + oCreds["Site"], headers=dictHeaders)
        dictFromServer = res.json()
        sId = dictFromServer["result"][0]["id"]
        res = requests.delete('https://api.cloudflare.com/client/v4/zones/' + oCreds["ZoneID"] + "/dns_records/" + sId, headers=dictHeaders)
        print(res.text)



        load_projects("./users/" + sUserName)
        return jsonify(path=directory)
    else:
        return "unauthorized", 403


@app.route(API_V1 + "search", methods=['POST'])
def search():
    """
    search for a project on a docker-compose registry 
    """
    query = loads(request.data)['query']
    response = requests.get(COMPOSE_REGISTRY + '/api/v1/search', \
        params={'query': query}, headers={'x-key': 'default'})
    result = jsonify(response.json())
    if response.status_code != 200:
        result.status_code = response.status_code
    return result


@app.route(API_V1 + "yml", methods=['POST'])
def yml():
    """
    get yml content from a docker-compose registry 
    """
    item_id = loads(request.data)['id']
    response = requests.get(COMPOSE_REGISTRY + '/api/v1/yml', \
        params={'id': item_id}, headers={'x-key': 'default'})
    return jsonify(response.json())


@app.route(API_V1 + "_create", methods=['POST'])
@requires_auth
def create():
    """
    docker-compose create
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        name = loads(request.data)["id"]
        get_project_with_name(YML_PATH, name).create()
        return jsonify(command='create')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "start", methods=['POST'])
@requires_auth
def start():
    """
    docker-compose start
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]

        name = loads(request.data)["id"]
        get_project_with_name(YML_PATH, name).start()
        return jsonify(command='start')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "stop", methods=['POST'])
@requires_auth
def stop():
    """
    docker-compose stop
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        name = loads(request.data)["id"]
        get_project_with_name(YML_PATH, name).stop()
        return jsonify(command='stop')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "down", methods=['POST'])
@requires_auth
def down():
    """
    docker-compose down
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        name = loads(request.data)["id"]
        get_project_with_name(YML_PATH, name).down(ImageType.none, None)
        return jsonify(command='down')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "restart", methods=['POST'])
@requires_auth
def restart():
    """
    docker-compose restart
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        name = loads(request.data)["id"]
        get_project_with_name(YML_PATH, name).restart()
        return jsonify(command='restart')
    else:
        return "unauthorized", 403

@app.route(API_V1 + "logs/<name>", defaults={'limit': "all"}, methods=['GET'])
@app.route(API_V1 + "logs/<name>/<int:limit>", methods=['GET'])
def logs(name, limit):
    """
    docker-compose logs
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        lines = {}
        for k in get_project_with_name(YML_PATH, name).containers(stopped=True):
            lines[k.name] = k.logs(timestamps=True, tail=limit).decode("utf8").split('\n')

        return jsonify(logs=lines)
    else:
        return "unauthorized", 403

@app.route(API_V1 + "logs/<name>/<container_id>", defaults={'limit': "all"}, methods=['GET'])
@app.route(API_V1 + "logs/<name>/<container_id>/<int:limit>", methods=['GET'])
def container_logs(name, container_id, limit):
    """
    docker-compose logs of a specific container
    """
    if("username" in session):
        YML_PATH = "./users/" + session["username"]
        project = get_project_with_name(YML_PATH, name)
        container = get_container_from_id(project.client, container_id)
        lines = container.logs(timestamps=True, tail=limit).decode("utf8").split('\n')
        return jsonify(logs=lines)
    else:
        return "unauthorized", 403

@app.route(API_V1 + "host", methods=['GET'])
def host():
    """
    docker host info
    """
    if('username' in session):
        host_value = os.getenv('DOCKER_HOST')

        return jsonify(host=host_value, workdir="/" + session['username'] + "/")

    else:
        return "unauthorized", 403
    

@app.route(API_V1 + "compose-registry", methods=['GET'])
def compose_registry():
    """
    docker compose registry
    """
    return jsonify(url = COMPOSE_REGISTRY)

@app.route(API_V1 + "web_console_pattern", methods=['GET'])
def get_web_console_pattern():
    """
    forward WEB_CONSOLE_PATTERN env var from server to spa
    """
    sWebConsolePattern = os.getenv('WEB_CONSOLE_PATTERN')
    if(sWebConsolePattern == None):
        return jsonify(web_console_pattern="/web-console/?cid={containerName}&cmd={command}")
    else:
        return jsonify(web_console_pattern=sWebConsolePattern)

@app.route(API_V1 + "health", methods=['GET'])
def health():
    """
    docker health
    """
    return jsonify(info())

@app.route(API_V1 + "host", methods=['POST'])
@requires_auth
def set_host():
    """
    set docker host
    """
    new_host = loads(request.data)["id"]
    if new_host is None:
        if 'DOCKER_HOST' in os.environ:
            del os.environ['DOCKER_HOST']
        return jsonify()
    else:
        os.environ['DOCKER_HOST'] = new_host
        return jsonify(host=new_host)

@app.route(API_V1 + "authentication", methods=['GET'])
def authentication():
    """
    check if basic authentication is enabled
    """
    return jsonify(enabled=authentication_enabled())

@app.route(API_V1 + "authentication", methods=['DELETE'])
@requires_auth
def disable_basic_authentication():
    """
    disable basic authentication
    """
    disable_authentication()
    return jsonify(enabled=False)

@app.route(API_V1 + "authentication", methods=['POST'])
@requires_auth
def enable_basic_authentication():
    """
    set up basic authentication
    """
    data = loads(request.data)
    set_authentication(data["username"], data["password"])
    return jsonify(enabled=True)

# static resources
@app.route("/")
def index():
    """
    index.html
    """
    if 'username' in session:
        return render_template('index.html', username=session['username'])
    else:
        with open('github.json') as json_data_file:
            oCreds = loads(json_data_file.read())
        return render_template('login.html', client_id=oCreds["client_id"] )

# login
@app.route("/oauth2callback")
def login():
    with open('github.json') as json_data_file:
        oCreds = loads(json_data_file.read())
    sCode = request.args.get('code')
    print("Code was", sCode )
    dictToSend = {'client_id':oCreds["client_id"], 'client_secret':oCreds["client_secret"], 'code': sCode}
    dictHeaders = {"Accept":"application/json"}
    res = requests.post('https://github.com/login/oauth/access_token', json=dictToSend, headers=dictHeaders)
    print('response from server:',res.text)
    dictFromServer = res.json()
    dictHeaders["Authorization"] = "token " + dictFromServer["access_token"]
    resUser = requests.get("https://api.github.com/user", headers=dictHeaders)
    print('response from server:',resUser.text)
    dictFromServer = resUser.json()
    sUser = dictFromServer["login"].lower()
    session["username"] = sUser

    if(not os.path.isdir("./users")):
        os.mkdir("./users")
    if(not os.path.isdir("./users/" + sUser )):
        os.mkdir("./users/" + sUser)
        with open("./users/" + sUser + "/info.json", "w") as oInfo:
            oInfo.write(resUser.text) 
    return redirect(url_for('index'))

## basic exception handling

@app.errorhandler(requests.exceptions.ConnectionError)
def handle_connection_error(err):
    """
    connection exception handler
    """
    return 'docker host not found: ' + str(err), 500

@app.errorhandler(docker.errors.DockerException)
def handle_docker_error(err):
    """
    docker exception handler
    """
    return 'docker exception: ' + str(err), 500

@app.errorhandler(Exception)
def handle_generic_error(err):
    """
    default exception handler
    """
    traceback.print_exc()
    return 'error: ' + str(err), 500

# run app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5001, debug=False, threaded=True)
