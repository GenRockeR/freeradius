#!/usr/bin/python
"""Supports convering trace logs into a database store."""

import ast
import sys
import sqlite3
import replay
import wrapper

DB_NAME = "dump.db"
USER_NAME = "User-Name"
CALLING_STATION = "Calling-Station-Id"


class Entry(object):
    """represents a single entry for a name/value pair."""
    def __init__(self, line, instance, date, time, typed, key_val):
        """initialiez the instance."""
        self.line = line
        self.instance = instance
        self.time = time
        self.date = date
        self.typed = typed
        self.key = key_val[0]
        self.val = key_val[1]

    def to_row(self):
        """convert to an inserted row."""
        return [self.date,
                self.time,
                self.line,
                self.instance,
                self.key,
                self.val,
                self.typed]

def _clean_object(cursor, table, column, key, conv):
    cursor.execute('CREATE TABLE {0} (line integer, {1} text)'.format(table,
                                                                      column))
    cursor.execute("SELECT line, val FROM data WHERE key = '{0}'".format(key))
    for row in cursor.fetchall():
        line = row[0]
        obj = row[1]
        obj = conv(obj)
        cursor.execute("INSERT INTO {0} VALUES (?, ?)".format(table),
                       [line, obj])


def _accept(input_stream):
    """accept the input stream."""
    line_num = 1
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE data
                (date text,
                 time text,
                 line integer,
                 instance text,
                 key text,
                 val text,
                 type text)''')
    print "streaming text into database..."
    for line in input_stream:
        parts = line.split(replay.KEY)
        meta = parts[0]
        data = ast.literal_eval(parts[1])
        last = meta.rfind(":")
        inst = meta[last + 1:]
        time_type = meta[:last].split(" ")
        date = time_type[0]
        time = " ".join(time_type[1:-1])
        typed = time_type[-1]
        for datum in data:
            entry = Entry(line_num, inst, date, time, typed, datum)
            row = entry.to_row()
            c.execute("INSERT INTO data VALUES (?, ?, ?, ?, ?, ?, ?)", row)
        line_num = line_num + 1
    print "cleaning up users..."
    def _user_conv(user_name):
        return wrapper.convert_user(user_name)[:20]
    _clean_object(c, "users", "user", USER_NAME, _user_conv)
    print "cleaning up mac/calling station..."
    def _mac_conv(mac):
        return wrapper.convert_mac(mac)
    _clean_object(c, "macs", "mac", CALLING_STATION, _mac_conv)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    _accept(sys.stdin)
