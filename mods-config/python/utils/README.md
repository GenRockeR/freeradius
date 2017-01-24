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
