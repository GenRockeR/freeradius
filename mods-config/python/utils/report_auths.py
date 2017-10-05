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
                if uuid in uuid_log:
                    user = uuid_log[uuid]
                    auth_info[user] = day_offset
            else:
                if "User-Name" in data:
                    idx = data.index("User-Name") + 13
                    user_start = data[idx:]
                    user_start = user_start[:user_start.index(")") - 1]
                    calling = None
                    if "Calling-Station-Id" in data:
                        calling_station = data.index("Calling-Station-Id") + 22
                        calling = data[calling_station:]
                        calling = calling[:calling.index(")") - 1]
                        calling = replace(":", "").replace("-", "").lower()
                        key = "{}->{}".format(user_start, calling)
                        uuid_log[uuid] = key
                        if key not in auth_info:
                            auth_info[key] = None


def main():
    """Accept/reject reporting."""
    authd = {}
    today = dt.date.today()
    for x in reversed(range(1, 11)):
        _file("{}".format(today - dt.timedelta(days=x)), authd)
    print("| user | mac | date |")
    print("| ---  | --- | ---  |")
    for item in sorted(authd.keys()):
        on = authd[item]
        parts = item.split("->")
        if on is None:
            on = ""
        print("| {} | {} | {} |".format(parts[0], parts[1], on))

if __name__ == "__main__":
    main()
