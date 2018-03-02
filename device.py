
import datetime
import re
from calibration import Calibration
from log import Log
from profiles import Profiles
import nvidia
from config import Config
from miners import Miners
import os
from units import Units
import yaml
from pools import Pools
from nicehash import Nicehash
from gs import MinotaurGS
from stats import Stats

# pools
from nicehash import Nicehash
from miningpoolhub import Miningpoolhub
from pool import Pool
from pools import Pools

class Device:
  keys = {
    "id": None,
    "name": None,
    "dclass": None,
    "state": "unknown",
    "changed": None,
    "algos": [],
    "best_pool": None,
    "best_miner": None,
    "best_algo": None,
    "best_region": None,
    "pin": False,
    "profile": None,
    "gpu_u": None,
    "gpu_u_i": None,
    "mem_u": None,
    "mem_u_i": None,
    "gpu_t": None,
    "gpu_t_i": None,
    "power": None,
    "power_f": None,
    "limit": None,
    "limit_f": None,
    "default_power_limit": None,
    "default_power_limit_f": None,
    "min_power_limit": None,
    "min_power_limit_f": None,
    "max_power_limit": None,
    "max_power_limit_f": None,
    "gpu_f": None,
    "mem_f": None,
    "ps": None,
    "fan": None,
    "stat": None,
    "grub": False,
    "grubtime": 0
  }


  def __init__(self, data={}):
    for key in self.keys:
      setattr(self, key, self.keys[key])

    for key in data.keys():
      setattr(self, key, data[key])

    self.changed = datetime.datetime.now()


  def to_hash(self):
    _hash = {}

    for key in self.keys:
      _hash[key] = getattr(self, key)

    return _hash


  def get_profile_for_algo(self, algorithm=None):
    if algorithm == None:
      algorithm = self.algos[0]['algo']

    return Profiles().get_for_device_algo(self, algorithm)


  def get_calibrated_algorithms(self):
    return Calibration().get_calibrated_algorithms_for_device(self)


  def ignored(self):
    ignore_list = Config().get('ignore_devices')
    return ignore_list and self.id in ignore_list or self.dclass in ignore_list or self.name in ignore_list


  def calibrating(self):
    return self.state == 'calibrating'


  def update_bests(self):
    best_pool, best_miner, best_algo, best_region = Pools().get_most_profitable_action(self)

    if best_pool != self.best_pool or best_miner != self.best_miner or best_algo != self.best_algo or best_region != self.best_region:
      self.best_pool = best_pool
      self.best_miner = best_miner
      self.best_algo = best_algo
      self.best_region = best_region

      if self.pin:
        suffix = ' [pinned]'
      else:
        suffix = ''

      self.log('info', 'most profitable is now: %s/%s in region: %s using %s%s' % (best_pool, best_algo, best_region, best_miner, suffix))


  def update(self):
    self.update_bests()

    if self.ignored():
      if self.state != 'ignored':
        self.log('info', 'added to ignore list')

        if self.state == 'active':
          self.stop()

        self.state = 'ignored'
        self.changed = datetime.datetime.now()
      return
    else:
      if self.state == 'ignored':
        self.log('info', 'removed from ignore list')

    previous_state = self.state

    Miners().get_device_state(self)

    if self.state == 'active':
      profile = self.get_profile_for_algo(self.algos[0]['algo'])
      self.profile = profile.name

    if self.state == 'calibrating' and previous_state != 'calibrating':
      self.log('info', 'being used for calibration - ignoring')
      return

    if previous_state == 'calibrating' and self.state != 'calibrating':
      self.log('info', 'no longer being used for calibration')
      return

    pin = self.get_pin()

    if pin:
      if "idle" in pin.keys():
        if not self.pin or not "idle" in self.pin.keys():
          self.log('info', 'pinned to IDLE')
          self.pin = pin

          if self.state == 'active':
            Miners().schedule('stop', self)

      elif "calibration" in pin.keys():
        if not self.pin or not "calibration" in self.pin.keys():
          if self.state == 'active':
            Miners().schedule('stop', self)

          self.log('info', 'being used for calibration - ignoring')
          self.pin = pin

      elif not self.pin or 'idle' in self.pin.keys() or 'calibration' in self.pin.keys() or self.pin['pool_name'] != pin['pool_name'] or self.pin['algorithm'] != pin['algorithm'] or self.pin['region'] != pin['region'] or self.pin['miner_name'] != pin['miner_name']:
        self.log('info', 'pinned to miner=%s pool=%s algorithm=%s region=%s' % (pin['miner_name'], pin['pool_name'], pin['algorithm'], pin['region']))

        self.pin = pin

        if self.state == 'active' and (self.algos[0]['pool'] != pin['pool_name'] or self.algos[0]['algo'] != pin['algorithm'] or self.algos[0]['region'] != pin['region'] or self.algos[0]['miner'] != pin['miner_name']):
          Miners().schedule('restart', self)

    else:
      if self.pin:
        self.log('info', 'unpinned')

        self.pin = False

        if self.state == 'active':
          Miners().schedule('restart', self)
        elif self.state == 'inactive':
          Miners().schedule('start', self)


  def get_pin(self):
    if os.path.exists("/var/run/minotaur/pin%d" % (self.id)):
      return yaml.load(open("/var/run/minotaur/pin%d" % (self.id)).read())

    return False


  def remove_pin(self):
    if os.path.exists("/var/run/minotaur/pin%d" % (self.id)):
      os.remove("/var/run/minotaur/pin%d" % (self.id))


  def stop(self, silent=False):
    return Miners().stop_device(self, silent)


  def start(self, silent=False):
    return Miners().start_device(self, silent)


  def log(self, event, message):
    Log().add(event, 'device %d [%s]: %s' % (self.id, self.dclass, message))


  def can_run(self):
    if self.ignored():
      if Config().get('debug'):
        self.log('debug', 'device is ignored - not starting worker')
      return False

    if self.calibrating():
      if Config().get('debug'):
        self.log('debug', 'device is calibrating - not starting worker')
      return False

    if not Calibration().get_hashrates(self):
      if Config().get('debug'):
        self.log('debug', 'device has no calibration data - not starting worker')
      return False

    if self.pin:
      if 'idle' in self.pin.keys() or 'calibration' in self.pin.keys():
        if Config().get('debug'):
          self.log('debug', 'device is pinned to calibration or idle - not starting worker')
        return False

      return True

    if not self.best_pool:
      self.log('warning', 'unable to use - no best pool')
      return False

    if not self.best_miner:
      self.log('warning', 'unable to use - no best miner')
      return False

    if not self.best_algo:
      self.log('warning', 'unable to use - no best algorithm')
      return False

    if self.best_miner == 'nicehash' and not self.best_region:
      self.log('warning', 'unable to use - no best region')
      return False

    return True


  def running(self):
    return self.state == 'active'


  def is_optimal(self):
    return self.best_pool == self.algos[0]['pool'] and self.best_miner == self.algos[0]['miner'] and self.best_algo == self.algos[0]['algo'] and self.best_region == self.algos[0]['region']


  def warming_up(self):
    return (datetime.datetime.now() - self.changed).seconds < Config().get('algo_warmup_period_mins')


  def hashrate_str(self):
    if self.algos[0]['algo'] in Config().get('algorithms.single'):
      return Units().hashrate_str(self.algos[0]['hashrate'][0])

    return Units().hashrate_str(self.algos[0]['hashrate'])


  def update_metrics(self, metrics):
    for key in nvidia.Nvidia().metrics_keys():
      setattr(self, key, getattr(metrics, key))


  def mbtc_per_day(self):
    if self.state in ['active', 'calibrating']:
      hashrates = Calibration().get_hashrates(self)

      return Pools().get_payrate(self, hashrates, self.algos[0]['pool'], self.algos[0]['miner'], self.algos[0]['algo'], self.algos[0]['region'])

    return 0


  def check_hashrate(self):
    hashrates = Calibration().get_hashrates(self)

    if len(self.algos) == 0:
      return

    miner = self.algos[0]['miner']
    algo = self.algos[0]['algo']

    if not miner in hashrates.keys() or not algo in hashrates[miner].keys():
      self.log('warning', 'running uncalibrated algorithm %s with miner %s' % (algo, miner))
      return

    if self.algos[0]['algo'] in Config().get('algorithms.single'):
      baseline = float(hashrates[miner][algo]['hashrate'])
    else:
      baseline = float(hashrates[miner][algo]['hashrate'][0])

    threshold_pc_value = (baseline / 100) * Config().get('hashrate_alert_threshold_percent')

    hr_s = Units().hashrate_str(self.algos[0]['hashrate'][0])
    bl_s = Units().hashrate_str(baseline)

    if self.algos[0]['hashrate'][0] < baseline and (baseline - self.algos[0]['hashrate'][0]) >= threshold_pc_value:
      self.log('warning', 'hashrate %d%% below calibrated rate [%s < %s]' % (Config().get('hashrate_alert_threshold_percent'), hr_s, bl_s))

    if self.algos[0]['hashrate'][0] > baseline and (self.algos[0]['hashrate'][0] - baseline) >= threshold_pc_value:
      self.log('warning', 'hashrate %d%% above calibrated rate [%s > %s]' % (Config().get('hashrate_alert_threshold_percent'), hr_s, bl_s))


  def set_power_limit(self, watts):
    nvidia.Nvidia().set_power_limit(self, watts)


  def apply_profile(self):
    profile = self.get_profile_for_algo()
    nvidia.Nvidia().set_profile(self, self.get_profile_for_algo())


  def get_power_limit_for_algorithm(self, miner_name, algorithm):
    calibrated = Calibration().get('%s.%s.%s' % (self.dclass, miner_name, algorithm))

    if calibrated:
      return calibrated['power_limit']

    return None


  def get_best_miner_for_algorithm(self, algorithm, supported_miners=[]):
    calibration_data = Calibration().get_hashrates(self)

    best_hashrate = 0
    best_miner = None

    if calibration_data:
      for miner_name in calibration_data.keys():
        if algorithm in calibration_data[miner_name].keys() and calibration_data[miner_name][algorithm]["hashrate"] > best_hashrate:
          if Miners().enabled(miner_name) and Miners().is_up(miner_name):
            if supported_miners == [] or miner_name in supported_miners:
              best_hashrate = calibration_data[miner_name][algorithm]["hashrate"]
              best_miner = miner_name

    return best_miner


  def get_current_payrate(self):
    hashrates = Calibration().get_hashrates(self)

    return Pools().get_payrate(self, hashrates, self.algos[0]['pool'], self.algos[0]['miner'], self.algos[0]['algo'], self.algos[0]['region'])


  def get_best_payrate(self):
    hashrates = Calibration().get_hashrates(self)

    return Pools().get_payrate(self, hashrates, self.best_pool, self.best_miner, self.best_algo, self.best_region)


  def power_supported(self):
    return self.default_power_limit_f >0 and self.min_power_limit_f >0 and self.max_power_limit_f >0


  def log_stats(self):
    if Config().get('stats.enable') and len(self.algos) >0:
      if '_' in self.algos[0]['algo']:
        benchmarks = {
          self.algos[0]['algo']: self.algos[0]['hashrate']
        }
      else:
        benchmarks = {
          self.algos[0]['algo']: self.algos[0]['hashrate'][0]
        }

      pool = Pools().pools[self.algos[0]['pool']]

      if '_' in self.algos[0]['algo']:
        algo1, algo2 = self.algos[0]['algo'].split('_')

        gross_mbtc = pool.mbtc_per_day(benchmarks)[self.algos[0]['region']][algo1] + \
          pool.mbtc_per_day(benchmarks)[self.algos[0]['region']][algo2]
      else:
        mbtc_per_day = pool.mbtc_per_day(benchmarks)[self.algos[0]['region']]

        if self.algos[0]['algo'] in mbtc_per_day.keys():
          gross_mbtc = mbtc_per_day[self.algos[0]['algo']]
        else:
          gross_mbtc = 0

      match = re.match("^([\d\.]+)", self.power)
      if match:
        power = float(match.group(1))
        margin = MinotaurGS().calculate_profit_margin_for_card(gross_mbtc, power)
        net_mbtc = (gross_mbtc / 100) * margin
      else:
        net_mbtc = 0

      net_mbtc_s = "%.2f" % (net_mbtc)

      total_watts = nvidia.Nvidia().get_total_power_draw()

      if self.stat and self.stat['algo'] == self.algos[0]['algo'] and self.stat['pool'] == self.algos[0]['pool'] and self.stat['miner'] == self.algos[0]['miner'] and self.stat['region'] == self.algos[0]['region'] and self.stat['net_mbtc'] == net_mbtc_s and self.stat['power'] == self.power_f and self.stat['total_power'] == total_watts:
        return

      Stats().add(self.id, self.dclass, self.algos[0]['pool'], self.algos[0]['miner'], self.algos[0]['algo'], self.algos[0]['region'], self.algos[0]['hashrate'], gross_mbtc, net_mbtc, self.power_f, total_watts)

      self.stat = {
        'algo': self.algos[0]['algo'],
        'pool': self.algos[0]['pool'],
        'miner': self.algos[0]['miner'],
        'region': self.algos[0]['region'],
        'net_mbtc': net_mbtc_s,
        'power': self.power_f,
        'total_power': total_watts
      }
