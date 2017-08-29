"""User in multiple vlans."""
import __config__
normal = __config__.Assignment()
normal.macs = ["001122334455"]
normal.password = "1057687797.863093848|4050535148.2760919111|64205524.3092519096"
normal.vlan = "dev"

admin = __config__.Assignment()
admin.macs = normal.macs
admin.password = normal.password + "user2"
admin.vlan = "prod"
admin.password = "1057687797.863093848|4050535148.2760919111|64205524.3092519096|1046040092.2821704132|3813347290.3145056057"
