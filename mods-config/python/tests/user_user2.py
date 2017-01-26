import __config__
normal = __config__.Assignment()
normal.macs = ["001122334455"]
normal.password = "12345678910aaaaaaaaaaaaaaa111213141516user2"
normal.vlan = "dev"

admin = __config__.Assignment()
admin.macs = normal.macs
admin.password = normal.password + "user2"
admin.vlan = "prod"
