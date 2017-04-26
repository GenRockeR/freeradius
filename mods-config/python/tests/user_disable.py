"""User with a disabled setting."""
import __config__
import common
disabled = "11ff33445566"
normal = __config__.Assignment()
normal.macs = [common.VALID_MAC]
normal.password = "12345d678910aaaaaaaaaaaaaaa111213141516etc"
normal.bypass = [disabled]
normal.disable = {disabled: "2017-01-01"}
normal.vlan = "dev"
