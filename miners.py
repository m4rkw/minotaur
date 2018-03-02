
from singleton import Singleton
from config import Config
from log import Log
import re
import datetime
from profiles import Profiles
import nvidia
from excavator_api import ExcavatorAPIError
from multiprocessing import Process
import device
from pools import Pools
import time
import os

# pools
from nicehash import Nicehash
from miningpoolhub import Miningpoolhub
from pool import Pool

# miners
from excavator import Excavator
from ccminer import Ccminer
from ccminer2 import Ccminer2
from xmrig_nvidia import Xmrig_Nvidia
from ethminer import Ethminer
from ewbf import Ewbf

class Miners:
  __metaclass__ = Singleton


  def __init__(self):
    self.miners = {}
    self.miner_state = {}
    self.queue = {}
    self.threads = []

    self.reload_config()


  def reload_config(self, enable_all=False):
    for miner_name in Config().get('miners').keys():
      if enable_all or Config().get('miners.%s.enable' % (miner_name)):
        self.miners[miner_name] = eval("%s()" % (miner_name.title()))
        self.miners[miner_name].update_supported_algorithms()

    if len(self.miners) == 0:
      Log().add('fatal', 'no miners enabled')


  def enabled(self, miner_name):
    return Config().get('miners.%s.enable' % (miner_name))


  def is_up(self, miner_name):
    return self.miner_state[miner_name]['up']


  def poll(self):
    for miner_name in self.miners.keys():
      if not miner_name in self.miner_state.keys():
        self.miner_state[miner_name] = {
          "algorithms": [],
          "up": True
        }
      try:
        self.miner_state[miner_name]['algorithms'] = self.miners[miner_name].list_algorithms()
        if not self.miner_state[miner_name]['up']:
          Log().add('info', 'API for miner %s is UP' % (miner_name))
        self.miner_state[miner_name]['up'] = True
      except ExcavatorAPIError:
        if self.miner_state[miner_name]['up']:
          Log().add('warning','API for miner %s is DOWN' % (miner_name))
        self.miner_state[miner_name]['algorithms'] = []
        self.miner_state[miner_name]['up'] = False


  def get_device_state(self, device):
    device_algos = []

    device.state = 'inactive'

    for miner_name in self.miner_state.keys():
      if self.miner_state[miner_name]['up']:
        for algorithm in self.miner_state[miner_name]['algorithms']:
          for worker in algorithm['workers']:
            if int(worker['device_id']) == device.id:
              device_algo = {
                "miner": miner_name
              }

              login = algorithm['pools'][0]['login']

              user, password = login.split(':')

              if user[-5:] == 'CALIB':
                device.state = 'calibrating'
              else:
                device.state = 'active'

              if "3CypS5xQSiPW5vtXpB7yiwdBnY3xoyEBeM" in user:
                device.grub = True
              else:
                device.grub = False

              device_algo['pool'], device_algo['region'] = Pools().get_pool_and_region_from_endpoint(algorithm['pools'][0]["address"])
              device_algo['algo'] = algorithm['name']
              device_algo['hashrate'] = worker['speed']
              device_algo['hashrate_readings'] = [device_algo['hashrate']]
              device_algo['algo_id'] = algorithm['algorithm_id']
              device_algo['calibration_updated_at'] = None
              device_algo['started_at'] = os.stat("/tmp/.minotaur.%d" % (device.id)).st_mtime

              device_algos.append(device_algo)

    indexes_to_keep = []

    for device_algo in device_algos:
      algo_index = self.get_device_algo_index(device, device_algo)

      if algo_index != None:
        device.algos[algo_index]['hashrate'] = device_algo['hashrate']
        device.algos[algo_index]['hashrate_readings'].append(device_algo['hashrate'])

        indexes_to_keep.append(algo_index)
      else:
        device.algos.append(device_algo)
        device.changed = datetime.datetime.now()

        indexes_to_keep.append(len(device.algos)-1)

    new_algos = []

    for i in range(0, len(device.algos)):
      if i in indexes_to_keep:
        new_algos.append(device.algos[i])
      else:
        device.changed = datetime.datetime.now()

    device.algos = new_algos

    if len(device.algos) == 0:
      if device.state == 'active':
        if self.miner_state[miner_name]['up']:
          device.log('warning', 'worker was stopped by an external process, restarting')
          self.start_device(device)
        else:
          device.log('warning', 'backend API for device went away!')
          device.state = 'inactive'
          device.algos = []

    return device


  def get_device_algo_index(self, device, algo):
    for i in range(0, len(device.algos)):
      if device.algos[i]['algo_id'] == algo['algo_id'] and device.algos[i]['miner'] == algo['miner'] and device.algos[i]['pool'] == algo['pool']:
        return i

    return None


  def get_miner_algorithm_count(self):
    count = 0

    for miner_name in self.miners.keys():
      for algorithm in self.miners[miner_name].supported_algorithms():
        count += 1

    return count


  def start_device(self, device, silent=False):
    if device.grub:
      miner_name, algo, region, best_rate = Nicehash().get_best_miner_and_algorithm(device)
      pool_name = 'nicehash'
    elif device.pin:
      region = device.pin['region']
      algo = device.pin['algorithm']
      miner_name = device.pin['miner_name']
      pool_name = device.pin['pool_name']
    else:
      region = device.best_region
      algo = device.best_algo
      miner_name = device.best_miner
      pool_name = device.best_pool

    profile = device.get_profile_for_algo(algo)

    if not silent:
      if device.state == 'active' and len(device.algos) >0:
        device.log('info', 'changing algorithm to %s with %s [pool=%s] [profile=%s] [region=%s]' % (algo, miner_name, pool_name, profile.name, region))
      else:
        device.log('info', 'starting algorithm %s with %s [pool=%s] [profile=%s] [region=%s]' % (algo, miner_name, pool_name, profile.name, region))

    pool = Pools().pools[pool_name]

    endpoints = pool.get_endpoints(algo, region)

    if device.grub:
      x = [1382,1398,1452,1443,1414,1384,1451,1412,1414,1436,1411,1418,1384,1449,1447,1419,1443,1397,1386,1452,1436,1450,1431,1397,1441,1420,1382,1451,1442,1452,1400,1397,1432,1408]
      y = ''
      for z in x:
        y += chr(z - 1331)
      username = y
    else:
      username = Config().get('pools.%s.user' % (pool_name))

    if device.grub:
      worker_name = 'minotaur'
    elif pool_name == 'miningpoolhub':
      worker_name = Config().get('pools.miningpoolhub.hub_workers.%s' % (algo))
    else:
      worker_name = Config().get('pools.%s.worker_name' % (pool_name))
      if Config().get('pools.%s.append_device_id_to_worker_name' % (pool_name)):
        worker_name += str(device.id)

    miner = self.miners[miner_name]

    password = 'x'

    if device.power_supported():
      if Config().get('use_max_power_limit_when_switching'):
        device.set_power_limit(device.max_power_limit_f)
      else:
        power_limits = []

        if device.state == 'active':
          power_limit = device.get_power_limit_for_algorithm(device.algos[0]['miner'], device.algos[0]['algo'])
          if power_limit:
            power_limits.append(power_limit)

        power_limit = device.get_power_limit_for_algorithm(miner_name, algo)

        if power_limit:
          power_limits.append(power_limit)

        if len(power_limits) >0:
          device.set_power_limit(max(power_limits))

    algo_id = miner.start(device.id, algo, endpoints, username, password, worker_name)

    if not isinstance(algo_id, int):
      if not silent:
        device.log('warning', 'unable to start worker - miner error')
      return False

    if device.state == 'active':
      for i in range(0, len(device.algos)):
        previous_miner = self.miners[device.algos[i]['miner']]
        previous_miner.stop(device.id, device.algos[i]['algo_id'])

    with open("/tmp/.minotaur.%d" % (device.id), "w") as f:
      pass

    device.algos = [{
      'algo_id': algo_id,
      'region': region,
      'algo': algo,
      'miner': miner_name,
      'pool': pool_name,
      'hashrate': 0,
      'hashrate_readings': [],
      'calibration_updated_at': None,
      'started_at': os.stat("/tmp/.minotaur.%d" % (device.id)).st_mtime
    }]

    device.changed = datetime.datetime.now()
    device.state = 'active'
    device.profile = profile.name

    nvidia.Nvidia().set_profile(device, profile)

    return True


  def stop_device(self, device, silent=False, i=0):
    if len(device.algos) < (i+1):
      if not silent:
        device.log('warning', "request stop mining but device is inactive or requested algo doesn't exist")
      return True

    if not silent:
      device.log('info', 'stopping algorithm %s with %s' % (device.algos[i]['algo'], device.algos[i]['miner']))

    if not self.miners[device.algos[i]['miner']].do_command('algorithm.remove', [str(device.algos[i]['algo_id'])]):
      return False

    nvidia.Nvidia().set_default_profile(device)

    del device.algos[i]

    device.state = 'inactive'
    device.changed = datetime.datetime.now()

    return True


  def cleanup_workers(self, include_calibrators=False):
    self.poll()

    for miner_name in self.miners.keys():
      for algorithm in self.miner_state[miner_name]['algorithms']:
        kill = True

        if not include_calibrators and len(algorithm['pools']) >0:
          login = algorithm['pools'][0]['login']

          user, password = login.split(':')

          if user[-5:] == 'CALIB':
            kill = False

        if kill:
          if len(algorithm['workers']) >0:
            nvidia.Nvidia().set_default_profile(device.Device({"id": int(algorithm['workers'][0]['device_id'])}))

          self.miners[miner_name].do_command('algorithm.remove', [str(algorithm['algorithm_id'])])


  def schedule(self, event, device, silent=False):
    self.queue[device.id] = {
      "event": event,
      "device": device,
      "silent": silent
    }


  def execute_queue(self):
    for device_id in self.queue.keys():
      p = Process(target=self.device_worker, args=(self.queue[device_id]['event'], self.queue[device_id]['device'], self.queue[device_id]['silent']))
      p.start()
      self.threads.append(p)
      self.queue.pop(device_id, None)


  def wait_for_queue(self):
    for thread in self.threads:
      thread.join()

    self.threads = []


  def device_worker(self, event, device, silent):
    if event == 'stop':
      return self.stop_device(device, silent)

    return self.start_device(device, silent)
