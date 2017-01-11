import radiusd
import json
import logging
import threading
from logging.handlers import TimedRotatingFileHandler
"""Supports user + mac mapping and general configuration."""


def byteify(input):
  if isinstance(input, dict):
    return {byteify(key): byteify(value) for key, value in input.iteritems()}
  elif isinstance(input, list):
    return [byteify(element) for element in input]
  elif isinstance(input, unicode):
    return input.encode('utf-8')
  else:
    return input

# json keys
PASS_KEY = "pass"
MAC_KEY = "macs"
USER_KEY = "users"
VLAN_KEY = "vlans"
rlock = threading.RLock()
logger = None


def _config(user_name):
  """get a user config from file."""
  with open('/etc/raddb/mods-config/python/network.json') as f:
    obj = byteify(json.loads(f.read()))
    users = obj[USER_KEY]
    vlans = obj[VLAN_KEY]
    user_obj = None
    vlan_obj = None
    if "." in user_name:
      parts = user_name.split(".")
      vlan = parts[0]
      if user_name in users:
        user_obj = users[user_name]
      if vlan in vlans:
        vlan_obj = vlans[vlan]
    return (user_obj, vlan_obj)

def _get_pass(user_name):
  """set the configuration for down-the-line modules."""
  config = _config(user_name)
  user = config[0]
  if user is not None:
    if PASS_KEY in user:
      return user[PASS_KEY]

def _get_vlan(user_name, mac):
  """set the reply for a user and mac."""
  config = _config(user_name)
  user = config[0]
  vlan = config[1]
  if user is not None and vlan is not None:
    if MAC_KEY in user:
      macs = user[MAC_KEY]
      if mac in macs:
        return vlan

def _get_user_mac(p):
  """extract user/mac from request."""
  user_name = None
  mac = None
  for item in p:
    if item[0] == "User-Name":
      user_name = item[1]
    elif item[0] == "Calling-Station-Id":
      mac = item[1].replace(":", "").replace("-", "").lower()
  return (user_name, mac)

def _log(name, params):
  """common logging."""
  with rlock:
    if logger is not None:
      logger.info("{0} -> {1}".format(name, params))

def instantiate(p):
  print "*** instantiate ***"
  print p
  # return 0 for success or -1 for failure
  with rlock:
    global logger
    logger = logging.getLogger("freepydius-logger")
    logger.setLevel(logging.INFO)
    handler = TimedRotatingFileHandler("/var/log/radius/freepydius/trace.log",
                                       when="midnight",
                                       interval=1)
    formatter = logging.Formatter("%(asctime)s %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)
    _log("INSTNCE", "created")
  return 0

def authenticate(p):
  _log("AUTHICT", p)
  radiusd.radlog(radiusd.L_INFO, '*** radlog call in authenticate ***')
  print
  print p
  print
  print radiusd.config
  return radiusd.RLM_MODULE_OK

def checksimul(p):
  return radiusd.RLM_MODULE_OK

def authorize(p):
  _log("AUTHRZE", p)
  print "*** authorize ***"
  print
  radiusd.radlog(radiusd.L_INFO, '*** radlog call in authorize ***')
  print
  print p
  print
  print radiusd.config
  print
  user_mac = _get_user_mac(p)
  user = user_mac[0]
  mac = user_mac[1]
  reply = ()
  conf = ()
  if user is not None:
    password = _get_pass(user)
    if password is not None:
      conf = ( ('Cleartext-Password', password), )
    if mac is not None:
      vlan = _get_vlan(user, mac)
      if vlan is not None:
        reply = ( ('Tunnel-Type', 'VLAN'),
                  ('Tunnel-Medium-Type', 'IEEE-802'),
                  ('Tunnel-Private-Group-Id', vlan), )
  return (radiusd.RLM_MODULE_OK, reply, conf)

def preacct(p):
  print "*** preacct ***"
  print p
  return radiusd.RLM_MODULE_OK

def accounting(p):
  _log("ACCTING", p)
  print "*** accounting ***"
  radiusd.radlog(radiusd.L_INFO, '*** radlog call in accounting (0) ***')
  print
  print p
  return radiusd.RLM_MODULE_OK

def pre_proxy(p):
  print "*** pre_proxy ***"
  print p
  return radiusd.RLM_MODULE_OK

def post_proxy(p):
  print "*** post_proxy ***"
  print p
  return radiusd.RLM_MODULE_OK

def post_auth(p):
  _log("PSTAUTH", p)
  print "*** post_auth ***"
  print p
  user_mac = _get_user_mac(p)
  response = radiusd.RLM_MODULE_REJECT
  user = user_mac[0]
  mac = user_mac[1]
  if user is not None and mac is not None:
    if _get_vlan(user, mac) is not None:
      response = radiusd.RLM_MODULE_OK
  return response

def recv_coa(p):
  print "*** recv_coa ***"
  print p
  return radiusd.RLM_MODULE_OK

def send_coa(p):
  print "*** send_coa ***"
  print p
  return radiusd.RLM_MODULE_OK


def detach():
  print "*** goodbye from example.py ***"
  return radiusd.RLM_MODULE_OK

