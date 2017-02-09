import __config__
import common
normal = __config__.Assignment()
normal.macs = [common.VALID_MAC]
normal.password = "12345678910aaaaaaaaaaaaaaa111213141516etc"
normal.bypass = ["112233445566"]
normal.vlan = "dev"

admin = __config__.Assignment()
admin.macs = normal.macs
admin.password = normal.password + "admin"
admin.vlan = "prod"
