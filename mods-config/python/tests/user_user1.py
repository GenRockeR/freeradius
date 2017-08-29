"""User with admin and dev and various macs."""
import __config__
import common
normal = __config__.Assignment()
normal.macs = [common.VALID_MAC]
normal.password = "1057687797.863093848|4050535148.2760919111|2943557348.3572403425"
normal.bypass = ["112233445566"]
normal.vlan = "dev"

admin = __config__.Assignment()
admin.macs = normal.macs
admin.password = 1057687797.863093848|4050535148.2760919111|2943557348.3572403425|1046040092.2821704132|3813347290.3145056057
admin.vlan = "prod"
