#!/usr/bin/python
"""wrapper/helper for freepydius common util implementation(s)."""

import sys
sys.path.append('../')  # nopep8
import freepydius
import radiusd


def convert_user(name):
    """convert user."""
    return freepydius._convert_user_name(name)


def convert_mac(mac):
    """convert mac."""
    return freepydius._convert_mac(mac)


def encrypt(value, key):
    """encrypt a value."""
    return freepydius._encrypt(value, key)


def decrypt(value, key):
    """decrypt a value."""
    return freepydius._decrypt(value, key)

PORT = freepydius.PORT_BYPASS_KEY
LOG_FILE = freepydius._LOG_FILE_NAME
LOG_NAME = freepydius._LOG_FILE
CONFIG = freepydius._CONFIG_FILE
CONFIG_NAME = freepydius._CONFIG_FILE_NAME
USERS = freepydius.USER_KEY
MACS = freepydius.MAC_KEY
ATTR = freepydius.ATTR_KEY
