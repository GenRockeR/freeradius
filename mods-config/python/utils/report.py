#!/usr/bin/python
"""reports for processing."""

import argparse
import sqlite3
import uuid
import store
import csv
import sys

# key/vals
OUT_PACKETS = 'Acct-Output-Packets'
IN_PACKETS = 'Acct-Input-Packets'
IN_OCTET = "Acct-Input-Octets"
OUT_OCTET = 'Acct-Output-Octets'
ACCT_SESS_TIME = "Acct-Session-Time"

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
        select date, user, 1 as authorizes
        from data
        inner join users on users.line = data.line
        where type = 'AUTHORIZE'
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
        select date, user, mac
        from data
        inner join users on users.line = data.line
        inner join macs on macs.line = data.line
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
        select user, date from data
        inner join users on users.line = data.line
        where key = '{0}'
        order by date desc
    ) group by user order by date
""".format(store.USER_NAME)

ALL_USERS_REPORT = "select user from ({0}) group by user"

NAS_INFO_COLS = """
    ifnull(nasipaddr.val, 'n/a') as nip,
    ifnull(nasport.val, 'n/a') as np,
    ifnull(nasporttype.val, 'n/a') as npt
"""

NAS_INFO = """
    left join
    (
        select line, val from data where key = 'NAS-IP-Address'
    ) as nasipaddr
    on nasipaddr.line = data.line
    left join
    (
        select line, val from data where key = 'NAS-Port'
    ) as nasport
    on nasport.line = data.line
    left outer join
    (
        select line, val from data where key = 'NAS-Port-Type'
    ) as nasporttype
    on nasporttype.line = data.line
"""

FAILED_AUTHS = """
select user as user, max(date) as date, nip as IP, np as Port, npt as Method
from
(
    select date, user, {0} from data
    inner join users on users.line = data.line
    {1}
    where
    instance not in
    (
        select distinct instance from data
        where key = 'Tunnel-Type'
    )
    and type = 'AUTHORIZE'
    and instance not in
    (
        select distinct instance from data
        where key = 'FreeRADIUS-Proxied-To'
    )
    and key = '{2}'
) as auths
group by user, np, npt, nip
order by date
""".format(NAS_INFO_COLS, NAS_INFO, store.USER_NAME)

SIGNATURES = """
    select distinct user, mac, {0}
    from data
    inner join users on users.line = data.line
    inner join macs on macs.line = data.line
    {1}
    order by user, mac, nip, np, npt
""".format(NAS_INFO_COLS, NAS_INFO)


def _packets_daily(cursor, opts):
    """packet report daily."""
    _packets(cursor, False, opts)


def _packets_all(cursor, opts):
    """packet report all."""
    _packets(cursor, True, opts)


def _octets_all(cursor, opts):
    """octet report all."""
    _octets(cursor, True, opts)


def _octets_daily(cursor, opts):
    """octet report daily."""
    _octets(cursor, False, opts)


def _session_time_all(cursor, opts):
    """session time all."""
    _session_time(cursor, True, opts)


def _session_time_daily(cursor, opts):
    """session time daily."""
    _session_time(cursor, False, opts)


def _authorizes_all(cursor, opts):
    """all authorizes."""
    _authorizes(cursor, True, opts)


def _authorizes_daily(cursor, opts):
    """daily authorizes."""
    _authorizes(cursor, False, opts)


def _packets(cursor, aggr, opts):
    """print information about packet throughput."""
    _accounting_stat(cursor, IN_PACKETS, OUT_PACKETS, aggr, opts)


def _octets(cursor, aggr, opts):
    """print information about octet throughput."""
    _accounting_stat(cursor, IN_OCTET, OUT_OCTET, aggr, opts)


def _print_data(cat, curs, opts, converter=None):
    """output data."""
    if converter is None:
        cols = _get_cols(curs)
    else:
        cols = converter(None, True)

    def _gen():
        for row in curs.fetchall():
            if converter is None:
                yield row
            else:
                row_res = converter(row, False)
                if row_res:
                    yield row_res
    if opts.csv:
        writer = csv.writer(sys.stdout)
        writer.writerow(cols)
        for r in _gen():
            writer.writerow(r)
        return
    print
    format_str = []
    for col in cols:
        use_format = "15"
        if col in ["attr", "user"]:
            use_format = "25"
        if col in ["signature"]:
            use_format = "50"
        if col == "mac":
            use_format = "20"
        format_str.append("{:>" + use_format + "}")
    join_fmt = ""
    if opts.markdown:
        join_fmt = " | "
    formatter = join_fmt.join(format_str)
    if opts.markdown:
        formatter = "| " + formatter + " |"
        print formatter.format(*cols)
        print formatter.format(*["--" for x in cols])
    else:
        print "{0} - ({1})".format(cat, ", ".join(cols))
        print "==="
    for row in _gen():
        print formatter.format(*row)
    print


def _get_cols(cursor):
    """get column names."""
    return list(map(lambda x: x[0], cursor.description))


def _session_time(cursor, aggr, opts):
    """print information about session time."""
    query = USERS_BY_KEY.format("'" + ACCT_SESS_TIME + "'")
    query = SESSION_TIME_STATS.format(query)
    if aggr:
        query = SESSION_TIME_AGGR.format(query)
    cursor.execute(query)
    _print_data("sessions", cursor, opts)


def _authorizes(cursor, aggr, opts):
    """get the number of authorizes by user by day."""
    query = AUTHORIZES.format(store.USER_NAME)
    if aggr:
        query = AUTHORIZES_AGGR.format(query)
    cursor.execute(query)
    _print_data("authorizes", cursor, opts)


def _accounting_stat(cursor, in_col, out_col, aggr, opts):
    """accounting stats."""
    query = USERS_BY_KEY.format("'" + "','".join([out_col, in_col]) + "'")
    query = ACCOUNTING_SUM.format(query)
    if aggr:
        query = ACCOUNTING_SUM_AGGR.format(query)
    cursor.execute(query)
    _print_data("accounting", cursor, opts)


def _user_last(cursor, opts):
    """all user report."""
    _user_last_full(cursor, True, opts)


def _user_last_daily(cursor, opts):
    """user last logged time."""
    _user_last_full(cursor, False, opts)


def _user_last_full(cursor, aggr, opts):
    """user last full query."""
    query = ALL_USERS
    if aggr:
        query = ALL_USERS_REPORT.format(query)
    cursor.execute(query)
    _print_data("users", cursor, opts)


def _user_mac_last_daily(cursor, opts):
    """user+mac last logged time."""
    _user_mac_last(cursor, False, opts)


def _user_mac_full(cursor, opts):
    """user+mac list detected."""
    _user_mac_last(cursor, True, opts)


def _user_mac_last(cursor, aggr, opts):
    """user mac querying."""
    query = USER_MACS.format(store.CALLING_STATION)
    if aggr:
        query = USER_MAC_REPORT.format(query)
    cursor.execute(query)
    _print_data("user/mac report", cursor, opts)


def _signatures(cursor, opts):
    """signature output."""
    cursor.execute(SIGNATURES)

    def _conv(row, get_columns):
        if get_columns:
            return ["user", "mac", "signature"]
        else:
            return [row[0], row[1], ":::".join(row[2:])]
    _print_data("signatures", cursor, opts, converter=_conv)


def _failed_auths(cursor, opts):
    """failed auths."""
    cursor.execute(FAILED_AUTHS)
    _print_data("failures", cursor, opts)


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
available["signatures"] = _signatures
available["failures"] = _failed_auths


class Options(object):
    """Options for reports."""

    MARKDOWN = "markdown"
    CSV = "csv"

    markdown = False
    csv = False


def main():
    """main entry."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--database",
                        required=True,
                        type=str,
                        default=store.DB_NAME)
    parser.add_argument("--reports", nargs='*', choices=available.keys())
    parser.add_argument("--output", choices=[Options.MARKDOWN, Options.CSV])
    args = parser.parse_args()
    if args.reports is None or len(args.reports) == 0:
        execute = available.keys()
    else:
        execute = args.reports
    conn = sqlite3.connect(args.database)
    curs = conn.cursor()
    opts = Options()
    if args.output == Options.MARKDOWN:
        opts.markdown = True
    elif args.output == Options.CSV:
        opts.csv = True
    for item in execute:
        if item in available:
            available[item](curs, opts)
        else:
            print "unknown report..." + item
    conn.close()

if __name__ == "__main__":
    main()
