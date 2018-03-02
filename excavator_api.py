
from log import Log
from config import Config
import socket
import json
import re
import sys
import nicehash
import time

class ExcavatorAPIError(Exception):
  pass

class ExcavatorAPI(object):
  def __init__(self):
    self.name = self.__class__.__name__.lower()
    self.supported = self.get_supported_algorithms()


  def do_command(self, method, params, silent=False):
    BUF_SIZE = 1024
    command = {
        'id': 1,
        'method': method,
        'params': params
        }

    timeout = Config().get('miners.%s.timeout' % (self.name))

    if not timeout:
      timeout = 10

    ip = Config().get('miners.%s.ip' % (self.name))
    port = Config().get('miners.%s.port' % (self.name))

    try:
      s = socket.create_connection((ip, port), timeout)
    except socket.error:
      Log().add('error', "failed to connect to %s miner backend at: %s:%d, make sure it's running" % (self.name, ip, port))
      raise ExcavatorAPIError({"error": "connection failed"})

    s.sendall((json.dumps(command).replace('\n', '\\n') + '\n').encode())
    response = ''
    while True:
        chunk = s.recv(BUF_SIZE).decode()
        if '\n' in chunk:
            response += chunk[:chunk.index('\n')]
            break
        else:
            response += chunk
    s.close()

    response_data = json.loads(response)
    if response_data['error'] is None:
        return response_data
    else:
        if not silent:
          Log().add('error', '%s: failed to execute method %s: %s' % (self.name, command, response_data['error']))
        raise ExcavatorAPIError(response_data)


  def list_algorithms(self):
    resp = self.do_command('algorithm.list', [])

    if resp:
      return resp['algorithms']

    return []


  def start(self, device_id, algorithm, endpoints, username, password, worker_name):
    auth = '%s.%s:%s' % (username, worker_name, password)

    if "nicehash" in endpoints[0]:
      l_stratum = lambda algo: '%s.%s:%s' % (algo, endpoints[0], nicehash.Nicehash().ports[algo])

      if "_" in algorithm:
        first, second = algorithm.split("_")
        params = [algorithm, l_stratum(first), auth, l_stratum(second), auth]
      else:
        params = [algorithm, l_stratum(algorithm), auth]
    else:
      if len(endpoints) >1:
        params = [algorithm, endpoints[0], auth, endpoints[1]]
      else:
        params = [algorithm, endpoints[0], auth]

    algo_params = Config().get('miners.%s.algo_params.%s' % (self.name, algorithm))

    if algo_params:
      for key in algo_params.keys():
        params.append("%s=%s" % (key, algo_params[key]))

    try:
      resp = self.do_command('algorithm.list', [])

      for algorithm in resp['algorithms']:
        if len(algorithm['pools']) >0:
          for worker in algorithm['workers']:
            if int(worker['device_id']) == device_id:
              login = algorithm['pools'][0]['login']
              user, password = login.split(':')

              if user[-5:] == 'CALIB':
                Log().add('warning', "%s: device %d is being used for calibration - not starting worker" % (self.name, device_id))
                return False

      resp = self.do_command('algorithm.add', params)

      if resp["error"] != None:
        Log().add('error', '%s: failed to add algorithm: %s' % (self.name, resp['error']))
        return

      if not "algorithm_id" in resp.keys():
        Log().add('error', '%s: missing algorithm_id in response' % (self.name))
        Log().add('error', resp)
        return

      algo_id = resp['algorithm_id']

      resp = self.do_command('worker.add', [str(algo_id), str(device_id)])

      if resp["error"] != None:
        Log().add('error', '%s: failed to add worker: %s' % (self.name, resp['error']))
        return

      return algo_id

    except ExcavatorAPIError as e:
      Log().add('error', '%s: failed to start excavator algorithm on device %d' % (self.name, device_id))
      return False


  def stop(self, device_id, algo_id=None):
    found = False

    try:
      for algorithm in self.list_algorithms():
        remove = False

        if len(algorithm['workers']) == 0:
          remove = True
        else:
          if algo_id == None or int(algo_id) == int(algorithm['algorithm_id']):
            for worker in algorithm['workers']:
              if int(worker['device_id']) == device_id:
                remove = True
                found = True

        if remove:
          self.do_command('algorithm.remove', [str(algorithm['algorithm_id'])])
          break
    except ExcavatorAPIError as e:
      Log().add('error', '%s: failed to stop on device %d' % (self.name, device_id))
      return False

    if not found:
      Log().add('warning', "%s: request to stop on device %d which isn't mining" % (self.name, device_id))

    return True


  def supported_algorithms(self):
    return self.supported


  def update_supported_algorithms(self):
    new_supported_algorithms = self.get_supported_algorithms()

    for algorithm in new_supported_algorithms:
      if algorithm not in self.supported:
        Log().add('info', '%s now supports algorithm: %s' % (self.name, algorithm))
        self.supported.append(algorithm)


    for algorithm in self.supported:
      if algorithm not in new_supported_algorithms:
        Log().add('info', '%s no longer supports algorithm: %s' % (self.name, algorithm))
        self.supported.remove(algorithm)
