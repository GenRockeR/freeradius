#!/usr/bin/python
"""reports for processing."""

import argparse
import sqlite3

OUT_PACKETS = 'Acct-Output-Packets'
IN_PACKETS = 'Acct-Input-Packets'
IN_OCTET = "Acct-Input-Octets"
OUT_OCTET = 'Acct-Output-Octets'


def _packets(cursor):
    """print information about packet throughput."""
    _accounting_stat(cursor, IN_PACKETS, OUT_PACKETS)

def _octets(cursor):
    """print information about octet throughput."""
    _accounting_stat(cursor, IN_OCTET, OUT_OCTET)

def _accounting_stat(cursor, in_col, out_col):
    cursor.execute("select line, key, val from data where key = '{0}' or key = '{1}'".format(out_col, in_col))
    queries = {}
    for row in cursor.fetchall():
        num = row[0]
        key = row[1]
        val = row[2]
        query = "select substr(date, 0, 11) as date, val, {0} as packets from data where line = {1} and key = 'User-Name'".format(val, num)
        if key not in queries:
            queries[key] = []
        queries[key].append(query)
    template = "select val, date, sum(packets) from ({0}) as X group by val, date order by val, date"
    for q in queries:
        query = template.format(" UNION ".join(queries[q]))
        cursor.execute(query)
        print q
        print "==="
        for row in cursor.fetchall():
            print "{:>15}{:>15}{:>15}".format(row[0], row[1], row[2])
        print


# available reports
available = {}
available["packets"] = _packets
available["octets"] = _octets


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
    conn = sqlite3.connect(args.database)
    curs = conn.cursor()
    for item in execute:
        if item in available:
            available[item](curs)
        else:
            print "unknown report..." + item
    conn.close()

if __name__ == "__main__":
    main()
