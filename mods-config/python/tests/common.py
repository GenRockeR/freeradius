"""Common testing definitions."""
VALID_MAC = "001122334455"


def ready(obj):
    """Called on object setup/ready."""
    if obj.password.endswith('admin'):
        obj.password = obj.password[0:-1]
    return obj
