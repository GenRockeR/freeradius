"""Common testing definitions."""
import keying
VALID_MAC = "001122334455"


def ready(obj):
    """Called on object setup/ready."""
    if obj.password.endswith('admin'):
        obj.password = obj.password[0:-1]
    if obj.password:
        obj.password = key.change_password(None, "test", obj.password))
    return obj
