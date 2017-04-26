utils
===

utilities for interacting with, debug, and reporting over freepydius information

## harness

harness to test method with certain key/value pairs
```
python2.7 harness.py accounting User-Name=test.user Calling-Station-Id=11-22-33-44-55-66
```

## replay

replay a log into the freepydius implementation
```
python2.7 replay.py --file trace.log
```

## report

run reports over the output of a store
```
python2.7 --database dump.db --reports packets rebuild 
```

## store

convert the (or multiple) trace.log files into a sqlite database

```
cat trace.log | python2.7 store.py
```

## wrapper

helpers for the other utils

## config_compose

composes the configuration file from a subset of python definition, review the README in users/README.md

## manage

supports managing configurations from another (private) repo with user definitions _actually_ in it

in the other repo, put your users in a "users" folder
```
mkdir users
```

use this bash script at the level in which the "users" folder is defined
```
#!/bin/bash
LOCAL_CONF=~/.config/epiphyte/env
source /etc/environment
if [ -e $LOCAL_CONF ]; then
    source $LOCAL_CONF
fi
git pull
offset=$FREERADIUS_REPO/mods-config/python
PYTHONPATH=$offset:$FREERADIUS_REPO:$PYTHONPATH python2.7 $offset/utils/manage.py $@
```
