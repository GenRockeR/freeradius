import radiusd
import json

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

def _user_config(user_name):
  """get a user config from file."""
  with open('/etc/raddb/mods-config/python/network.json') as f:
    obj = byteify(json.loads(f.read()))
    if user_name in obj:
      return obj[user_name]

def _get_pass(user_name):
  """set the configuration for down-the-line modules."""
  user = _user_config(user_name)
  if user is not None:
    config = ()
    if PASS_KEY in user:
      return user[PASS_KEY]

def _get_vlan(user_name, mac):
  """set the reply for a user and mac."""
  user = _user_config(user_name)
  if user is not None:
    if MAC_KEY in user:
      macs = user[MAC_KEY]
      if mac in macs:
        return str(macs[mac])

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

def instantiate(p):
  print "*** instantiate ***"
  print p
  # return 0 for success or -1 for failure
  return 0

def authenticate(p):
  radiusd.radlog(radiusd.L_INFO, '*** radlog call in authenticate ***')
  print
  print p
  print
  print radiusd.config
  return radiusd.RLM_MODULE_OK

def checksimul(p):
  return radiusd.RLM_MODULE_OK

def authorize(p):
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

