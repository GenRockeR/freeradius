#!/usr/bin/python
import argparse
import os
import sqlite3 as sl
import sys
import datetime
from ast import literal_eval as make_tuple
import wrapper


def _object(user, port, nas_ip, mac):
    return (user, port, nas_ip, wrapper.convert_mac(mac))

def _get(key, existing, tple):
    if existing:
        return existing
    if tple[0] == key:
        return tple[1]

def _report(conn, tracked):
    """Report on new entries as found."""
    curs = conn.cursor()
    curs.execute("""
CREATE TABLE IF NOT EXISTS tracked
(
    date text,
    user text,
    nasp text,
    nasi text
)
""")
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    for row in curs.execute("select user, nasp, nasi from tracked"):
        t = _object(u, p, n)
        if t in tracked:
            tracked.remove(t)
    print(tracked) 

def main():
    """Main entry."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=".")
    args = parser.parse_args()
    lines = sys.stdin.readlines()
    with sl.connect(os.path.join("test.db")) as c:
        tracked = []
        for l in lines:
            if "->" in l:
                t = make_tuple(l.split("->")[1].strip())
                user = None
                nasp = None
                nasi = None
                macs = []
                for k in t:
                    user = _get("User-Name", user, k)
                    nasp = _get("NAS-Port", nasp, k)
                    nasi = _get("NAS-IP-Address", nasi, k)
                    mac = _get("Calling-Station-Id", None, k)
                    if mac:
                        macs.append(mac)
                macs = list(set(macs))
                for mac in macs:
                    tracked.append(_object(user, nasp, nasi, mac))
        _report(c, list(set(tracked)))



if __name__ == "__main__":
    main()
