VALID_MAC = "001122334455"

def ready(obj):
    if obj.password.endswith('admin'):
        obj.password = obj.password[0:-1]
    return obj
