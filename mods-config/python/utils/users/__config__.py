#!/usr/bin/python
"""configuration base."""
from datetime import datetime
import re

PASSWORD_LENGTH = 32


def is_mac(value):
    """validate if something appears to be a mac."""
    valid = False
    if len(value) == 12:
        valid = True
        for c in value:
            if c not in ['0',
                         '1',
                         '2',
                         '3',
                         '4',
                         '5',
                         '6',
                         '7',
                         '8',
                         '9',
                         'a',
                         'b',
                         'c',
                         'd',
                         'e',
                         'f']:
                valid = False
                break
    return valid


class VLAN(object):
    """VLAN definition."""

    def __init__(self, name, number):
        """init the instance."""
        self.name = name
        self.num = number
    def check(self):
        if self.name is None or len(self.name) == 0 or not isinstance(self.num, int):
            return False
        return True


class Blacklist(object):
    """Blacklist object."""

    def __init__(self, obj):
        self.obj = obj
    def check(self):
        if self.obj is None or len(self.obj) == 0:
            return False
        return True


class Assignment(object):
    """assignment object."""
    def __init__(self):
        self.macs = []
        self.password = ""
        self.bypass = []
        self.vlan = None
        self.disable = {}
        self.no_login = False
        self.attrs = None
        self.expires = None
        self.expired = False

    def _compare_date(self, value, regex, today):
        """compare date."""
        matches = regex.findall(value)
        for match in matches:
            as_date = datetime.strptime(match, '%Y-%m-%d')
            return as_date < today
        return None

    def report(self, cause):
        """report an issue."""
        print cause
        return False

    def check(self):
        """check the assignment definition."""
        today = datetime.now()
        today = datetime(today.year, today.month, today.day)
        regex = re.compile(r'\d{4}[-/]\d{2}[-/]\d{2}')
        if self.expires is not None:
            res = self._compare_date(self.expires, regex, today)
            if res is not None:
                self.expired = res
            else:
                return self.report("invalid expiration")
        if self.vlan is None or len(self.vlan) == 0:
            return self.report("no vlan assigned")
        if self.macs is None or len(self.macs) == 0:
            return self.report("no macs listed")
        for mac in self.macs:
            if not is_mac(mac):
                return self.report("invalid mac")
        if self.password is None or len(self.password) < 32:
            return self.report("no or short password")
        if not self.password.isalnum():
            return self.report("only alphanumerics supported in passwords")
        if self.bypass is not None and len(self.bypass) > 0:
            for mac in self.bypass:
                if not is_mac(mac):
                    return self.report("invalid bypass mac")
        if len(self.macs) != len(set(self.macs)):
            return self.report("macs not unique")
        if self.disable is not None and len(self.disable) > 0:
            if isinstance(self.disable, dict):
                for key in self.disable.keys():
                    val = self.disable[key]
                    res = self._compare_date(val, regex, today)
                    if res is not None:
                        if res:
                            print("{0} has been time-disabled".format(key))
                            if key in self.bypass:
                                self.bypass.remove(key)
                            if key in self.macs:
                                self.macs.remove(key)
                    else:
                        return self.report("invalid MAC date")
        return True
