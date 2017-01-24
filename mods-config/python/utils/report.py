#!/usr/bin/python
"""reports for processing."""

import argparse


def _packets(database):
    """print information about packet thru-put."""
    print database


# available reports
available = {}
available["packets"] = _packets


def main():
    """main entry."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=str)
    parser.add_argument("--reports", nargs='*')
    args = parser.parse_args()
    if args.reports is None or len(args.reports) == 0:
        print "please give some reports to run..."
        exit(1)
    execute = args.reports
    for item in execute:
        if item in available:
            available[item](args.database)
        else:
            print "unknown report..." + item
            exit(1)

if __name__ == "__main__":
    main()
