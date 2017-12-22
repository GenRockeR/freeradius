#!/usr/bin/python
import argparse
import os
import sqlite3 as sl
import sys


def _extract(line, attr):
    key = "'{}'".format(attr)
    if key in line:
        idx = line.index(key)
        sub = line[idx + len(key) + 2:len(line)]
        val = sub.strip().split(" ")[0].replace("'", "").replace(")", "").replace(",", "")
        return val



def main():
    """Main entry."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=".")
    args = parser.parse_args()
    lines = sys.stdin.readlines()
    tracked = []
    with sl.connect(os.path.join("test.db")) as c:
        for l in lines:
            u = _extract(l, "User-Name")
            if u:
                p = _extract(l, "NAS-Port")
                if p:
                    n = _extract(l, "NAS-IP-Address")
                    if n:
                        tracked.append((u, p, n))
    print(set(tracked))



if __name__ == "__main__":
    main()
