#!/usr/bin/python
"""Provides configuration management/handling for managing freeradius."""
import argparse
import os
import shutil
import hashlib
import json
import subprocess
import wrapper
import random
import string
import filecmp
import pwd
import urllib.parse
import urllib.request
import datetime

# user setup
CHARS = string.ascii_uppercase + string.ascii_lowercase + string.digits

# arguments
CHECK = "check"
ADD_USER = "useradd"
BUILD = "build"
GEN_PSWD = "password"

# file handling
FILE_NAME = wrapper.CONFIG_NAME
PREV_FILE = FILE_NAME + ".prev"
USER_FOLDER = "users/"
PYTHON_MODS = "mods-config/python"

# env vars
FREERADIUS_REPO = "FREERADIUS_REPO"
NETCONFIG = "NETCONF"
PHAB_SLUG = "PHAB_SLUG"
PHAB_TOKEN = "PHAB_TOKEN"
PHAB_HOST = "PHAB_HOST"
LOG_FILES = "LOG_FILES"
WORK_DIR = "WORKING_DIR"
LEASE_PASTE = "PHAB_LEASE_PASTE"
FLAG_MGMT_LEASE = "LEASE_MGMT"
IS_SECONDARY = "IS_SECONDARY"
OFF_DAYS = "OFF_DAYS"
SYNAPSE_FEED = "SYNAPSE_FEED"


class Env(object):
    """Environment definition."""

    def __init__(self):
        """Init the instance."""
        self.freeradius_repo = None
        self.backing = {}
        self.net_config = None
        self.phab_token = None
        self.phab_slug = None
        self.phab = None
        self.log_files = None
        self.working_dir = None
        self.phab_leases = None
        self.mgmt_ips = None
        self.is_secondary = None
        self.off_days = None
        self.synapse_feed = None

    def add(self, key, value):
        """Add a key, sets into environment."""
        os.environ[key] = value
        if key == FREERADIUS_REPO:
            self.freeradius_repo = value
        elif key == NETCONFIG:
            self.net_config = value
        elif key == PHAB_SLUG:
            self.phab_slug = value
        elif key == PHAB_TOKEN:
            self.phab_token = value
        elif key == PHAB_HOST:
            self.phab = value
        elif key == LOG_FILES:
            self.log_files = value
        elif key == WORK_DIR:
            self.working_dir = value
        elif key == LEASE_PASTE:
            self.phab_leases = value
        elif key == FLAG_MGMT_LEASE:
            self.mgmt_ips = value
        elif key == IS_SECONDARY:
            self.is_secondary = value
        elif key == OFF_DAYS:
            self.off_days = value
        elif key == SYNAPSE_FEED:
            self.synapse_feed = value

    def _error(self, key):
        """Print an error."""
        print("{} must be set".format(key))

    def _in_error(self, key, value):
        """Indicate on error."""
        if value is None:
            self._error(key)
            return 1
        else:
            return 0

    def validate(self, full=False):
        """Validate the environment setup."""
        errors = 0
        errors += self._in_error(FREERADIUS_REPO, self.freeradius_repo)
        if full:
            errors += self._in_error(NETCONFIG, self.net_config)
            errors += self._in_error(PHAB_SLUG, self.phab_slug)
            errors += self._in_error(PHAB_TOKEN, self.phab_token)
            errors += self._in_error(PHAB_HOST, self.phab)
            errors += self._in_error(LOG_FILES, self.log_files)
            errors += self._in_error(WORK_DIR, self.working_dir)
            errors += self._in_error(LEASE_PASTE, self.phab_leases)
            errors += self._in_error(FLAG_MGMT_LEASE, self.mgmt_ips)
            errors += self._in_error(IS_SECONDARY, self.is_secondary)
            errors += self._in_error(OFF_DAYS, self.off_days)
            errors += self._in_error(SYNAPSE_FEED, self.synapse_feed)
        if errors > 0:
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


def get_not_cruft(users):
    """Not-cruft users."""
    not_cruft = []
    for flag in ["nocruft", "secondary"]:
        attrs = get_user_attr(users, flag)
        for u in attrs:
            if attrs[u] == "1":
                not_cruft.append(u)
    return not_cruft


def get_file_hash(file_name):
    """Get a sha256 hash of a file."""
    with open(file_name, 'rb') as f:
        sha = hashlib.sha256(f.read())
        return sha.hexdigest()


def _get_exclude(name):
    """Define an rsync exclude."""
    return '--exclude={}'.format(name)


def call(cmd, error_text, working_dir=None, ins=None):
    """Call for subproces/ing."""
    std_in = None
    if ins is not None:
        std_in = subprocess.PIPE
    p = subprocess.Popen(cmd, cwd=working_dir, stdin=std_in)
    if ins is not None:
        p.stdin.write(ins.encode('utf-8'))
        out, err = p.communicate()
        if out is not None:
            print(out.decode('utf-8'))
        if err is not None:
            print(err.decode('utf-8'))
        return
    p.wait()
    if p.returncode != 0:
        print("unable to {}".format(error_text))
        exit(1)


def _get_utils(env):
    """Get utils location."""
    return os.path.join(env.freeradius_repo, PYTHON_MODS, "utils")


def compose(env):
    """Compose the configuration."""
    offset = _get_utils(env)
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


def gen_pass(dump, key):
    """Generate password for a user account."""
    if key is None:
        print("no key available")
        exit(1)
    rands = ''.join(random.choice(CHARS) for _ in range(64))
    encoded = wrapper.encrypt(rands, key)
    raw = wrapper.decrypt(encoded, key)
    if rands != raw:
        print("encrypt/decrypt problem")
        exit(1)
    if dump:
        print("password:")
        print(raw)
        print("config file encoded")
        print(encoded)
    else:
        return (raw, encoded)


def add_user(key):
    """Add a new user definition."""
    print("please enter the user name:")
    named = input()
    print("please enter the phabricator name to alias (blank to skip)")
    aliased = input()
    alias = ""
    if aliased is not None and len(aliased) > 0:
        alias = "u_obj.attrs = [common.ALIASED + '{}']".format(aliased)
    passes = gen_pass(False, key)
    raw = passes[0]
    password = passes[1]
    user_definition = """
import __config__
import common

u_obj = __config__.Assignment()
u_obj.password = '{}'
u_obj.vlan = None
u_obj.group = None
{}
""".format(password, alias)
    with open(os.path.join(USER_FOLDER, "user_" + named + ".py"), 'w') as f:
        f.write(user_definition.strip())
    print("{} was created with a password of {}".format(named, raw))


def post_get_data(env, endpoint, data):
    """Post to get data."""
    data["api.token"] = env.phab_token
    payload = urllib.parse.urlencode(data)
    r = urllib.request.urlopen(env.phab + "/api/" + endpoint,
                               data=payload.encode("utf-8"))
    resp = r.read()
    print(resp)
    return resp


def post_content(env, page, title, content):
    """Post content to a wiki page."""
    data = {"slug": env.phab_slug + page,
            "title": title,
            "content": content}
    post_get_data(env, "phriction.edit", data)


def get_user_attr(user, key):
    """Get user attributes."""
    attributes = {}
    for u in user:
        attrs = [x for x in user[u][wrapper.ATTR] if x.startswith(key + "=")]
        if len(attrs) == 1:
            attributes[u] = attrs[0].split("=")[1]
    return attributes


def get_user_resolutions(user):
    """Get user resolutions."""
    return get_user_attr(user, "alias")


def resolve_user(user_name, user_resolutions):
    """Resolve user names."""
    user = user_name
    if user in user_resolutions:
        user = user_resolutions[user]
    else:
        user = user_name.split(".")[1]
    return "[@{}](/p/{})".format(user, user)


def update_wiki(env, running_config):
    """Update wiki pages with config information for VLANs."""
    defs = {}
    with open(running_config, 'r') as f:
        defs = json.loads(f.read())
    users = defs[wrapper.USERS]
    vlans = {}
    for user in sorted(users.keys()):
        vlan_parts = user.split(".")
        vlan = vlan_parts[0].upper()
        if vlan not in vlans:
            vlans[vlan] = []
        vlans[vlan].append(user)
    first = True
    outputs = [("vlan", "user"), ("---", "---")]
    user_resolved = get_user_resolutions(users)
    for vlan in sorted(vlans.keys()):
        if not first:
            outputs.append(("-", "-"))
        first = False
        for user in vlans[vlan]:
            user_name = resolve_user(user, user_resolved)
            outputs.append((vlan, user_name))
    content = _create_header()
    for output in outputs:
        content = content + "| {} | {} |\n".format(output[0], output[1])
    post_content(env, "vlans", "VLANs", content)


def update_leases(env, running_config):
    """Update the wiki with lease information."""
    leases = {}
    lease_unknown = []
    statics = []
    mgmts = []
    try:
        data = {
                "constraints[phids][0]": env.phab_leases,
                "attachments[content]": 1
                }
        resp = post_get_data(env, "paste.search", data)
        data = json.loads(resp)["result"]["data"][0]
        raw = data["attachments"]["content"]["content"]
        for line in raw.split("\n"):
            if len(line.strip()) == 0:
                continue
            try:
                parts = line.split(" ")
                time = parts[0]
                mac = wrapper.convert_mac(parts[1])
                ip = parts[2]
                init = [ip]
                is_static = "dynamic"
                if time == "static":
                    is_static = "static"
                    statics.append(mac)
                else:
                    lease_unknown.append(mac)
                if ip.startswith(env.mgmt_ips):
                    mgmts.append(mac)
                if mac not in leases:
                    leases[mac] = []
                leases[mac].append("{} ({})".format(ip, is_static))
            except Exception as e:
                print("error parsing line: " + line)
                print(str(e))
                continue
    except Exception as e:
        print("error parsing leases.")
        print(str(e))
    conf = None
    with open(running_config, 'r') as f:
        conf = json.loads(f.read())[wrapper.USERS]
    user_resolutions = get_user_resolutions(conf)
    for user in conf:
        user_name = resolve_user(user, user_resolutions)
        macs = conf[user][wrapper.MACS]
        port = conf[user][wrapper.PORT]
        auto = conf[user][wrapper.WILDCARD]
        for lease in leases:
            port_by = lease in port
            leased = lease in macs
            is_wildcard = False
            for wild in auto:
                if is_wildcard:
                    break
                for l in leases[lease]:
                    if wild in l:
                        is_wildcard = True
                        break
            if leased or port_by or is_wildcard:
                leases[lease].append(user_name)
                if lease in lease_unknown:
                    while lease in lease_unknown:
                        lease_unknown.remove(lease)
            if port_by:
                leases[lease].append("port-bypass")
            if is_wildcard and not port_by:
                leases[lease].append("auto-assigned")

    def is_mgmt(lease):
        """Check if a management ip."""
        return lease in mgmts

    def is_normal(lease):
        """Check if a 'normal' ip."""
        return not is_mgmt(lease)
    content = _create_header()
    content = content + _create_lease_table(env,
                                            leases,
                                            lease_unknown,
                                            statics,
                                            "normal",
                                            is_normal)
    content = content + _create_lease_table(env,
                                            leases,
                                            lease_unknown,
                                            statics,
                                            "management",
                                            is_mgmt)
    post_content(env, "leases", "Leases", content)


def _create_lease_table(env, leases, unknowns, statics, header, filter_fxn):
    """Create a lease wiki table output."""
    outputs = []
    outputs.append(["mac", "attributes"])
    outputs.append(["---", "---"])
    report_objs = []
    for lease in sorted(leases.keys()):
        if not filter_fxn(lease):
            continue
        current = leases[lease]
        attrs = []
        lease_value = lease
        for obj in sorted(set(current)):
            attrs.append(obj)
        if lease in unknowns and lease not in statics:
            report_objs.append(lease_value)
            lease_value = "**{}**".format(lease_value)
        cur_out = [lease_value]
        cur_out.append(" ".join(attrs))
        outputs.append(cur_out)
    content = "\n\n# " + header + "\n\n----\n\n"
    for output in outputs:
        content = content + "| {} | {} |\n".format(output[0],
                                                   output[1])
    if len(report_objs) > 0:
        _smirc("unknown leases (" + header + "): " + ", ".join(report_objs))
    return content


def _smirc(text):
    """Sending via smirc."""
    import smirc
    print("smirc: {}".format(text))
    try:
        smirc.run(arguments=[text])
    except smirc.SMIRCError as e:
        print("smirc error")
        print(str(e))


def _get_date_offset(days):
    """Create a date-offset with formatting."""
    return (datetime.date.today() -
            datetime.timedelta(days)).strftime("%Y-%m-%d")


def call_wrapper(env, method, added):
    """Call the report-wrapper implementation."""
    base = _get_utils(env)
    cmd = [os.path.join(base, "report-wrapper.sh"), method]
    for x in added:
        cmd.append(x)
    call(cmd, "report wrapper", working_dir=base)


def execute_report(env, report, out_type, skip_lines, out_file, fxn="report"):
    """Execute a report."""
    call_wrapper(env, fxn, [
           report,
           out_type,
           str(skip_lines),
           out_file])
    with open(out_file, 'r') as f:
        return f.read()


def delete_if_exists(file_name):
    """Delete a file if it exists."""
    if os.path.exists(file_name):
        os.remove(file_name)


def _create_header():
    """Create a report header."""
    return """
> this page is maintained by a bot
> do _NOT_ edit it here
"""


def optimize_config(env, optimized_configs, running_config):
    """Check any configuration optimizations."""
    opt_conf = {}
    # need to merge these into a single configuration
    for optimized in optimized_configs:
        for user in optimized:
            if user not in opt_conf:
                opt_conf[user] = []
            for mac in optimized[user]:
                if mac not in opt_conf[user]:
                    opt_conf[user].append(mac)
    run_conf = None
    with open(running_config, 'r') as f:
        run_conf = json.loads(f.read())
    suggestions = []
    users = run_conf[wrapper.USERS]
    not_cruft = get_not_cruft(users)
    for user in users:
        if user not in opt_conf:
            if user not in not_cruft:
                suggestions.append("drop user {}".format(user))
    cruft = []
    for user in opt_conf:
        if user not in users:
            continue
        macs = users[user][wrapper.MACS]
        for mac in opt_conf[user]:
            if mac in macs:
                macs.remove(mac)
        for m in macs:
            if user not in not_cruft:
                cruft.append((user, m))
    content = _create_header()
    content += "\n"
    if len(cruft) > 0:
        cruft = sorted(cruft)
        cruft.insert(0, ("---", "---"))
        cruft.insert(0, ("user", "mac"))
        for item in cruft:
            content += "| {} | {} |\n".format(item[0], item[1])
    else:
        content += "nothing to cleanup"
    post_content(env, "cruft", "Cruft", content)
    if len(suggestions) > 0:
        _smirc("\n".join(sorted(suggestions)))


def daily_report(env, running_config):
    """Write daily reports."""
    today = datetime.datetime.now()
    week = str(today.weekday())
    if week in env.off_days.split(" "):
        return
    hour = today.hour
    report_indicator = env.working_dir + "indicator"
    if hour != 9:
        delete_if_exists(report_indicator)
        return
    if os.path.exists(report_indicator):
        return
    print('completing daily reports')
    with open(report_indicator, 'w') as f:
        f.write("")
    reports = {}
    titles = {}
    optimized_confs = []
    for item in range(1, 11):
        date_offset = _get_date_offset(item)
        path = os.path.join(env.log_files,
                            wrapper.LOG_FILE) + "." + date_offset
        if not os.path.exists(path):
            continue
        print(date_offset)
        call_wrapper(env, "store", [path])
        for report in [("failures", "Rejections")]:
            output_file = env.working_dir + report[0]
            report_name = report[0]
            titles[report_name] = report[1]
            if report_name not in reports:
                reports[report_name] = _create_header()
            use_markdown = """

### {}

---

""".format(date_offset)
            use_markdown += execute_report(env,
                                           report_name,
                                           "markdown",
                                           1,
                                           output_file)
            reports[report_name] += use_markdown
            opt_file = env.working_dir + "optimized.json"
            optimized_config = execute_report(env,
                                              "optimized",
                                              "n/a",
                                              0,
                                              opt_file,
                                              "optimize")
            opt_conf = json.loads(optimized_config)
            optimized_confs.append(opt_conf)

    for report in reports:
        html = reports[report]
        title = titles[report]
        post_content(env, title.lower(), title, html)
    update_leases(env, running_config)
    optimize_config(env, optimized_confs, running_config)


def _feed(env, text):
    """Send a feed message to phabricator."""
    import feedmepy
    message = feedmepy.FeedMe()
    code = message.now(text,
                       room=env.synapse_feed,
                       url=env.phab,
                       token=env.phab_token)
    print("feedme: {}".format(str(code)))


def build():
    """Build and apply a user configuration."""
    env = _get_vars("/etc/environment")
    secondary = env.is_secondary and os.path.exists(env.is_secondary)
    env.validate(full=True)
    os.chdir(env.net_config)
    compose(env)
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
        git = "latest commit"
        git_indicator = env.working_dir + "git"
        if os.path.exists(git_indicator):
            with open(git_indicator, 'r') as f:
                git = f.read().strip()
        status = "ready"
        if secondary:
            status = "secondary"
        _smirc("{} -> {} ({})".format(status, git, hashed))
        _feed(env, "radius configuration updated")
    if not secondary:
        daily_report(env, run_config)


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
            output = json.dumps(j,
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
                        choices=[CHECK, ADD_USER, BUILD, GEN_PSWD],
                        default=CHECK)
    parser.add_argument('--key', type=str)
    args = parser.parse_args()
    key = None
    if args.key:
        key = wrapper.convert_key(args.key)
    if args.action == CHECK:
        check()
    elif args.action == BUILD:
        build()
    elif args.action == ADD_USER:
        add_user(key)
    elif args.action == GEN_PSWD:
        gen_pass(True, key)

if __name__ == "__main__":
    main()
