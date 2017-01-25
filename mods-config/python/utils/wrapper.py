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

LOG_NAME = freepydius._LOG_FILE
CONFIG = freepydius._CONFIG_FILE
