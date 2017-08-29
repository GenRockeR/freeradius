#!/usr/bin/python
"""Password change/keying/etc."""
import wrapper
import argparse


def _key(key):
    """convert to a key."""
    return [ord(x) for x in key]


def change_password(old_key, new_key, password):
    """change a password."""
    old = password
    if old_key is not None:
        old = wrapper.decrypt(old, wrapper.convert_key(old_key))
    print("was: {}".format(password))
    print("decrypted: {}".format(old))
    print("now:")
    print(wrapper.encrypt(old, wrapper.convert_key(new_key)))


def main():
    """main-entry point."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--oldkey", type=str)
    parser.add_argument("--newkey", required=True, type=str)
    parser.add_argument("--password", required=True, type=str)
    args = parser.parse_args()
    change_password(args.oldkey, args.newkey, args.password)

if __name__ == "__main__":
    main()
