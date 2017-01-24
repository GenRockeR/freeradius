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


def _session_time(cursor):
    """print information about session time."""
    cursor.execute("select line from data where key = 'Acct-Status-Type' and val = 'Stop'")
    stop_lines = [x[0] for x in cursor.fetchall()]
    queries = []
    for stop in stop_lines:
        user = "select val, line from data where line = {0} and key = 'User-Name'".format(stop)
        sess = "select val, line from data where line = {0} and key = 'Acct-Session-Time'".format(stop)
        q = "select substr(date, 0, 11) as date, u.val as user, s.val from (select date, line from data where line = {0}) as X inner join ({1}) as u on u.line = X.line inner join({2}) as s on s.line = X.line".format(stop, user, sess)
        queries.append(q)
    cursor.execute("select date, user, avg(val), max(val), min(val), sum(val) from (" + " UNION ".join(queries) + ") as Y group by date, user order by date, user")
    def _gen():
        for row in cursor.fetchall():
            yield "{:>20}{:>15}{:>15}{:>15}{:>15}{:>15}".format(row[1], row[0], row[2], row[3], row[4], row[5])
    _print_data("sessions (avg, max, min, sum)", _gen)


def _print_data(cat, generator):
    print
    print cat
    print "==="
    for row in generator():
        print row
    print

def _authorizes(cursor):
    """get the number of authorizes by user by day."""
    cursor.execute("select val, date, sum(authorizes) from (select substr(date, 0, 11) as date, val, 1 as authorizes from data where type = 'AUTHORIZE' and key = 'User-Name' group by date, val) as X group by date, val order by date, val")
    def _gen():
        for row in cursor.fetchall():
            yield "{:>20}{:>15}{:>15}".format(row[0], row[1], row[2])
    _print_data("authorizes", _gen)


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
        def _gen():
            for row in cursor.fetchall():
                yield "{:>20}{:>15}{:>15}".format(row[0], row[1], row[2])
        _print_data(q, _gen)


# available reports
available = {}
available["packets"] = _packets
available["octets"] = _octets
available["authorizes"] = _authorizes
available["session-time"] = _session_time


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
