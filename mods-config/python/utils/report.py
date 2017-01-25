#!/usr/bin/python
"""reports for processing."""

import argparse
import sqlite3

OUT_PACKETS = 'Acct-Output-Packets'
IN_PACKETS = 'Acct-Input-Packets'
IN_OCTET = "Acct-Input-Octets"
OUT_OCTET = 'Acct-Output-Octets'


def _packets_daily(cursor):
    _packets(cursor, False)


def _packets_all(cursor):
    _packets(cursor, True)


def _octets_all(cursor):
    _octets(cursor, True)


def _octets_daily(cursor):
    _octets(cursor, False)


def _session_time_all(cursor):
    _session_time(cursor, True)


def _session_time_daily(cursor):
    _session_time(cursor, False)


def _authorizes_all(cursor):
    _authorizes(cursor, True)


def _authorizes_daily(cursor):
    _authorizes(cursor, False)


def _packets(cursor, aggr):
    """print information about packet throughput."""
    _accounting_stat(cursor, IN_PACKETS, OUT_PACKETS, aggr)


def _octets(cursor, aggr):
    """print information about octet throughput."""
    _accounting_stat(cursor, IN_OCTET, OUT_OCTET, aggr)

USER_NAME = 'User-Name'
STOP_QUERY = """
    select line from data
    where key = 'Acct-Status-Type' and val = 'Stop'
"""

VAL_LINE_WHERE = """
    select val, line from data where line = {0} and key = '{1}'
"""

SESSION_USER = """
    select date, u.val as user, s.val
    from (select date, line from data where line = {0}) as X
    inner join ({1}) as u on u.line = X.line
    inner join({2}) as s on s.line = X.line
"""

def _session_time(cursor, aggr):
    """print information about session time."""
    cursor.execute(STOP_QUERY)
    stop_lines = [x[0] for x in cursor.fetchall()]
    queries = []
    for stop in stop_lines:
        user = VAL_LINE_WHERE.format(stop, USER_NAME)
        sess = VAL_LINE_WHERE.format(stop, "Acct-Session-Time")
        q = SESSION_USER.format(stop, user, sess)
        queries.append(q)
    query = "select date, user, avg(val) as a, max(val) as mx, min(val) as mn, sum(val) as s from (" + " UNION ".join(queries) + ") as Y group by date, user order by date, user"
    if aggr:
        query = "select 'all', user, avg(a), max(mx), min(mn), sum(s) from (" + query + ") as Z group by user"
    cursor.execute(query)
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

def _authorizes(cursor, aggr):
    """get the number of authorizes by user by day."""
    query = "select val, date, sum(authorizes) as s from (select substr(date, 0, 11) as date, val, 1 as authorizes from data where type = 'AUTHORIZE' and key = 'User-Name' group by date, val) as X group by date, val order by date, val"
    if aggr:
        query = "select val, 'all', sum(s) from (" + query + ") as Z group by val"
    cursor.execute(query)
    def _gen():
        for row in cursor.fetchall():
            yield "{:>20}{:>15}{:>15}".format(row[0], row[1], row[2])
    _print_data("authorizes", _gen)


def _accounting_stat(cursor, in_col, out_col, aggr):
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
    template = "select val, date, sum(packets) s from ({0}) as X group by val, date order by val, date"
    for q in queries:
        query = template.format(" UNION ".join(queries[q]))
        if aggr:
            query = "select val, 'all', sum(s) from (" + query + ") as Z group by val"
        cursor.execute(query)
        def _gen():
            for row in cursor.fetchall():
                yield "{:>20}{:>15}{:>15}".format(row[0], row[1], row[2])
        _print_data(q, _gen)


# available reports
available = {}
available["packets"] = _packets_all
available["octets"] = _octets_all
available["authorizes"] = _authorizes_all
available["session-time"] = _session_time_all
available["packets-daily"] = _packets_daily
available["octets-daily"] = _octets_daily
available["authorizes-daily"] = _authorizes_daily
available["session-time-daily"] = _session_time_daily


def main():
    """main entry."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--database", required=True, type=str)
    parser.add_argument("--reports", nargs='*')
    args = parser.parse_args()
    if args.reports is None or len(args.reports) == 0:
        execute = available.keys()
    else:
        execute = args.reports
    conn = sqlite3.connect(args.database)
    curs = conn.cursor()
    for item in execute:
        print "executing " + item
        if item in available:
            available[item](curs)
        else:
            print "unknown report..." + item
    conn.close()

if __name__ == "__main__":
    main()
