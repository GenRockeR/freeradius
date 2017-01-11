#!/bin/bash
function print-bar()
{
    echo "
==================
$@
=================="
    read
}
cd /etc/raddb/certs
print-bar "this script assumes all passwords are the same, this is viable for a restricted area LAN at best. you will be prompted for each password (use the same one), make sure passwords.mk has already been updated."
if [ ! -f passwords.mk ]; then
    echo "no passwords file..."
    exit -1
fi
echo "removing previous certs"
rm -f *.pem *.der *.csr *.crt *.key *.p12 serial* index.txt*
echo "rebuilding certs"
./bootstrap
print-bar "before start/restarting radius, update the clients.conf and add [certprivkey = <password>]"
