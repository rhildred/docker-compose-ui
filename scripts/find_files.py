"""
find docker-compose.yml files
"""

import fnmatch
import os

def find_yml_files(path):
    """
    find docker-compose.yml files in path
    """
    matches = {}

    for item in os.listdir(path):
        sFolder = os.path.join(path, item)
        if os.path.isdir(sFolder):
            aFiles = os.listdir(sFolder)
            if 'docker-compose.yml' in aFiles or 'docker-compose.yaml' in aFiles:
                sKey = sFolder.split('/')[-1]
                matches[sKey] = sFolder
    return matches


def get_readme_file(path):
    """
    find case insensitive readme.md in path and return the contents
    """

    readme = None

    for file in os.listdir(path):
        if file.lower() == "readme.md" and os.path.isfile(os.path.join(path, file)):
            file = open(os.path.join(path, file))
            readme = file.read()
            file.close()
            break

    return readme

def get_logo_file(path):
    """
    find case insensitive logo.png in path and return the contents
    """

    logo = None

    for file in os.listdir(path):
        if file.lower() == "logo.png" and os.path.isfile(os.path.join(path, file)):
            file = open(os.path.join(path, file), "rb")
            logo = file.read()
            file.close()
            break

    return logo
