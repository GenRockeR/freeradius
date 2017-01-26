import __config__
normal = __config__.Assignment()
normal.macs = ["001122334455"]
normal.password = "12345678910aaaaaaaaaaaaaaa111213141516etc"
normal.bypass = ["112233445566"]
normal.vlan = "dev"

admin = __config__.Assignment()
admin.macs = normal.macs
admin.password = normal.password + "admin"
admin.vlan = "prod"
