#!/usr/bin/python
"""Testing harness for freepydius implementation."""

import argparse
import freepydius

def main():
    options = dir(freepydius)
    choices = []
    for opt in options:
        if opt.endswith("_KEY"):
            continue
        elif opt.startswith("_"):
            continue
        elif opt in ["byteify", "radiusd", "Log", "TimedRotatingFileHandler", "json", "logger", "logging", "rlock", "threading", "uuid"]:
            continue
        choices.append(opt)
    parser = argparse.ArgumentParser(description="freepyidus test harness")
    parser.add_argument('method', choices=choices, help="method to execute")
    parser.add_argument('kv', nargs='*', help="key/value pairs")
    args = parser.parse_args()
    kv = []
    for val in args.kv:
        if "=" not in val:
            print("key/value must be key=value")
            exit(-1)
        parts = val.split("=")
        new_kv = (parts[0], parts[1])
        kv.append(new_kv)
    tuples = tuple(tuple(x) for x in kv)
    freepydius._CONFIG_FILE = "network.json"
    attr = getattr(freepydius, args.method)
    res = attr(tuples)
    print(res)

if __name__ == '__main__':
    main()
