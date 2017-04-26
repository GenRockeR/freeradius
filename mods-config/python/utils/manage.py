#!/usr/bin/python
""" Provides configuration management/handling for managing freeradius."""
import argparse
import os
import shutil
import hashlib
import json
import base64
import subprocess
import wrapper

# arguments
CHECK = "check"
ADD_USER = "useradd"
BUILD = "build"

# file handling
FILE_NAME = wrapper.CONFIG_NAME
PREV_FILE = FILE_NAME + ".prev"

# env vars
FREERADIUS_REPO = "FREERADIUS_REPO"


class Env(object):
    """ Environment definition. """
    def __init__(self):
        """ Init the instance. """
        self.freeradius_repo = None
        self.backing = {}

    def add(self, key, value):
        """ Add a key, sets into environment. """
        os.environ[key] = value
        if key == FREERADIUS_REPO:
            self.freeradius_repo = value

    def _error(self, key):
        """ Print an error. """
        print("{} must be set".format(key))

    def validate(self):
        """ Validate the environment setup. """
        validation_error = False
        if self.freeradius_repo is None:
            self._error(FREERADIUS_REPO)
            validation_error = True
        if validation_error:
            exit(1)


def _get_vars():
    """ Get the environment setup. """
    result = Env()
    with open(os.path.expandvars("$HOME/.config/epiphyte/env"), 'r') as env:
        for line in env.readlines():
            if line.startswith("#"):
                continue
            parts = line.split("=")
            if len(parts) > 1:
                key = parts[0]
                val = "=".join(parts[1:]).strip()
                if val.startswith('"') and val.endswith('"'):
                    val = val[1:len(val) - 1]
                result.add(key, os.path.expandvars(val))
    result.validate()
    return result


def get_file_hash(file_name):
    """Get a sha256 hash of a file."""
    with open(file_name, 'rb') as f:
        sha = hashlib.sha256(f.read())
        return sha.hexdigest()


def _get_exclude(name):
    """ Define an rsync exclude."""
    return '--exclude={}'.format(name)


def compose(env):
    """Compose the configuration."""
    offset = os.path.join(env.freeradius_repo, "mods-config/python/utils")
    rsync = ["rsync",
             "-aczv",
             "users/",
             os.path.join(offset, "users/"),
             "--delete-after",
             _get_exclude("*.pyc"),
             _get_exclude("README.md"),
             _get_exclude("__init__.py"),
             _get_exclude("__config__.py")]
    subprocess.call(rsync)
    here = os.getcwd()
    composition = ["python2.7",
                   "config_compose.py",
                   "--output", os.path.join(here, FILE_NAME)]
    p = subprocess.Popen(composition, cwd=offset)
    p.wait()
    if p.returncode != 0:
        print("unable to compose configuration")
        exit(1)


def _base_json(obj):
    """ Convert 'pass' keys to base64 'pass64' keys. """
    if isinstance(obj, dict):
        res = {}
        for key in obj.keys():
            new_obj = obj[key]
            if key == "pass":
                b = new_obj.encode("utf-8")
                res[key + "64"] = base64.b64encode(b).decode("utf-8")
            else:
                new_obj = _base_json(new_obj)
                res[key] = new_obj
        return res
    else:
        if isinstance(obj, list):
            res = []
            for key in obj:
                res.append(_base_json(key))
            return res
        else:
            return obj


def check():
    """ Check composition. """
    env =_get_vars()
    if os.path.exists(FILE_NAME):
        shutil.copyfile(FILE_NAME, PREV_FILE)
    compose(env)
    if os.path.exists(FILE_NAME):
        print(get_file_hash(FILE_NAME))
        output = None
        with open(FILE_NAME, 'r') as f:
            j = json.loads(f.read())
            output = json.dumps(_base_json(j),
                                sort_keys=True,
                                indent=4,
                                separators=(',', ': '))
        with open(FILE_NAME, 'w') as f:
            f.write(output)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument('--action',
                        choices=[CHECK, ADD_USER, BUILD],
                        default=CHECK)
    args = parser.parse_args()
    if args.action == CHECK:
        check()
    elif args.action == BUILD:
        build()
    elif args.action == ADD_USER:
        add_user()

if __name__ == "__main__":
    main()
