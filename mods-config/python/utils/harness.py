#!/usr/bin/python
"""Testing harness for freepydius implementation."""

import argparse
import wrapper


def main():
    """main entry."""
    options = dir(wrapper.freepydius)
    choices = []
    for opt in options:
        if opt.endswith("_KEY"):
            continue
        elif opt.startswith("_"):
            continue
        elif opt in ["FORCE_VLAN",
                     "byteify",
                     "radiusd",
                     "Log",
                     "TimedRotatingFileHandler",
                     "json",
                     "logger",
                     "logging",
                     "rlock",
                     "threading",
                     "uuid"]:
            continue
        choices.append(opt)
    parser = argparse.ArgumentParser(description="freepyidus test harness")
    parser.add_argument('method', choices=choices, help="method to execute")
    parser.add_argument('kv', nargs='*', help="key/value pairs")
    args = parser.parse_args()
    kv = []
    wrapper.radiusd.config = ()
    for val in args.kv:
        if "=" not in val:
            print("key/value must be key=value")
            exit(-1)
        parts = val.split("=")
        new_kv = (parts[0], parts[1])
        kv.append(new_kv)
    tuples = tuple(tuple(x) for x in kv)
    wrapper.freepydius._CONFIG_FILE = "../network.json"
    attr = getattr(wrapper.freepydius, args.method)
    res = attr(tuples)
    print(res)
    print

if __name__ == '__main__':
    main()
