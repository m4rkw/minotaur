
from singleton import Singleton
import os
import yaml
from log import Log
from nvidia import Nvidia
import time
from config import Config
import re
from ccminer import Ccminer
import math
import signal
import sys
from profiles import Profiles
from miners import Miners
from units import Units
from pools import Pools
from calibration import Calibration

# miners
from excavator import Excavator
from ccminer import Ccminer
from ccminer2 import Ccminer2
from xmrig_nvidia import Xmrig_Nvidia
from ethminer import Ethminer
from ewbf import Ewbf

class Calibrate(object):
  __metaclass__ = Singleton


  def __init__(self):
    self.data_path = os.getenv("HOME") + "/.minotaur"
    self.calibrating_devices = []
    self.miner = None
    self.device_id = None
    self.pin = False

    if not os.path.exists(self.data_path):
      os.mkdir(self.data_path)

    signal.signal(signal.SIGINT, self.sigint_handler)
    signal.signal(signal.SIGHUP, self.sighup_handler)


  def start(self, device, pool_name, miner, algorithm, region, quick=False, force=False):
    self.miner = miner
    self.device = device
    self.default_profile = Config().get('device_profiles.default')

    Miners().reload_config()

    device.pin = {
      'pool_name': pool_name,
      'miner_name': miner.name,
      'algorithm': algorithm,
      'region': region
    }

    if not Config().get('calibration'):
      Log().add('fatal', "calibration config missing from config file")

    for key in ["hashrate_stabilisation_timeout_mins", "hashrate_stabilisation_tolerance", "hashrate_stabilisation_consecutive_readings_required", "algorithm_start_timeout"]:
      if Config().get('calibration.%s' % (key)) == None:
        Log().add('fatal', "missing config option: calibration.%s" % (key))

    if Config().get('calibration.power_tuning.enable'):
      for key in ["decrement_watts", "acceptable_loss_percent"]:
        if not Config().get('calibration.power_tuning.%s' % (key)):
          Log().add('fatal', "missing config option: calibration.power_tuning.%s" % (key))

    Config().set('pools.%s.append_device_id_to_worker_name' % (pool_name), False)

    if pool_name == 'miningpoolhub':
      if Config().get('pools.miningpoolhub.hub_workers.%s' % (algorithm))[-5:] != 'CALIB':
        Config().set('pools.miningpoolhub.hub_workers.%s' % (algorithm), Config().get('pools.miningpoolhub.hub_workers.%s' % (algorithm)) + 'CALIB')
    else:
      if Config().get('pools.%s.worker_name' % (pool_name))[-5:] != 'CALIB':
        Config().set('pools.%s.worker_name' % (pool_name), Config().get('pools.%s.worker_name' % (pool_name)) + "CALIB")

    if quick:
      Config().set('calibration.power_tuning.enable', False)

    profile = Profiles().get_for_device_algo(device, algorithm)

    Log().add('info', '     device id: %d' % (device.id))
    Log().add('info', '          pool: %s' % (pool_name))
    Log().add('info', '  device class: %s' % (device.dclass))
    Log().add('info', 'device profile: %s' % (profile.name))
    Log().add('info', '         miner: %s' % (miner.name))
    Log().add('info', '     algorithm: %s' % (algorithm))
    Log().add('info', '        region: %s' % (region))

    Miners().poll()
    Miners().get_device_state(device)

    if device.state != 'inactive':
      if device.state == 'calibrating':
        device.log('fatal', 'this device is already being used for calibration')

      if force:
        device.log('info', 'terminating existing worker')
        if not device.stop(True):
          device.log('fatal', 'failed to stop existing worker')
      else:
        device.log('fatal', 'unable to start calibration - device is in use (use --force to override)')

    self.set_pin(device.id)

    default_power_limit = device.default_power_limit_f
    min_power_limit = device.min_power_limit_f
    max_power_limit = device.max_power_limit_f

    if max_power_limit == 0:
      device.log('info', 'device does not support power monitoring')
    else:
      device.log('info', 'max power limit: %d W' % (max_power_limit))

    device.log('info', 'stabilisation tolerance: %.2f%%' % (Config().get('calibration.hashrate_stabilisation_tolerance')))

    if Config().get('debug'):
      device.log('debug', 'loading default profile')

    Nvidia().set_default_profile(device)

    if Config().get('debug'):
      device.log('debug', 'initialising pools')

    Pools()

    sample_timeout = Config().get('calibration.hashrate_stabilisation_timeout_mins')

    if default_power_limit != None and Config().get('calibration.power_tuning.enable'):
      device.log('info', 'starting initial run at max power limit [timeout=%dmins]' % (sample_timeout))
    else:
      device.log('info', 'starting single run [timeout=%dmins]' % (sample_timeout))

    Miners().poll()
    Miners().get_device_state(device)

    if device.state != 'calibrating':
      if not device.start(True):
        device.log('fatal', 'worker failed to start')

    if Config().get('calibration.power_tuning.enable'):
      if not device.power_supported():
        device.log('info', 'device does not support power monitoring')
      else:
        device.set_power_limit(max_power_limit)

    initial_hashrate, initial_max_power_draw = self.get_max_hashrate_and_power_draw(miner, device, sample_timeout * 60)

    if initial_hashrate == None:
      device.log('info', 'skipping algorithm as we failed to get a stable reading')
      print ""
      return

    if initial_max_power_draw != None and initial_max_power_draw > max_power_limit:
      initial_max_power_draw = max_power_limit

    device.log('info', 'benchmark hashrate: %s' % (Units().hashrate_str(initial_hashrate)))

    if initial_max_power_draw != None:
      device.log('info', 'max power draw: %.2f' % (initial_max_power_draw))
      initial_power_limit = int(math.ceil(initial_max_power_draw))

    hashrate = initial_hashrate

    if initial_max_power_draw == None:
      power_limit = None
    elif Config().get('calibration.power_tuning.enable'):
      if max_power_limit == 0 or min_power_limit == 0 or default_power_limit == 0:
        device.log('error', 'device did not give us sane values for its min/max/default power limits')
        device.log('error', 'unable to proceed with power calibration - device may not support changing the power limit')

        power_limit = default_power_limit
      else:
        power_limit = initial_power_limit

        device.log('info', 'tuning power limit for optimum efficiency')
        hashrate, power_limit = self.do_power_calibration(device, power_limit, miner, hashrate, min_power_limit)
    else:
      power_limit = default_power_limit

    Nvidia().set_default_profile(device)

    self.unset_pin(device.id)

    device.log('info', 'storing calibration data')

    Calibration().update_calibration_data(device.dclass, miner.name, algorithm, hashrate, power_limit)

    if not device.stop(True):
      device.log('fatal', "failed to stop the miner process")

    print ""

    device.log('info', '   calibrated hashrate: %s' % (Units().hashrate_str(hashrate)))

    if power_limit != None:
      device.log('info', 'calibrated power limit: %.2f W' % (power_limit))

    print ""


  def set_pin(self, device_id):
    with open("/var/run/minotaur/pin%d" % (device_id), "w") as f:
      f.write(yaml.dump({"calibration":True}))


  def unset_pin(self, device_id):
    if os.path.exists("/var/run/minotaur/pin%d" % (device_id)):
      os.remove("/var/run/minotaur/pin%d" % (device_id))


  def get_max_hashrate_and_power_draw(self, miner, device, time_limit):
    max_power_draw = 0

    timeout = 30
    count = 0

    while len(device.algos) == 0:
      time.sleep(1)
      Miners.poll()
      count += 1

      if count >= 30:
        device.log('fatal', 'timed out waiting for worker to start')

    algorithm = device.algos[0]['algo']

    if "_" in algorithm:
      readings_a = []
      readings_b = []
    else:
      readings = []

    time_start = time.time()
    count = 0
    err = 0
    reading_count = 0
    stable = False
    variance_pc = None

    while stable == False and (time.time() - time_start) <= time_limit:
      time.sleep(1)

      if count % 5 == 0:
        Miners().poll()

        if not Miners().is_up(miner.name):
          device.log('fatal', 'miner API went away, aborting')

        Miners().get_device_state(device)

        if len(device.algos) == 0:
          device.log('fatal', 'worker was stopped by an external process')

        rate_a, rate_b = device.algos[0]['hashrate']

        if "_" in algorithm:
          r_len = len(readings_a)
        else:
          r_len = len(readings)

        if r_len >0:
          if "_" in algorithm:
            variance_pc, n = Calibration().get_variance(readings_a + [rate_a], readings_b + [rate_b])
          else:
            variance_pc, n = Calibration().get_variance(readings + [rate_a])

          device.log('info', 'hashrate: %s (variance %.2f%%)' % (device.hashrate_str(), variance_pc))
        else:
          device.log('info', 'hashrate: %s' % (device.hashrate_str()))

        if rate_a == 0:
          if reading_count >= 3:
            device.log('warning', 'hashrate dropped to 0!')

            if device.state != 'calibrating':
              device.log('fatal', 'our worker was stopped by an external process, aborting.')

            err += 1

            if err >= 10:
              device.stop()
              device.log('fatal', 'failed to get a hashrate reading from the worker')
        else:
          if "_" in algorithm:
            readings_a.append(rate_a)
            readings_b.append(rate_b)
          else:
            readings.append(rate_a)

          if variance_pc != None and Calibration().is_stable(variance_pc, n):
            device.log('info', 'hashrate stabilised')
            stable = True

        reading_count += 1

      count += 1

      metrics = Nvidia().get_nvidia_metrics_for_device(device.id)

      if metrics['power_f']:
        max_power_draw = metrics['power_f']
      else:
        max_power_draw = None

    if stable == False:
      device.stop(True)

      device.log('error', 'hashrate failed to stabilise after %d minutes\ntry increasing the timeout or loosen the stabilisation tolerance by increasing the "hashrate_stabilisation_tolerance" parameter' % (time_limit / 60))

      return [None, None]

    if "_" in algorithm:
      hashrate = [Calibration().get_nominal_hashrate_from_range(readings_a), Calibration().get_nominal_hashrate_from_range(readings_b)]
    else:
      hashrate = Calibration().get_nominal_hashrate_from_range(readings)

    return [hashrate, max_power_draw]


  def do_power_calibration(self, device, power_limit, miner, initial_hashrate, min_power_limit):
    sample_timeout = Config().get('calibration.hashrate_stabilisation_timeout_mins')
    acceptable_loss_pc = Config().get('calibration.power_tuning.acceptable_loss_percent')

    dial_back = False
    dialed_back = False
    hashrate = initial_hashrate

    if "_" in device.algos[0]['algo']:
      initial_value = initial_hashrate[0]
    else:
      initial_value = initial_hashrate

    while True:
      if dial_back:
        power_limit += Config().get('calibration.power_tuning.decrement_watts') / 2
        dialed_back = True
      else:
        power_limit -= Config().get('calibration.power_tuning.decrement_watts')

      if power_limit < min_power_limit:
        power_limit = min_power_limit

      device.log('info', 'setting power limit: %d W' % (power_limit))

      device.set_power_limit(power_limit)

      new_hashrate, max_power_draw = self.get_max_hashrate_and_power_draw(miner, device, sample_timeout * 60)

      if new_hashrate == None:
        device.log('info', 'skipping algorithm as we failed to get a stable reading')
        print ""
        return

      if "_" in device.algos[0]['algo']:
        new_value = new_hashrate[0]
      else:
        new_value = new_hashrate

      device.log('info', 'nominal hashrate: %s' % (Units().hashrate_str(new_hashrate)))

      if new_value > initial_value:
        device.log('info', 'hashrate is higher than before, w00t!')
        hashrate = new_hashrate
        initial_value = new_value
      elif new_value >= (initial_value - (initial_value / 100) * acceptable_loss_pc):
        hashrate = new_hashrate
        if power_limit == min_power_limit or dial_back:
          device.log('info', 'hashrate loss is within acceptable %.2f%%' % (acceptable_loss_pc))
        else:
          device.log('info', 'hashrate loss is within acceptable %.2f%%, continuing' % (acceptable_loss_pc))
      else:
        if dial_back or Config().get('calibration.power_tuning.decrement_watts') == 1:
          device.log('info', 'hashrate still below our acceptable loss level of %.2f%%, stopping' % (acceptable_loss_pc))

          if Config().get('calibration.power_tuning.decrement_watts') == 1:
            power_limit += 1
          else:
            power_limit += Config().get('calibration.power_tuning.decrement_watts') / 2
          break
        else:
          device.log('info', 'hashrate fell below our acceptable loss level of %.2f%%, dialling back %d W' % (acceptable_loss_pc, Config().get('calibration.power_tuning.decrement_watts') / 2))
          dial_back = True

      if dialed_back:
        break

      if power_limit == min_power_limit and not dial_back:
        device.log('info', 'minimum power limit reached, stopping')
        break

    return [hashrate, power_limit]


  def sigint_handler(self, a, b):
    Log().add('info', 'interrupt received, cleaning up')

    Miners().poll()
    Miners().get_device_state(self.device)

    if self.device.state == 'calibrating':
      self.device.stop(True)

    self.unset_pin(self.device.id)

    sys.exit(0)


  def sighup_handler(self, a, b):
    pass
