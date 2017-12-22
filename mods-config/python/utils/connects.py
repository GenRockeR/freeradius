#!/usr/bin/python
"""Report on auth connects attempts."""
import argparse
import os
import sqlite3 as sl
import sys
import datetime
from ast import literal_eval as make_tuple
import wrapper
import smirc


def _object(user, port, nas_ip, mac):
    """Create an object."""
    return (user, port, nas_ip, wrapper.convert_mac(mac))


def _get(key, existing, tple):
    """Get a tuple key if not set."""
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
    port text,
    ip text,
    mac text
)
""")
    date = datetime.datetime.now().strftime("%Y-%m-%d")
    for row in curs.execute("select user, port, ip, mac from tracked"):
        t = _object(row[0], row[1], row[2], row[3])
        if t in tracked:
            tracked.remove(t)
    for t in tracked:
        try:
            txt = "auth attempt: {}".format(t)
            smirc.run(arguments=[txt])
            print(txt)
            curs.executemany("""
INSERT INTO tracked (date, user, port, ip, mac) VALUES (?, ?, ?, ?, ?)
                             """, [(date, t[0], t[1], t[2], t[3]), ])
        except Exception as e:
            print("reporting error")
            print(t)
            print(e)


def main():
    """Main entry."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default="/var/db")
    args = parser.parse_args()
    lines = sys.stdin.readlines()
    with sl.connect(os.path.join(args.db, "auths.db")) as c:
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
