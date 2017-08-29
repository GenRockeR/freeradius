# Copyright 2017
# MIT License
# Sean Enck
# Support user+mac mapping and VLAN assignment
# Fully supports User-Password authentication (PEAP+MSChapV2)
# Supports reply attributes needed by Ubiquiti equipment for VLAN assignment
import radiusd
import json
import logging
import os
import threading
import uuid
import random
from ctypes import *
from logging.handlers import TimedRotatingFileHandler

# json keys
PASS_KEY = "pass"
MAC_KEY = "macs"
USER_KEY = "users"
VLAN_KEY = "vlans"
BLCK_KEY = "blacklist"
BYPASS_KEY = "bypass"
ATTR_KEY = "attr"
PORT_BYPASS_KEY = "port"
_IS_BYPASS = "isbypass"
rlock = threading.RLock()
logger = None
_CONFIG_FILE_NAME="network.json"
_PY_CONF = '/etc/raddb/mods-config/python/'
_CONFIG_FILE = _PY_CONF + _CONFIG_FILE_NAME
_LOG_FILE_NAME = 'trace.log'
_LOG_FILE = "/var/log/radius/freepydius/" + _LOG_FILE_NAME
_DOMAIN_SLASH = "\\"
_ENC_KEY_FILE = _PY_CONF + 'keyfile'
_ENC_DELIMITER = "."
_ENC_KEY = "|"
_ENC_PAD = ord(":")

def byteify(input):
  """make sure we get strings."""
  if isinstance(input, dict):
    return {byteify(key): byteify(value) for key, value in input.iteritems()}
  elif isinstance(input, list):
    return [byteify(element) for element in input]
  elif isinstance(input, unicode):
    return input.encode('utf-8')
  else:
    return input


def _convert_user_name(name):
  """rules to support user name conversion(s)."""
  user_name = name
  # prepending of domain name to user-name...thanks Windows
  if _DOMAIN_SLASH in user_name:
    idx = user_name.index(_DOMAIN_SLASH)
    user_name = user_name[idx + len(_DOMAIN_SLASH):]
  return user_name


def _blacklist_objects(objs, blacklist, sep=None, sub_key=None, value=False):
  """cleanse blacklisted objects from the config."""
  cleansed = {}
  for item in objs:
    if item in blacklist:
      continue
    if sep is not None:
      parts = item.split(sep)
      valid = True
      for part in parts:
        if part in blacklist:
          valid = False
          break
      if not valid:
        continue
      if sub_key is not None and len(sub_key) > 0: 
        valid = True
        for sk in sub_key:
          if not valid:
            break
          if sk in objs[item]:
            for sub in objs[item][sk]:
              if sub in blacklist:
                valid = False
                break
        if not valid:
          continue
    if value:
      if objs[item] in blacklist:
        continue
    cleansed[item] = objs[item]
  return cleansed


def _mac(possible_mac):
  """check if an object is a mac."""
  valid = False
  if len(possible_mac) == 12:
    valid = True
    for c in possible_mac:
      if c not in ['0', '1', '2', '3', '4', '5', '6', '7', '8', '9', 'a', 'b', 'c', 'd', 'e', 'f']:
        valid = False
        break
  return valid


def _config(input_name):
  """get a user config from file."""
  user_name = _convert_user_name(input_name)
  with open(_CONFIG_FILE) as f:
    obj = byteify(json.loads(f.read()))
    blacklist = obj[BLCK_KEY]
    users = _blacklist_objects(obj[USER_KEY], blacklist, sep=".", sub_key=[MAC_KEY, ATTR_KEY])
    vlans = _blacklist_objects(obj[VLAN_KEY], blacklist)
    bypass = _blacklist_objects(obj[BYPASS_KEY], blacklist, value=True)
    user_obj = None
    vlan_obj = None
    if "." in user_name:
      parts = user_name.split(".")
      vlan = parts[0]
      if user_name in users:
        user_obj = users[user_name]
      if vlan in vlans:
        vlan_obj = vlans[vlan]
    else:
      lowered = user_name.lower()
      valid = _mac(lowered)
      if valid and lowered in bypass:
        vlan_name = bypass[lowered]
        if vlan_name in vlans:
          # input_name (User-Name) HAS to == "pass"
          user_obj = { PASS_KEY: input_name, MAC_KEY: [lowered], _IS_BYPASS: True }
          vlan_obj = vlans[vlan_name]
    return (user_obj, vlan_obj)


def _convert_key(key):
    """Convert a key."""
    return [ord(x) for x in key]


def _get_tea_key():
  """Get the TEA key from keyfile."""
  with open(_ENC_KEY_FILE, 'r') as f:
    return _convert_key(f.read().strip())


def _split_key(key):
  if _ENC_PAD not in key:
    raise Exception("invalid key input - no padding indicator")
  idx = key.index(_ENC_PAD)
  pad = "".join([chr(x) for ind, x in enumerate(key) if ind < idx])
  keyed = [x for ind, x in enumerate(key) if ind > idx]
  return (int(pad), keyed)


def _pad(pad):
    """Pad a value."""
    if pad == 0:
        return ""
    return str(random.random()).replace(".", "").rjust(pad, '0')[0:pad]


def _encrypt(v, key_input):
  if len(v) % 2 != 0:
    raise Exception("value must be divisible by 2")
  resulting = []
  key_parts = _split_key(key_input)
  key = key_parts[1]
  pad = key_parts[0]
  for i in range(0, len(v)):
    if i % 2 == 1:
      continue
    k = key[i:i+4]
    cur = (ord(v[i]), ord(v[i + 1]))
    res = _tea_encrypt(cur, k)
    f_pad = _pad(pad)
    l_pad = _pad(pad)
    resulting.append("{}{}{}{}{}".format(f_pad,
                                         res[0],
                                         _ENC_DELIMITER,
                                         l_pad,
                                         res[1]))
  return _ENC_KEY.join(resulting)


def _decrypt(v, key_input):
  split = v.split(_ENC_KEY)
  resulting = []
  idx = 0
  key_parts = _split_key(key_input)
  key = key_parts[1]
  pad = key_parts[0]
  for item in split:
    k = key[idx:idx+4]
    parts = item.split(_ENC_DELIMITER)
    res = _tea_decrypt((int(parts[0][pad:]), int(parts[1][pad:])), k)
    resulting.append(chr(res[0]))
    resulting.append(chr(res[1]))
    idx = idx + 2
  return "".join(resulting)


def _tea_encrypt(v, k):
  y = c_uint32(v[0]);
  z = c_uint32(v[1]);
  s = c_uint32(0);
  delta = 0x9E3779B9;
  n = 32
  w = [0,0]
  while (n > 0):
    s.value += delta
    y.value += ( z.value << 4 ) + k[0] ^ z.value + s.value ^ ( z.value >> 5 ) + k[1]
    z.value += ( y.value << 4 ) + k[2] ^ y.value + s.value ^ ( y.value >> 5 ) + k[3]
    n -= 1
  w[0] = y.value
  w[1] = z.value
  return w

def _tea_decrypt(v, k):
  y=c_uint32(v[0])
  z=c_uint32(v[1])
  sum=c_uint32(0xC6EF3720)
  delta=0x9E3779B9
  n=32
  w=[0,0]
  while(n>0):
      z.value -= ( y.value << 4 ) + k[2] ^ y.value + sum.value ^ ( y.value >> 5 ) + k[3]
      y.value -= ( z.value << 4 ) + k[0] ^ z.value + sum.value ^ ( z.value >> 5 ) + k[1]
      sum.value -= delta
      n -= 1

  w[0]=y.value
  w[1]=z.value
  return w

def _get_pass(user_name):
  """set the configuration for down-the-line modules."""
  config = _config(user_name)
  user = config[0]
  if user is not None:
    if PASS_KEY in user:
      if _IS_BYPASS in user and user[_IS_BYPASS]:
        return user[PASS_KEY]
      else:
        return _decrypt(user[PASS_KEY], _get_tea_key())


def _get_vlan(user_name, macs):
  """set the reply for a user and mac."""
  config = _config(user_name)
  user = config[0]
  vlan = config[1]
  if user is not None and vlan is not None:
    if MAC_KEY in user:
      mac_set = user[MAC_KEY]
      for mac in macs:
        if mac in mac_set:
          return vlan


def _convert_mac(mac):
  """convert a mac to a lower, cleansed value."""
  using = mac.lower()
  for c in [":", "-"]:
    using = using.replace(c, "")
  return using


def _get_user_mac(p):
  """extract user/mac from request."""
  user_name = None
  macs = []
  for item in p:
    if item[0] == "User-Name":
      user_name = item[1]
    elif item[0] == "Calling-Station-Id":
      mac = _convert_mac(item[1])
      macs.append(mac)
  mac_set = None
  if len(macs) > 0:
    mac_set = macs
  return (user_name, mac_set)


class Log(object):
  """logging object."""
  def __init__(self, cat):
    self.id = str(uuid.uuid4())
    self.name = cat

  def log(self, params):
    """common logging."""
    with rlock:
      if logger is not None:
        logger.info("{0}:{1} -> {2}".format(self.name, self.id, params))


def instantiate(p):
  print("*** instantiate ***")
  print(p)
  with rlock:
    global logger
    logger = logging.getLogger("freepydius-logger")
    logger.setLevel(logging.INFO)
    handler = TimedRotatingFileHandler(_LOG_FILE,
                                       when="midnight",
                                       interval=1)
    formatter = logging.Formatter("%(asctime)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    log = Log("INSTANCE")
    log.log(( ('Response', 'created'), ))
  # return 0 for success or -1 for failure
  return 0


def authenticate(p):
  log = Log("AUTHENTICATE")
  log.log(p)
  radiusd.radlog(radiusd.L_INFO, '*** radlog call in authenticate ***')
  print("")
  print(p)
  print("")
  print(radiusd.config)
  return radiusd.RLM_MODULE_OK


def checksimul(p):
  return radiusd.RLM_MODULE_OK


def authorize(p):
  log = Log("AUTHORIZE")
  log.log(p)
  print("*** authorize ***")
  print("")
  radiusd.radlog(radiusd.L_INFO, '*** radlog call in authorize ***')
  print("")
  print(p)
  print("")
  print(radiusd.config)
  print("")
  user_mac = _get_user_mac(p)
  user = user_mac[0]
  macs = user_mac[1]
  reply = ()
  conf = ()
  if user is not None:
    password = _get_pass(user)
    if password is not None:
      conf = ( ('Cleartext-Password', password), )
    if macs is not None:
      vlan = _get_vlan(user, macs)
      if vlan is not None:
        reply = ( ('Tunnel-Type', 'VLAN'),
                  ('Tunnel-Medium-Type', 'IEEE-802'),
                  ('Tunnel-Private-Group-Id', vlan), )
  log.log(reply)
  log.log(conf)
  return (radiusd.RLM_MODULE_OK, reply, conf)


def preacct(p):
  print("*** preacct ***")
  print(p)
  return radiusd.RLM_MODULE_OK


def accounting(p):
  log = Log("ACCOUNTING")
  log.log(p)
  print("*** accounting ***")
  radiusd.radlog(radiusd.L_INFO, '*** radlog call in accounting (0) ***')
  print("")
  print(p)
  return radiusd.RLM_MODULE_OK


def pre_proxy(p):
  print("*** pre_proxy ***")
  print(p)
  return radiusd.RLM_MODULE_OK


def post_proxy(p):
  print("*** post_proxy ***")
  print(p)
  return radiusd.RLM_MODULE_OK


def post_auth(p):
  log = Log("POSTAUTH")
  log.log(p)
  print("*** post_auth ***")
  print(p)
  user_mac = _get_user_mac(p)
  response = radiusd.RLM_MODULE_REJECT
  user = user_mac[0]
  macs = user_mac[1]
  if user is not None and macs is not None:
    if _get_vlan(user, macs) is not None:
      response = radiusd.RLM_MODULE_OK
  log.log(( ('Response', response), ))
  return response


def recv_coa(p):
  print("*** recv_coa ***")
  print(p)
  return radiusd.RLM_MODULE_OK


def send_coa(p):
  print("*** send_coa ***")
  print(p)
  return radiusd.RLM_MODULE_OK


def detach():
  print("*** goodbye from example.py ***")
  return radiusd.RLM_MODULE_OK
