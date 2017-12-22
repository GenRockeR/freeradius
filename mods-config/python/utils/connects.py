#!/usr/bin/python
import argparse
import os
import sqlite3 as sl
import sys


def main():
    """Main entry."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", default=".")
    args = parser.parse_args()
    lines = sys.stdin.readlines()
    report = []
    with sl.connect(os.path.join("test.db")) as c:
        for l in lines:
            if "User-Name" in l and "AUTHORIZE" in l:
                print(l)




if __name__ == "__main__":
    main()
