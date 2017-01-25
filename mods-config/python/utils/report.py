#!/usr/bin/python
"""reports for processing."""

import argparse
import sqlite3
import wrapper

# key/vals
OUT_PACKETS = 'Acct-Output-Packets'
IN_PACKETS = 'Acct-Input-Packets'
IN_OCTET = "Acct-Input-Octets"
OUT_OCTET = 'Acct-Output-Octets'
USER_NAME = 'User-Name'
ACCT_SESS_TIME = "Acct-Session-Time"

# queries
ACCOUNTING_BY_KEY = """
    select line, key, val from data where key = '{0}' or key = '{1}'
"""
ACCOUNT_BY_LINE_KEY = """
    select date, val as user, {0} as datum from data
    where line = {1} and key = '{2}'
"""
ACCOUNTING_SUM = """
    select user, date, sum(datum) as datum from ({0}) as X
    group by user, date order by user, date
"""
ACCOUNTING_SUM_AGGR = """
    select user, sum(datum) as datum from ({0}) as Z group by user
"""
AUTHORIZES = """
    select user, date, sum(authorizes) as total
    from (
        select date, val as user, 1 as authorizes
        from data where type = 'AUTHORIZE' 
        and key = '{0}'
    ) as X
    group by date, user order by date, user
"""
AUTHORIZES_AGGR = """
    select user, sum(total) as total from ({0}) as Z group by user
"""
STOP_QUERY = """
    select line from data
    where key = 'Acct-Status-Type' and val = 'Stop'
"""
SESSION_TIME_STATS = """
    select date,
    user,
    round(avg(val)) as avg_val,
    max(val) as max_val,
    min(val) as min_val,
    sum(val) as sum_val
    from ({0}) as Y
    group by date, user order by date, user
"""
SESSION_TIME_AGGR = """
    select user,
           avg(avg_val) as avg_val,
           max(max_val) as max_val,
           min(min_val) as min_val,
           sum(sum_val) as sum_val
           from ({0}) as Z
           group by user
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


def _packets_daily(cursor):
    """packets daily."""
    _packets(cursor, False)


def _packets_all(cursor):
    """packets all."""
    _packets(cursor, True)


def _octets_all(cursor):
    """octets all."""
    _octets(cursor, True)


def _octets_daily(cursor):
    """octets daily."""
    _octets(cursor, False)


def _session_time_all(cursor):
    """session time all."""
    _session_time(cursor, True)


def _session_time_daily(cursor):
    """session time daily."""
    _session_time(cursor, False)


def _authorizes_all(cursor):
    """all authorizes."""
    _authorizes(cursor, True)


def _authorizes_daily(cursor):
    """daily authorizes."""
    _authorizes(cursor, False)


def _packets(cursor, aggr):
    """print information about packet throughput."""
    _accounting_stat(cursor, IN_PACKETS, OUT_PACKETS, aggr)


def _octets(cursor, aggr):
    """print information about octet throughput."""
    _accounting_stat(cursor, IN_OCTET, OUT_OCTET, aggr)


def _print_data(cat, curs):
    """output data."""
    print
    cols = _get_cols(curs)
    def _gen():
        for row in curs.fetchall():
            yield row
    user_idx = -1
    format_str = []
    idx = 0
    for col in cols:
        use_format = "15"
        if col == "user":
            use_format = "20"
            user_idx = idx
        format_str.append("{:>" + use_format + "}")
        idx = idx + 1
    formatter = "".join(format_str)
    print "{0} - ({1})".format(cat, ", ".join(cols))
    print "==="
    for row in _gen():
        data = row
        use_data = []
        idx = 0
        for item in data:
            val = item
            if idx == user_idx:
                val = wrapper.convert_user(val)
            use_data.append(val)
            idx = idx + 1
        print formatter.format(*use_data)
    print


def _get_cols(cursor):
    """get column names."""
    return list(map(lambda x: x[0], cursor.description))


def _session_time(cursor, aggr):
    """print information about session time."""
    cursor.execute(STOP_QUERY)
    stop_lines = [x[0] for x in cursor.fetchall()]
    queries = []
    for stop in stop_lines:
        user = VAL_LINE_WHERE.format(stop, USER_NAME)
        sess = VAL_LINE_WHERE.format(stop, ACCT_SESS_TIME)
        q = SESSION_USER.format(stop, user, sess)
        queries.append(q)
    query = SESSION_TIME_STATS.format(" UNION ".join(queries))
    if aggr:
        query = SESSION_TIME_AGGR.format(query)
    cursor.execute(query)
    _print_data("sessions", cursor)


def _authorizes(cursor, aggr):
    """get the number of authorizes by user by day."""
    query = AUTHORIZES.format(USER_NAME)
    if aggr:
        query = AUTHORIZES_AGGR.format(query)
    cursor.execute(query)
    _print_data("authorizes", cursor)


def _accounting_stat(cursor, in_col, out_col, aggr):
    """accounting stats."""
    cursor.execute(ACCOUNTING_BY_KEY.format(out_col, in_col))
    queries = {}
    for row in cursor.fetchall():
        num = row[0]
        key = row[1]
        val = row[2]
        query = ACCOUNT_BY_LINE_KEY.format(val, num, USER_NAME)
        if key not in queries:
            queries[key] = []
        queries[key].append(query)
    for q in queries:
        query = ACCOUNTING_SUM.format(" UNION ".join(queries[q]))
        if aggr:
            query = ACCOUNTING_SUM_AGGR.format(query)
        cursor.execute(query)
        _print_data(q, cursor)


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
    parser.add_argument("--reports", nargs='*', choices=available.keys())
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
