freeradius
===

This is a freeradius setup that uses a python script to control user-password authentication and MACs to place user+MAC combinations into the proper vlan. This was done on Arch linux (in a container, as root)

At this point, before jumping in:

1. A lot of this was "radius the hard way" as the amount of documentation and people doing such an implementation is rather minimal and/or not documented. For that reason there is not much of a community
2. There are some oddities (that is the nice way to put it) for how freeradius has implemented some things (I'm looking at you tuple of tuples in python)
3. Due to 1 & 2 if you see holes and/or problems in this approach I would love to have a conversation about them
4. If you have questions and/or comments about custom freeradius implementation I would do by best to help you understand what I can.

## overview

For definitive information and guides about freeradius, visit the project [site](http://freeradius.org/)

### Summarized

FreeRadius is a server that provides the following three things:

- Authentication (Your driver's license proves that you're the person you say you are)
- Authorization (Your driver's license lets you drive your car, motorcycle, or CDL)
- Accounting (A log shows that you've driven on these roads at a certain date)

### our goals

* Support a port-restricted LAN (+wifi) in a controlled, physical area
* Provide a singular authentication strategy for supported clients using [peap](https://en.wikipedia.org/wiki/Protected_Extensible_Authentication_Protocol)+[mschapv2](https://en.wikipedia.org/wiki/Protected_Extensible_Authentication_Protocol#PEAPv0_with_EAP-MSCHAPv2) (no CA validation).
 * Windows 7/10
 * Arch/Fedora Linux (any supporting modern versions of NetworkManager or systemd-networkd when server/headless)
 * Android 7+
* Map authenticated user+MAC combinations to specific VLANs
* Support MAC-based authentication (bypass) for systems that can not authenticate themselves
* Integrate with Ubiquiti devices
* Avoid client-issued certificates (and management)
* Centralized configuration file
* As few open endpoints as possible on the radius server (only open ports 1812 and 1813 for radius)
* Avoid deviations from the standard/installed freeradius configurations

---

## Implementation Details

### Flow

1. The user does not enter credentials - the switch will send a request (on behalf of the system) to do MAC-based authentication
2. The user does enter credentials - those credentials will be accepted/rejected, if rejected go-to 1

Unauthenticated users are assigned no VLAN by radius and will be, by the networking backbone, assigned to a VLAN with restricted connection for troubleshooting/requests only.

---

#### radius

1. The request is received
2. Authorize & Authenticate happen (recognizing those are not the same but for the sake of this document)...
3. Within those sections the python module is called, it will (at minimum) have the User-Name attribute - we can set the Cleartext-Password config attribute which...
4. The config, having a cleartext password for the user (else they've been rejected by python), can move through the system (e.g. inner-tunnel, (p)eap, mschapv2) with the necessary attributes
5. Having (assumingly) been authorized/authenticated - the post_auth step also hits the python module which interrogates the MAC (Calling-Station-Id) and verifies that the MAC is supported for the given user
6. Assuming the user: entered their user name and password (properly), on a device configured for them (MAC), they will be Accepted...otherwise they are rejected

MAC-based/bypass works similarly in that the system's MAC is passed as the User-Name and Calling-Station-Id and used as the auth password as well.

---

### Analysis

We are able to review information about accounting (e.g. Start/Stop) to see connection information (e.g. packets/octets) via the date-based trace log from the python module: 
* What devices are connecting over certain ports and switches (and by which user).
* Generate statistics and/or review stats over accepts/rejects/etc.

### Future Options

* Distribute the CA cert that freeradius uses; however, it is only minimally correct (it is correct-enough for inner-tunnel in freeradius) and becomes a management problem for us
* Limit further port authorization at the freeradius endpoint to switch + port (or similar)
* Perform functions based on being wired or wireless

### Technical Notes

* We do have Cleartext-Password both in the configuration enumerated below, but it is also (currently) logged to the trace log. Be advised of this when distributing/debugging logs
* Instead of removing commented out sections, they are there for reference in the configs
* Though the python module is configured to be available for each phase (e.g. authorize, authenticate, accounting, post_auth, pre_proxy, preacct), it is not currently enabled for all (e.g. preacct, pre_proxy)
* MAC spoofing is likely the highest risk (currently known) for this configuration, see 'Future Options' above for how this can and may be mitigated

---

[![Build Status](https://travis-ci.org/epiphyte/freeradius.svg?branch=stable)](https://travis-ci.org/epiphyte/freeradius)

## setup/install

install python2 and freeradius
```
pacman -S freeradius python2
```
sorry freeradius but we need to talk...
```
cd /etc
rm -rf raddb
git clone git@github.com:epiphyte/freeradius.git raddb
cd raddb
git checkout stable
```

to have freeradius actually able to execute the python scripts during execution (or debug)
```
vim /etc/environment
---
# append
PYTHONPATH=/etc/raddb/mods-config/python/
```

need to update the freeradius systemd script to include the environment setting for python
```
sudo systemctl edit freeradius.service
---
# add to the [Service] section
[Service]
EnvironmentFile=/etc/environment
```

freepydius logging
```
mkdir /var/log/radius/freepydius
chown radiusd:radiusd /var/log/radius/freepydius
```

run the renew script
```
cd /etc/raddb/certs
./renew.sh
```

now we need the system to have knowledge of the key
```
vim /etc/raddb/clients.conf
---
certprivkey = somestring
# also configure your clients at this point
```

at this point running the radius server should be possible, though nothing can auth to it
```
radiusd -X
```

finally we can configure a log rotation
```
ln -s /etc/raddb/radius.logrotate /etc/logrotate.d/radius
```

### additional

for some management communications/reporting, install [smirc and feedme](https://mirror.epiphyte.network/repos/)

---

## configuration file (network.json)

the json required (as shown below) uses a few approaches to get users+MAC into the proper VLAN and to support MAC-based/bypass
* [vlan].[name] is the user name which is used to set their password for freeradius configuration/checking
* [vlan] is used to set attributes to allow switches to get the corresponding attributes back
* [mac] is used to allow only certain devices to be used by certain users in certain vlans
* this corresponds to the implementation (in python) called freepydius under the mods-config/python folder (which is already setup in the mods-available/python file)

the following json represents a routing definition, prod.* and dev.* would be users, the 1234567890ab represents a MAC-device authenticating
```
vim /etc/raddb/mods-config/python/network.json
---
{
    "bypass":
    {
        "1234567890ab": "dev"
    },
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
            ],
            "attr": []
        },
        "prod.user2":
        {
            "pass": "prodaccount$2",
            "macs":
            [
                "4fff3a7e7a11",
                "7fff3a777a11"
            ],
            "attr": ["temp"]
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
    },
    "blacklist": ["dev"]
}
```

our config file is using a primitive encryption algorithm (TEA) to handle very simple encryption/password handling. A keyfile must be defined that is as long as (or longer than) the longest configured password
```
vim /etc/raddb/mods-config/python/keyfile
---
abcd
```

### blacklist

because it may be beneficial to temporarily disable a vlan, user, or device there is an ability to blacklist

the blacklist section is a list of strings where a string can be:
* users (e.g. user1)
* vlan (e.g. prod)
* vlan.user (e.g. prod.user1)
* MAC-based auth MAC
* MAC (for a user set) which will blacklist all users with that mac assigned to them
* An attribute ("attr" array) on users

---

## connecting

### headless/server

to connect a headless system using systemd-network and wpa_supplicant check [here](https://wiki.archlinux.org/index.php/WPA_supplicant#802.1x.2Fradius)

### android

* EAP method: PEAP
* Phase 2: MSCHAPV2
* CA Cert: Do not validate
* Identity: <vlan.user>
* Password: <pass>

### network-manager (nm-applet)

Create a connection and go to the "802.1X Security" tab

* Check the "Use 802.1X" box
* Auth: Protected EAP (PEAP)
* Check the "No CA certificate is required"
* PEAP version: Automatic
* Inner authentication: MSCHAPv2
* Username: <vlan.user>
* Password: <password>

---

## debugging

there are a few utilities in the mods-config/python/utils folder associated with freepydius.py. It is _very_ difficult to debug certain problems in a python module by allowing freeradius to execute it (information is eaten alive...). The harness and replay allow for using logs and/or manual input to test cases against the module. Regardless of feeling about python 2 vs. 3 - freeradius currently (at least here) is using 2 and so all tooling has been built to both match that requirement but some...styling decisions from the radiusd & example.py installed by freeradius

## examples/debugging (radius)

some generalized notes for debugging radius _without_ the python module in place or in use

to configure a plain-text user settings definition, also make sure sites-enabled/default has 'files' enabled for authorize/authenticate
```
vim /etc/raddb/users
---
testing Cleartext-Password := "hello"
```

always make sure to configure the clients.conf for the device that will actually be "dealing" with radius

```
vim /etc/raddb/clients.conf
---
# you should already have a cert key in here!

# when using something like an edgerouter lite
client EdgeRouterLite {
    secret = testing123
    ipaddr=192.168.0.10
}

# or maybe a set of edgeswitch devices
# on 'all' of 192.168.0.*
client 192.168.0.0/24 {
        secret = myedgeswitchpassword
        require_message_authenticator = no
        nastype = other
}

```

On the EdgeRouterLite, you add radius access by doing the following:
```
$ configure
$ set system login radius-server <ip address> secret <secret radius key>
$ commit
$ save
$ exit
```

This is slightly more complicated on an edge switch, please consult the ubnt documentation and/or community

either way, at this point, run radius in debug mode
```
radiusd -X
```

to test the configuration (from the radius host)
```
# testing and hello are the matching user credentials from above
# localhost when running locally
# 0 is the NAS-port, shouldn't normally matter
# testing123 is the client secret
radtest testing hello localhost 0 testing123
```

if everything is configured properly this should result in
```
rad_recv: Access-Accept packet from host 127.0.0.1 port 1812, length=20
```

## remotely

this requires that:
* the radius server is configured to listen/accept on the given ip below (e.g. iptables and client.conf setup)
* MAC is formatted as 00:11:22:aa:bb:cc

start with installing wpa_supplicant to get eapol_test
```
pacman -S wpa_supplicant
```

setup a test config
```
vim test.conf
---
network={
        key_mgmt=WPA-EAP
        eap=PEAP
        identity="<vlan.user>"
        password="<password>"
        phase2="autheap=MSCHAPV2"
}
```

to run
```
eapol_test -a <radius_server_ip> -c test.conf -s <secret_key> -M <mac>
```
