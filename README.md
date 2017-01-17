freeradius
===

This is a freeradius setup that uses a python script to control user-password authentication and MACs to place user+MAC combinations into the proper vlan. This was done on Arch linux (in a container, as root)

# goals

* Support a port-restricted LAN (+wifi) in a controlled physical area
* Provide a singular authentication strategy for supported clients (Windows, Linux, Android)
* Map authenticated user+MAC combinations to specific VLANs
* Integrate with Ubiquiti devices
* Avoid client-issued certificates (and management)
* Centralized configuration file
* As few open endpoints as possible

# notes

* This expects _ALL_ endpoints to support peap+mschapv2 (tested on Android 7.1.1, Arch using NetworkManager, and Windows 10)
* Avoids deviating from standard configs at all, assumes users are capable of handling things like systemd themselves
* The "default" config is the open point (e.g. ports 1812 and 1813 are open for udp traffic) so it has been stripped down where possible
* There is _NO_ issuance of any cert to clients for this implementation, we do handle managing the internal radius certs. This implementation is for a restricted area LAN.

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
EnvironmentFile=/etc/environment
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

need to set the internal certs. all passwords _MUST_ be the same (example here: somestring)
```
vim /etc/raddb/certs/passwords.mk
---
PASSWORD_SERVER = 'somestring'
PASSWORD_CA = 'somestring'
PASSWORD_CLIENT = 'somestring'
USER_NAME   = 'somestring'
CA_DEFAULT_DAYS  = '1825'
```

now run the renew script
```
/etc/raddb/certs/renew.sh
```

we need the system to have knowledge of the key
```
vim /etc/raddb/clients.conf
---
certprivkey = somestring
```

# blacklist

support blacklisting by
* users (e.g. user1)
* vlan (e.g. prod)
* vlan.user (e.g. prod.user1)

devices (MACs) per user can not be blacklisted, they should just be removed from the list of MACs

# configuration

the json required (as shown below) uses a few approaches to get users+MAC into the proper VLAN
* [vlan].[name] is the user name which is used to set their password for freeradius configuration/checking
* [vlan] is used to set attributes to allow switches to get the corresponding attributes back
* [mac] is used to allow only certain devices to be used by certain users in certain vlans
* this corresponds to the implementation (in python) called freepydius under the mods-config/python folder

the following json represents a routing definition, prod.* and dev.* would be users, the 1234567890ab represents a MAC-device authenticating
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
        },
        "1234567890ab":
        {
            "pass": "1234567890ab",
            "vlan": "dev",
            "macs":
            [
                "pass": "1234567890ab",
            ]
        }
    },
    "vlans":
    {
        "prod": "10",
        "dev": "20"
    },
    "blacklist": []
}
```
