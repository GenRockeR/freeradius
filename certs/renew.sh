#!/bin/bash
cd /etc/raddb/certs
echo "removing previous certs"
rm -f *.pem *.der *.csr *.crt *.key *.p12 serial* index.txt* passwords.mk
echo "rebuilding certs"
./bootstrap
echo "restarting freeradius"
systemctl restart freeradius
