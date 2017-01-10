freeradius
===

This is a freeradius setup that uses a python script to control user-password authentication and MACs to place user+MAC combinations into the proper vlan. This was done on Arch linux (in a container, as root)

# setup

to have freeradius actually able to execute the python scripts
```
vim /etc/environment
---
# append
PYTHONPATH=/etc/raddb/mods-config/python/
```

```
vim /usr/lib/systemd/system/freeradius.service
---
# add to the [Service] section
Environment=PYTHONPATH=/etc/raddb/mods-config/python/
```

install python2 and freeradius
```
pacman -S freeradius python2
```

freepydius logging
```
mkdir /var/log/radius/freepydius
chown radiusd:radiusd /var/log/radius/freepydius
```

# configuration

the json required (as shown below) uses a few approaches to get users+MAC into the proper VLAN
* [vlan].[name] is the user name which is used to set their password for freeradius configuration/checking
* [vlan] is used to set attributes to allow switches to get the corresponding attributes back
* [mac] is used to allow only certain devices to be used by certain users in certain vlans
* this corresponds to the implementation (in python) called freepydius under the mods-config/python folder

the following json represents a routing definition
```
vim /etc/raddb/mods-config/python/network.json
---
{
    "users":
    {
        "prod.user1":
        {
            "pass": "prodaccount$1",
            "macs":
            [
                "4fff3a7e7a11",
                "50009d1ea6cc",
                "6600991144dd"
            ]
        },
        "prod.user2":
        {
            "pass": "prodaccount$2",
            "macs":
            [
                "4fff3a7e7a11",
                "7fff3a777a11"
            ]
        },
        "dev.user1":
        {
            "pass": "devaccount",
            "macs":
            [
                "4fff3a7e7a11",
                "aaffbb112233"
            ]
        }
    },
    "vlans":
    {
        "prod": "10",
        "dev": "20"
    }
}
```
