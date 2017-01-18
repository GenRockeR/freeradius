#!/usr/bin/python
"""log replay for trace logging."""

import argparse
import ast
import subprocess

KEY = " -> "

def _commented(text):
    print "# " + text

def main():
    parser = argparse.ArgumentParser(description="freepyidus log replay")
    parser.add_argument('--file', help="file input", default="/var/log/radius/freepydius/trace.log")
    args = parser.parse_args()
    with open(args.file, 'r') as f:
        for line in f:
            idx = line.index(KEY)
            meta = line[0:idx]
            last = meta.rfind(":")
            meta = meta[0:last]
            typed = meta.split(" ")[-1]
            data = ast.literal_eval(line[idx + len(KEY):])
            objs = []
            for d in data:
                key = d[0]
                val = d[1]
                objs.append("=".join([str(key), str(val)]))
            _commented("replaying")
            method = None
            if typed == "AUTHORIZE":
                method = "authorize"
            elif typed == "POSTAUTH":
                method = "post_auth"
            elif typed == "ACCOUNTING":
                method = "accounting"
            else:
                print "unknown method: " + method
                exit(-1)
            cmd = ["python2.7", "freepydius_harness.py", method]
            for item in objs:
                cmd.append(item)
            _commented(method)
            print _commented(" ".join(cmd))
            subprocess.Popen(cmd)
            print

if __name__ == '__main__':
    main()
