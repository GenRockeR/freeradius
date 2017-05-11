"""User with inheritance."""
import __config__
normal = __config__.Assignment()
normal.macs = ["001122334455"]
normal.password = "12345678910aaaaaaaaaaaaaaa111213141516user3"
normal.vlan = "dev"
normal.attrs = ["test"]
normal.port_bypass = ["001122221100"]

admin = __config__.Assignment()
admin.inherits = normal
admin.vlan = "prod"
