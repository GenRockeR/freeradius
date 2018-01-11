#!/bin/bash

UPSTREAM="src"
MODS_CONF="mods-config"
MODS_CONF_PY="${MODS_CONF}/python/"
HERE="upstream/"
BIN="bin/"
EXPECT=${BIN}/expected.log
ACTUAL=${BIN}/actual.log
SITES_AVAIL="sites-available"
MODS_AVAIL="mods-available"
CERTS="certs"
SKIP="
all.mk
${CERTS}\/ca.cnf
${CERTS}\/client.cnf
${CERTS}\/demoCA\/cacert.pem
${CERTS}\/ocsp.cnf
${CERTS}\/renew.sh
${CERTS}\/server.cnf
clients.conf
LICENSE
${MODS_AVAIL}\/eap
${MODS_AVAIL}\/python
${MODS_CONF}\/files\/authorize
${MODS_CONF}\/perl
${MODS_CONF}\/python\/radiusd.py
${MODS_CONF}\/python\/network.json
${MODS_CONF}\/sql
radiusd.conf
radrelay.conf.in
README.md
${SITES_AVAIL}\/default
${SITES_AVAIL}\/inner-tunnel
vmpsd.conf.in
radius.logrotate
"

function checksum-files()
{
    get-files $1 $2 | awk '{print $2 " - (" $1 ")"}'
}

function get-files()
{
    for f in $(find $1 -type f| grep -v ".git" | grep -v -E "$2");do 
        sha256sum $f; 
    done
}

mkdir -p $BIN
rm -rf $UPSTREAM
git clone https://github.com/FreeRADIUS/freeradius-server.git $UPSTREAM
cd $UPSTREAM
git checkout tags/release_3_0_16
cd ..
checksum-files "../" "${MODS_CONF_PY}util|${MODS_CONF_PY}tests|${MODS_CONF_PY}freepydius|${HERE}|travis.yml" | sed "s/\.\.//g" | sort > $EXPECT
checksum-files "$UPSTREAM/raddb" "blah" | sed "s/src\/raddb//g" | sort > $ACTUAL
for f in $(echo "$ACTUAL $EXPECT"); do
    for r in $(echo "$SKIP"); do
        sed -i "/^\/$r/d" $f
    done
done
diff -u $ACTUAL $EXPECT
exit $?
