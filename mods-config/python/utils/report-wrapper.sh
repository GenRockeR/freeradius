#!/bin/bash
TMPDB=dump.db
case $1 in
    "report")
        python2.7 report.py --database $TMPDB --report $2 --output $3 | tail -n +$4 >> $5
        ;;
    "store")
        rm -f $TMPDB
        cat $2 | python2.7 store.py
        ;;
esac
