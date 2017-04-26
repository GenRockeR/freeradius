#!/bin/bash
python2.7 report.py --database dump.db --report $1 --output $2 | tail -n +$3 >> $4
