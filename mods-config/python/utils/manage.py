#!/usr/bin/python
"""Provides configuration management/handling for managing freeradius."""
import argparse
import os
import shutil
import hashlib
import json
import base64
import subprocess
import wrapper
import random
import string
import filecmp
import pwd
import urllib2
import urllib

# user setup
CHARS = string.ascii_uppercase + string.ascii_lowercase + string.digits

# arguments
CHECK = "check"
ADD_USER = "useradd"
BUILD = "build"

# file handling
FILE_NAME = wrapper.CONFIG_NAME
PREV_FILE = FILE_NAME + ".prev"
USER_FOLDER = "users/"
PYTHON_MODS = "mods-config/python"

# env vars
FREERADIUS_REPO = "FREERADIUS_REPO"
NETCONFIG = "NETCONF"
SENDFILE = "SYNAPSE_SEND_FILE"
MBOT = "MATRIX_BOT"
USER_LOOKUPS = "USER_LOOKUPS"
PHAB_SLUG = "PHAB_SLUG"
PHAB_TOKEN = "PHAB_TOKEN"
PHAB_HOST = "PHAB_HOST"


class Env(object):
    """Environment definition."""

    def __init__(self):
        """Init the instance."""
        self.freeradius_repo = None
        self.backing = {}
        self.net_config = None
        self.send_file = None
        self.matrix_bot = None
        self.user_lookups = None
        self.phab_token = None
        self.phab_slug = None
        self.phab = None

    def add(self, key, value):
        """Add a key, sets into environment."""
        os.environ[key] = value
        if key == FREERADIUS_REPO:
            self.freeradius_repo = value
        elif key == NETCONFIG:
            self.net_config = value
        elif key == SENDFILE:
            self.send_file = value
        elif key == MBOT:
            self.matrix_bot = value
        elif key == USER_LOOKUPS:
            self.user_lookups = value
        elif key == PHAB_SLUG:
            self.phab_slug = value
        elif key == PHAB_TOKEN:
            self.phab_token = value
        elif key == PHAB_HOST:
            self.phab = value

    def _error(self, keys):
        """Print an error."""
        print("{} must be set".format(", ".join(keys)))

    def validate(self, full=False):
        """Validate the environment setup."""
        errors = []
        if self.freeradius_repo is None:
            errors.append(FREERADIUS_REPO)
        if full:
            if self.net_config is None:
                errors.append(NETCONFIG)
            if self.send_file is None:
                errors.append(SENDFILE)
            if self.matrix_bot is None:
                errors.append(MBOT)
            if self.user_lookups is None:
                errors.append(USER_LOOKUPS)
            if self.phab_slug is None:
                errors.append(PHAB_SLUG)
            if self.phab_token is None:
                errors.append(PHAB_TOKEN)
            if self.phab_token is None:
                errors.append(PHAB_HOST)
        if len(errors) > 0:
            self._error(errors)
            exit(1)


def _get_vars(env_file):
    """Get the environment setup."""
    result = Env()
    with open(os.path.expandvars(env_file), 'r') as env:
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
    """Define an rsync exclude."""
    return '--exclude={}'.format(name)


def call(cmd, error_text, working_dir=None):
    """Call for subprocessing."""
    p = subprocess.Popen(cmd, cwd=working_dir)
    p.wait()
    if p.returncode != 0:
        print("unable to {}".format(error_text))
        exit(1)


def compose(env):
    """Compose the configuration."""
    offset = os.path.join(env.freeradius_repo, PYTHON_MODS, "utils")
    rsync = ["rsync",
             "-aczv",
             USER_FOLDER,
             os.path.join(offset, USER_FOLDER),
             "--delete-after",
             _get_exclude("*.pyc"),
             _get_exclude("README.md"),
             _get_exclude("__init__.py"),
             _get_exclude("__config__.py")]
    call(rsync, "rsync user definitions")
    here = os.getcwd()
    composition = ["python2.7",
                   "config_compose.py",
                   "--output", os.path.join(here, FILE_NAME)]
    call(composition, "compose configuration", working_dir=offset)


def _base_json(obj):
    """Convert 'pass' keys to base64 'pass64' keys."""
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


def add_user():
    """Add a new user definition."""
    print("please enter the user name:")
    named = raw_input()
    raw = ''.join(random.choice(CHARS) for _ in range(64))
    password = base64.b64encode(raw).decode("utf-8")
    user_definition = """
import __config__
import common

u_obj = __config__.Assignment()
u_obj.password = '{}'
u_obj.vlan = None
""".format(password)
    with open(os.path.join(USER_FOLDER, "user_" + named + ".py"), 'w') as f:
        f.write(user_definition.strip())
    print("{} was created with a password of {}".format(named, raw))


def post_content(env, page, title, content):
    """Post content to a wiki page."""
    data = {"api.token": env.phab_token,
            "slug": env.phab_slug + page,
            "title": title,
            "content": content}
    payload = urllib.urlencode(data)
    r = urllib2.urlopen(env.phab + "/api/phriction.edit", data=payload)
    print(r.read())


def update_wiki(env, running_config):
    """Update wiki pages with config information for VLANs."""
    defs = {}
    with open(running_config, 'r') as f:
        defs = json.loads(f.read())
    users = defs["users"]
    vlans = {}
    for user in sorted(users.keys()):
        vlan_parts = user.split(".")
        vlan = vlan_parts[0].upper()
        user = ".".join(vlan_parts[1:])
        if vlan not in vlans:
            vlans[vlan] = []
        vlans[vlan].append(user)
    user_resolved = {x.split("=")[0]: x.split("=")[1]
                     for x in env.user_lookups.split(",")}
    first = True
    outputs = [("vlan", "user"), ("---", "---")]
    for vlan in sorted(vlans.keys()):
        if not first:
            outputs.append(("-", "-"))
        first = False
        for user in vlans[vlan]:
            user_name = user
            if user in user_resolved:
                user_name = user_resolved[user]
            outputs.append((vlan, "@" + user_name))
    content = """
> this page is managed externally do NOT edit it here.
> it is updated when the freeradius configuration changes.

---
"""
    for output in outputs:
        content = content + "| {} | {} |\n".format(output[0], output[1])
    post_content(env, "vlans", "VLANs", content)


def send_to_matrix(env, content):
    """Send a change notification to matrix."""
    cmd = []
    cmd.append(env.matrix_bot)
    cmd.append("oneshot")
    with open(env.send_file, 'w') as f:
        f.write("<html>")
        f.write(content)
        f.write("</html>")
    call(cmd, "sending to matrix")
    os.remove(env.send_file)


def daily_report(env):
    """Write daily reports."""
    pass


def build():
    """Build and apply a user configuration."""
    env = _get_vars("/etc/environment")
    env.validate(full=True)
    os.chdir(env.net_config)
    compose(env)
    if os.path.exists(env.send_file):
        os.remove(env.send_file)
    new_config = os.path.join(env.net_config, FILE_NAME)
    run_config = os.path.join(env.freeradius_repo, PYTHON_MODS, FILE_NAME)
    diff = filecmp.cmp(new_config, run_config)
    if not diff:
        print('change detected')
        shutil.copyfile(run_config, run_config + ".prev")
        shutil.copyfile(new_config, run_config)
        u = pwd.getpwnam("radiusd")
        os.chown(run_config, u.pw_uid, u.pw_gid)
        update_wiki(env, run_config)
        hashed = get_file_hash(FILE_NAME)
        send_to_matrix(env, "ready -> {}".format(hashed))
    daily_report(env)


def check():
    """Check composition."""
    env = _get_vars("$HOME/.config/epiphyte/env")
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
    parser.add_argument('action',
                        nargs='?',
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
