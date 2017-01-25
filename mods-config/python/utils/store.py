#!/usr/bin/python
"""Supports convering trace logs into a database store."""

import ast
import sys
import sqlite3
import replay


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


def _accept(input_stream):
    """accept the input stream."""
    line_num = 1
    conn = sqlite3.connect("dump.db")
    c = conn.cursor()
    c.execute('''CREATE TABLE data
                (date text,
                 time text,
                 line integer,
                 instance text,
                 key text,
                 val text,
                 type text)''')
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
    c.execute('CREATE TABLE users (line integer, user text)')
    c.execute("""INSERT INTO users
                 SELECT line, val FROM data WHERE key='User-Name'""")
    conn.commit()
    conn.close()


_accept(sys.stdin)
