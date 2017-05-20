#!/usr/bin/python
"""composes the config from user definitions."""
import json
import argparse
import os
import users
import users.__config__
import wrapper
import importlib

# file indicators
IND_DELIM = "_"
USER_INDICATOR = "user" + IND_DELIM
VLAN_INDICATOR = "vlan" + IND_DELIM
BLKL_INDICATOR = "blacklist" + IND_DELIM


class ConfigMeta(object):
    """configuration meta information."""

    def __init__(self):
        """init the instance."""
        self.passwords = []
        self.macs = []
        self.bypasses = []
        self.vlans = []
        self.all_vlans = []
        self.blacklist = []
        self.user_name = []
        self.vlan_users = []
        self.attrs = []

    def password(self, password):
        """password group validation(s)."""
        if password in self.passwords:
            print "password duplicated"
            exit(-1)
        self.passwords.append(password)

    def bypassed(self, macs):
        """bypass management."""
        for mac in macs:
            if mac in self.bypasses:
                print "already bypassed"
                exit(-1)
            self.bypasses.append(mac)

    def user_macs(self, macs):
        """user+mac combos."""
        self.macs = self.macs + macs
        self.macs = list(set(self.macs))

    def attributes(self, attrs):
        """set attributes."""
        self.attrs = self.attrs + attrs
        self.attrs = list(set(self.attrs))

    def verify(self):
        """verify meta data."""
        for mac in self.macs:
            if mac in self.bypasses:
                print "mac is globally bypassed: " + mac
                exit(-1)
        for mac in self.bypasses:
            if mac in self.macs:
                print "mac is user assigned: " + mac
                exit(-1)
        if len(set(self.vlans)) != len(set(self.all_vlans)):
            print "unused vlans detected"
            exit(-1)
        if len(set(self.blacklist)) != len(self.blacklist):
            print "duplicate blacklisted items"
            exit(-1)
        for item in self.blacklist:
            if item not in self.user_name and \
               item not in self.macs and \
               item not in self.vlans and \
               item not in self.bypasses and \
               item not in self.vlan_users and \
               item not in self.attrs:
                    print "unknown entity to blacklist: " + item
                    exit(-1)

    def vlan_user(self, vlan, user):
        """indicate a vlan was used."""
        self.vlans.append(vlan)
        self.vlan_users.append(vlan + "." + user)
        self.user_name.append(user)


def _create_obj(macs, password, attrs, port_bypassed):
    """create a user definition."""
    return {wrapper.freepydius.MAC_KEY: macs,
            wrapper.freepydius.PASS_KEY: password,
            wrapper.freepydius.ATTR_KEY: attrs,
            wrapper.freepydius.PORT_BYPASS_KEY: port_bypassed}


def _get_mod(name):
    """import the module dynamically."""
    return importlib.import_module("users." + name)


def _load_objs(name, typed):
    mod = _get_mod(name)
    for key in dir(mod):
        obj = getattr(mod, key)
        if not isinstance(obj, typed):
            continue
        yield obj


def _get_by_indicator(indicator):
    """get by a file type indicator."""
    return [x for x in sorted(users.__all__) if x.startswith(indicator)]


def _common_call(common, method, entity):
    """make a common mod call."""
    obj = entity
    if common is not None and method in dir(common):
        call = getattr(common, method)
        if call is not None:
            obj = call(obj)
    return obj


def _process(output):
    """process the composition of users."""
    common_mod = None
    try:
        common_mod = _get_mod("common")
        print "loaded common definitions..."
    except:
        print "defaults only..."
    user_objs = {}
    vlans = None
    blacklist = []
    bypass_objs = {}
    meta = ConfigMeta()
    for v_name in _get_by_indicator(VLAN_INDICATOR):
        print "loading vlan..." + v_name
        for obj in _load_objs(v_name, users.__config__.VLAN):
            if vlans is None:
                vlans = {}
            if not obj.check():
                exit(-1)
            num_str = str(obj.num)
            for vk in vlans.keys():
                if num_str == vlans[vk]:
                    print "vlan number defined multiple times..."
                    exit(-1)
            vlans[obj.name] = num_str
    for b_name in _get_by_indicator(BLKL_INDICATOR):
        print "loading blacklist..." + b_name
        for obj in _load_objs(b_name, users.__config__.Blacklist):
            if not obj.check():
                exit(-1)
            blacklist.append(obj.obj)
    if vlans is None or blacklist is None:
        raise Exception("missing required config settings...")
    meta.all_vlans = vlans.keys()
    meta.blacklist = blacklist
    for f_name in _get_by_indicator(USER_INDICATOR):
        print "composing..." + f_name
        for obj in _load_objs(f_name, users.__config__.Assignment):
            obj = _common_call(common_mod, 'ready', obj)
            key = f_name.replace(USER_INDICATOR, "")
            if not key.isalnum():
                print "does not meet naming requirements..."
                exit(-1)
            vlan = obj.vlan
            if vlan not in vlans:
                raise Exception("no vlan defined for " + key)
            meta.vlan_user(vlan, key)
            fqdn = vlan + "." + key
            if not obj.check():
                print "did not pass check..."
                exit(-1)
            if obj.disabled:
                print "account is disabled or has expired..."
                continue
            macs = sorted(obj.macs)
            password = obj.password
            bypass = sorted(obj.bypass)
            port_bypassed = sorted(obj.port_bypass)
            attrs = []
            if obj.attrs:
                attrs = sorted(obj.attrs)
                meta.attributes(attrs)
            # meta checks
            meta.user_macs(macs)
            if not obj.inherits:
                meta.password(password)
            meta.bypassed(bypass)
            if fqdn in user_objs:
                raise Exception(fqdn + " previously defined")
            # use config definitions here
            if not obj.no_login:
                user_objs[fqdn] = _create_obj(macs,
                                              password,
                                              attrs,
                                              port_bypassed)
            if bypass is not None and len(bypass) > 0:
                for mac_bypass in bypass:
                    if mac_bypass in bypass_objs:
                        raise Exception(mac_bypass + " previously defined")
                    bypass_objs[mac_bypass] = vlan
    meta.verify()
    full = {}
    full[wrapper.freepydius.USER_KEY] = user_objs
    full[wrapper.freepydius.VLAN_KEY] = vlans
    full[wrapper.freepydius.BLCK_KEY] = blacklist
    full[wrapper.freepydius.BYPASS_KEY] = bypass_objs
    with open(output, 'w') as f:
        f.write(json.dumps(full, sort_keys=True,
                           indent=4, separators=[",", ": "]))


def main():
    """main entry."""
    success = False
    try:
        parser = argparse.ArgumentParser()
        parser.add_argument("--output", type=str, required=True)
        args = parser.parse_args()
        _process(args.output)
        success = True
    except Exception as e:
        print('unable to compose')
        print(str(e))
    if success:
        print("success")
        exit(0)
    else:
        print("failure")
        exit(1)


if __name__ == "__main__":
    main()
