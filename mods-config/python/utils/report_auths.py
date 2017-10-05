#!/usr/bin/python
"""Report authorization information."""
import datetime as dt


def _file(day_offset, auth_info):
    """Read a file."""
    uuid_log = {}
    with open("trace.log.{}".format(day_offset), 'r') as f:
        for l in f:
            parts = l.split("->")
            uuid = parts[0].split(":")[3].strip()
            data = parts[1]
            is_accept = "Tunnel-Type" in data
            if is_accept:
                user = uuid_log[uuid]
                auth_info[user] = day_offset
            else:
                if "User-Name" in data:
                    idx = data.index("User-Name") + 13
                    user_start = data[idx:]
                    user_start = user_start[:user_start.index(")") - 1]
                    uuid_log[uuid] = user_start
                    if user_start not in auth_info:
                        auth_info[user_start] = None


def main():
    """Accept/reject reporting."""
    authd = {}
    today = dt.date.today()
    for x in reversed(range(1, 11)):
        _file("{}".format(today - dt.timedelta(days=x)), authd)
    for item in sorted(authd.keys()):
        on = authd[item]
        print("{}={}".format(item, on))

if __name__ == "__main__":
    main()
