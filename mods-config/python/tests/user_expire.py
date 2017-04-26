"""Expired user."""
import __config__
import common
normal = __config__.Assignment()
normal.macs = [common.VALID_MAC]
normal.password = "12345aaa678910aaaaaaaaaaaaaaa111213141516etc"
normal.vlan = "dev"
normal.expired = "2017-01-01"
