#!/usr/bin/python
"""reports for processing."""

import argparse
import sqlite3
import wrapper
import uuid

# key/vals
OUT_PACKETS = 'Acct-Output-Packets'
IN_PACKETS = 'Acct-Input-Packets'
IN_OCTET = "Acct-Input-Octets"
OUT_OCTET = 'Acct-Output-Octets'
USER_NAME = 'User-Name'
ACCT_SESS_TIME = "Acct-Session-Time"
CALLING_STATION = 'Calling-Station-Id'

# queries
USERS_BY_KEY = """
    select key as attr, val datum, user, date 
    from data inner join users on users.line = data.line
    where key in ({0})
"""
ACCOUNTING_SUM = """
    select user, date, attr, sum(datum) as datum
    from ({0}) group by user, date, attr
"""
ACCOUNTING_SUM_AGGR = """
    select user, attr, sum(datum) as datum from ({0}) group by user, attr
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
SESSION_TIME_STATS = """
    select date,
    user,
    round(avg(datum)) as avg_val,
    max(datum) as max_val,
    min(datum) as min_val,
    sum(datum) as sum_val
    from ({0}) as Y
    group by date, user order by date, user
"""
SESSION_TIME_AGGR = """
    select user,
           round(avg(avg_val)) as avg_val,
           max(max_val) as max_val,
           min(min_val) as min_val,
           sum(sum_val) as sum_val
           from ({0}) as Z
           group by user
"""
USER_MACS = """
    select max(date) as date, user, mac from
    (
        select date, user, val as mac
        from data
        inner join users on users.line = data.line
        where key = '{0}'
    ) group by user, mac order by date
"""

USER_MAC_REPORT = """
    select user, mac from
    ({0})
    group by user, mac
    order by user, mac
"""

ALL_USERS = """
    select user, max(date) as date
    from (
        select val as user, date from data
        where key = '{0}' order by date desc
    ) group by user order by date
""".format(USER_NAME)

ALL_USERS_REPORT = "select user from ({0}) group by user"


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
    mac_idx = -1
    format_str = []
    idx = 0
    for col in cols:
        use_format = "15"
        if col == "user":
            use_format = "25"
            user_idx = idx
        if col == "attr":
            use_format = "25"
        if col == "mac":
            mac_idx = idx
            use_format = "20"
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
                val = wrapper.convert_user(val)[0:20]
            if idx == mac_idx:
                val = wrapper.convert_mac(val)
            use_data.append(val)
            idx = idx + 1
        print formatter.format(*use_data)
    print


def _get_cols(cursor):
    """get column names."""
    return list(map(lambda x: x[0], cursor.description))


def _session_time(cursor, aggr):
    """print information about session time."""
    query = USERS_BY_KEY.format("'" + ACCT_SESS_TIME + "'")
    query = SESSION_TIME_STATS.format(query)
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
    query = USERS_BY_KEY.format("'" + "','".join([out_col, in_col]) + "'")
    query = ACCOUNTING_SUM.format(query)
    if aggr:
        query = ACCOUNTING_SUM_AGGR.format(query)
    cursor.execute(query)
    _print_data("accounting", cursor)


def _user_last(cursor):
    """all user report."""
    _user_last_full(cursor, True)

def _user_last_daily(cursor):
    """user last logged time."""
    _user_last_full(cursor, False)

def _user_last_full(cursor, aggr):
    query = ALL_USERS
    if aggr:
        query = ALL_USERS_REPORT.format(query)
    cursor.execute(query)
    _print_data("users", cursor)


def _user_mac_last_daily(cursor):
    """user+mac last logged time."""
    _user_mac_last(cursor, False)

def _user_mac_full(cursor):
    """user+mac list detected."""
    _user_mac_last(cursor, True)

def _user_mac_last(cursor, aggr):
    query = USER_MACS.format(CALLING_STATION)
    if aggr:
        query = USER_MAC_REPORT.format(query)
    cursor.execute(query)
    _print_data("user/mac report", cursor)

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
available["users-daily"] = _user_last_daily
available["users"] = _user_last
available["user-macs-daily"] = _user_mac_last_daily
available["user-macs"] = _user_mac_full


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
