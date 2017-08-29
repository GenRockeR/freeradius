bash
===

bash helpers for managing/using the network configuration (json).

# pass-freeradius

## install

configure and setup the epiphyte [repository](https://github.com/epiphyte/repository)

install
```
pacman -S pass-freeradius
```

## setup

make sure the following keys are set:
```
vim ~/.config/epiphyte/env
---
FREERADIUS_REPO=/path/to/freeradius/epiphyte/repo/clone
TEA_KEY="decryptionstringkeywhathaveyou"
NETCONF=/path/to/local/network/configuration/location/
```

# usage

this is a subset of pass functionality but

list entries
```
pass-freeradius ls
```

show (or `-c` to clipboard copy)
```
pass-freeradius show <vlan>.<user>
```
