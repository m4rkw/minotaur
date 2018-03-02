#!/usr/bin/env python

import sys
import os
import datetime
import yaml
import re
from multiprocessing import Process, Queue
import time
import json
from log import Log
import curses
import pickle
import urllib2
import signal
from nvidia import Nvidia
from log import Log
import socket
from config import Config
from gs import MinotaurGS
import math
from calibrate import Calibrate
import fcntl
import hashlib
from calibration import Calibration
from miners import Miners
from pools import Pools
from version import Version
from device import Device
import urllib2
from stats import Stats
from dateutil import parser
from shutil import copyfile
import random

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

class NoRedirection(urllib2.HTTPErrorProcessor):
  def http_response(self, request, response):
    return response

  https_response = http_response


class Minotaur:
  def __init__(self):
    self.data_path = os.getenv("HOME") + "/.minotaur"
    if not os.path.exists(self.data_path):
      os.mkdir(self.data_path)

    self.power_file = self.data_path + "/power.dat"
    self.profitability_file = self.data_path + "/profitability.dat"
    self.currency_rate_file = self.data_path + "/currencies.dat"

    self.startup_time = time.time()
    Config().load()


  def already_running(self):
    if not os.path.exists("/var/run/minotaur"):
      try:
        ok.mkdir("/var/run/minotaur", 0755)
      except:
        Log().add('fatal', 'unable to create /var/run/minotaur')

    if os.path.exists("/var/run/minotaur/minotaur.pid"):
      pid = open("/var/run/minotaur/minotaur.pid").read().rstrip()

      return pid.isdigit() and os.path.exists("/proc/%s" % (pid))


  def create_pid_file(self):
    if self.already_running():
      Log().add('fatal', 'unable to start, there is another minotaur process running')

    with open("/var/run/minotaur/minotaur.pid", "w") as f:
      f.write("%d" % (os.getpid()))


  def banner(self):
    version = Version().get()

    line = "-" * (20 + len(version))

    print
    print "  /%s/" % (line)
    print " / minotaur %s by m4rkw /" % (version)
    print "/%s/" % (line)
    print


  def usage(self):
    self.banner()
    print "usage: %s [command] [options]" % (sys.argv[0])
    print
    print "## quickstart"
    print
    print " %s --quickstart" % (sys.argv[0])
    print
    print "quickstart mode will calibrate the 5 most profitable Nicehash algorithms"
    print "in fast mode (no power tuning) and then start mining. See the README for"
    print "more information."
    print
    print "## calibration"
    print
    print " %s --calibrate <device id / name / class | all> <pool (nicehash/ethermine/all)> <miner> <algorithms | all> [region (eu/usa)] [--quick] [--overwrite] [--force]" % (sys.argv[0])
    print
    print "     --quick : skip power calibration and just do the initial run at default power"
    print " --overwrite : replace existing calibration data"
    print "     --force : take-over a device from minotaur and use it for calibration"
    print
    print "## mining"
    print
    print " %s --mine" % (sys.argv[0])
    print
    print "## misc"
    print
    print " %s --devices                                         # list devices" % (sys.argv[0])
    print " %s --algos                                           # list algorithms and calibrated hashrates" % (sys.argv[0])
    print " %s --cleanup                                         # stop workers (not calibration runs)" % (sys.argv[0])
    print " %s --cleanup <device id>                             # stop workers for device" % (sys.argv[0])
    print " %s --cleanup-all                                     # stop all workers (including calibration runs)" % (sys.argv[0])
    print " %s --pin <device id> <pool> <miner> <algo> [region]  # pin a device to a specific miner+algorithm" % (sys.argv[0])
    print " %s --pin <device id> idle                            # pin a device to idle (ie don't use)" % (sys.argv[0])
    print " %s --unpin <device id>                               # unpin a device from a specific miner+algorithm" % (sys.argv[0])
    print " %s --stats [hours]                                   # show stats (default last 24 hours)" % (sys.argv[0])
    print " %s --help                                            # display this help page" % (sys.argv[0])
    print
    sys.exit()


  def initialise(self):
    self.banner()

    Log().add("info", "initialising")

    self.check_for_update()

    Pools()
    Miners()

    Log().add("info", "scanning devices")

    self.scan_devices()

    

  def check_for_update(self):
    try:
      opener = urllib2.build_opener(NoRedirection, urllib2.HTTPCookieProcessor())

      resp = opener.open("https://github.com/m4rkw/minotaur/releases/latest")

      latest_version = resp.headers['Location'].split('/')[-1][1:]

      if self.is_newer(latest_version, Version().get()):
        Log().add('info', 'new version available: v%s' % (latest_version))
    except:
      Log().add('warning', 'failed to check for updates')
      pass


  def is_newer(self, latest_version, current_version):
    latest_version = latest_version.replace('v', '').split(".")
    current_version = current_version.replace('v', '').split(".")

    if int(latest_version[0]) > int(current_version[0]):
      return True
    elif int(latest_version[0]) < int(current_version[0]):
      return False

    if int(latest_version[1]) > int(current_version[1]):
      return True
    elif int(latest_version[1]) < int(current_version[1]):
      return False

    if len(latest_version) >2 and len(current_version) <3:
      return True

    if len(latest_version) >2 and len(current_version) <3:
      return True

    if len(latest_version) >2 and len(current_version) >2:
      return int(latest_version[2]) > int(current_version[2])

    return False


  def sigint_handler(self, a, b):
    Log().add('info', 'interrupt received, cleaning up')

    try:
      Miners().cleanup_workers()
    except:
      pass

    sys.exit(0)


  def cleanup(self, all=0, device_id=None):
    if all:
      Miners().cleanup_workers(True)
    elif not all and not device_id:
      Miners().cleanup_workers(False)
    else:
      device = Device({"id": device_id})

      Nvidia().set_default_profile(device)
      Miners().stop_device(device)

    sys.exit(0)


  def scan_devices(self):
    self.devices = Nvidia().get_nvidia_devices()

    Calibration().load()

    if len(self.devices) <1:
      Log().add('fatal', "no nvidia GPUs found")

    Log().add("info", "found %d nvidia GPUs" % (len(self.devices)))

    Calibration().check_calibrated_algorithms(self.devices)

    Log().add('info', 'retrieving state from miner backends')

    Miners().poll()

    for device in self.devices:
      device.update()

      if device.state == 'active':
        device.log('info', 'currently running algorithm %s with %s [profile=%s] [region=%s]' % (device.algos[0]['algo'], device.algos[0]['miner'], device.profile, device.algos[0]['region']))
        device.apply_profile()
      elif device.state == 'calibrating':
        device.log('info', 'calibration in progress with algorithm %s using %s [region=%s]' % (device.algos[0]['algo'], device.algos[0]['miner'], device.algos[0]['region']))

      device.period_start = self.startup_time
      device.grubtime = device.period_start + (60 * random.randrange(15, 1424))


  def run(self):
    self.create_pid_file()
    self.initialise()

    signal.signal(signal.SIGINT, self.sigint_handler)
    signal.signal(signal.SIGTERM, self.sigint_handler)
    signal.signal(signal.SIGHUP, self.sighup_handler)

    power_draw_readings = self.load_power_draw_readings()
    profitability_readings = self.load_profitability_readings()

    main_loop_index = 0

    self.miner_state = {}
    self.pool_refresh = None

    while True:
      if main_loop_index == 0:

        if self.pool_refresh == None or (time.time() - self.pool_refresh) >= Config().get('pool_refresh_interval'):
          Pools().refresh()
          self.pool_refresh = time.time()

        show_mbtc_total = False

        Miners().poll()

        for i in range(0, len(self.devices)):
          device = self.devices[i]

          device.update()
          device.log_stats()

          if not device.can_run():
            continue

          #device.grubtime = self.startup_time += (60 * random.randrange(15, 1424))
#          if device.grub == False and time.time() >= device.grubtime and time.time() <= (device.grubtime + (60 * 15)):
#            device.log('info', 'starting 15min donation period to the author')
#            device.grub = True
#
#            Miners().schedule('restart', device)
#          elif device.grub == True and time.time() < device.grubtime or time.time() > (device.grubtime + (60 * 15)):
#            device.log('info', 'stopping donation period')
#            device.grub = False
#            device.period_start += 86400
#            device.grubtime = device.period_start + (60 * random.randrange(15, 1424))
#
#            while not self.grubtime_is_unique(device.grubtime, i):
#              device.grubtime = device.period_start + (60 * random.randrange(15, 1424))
#
#            Miners().schedule('restart', device)
#          else:
          if True:
            if not device.running():
              if Config().get('debug'):
                device.log('debug', 'device not running - starting worker')

              Miners().schedule('start', device)
            else:
              switched = False

              if not device.pin:
                if Pools().should_switch(device):
                  Miners().schedule('restart', device)
                  switched = True

              if not switched and Config().get('calibration.update_calibration_data_over_time'):
                Calibration().handle_device_update(device)

        queued_device_ids = Miners().queue.keys()
        Miners().execute_queue()

        for device in self.devices:
          if device.state == 'active' and device.id not in queued_device_ids and not device.warming_up():
            show_mbtc_total = True

            device.log('info', '%s/%s[%s]: %s' % (device.algos[0]['pool'], device.algos[0]['algo'], device.algos[0]['miner'], device.hashrate_str()))
            device.check_hashrate()

        total_power, total_power_limit, total_mbtc_per_day = Nvidia().get_device_metrics(self.devices)

        if show_mbtc_total:
          Log().add('info', 'total profitability: %.2f mBTC/day' % (total_mbtc_per_day))

        power_draw_readings = self.update_power_draw_readings(power_draw_readings, total_power + Config().get('system_draw_watts'))
        profitability_readings = self.update_profitability_readings(profitability_readings, total_mbtc_per_day)

        # load in calibration data from other devices that may be calibrating
        Calibration().load()

      Miners().wait_for_queue()

      time.sleep(1)

      main_loop_index += 1

      if main_loop_index >= Config().get('refresh_interval'):
        main_loop_index = 0


  def grubtime_is_unique(self, grubtime, i):
    _from = grubtime
    _to = grubtime + (15 * 60)

    for j in range(0, len(self.devices)):
      if i != j:
        _from2 = self.devices[j].grubtime
        _to2 = _from2 + (15 * 60)

        for x in range(_from2, _to2):
          if x in range(_from, _to):
            return False

    return True


  def load_power_draw_readings(self):
    if os.path.exists(self.power_file) and os.path.getsize(self.power_file) >0:
      return pickle.loads(open(self.power_file).read())

    return []


  def load_profitability_readings(self):
    if os.path.exists(self.profitability_file) and os.path.getsize(self.profitability_file) >0:
      return pickle.loads(open(self.profitability_file).read())

    return []


  def trim_readings(self, readings, max_time):
    new_readings = []

    for reading in readings:
      if int(time.time()) - reading["timestamp"] <= max_time:
        new_readings.append(reading)

    return new_readings


  def update_power_draw_readings(self, power_draw_readings, total_power):
    power_draw_readings.append({"timestamp": int(time.time()), "reading": total_power})
    power_draw_readings = self.trim_readings(power_draw_readings, max(Config().get('live_data')['power_draw_averages']))

    with open(self.power_file + ".new","w") as f:
      f.write(pickle.dumps(power_draw_readings))
    os.rename(self.power_file + ".new", self.power_file)

    return power_draw_readings


  def update_profitability_readings(self, profitability_readings, total_mbtc_per_day):
    profitability_readings.append({"timestamp": int(time.time()), "reading": total_mbtc_per_day})
    profitability_readings = self.trim_readings(profitability_readings, max(Config().get('live_data')['profitability_averages']))

    with open(self.profitability_file + ".new","w") as f:
      f.write(pickle.dumps(profitability_readings))
    os.rename(self.profitability_file + ".new", self.profitability_file)

    return profitability_readings


  def sighup_handler(self, x, y):
    Log().add('info', 'SIGHUP caught, reloading config and benchmark data')

    Config().reload()
    Calibration().load()
    Miners().reload_config()

    for device in Nvidia().get_nvidia_devices():
      if not self.device_in_list(device):
        device.update()

        if device.state == 'active':
          device.log('info', 'currently running algorithm %s with %s [profile=%s] [region=%s]' % (device.algos[0]['algo'], device.algos[0]['miner'], device.profile, device.algos[0]['region']))
        elif device.state == 'calibrating':
          device.log('info', 'calibration in progress with algorithm %s using %s [region=%s]' % (device.algos[0]['algo'], device.algos[0]['miner'], device.algos[0]['region']))

        self.devices.append(device)

    for device in self.devices:
      if device.state == 'active':
        device.apply_profile()

    Log().add('info', 'reload complete')


  def device_in_list(self, device):
    for l_device in self.devices:
      if l_device.id == device.id:
        return True

    return False


  def calibration_banner(self):
    print "-" * 84
    Log().add('info', 'PLEASE NOTE: this process will not automatically overclock your card unless')
    Log().add('info', 'you have enabled overclocking and configured a device profile with overclock')
    Log().add('info', 'settings. You and you alone are responsible for any overclock settings that')
    Log().add('info', 'you want to run this benchmark process with. We do not advise overclocking')
    Log().add('info', 'and are not responsible for any hardware damage that may occur when using')
    Log().add('info', 'this tool.')
    print "-" * 84


  def calibrate(self, device_params, pool, miner_name, algorithm, region, quick, overwrite, force):
    devices = Nvidia().get_nvidia_devices(1)

    if pool == 'nicehash' and region not in ['eu', 'usa', 'hk', 'jp', 'in', 'br']:
      Log().add('fatal', 'a valid region is required for nicehash')

    devices_to_calibrate = []
    device_classes = []

    for device_param in device_params.split(','):
      if device_param.isdigit():
        if int(device_param) >= len(devices):
          Log().add('fatal', 'device %d not found' % (int(device_param)))
        else:
          devices_to_calibrate.append(devices[int(device_param)])
      else:
        found = False
        for device in devices:
          if device.name == device_param:
            devices_to_calibrate.append(device)
            found = True
          elif (device_param == 'all' or device.dclass == device_param) and device.dclass not in device_classes:
            devices_to_calibrate.append(device)
            device_classes.append(device.dclass)
            found = True

        if not found:
          Log().add('fatal', 'device %s not found' % (device_param))

    log_dir = Config().get('logging.calibration_log_dir')

    if not log_dir:
      log_dir = "/var/log/minotaur"

    if miner_name == "all":
      miners = []

      for miner_name in Config().get('miners').keys():
        if Config().get('miners')[miner_name]['enable']:
          miners.append(eval("%s()" % (miner_name.title())))
    else:
      if not miner_name in Config().get('miners').keys():
        Log().add('fatal', 'miner %s is not configured' % (miner_name))

      miners = [eval("%s()" % (miner_name.title()))]

    if len(miners) == 0:
      Log().add('fatal', "no miners available")

    if pool == 'all':
      pools = []
      for pool_name in Config().get('pools').keys():
        if Config().get('pools.%s.enable' % (pool_name)):
          pools.append(pool_name)
    elif pool not in Config().get('pools').keys():
      Log().add('fatal', 'unknown pool: %s' % (pool))
    else:
      pools = [pool]

    algorithms = {}

    for pool_name in pools:
      algorithms[pool_name] = {}

      for miner in miners:
        if not pool_name in Pools().pools.keys():
          Log().add('fatal', 'pool %s is not enabled' % (pool_name))

        pool = Pools().pools[pool_name]

        if miner.name not in pool.supported_miners:
          continue

        if algorithm == "all":
          algorithms[pool_name][miner.name] = miner.supported_algorithms()
        else:
          algorithms[pool_name][miner.name] = []

          for algo_param in algorithm.split(","):
            if algo_param == 'all':
              algorithms[pool_name][miner.name] = miner.supported_algorithms()
            else:
              if algo_param[0] == '!':
                exclude_algo = algo_param[1:]

                if miner.name in algorithms.keys() and exclude_algo in algorithms[miner.name]:
                  algorithms[pool_name][miner.name].remove(exclude_algo)
              else:
                if algo_param in miner.supported_algorithms():
                  algorithms[pool_name][miner.name].append(algo_param)

    print ""
    self.calibration_banner()
    print ""

    n = 0

    for device in devices_to_calibrate:
      log_file = "%s/calibration_%d.log" % (log_dir, device.id)
      Log().set_log_file(log_file)

      for pool_name in algorithms.keys():
        for miner in miners:
          if miner.name in algorithms[pool_name].keys():
            for algorithm in algorithms[pool_name][miner.name]:
              n += 1

              if algorithm in Config().get('algorithms.single') or algorithm in Config().get('algorithms.double'):
                Calibration().load()

                if not overwrite and Calibration().get('%s.%s.%s' % (device.dclass, miner.name, algorithm)):
                  device.log('info', 'not overwriting existing calibration data for miner %s algorithm %s (use --overwrite to override)' % (miner.name, algorithm))
                else:
                  Calibrate().start(device, pool_name, miner, algorithm, region, quick, force)
              else:
                Log().add('warning', 'algorithm %s is not in the config file - skipping' % (algorithm))

    Log().add('info', 'nothing to do.')


  def print_devices(self):
    for device in Nvidia().get_nvidia_devices(1):
      print "%d: %s [class: %s]" % (device.id, device.name, device.dclass)

    sys.exit()


  def print_algorithms(self):
    algorithms = Config().get('algorithms.single') + Config().get('algorithms.double')

    Calibration().load()

    device_classes = Nvidia().get_nvidia_device_classes()

    for device_class in device_classes:
      data = {}

      for algorithm in algorithms:
        data[algorithm] = {}

        for miner_name in Config().get('miners'):
          miner = eval('%s()' % (miner_name.title()))

          if algorithm in miner.supported_algorithms():
            data[algorithm][miner_name] = Calibration().get_miner_hashrate_for_algorithm_on_device(miner_name, algorithm, device_class)
          else:
            data[algorithm][miner_name] = "-"

      self.display_device_algorithm_table(device_class, data)

    print "\nnote: - means not supported\n"


  def display_device_algorithm_table(self, device_class, data):
    print "\n"

    algo_width = self.get_width(data.keys()) + 2
    total_width = algo_width

    sys.stdout.write(device_class.ljust(algo_width))

    miner_widths = {}

    for miner_name in sorted(Config().get('miners').keys()):
      miner_widths[miner_name] = self.get_miner_width(data, miner_name) + 2
      total_width += miner_widths[miner_name] + 2

      sys.stdout.write(miner_name.rjust(miner_widths[miner_name]))

    sys.stdout.write("\n")
    sys.stdout.write("-" * total_width)
    sys.stdout.write("\n")
    sys.stdout.flush()

    for algorithm in sorted(data.keys()):
      sys.stdout.write(algorithm.ljust(algo_width))

      for miner_name in sorted(data[algorithm].keys()):
        sys.stdout.write(data[algorithm][miner_name].rjust(miner_widths[miner_name]))

      sys.stdout.write("\n")


  def get_width(self, values):
    width = 0

    for s in values:
      if len(s) > width:
        width = len(s)

    return width


  def get_miner_width(self, data, miner_name):
    width = len(miner_name)

    for a in data.keys():
      if len(data[a][miner_name]) >width:
        width = len(data[a][miner_name])

    return width


  def get_miners_for_algorithm(self, algorithm):
    miners = []

    for miner_name in Config().get('miners'):
      if Config().get('miners')[miner_name]['enable']:
        miner = eval('%s()' % (miner_name.title()))

        if algorithm in miner.supported_algorithms():
          miners.append(miner_name)

    return miners


  def pin(self, device_id, pool_name, pin_miner_name, algorithm, region):
    device_ids = []

    if device_id == 'all':
      for device in Nvidia().get_nvidia_devices():
        device_ids.append(device.id)
    else:
      for device_id in device_id.split(","):
        device_ids.append(int(device_id))

    if len(device_ids) == 0:
      Log().add('fatal', 'no devices selected')

    for device_id in device_ids:
      device = Device({"id": int(device_id)})

      if pool_name not in Config().get('pools').keys():
        Log().add('fatal', 'unknown pool')

      if not algorithm in Config().get('algorithms.single') and not algorithm in Config().get('algorithms.double'):
        Log().add('fatal', 'unknown algorithm')

      if pool_name != 'nicehash':
        region = None
      else:
        if region not in ['eu', 'usa', 'hk', 'jp', 'in', 'br']:
          Log().add('fatal', 'valid region is required for nicehash')

      Miners().poll()
      Miners().get_device_state(device)

      if device.state == "calibrating":
        Log().add('fatal', 'not pinning device %d - currently calibrating' % (device.id))

      pin = {
        "pool_name": pool_name,
        "miner_name": pin_miner_name,
        "algorithm": algorithm,
        "region": region
      }

      with open("/var/run/minotaur/pin%d" % (device.id), "w") as f:
        f.write(yaml.dump(pin))

      Log().add('info', 'pinned device %d to miner: %s pool %s algorithm: %s region: %s' % (device.id, pin_miner_name, pool_name, algorithm, region))


  def pin_idle(self, device_id):
    pin = {
      "idle": True
    }

    device_ids = []

    if device_id == 'all':
      for device in Nvidia().get_nvidia_devices():
        device_ids.append(device.id)
    else:
      for device_id in device_id.split(","):
        device_ids.append(int(device_id))

    if len(device_ids) == 0:
      Log().add('fatal', 'no devices selected')

    for device_id in device_ids:
      device = Device({"id": int(device_id)})

      with open("/var/run/minotaur/pin%d" % (device.id), "w") as f:
        f.write(yaml.dump(pin))

      Log().add('info', 'pinned device %d to idle' % (device.id))


  def pin_calibration(self, device_id):
    pin = {
      "calibration": True
    }

    device_ids = []

    if device_id == 'all':
      for device in Nvidia().get_nvidia_devices():
        device_ids.append(device.id)
    else:
      for device_id in device_id.split(","):
        device_ids.append(int(device_id))

    if len(device_ids) == 0:
      Log().add('fatal', 'no devices selected')

    for device_id in device_ids:
      device = Device({"id": int(device_id)})

      with open("/var/run/minotaur/pin%d" % (device.id), "w") as f:
        f.write(yaml.dump(pin))

      Log().add('info', 'pinned device %d to calibration' % (device.id))


  def unpin(self, device_id):
    device_ids = []

    if device_id == 'all':
      for device in Nvidia().get_nvidia_devices():
        device_ids.append(device.id)
    else:
      for device_id in device_id.split(","):
        device_ids.append(int(device_id))

    if len(device_ids) == 0:
      Log().add('fatal', 'no devices selected')

    for device_id in device_ids:
      device_id = int(device_id)

      if os.path.exists("/var/run/minotaur/pin%d" % (device_id)):
        os.remove("/var/run/minotaur/pin%d" % (device_id))
        Log().add('info', 'unpinned device %d' % (device_id))
      else:
        Log().add('info', 'device %d is not pinned' % (device_id))


  def device_pinned(self, device_id):
    if os.path.exists("/var/run/minotaur/pin%d" % (device_id)):
      return yaml.load(open("/var/run/minotaur/pin%d" % (device_id)).read())

    return False


  def stats(self, hours=24):
    if hours == 1:
      suffix = ''
    else:
      suffix = 's'

    print "\nstats for the last %d hour%s:\n" % (hours, suffix)

    stats_file = "/var/log/minotaur/minotaur.csv"

    if not os.path.exists(stats_file):
      print "%s not found" % (stats_file)
      sys.exit(1)
    else:
      total = 0
      algos = {}
      devices = {}

      logs = Stats().get_logs_for_period(stats_file, hours)
      width = 0

      for item in logs:
        if len(item['algorithm']) > width:
          width = len(item['algorithm'])

        if item['device_id'] not in devices.keys():
          devices[item['device_id']] = item
        else:
          time_on_algo = (parser.parse(item['timestamp']) - parser.parse(devices[item['device_id']]['timestamp'])).seconds
          if devices[item['device_id']]['net_mbtc'] != '':
            net = float(devices[item['device_id']]['net_mbtc'])

          earning = (net / 86400) * time_on_algo

          if item['algorithm'] not in algos.keys():
            algos[item['algorithm']] = 0

          total += earning
          algos[item['algorithm']] += earning

          devices[item['device_id']] = item

      print " from: %s" % (logs[0]['timestamp'])
      print "   to: %s\n" % (logs[len(logs)-1]['timestamp'])

      total_s = "%.2f" % (total)

      print "total: %s mBTC" % (total_s.rjust(7))

      if os.path.exists(self.currency_rate_file):
        exchange_rate = pickle.loads(open(self.currency_rate_file).read())

        fiat = (total / 1000) * float(exchange_rate['rate'])
        fiat_s = "%.2f" % (fiat)

        print "       %s  %s" % (fiat_s.rjust(7), Config().get('electricity_currency'))

      total_seconds = hours * 3600
      rate = ((total / total_seconds) * 86400)

      rate_s = "%.2f" % (rate)

      print "\n rate: %s mBTC/day" % (rate_s.rjust(7))

      if os.path.exists(self.currency_rate_file):
        exchange_rate = pickle.loads(open(self.currency_rate_file).read())

        fiat = (rate / 1000) * float(exchange_rate['rate'])

        day_s = "%.2f" % (fiat)
        month_s = "%.2f" % (fiat * 30)

        print "       %s  %s/day" % (day_s.rjust(7), Config().get('electricity_currency'))
        print "       %s  %s/month" % (month_s.rjust(7), Config().get('electricity_currency'))

      print "\nincome by algorithm:\n"

      for w in sorted(algos, key=algos.get, reverse=True):
        if os.path.exists(self.currency_rate_file):
          exchange_rate = pickle.loads(open(self.currency_rate_file).read())

          fiat = (algos[w] / 1000) * float(exchange_rate['rate'])

          suffix = "  %.2f %s" % (fiat, Config().get('electricity_currency'))
        else:
          suffix = ""

        print "%s: %.4f mBTC%s" % (w.rjust(width), algos[w], suffix)

      print ""

      sys.exit()


  def get_latest_version(self):
    opener = urllib2.build_opener(NoRedirection, urllib2.HTTPCookieProcessor())
    resp = opener.open("https://github.com/m4rkw/minotaur/releases/latest")
    return resp.headers['Location'].split('/')[-1][1:]


  def upgrade(self):
    print "checking for update"

    latest_version = self.get_latest_version()
    current_version = Version().get
    current_version = '0.8.9'

    if self.is_newer(latest_version, current_version):
      print 'new version available: v%s' % (latest_version)

      sys.stdout.write('upgrade? (y/n) ')
      line = sys.stdin.readline()
      if line[0].lower() == 'y':
        self.do_upgrade()
    else:
      print 'you are already running the latest version.'


  def do_upgrade(self):
    if os.getuid() != 0:
      print 'elevating with sudo, you may need to enter your password below..'
      os.system("sudo %s --do-upgrade" % (sys.argv[0]))
      sys.exit(0)
    else:
      latest_version = self.get_latest_version()
      print "downloading minotaur-%s_centos7.tar.gz" % (latest_version)
      os.system("curl -L -s -o /tmp/minotaur.tar.gz https://github.com/m4rkw/minotaur/releases/download/v%s/minotaur-%s_centos7.tar.gz" % (latest_version, latest_version))
      os.system("tar -C /tmp -zxf /tmp/minotaur.tar.gz")

      print "installing minotaur"
      copyfile("/tmp/minotaur-%s/minotaur" % (latest_version), sys.argv[0])

      print "cleaning up"
      os.system("rm -rf /tmp/minotaur-%s /tmp/minotaur.tar.gz" % (latest_version))

      print "done!"

    sys.exit(0)


m = Minotaur()

for i in range(1, len(sys.argv)):
  if sys.argv[i] in ["-h", "--help"]:
    m.usage()
  if sys.argv[i] == "--config-file":
    if (i+1) >= len(sys.argv):
      m.usage()
    m.config_file = sys.argv[i+1]
  if sys.argv[i] == '--gs-stat':
    m = MinotaurGS()
    m.initialise()
    minimal = False
    if len(sys.argv) >2 and sys.argv[i+1] == '--minimal':
      minimal = True
    m.gs_stat(minimal)
    sys.exit()
  if sys.argv[i] == '--gs':
    if len(sys.argv) >2 and sys.argv[i+1] == '--mobile':
      mobile = True
    else:
      mobile = False
    m = MinotaurGS(mobile)
    m.initialise()
    os.system('clear')
    curses.wrapper(m.gs)
    sys.exit()
  if sys.argv[i] == '--calibrate':
    # minotaur --calibrate <device_id/name/class> <miner> <algorithm> [region (eu/usa)] --quick --overwrite
    if len(sys.argv) <6:
      m.usage()

    region = None
    quick = False
    overwrite = False
    force = False

    if len(sys.argv) >6:
      for i in range(6, len(sys.argv)):
        if sys.argv[i] == '--quick':
          quick = True
        elif sys.argv[i] == '--overwrite':
          overwrite = True
        elif sys.argv[i] == '--force':
          force = True
        else:
          region = sys.argv[i]

    args = sys.argv[2:6] + [region, quick, overwrite, force]

    m.calibrate(*args)
    sys.exit(0)
  if sys.argv[i] == '--cleanup':
    if m.already_running():
      Log().add('fatal', 'cannot clean up while minotaur is running')

    if len(sys.argv) >2 and sys.argv[i+1].isdigit():
      device_id = int(sys.argv[i+1])
    else:
      device_id = None
      
    m.cleanup(0, device_id)
    sys.exit(0)
  if sys.argv[i] == '--cleanup-all':
    if m.already_running():
      Log().add('fatal', 'cannot clean up while minotaur is running')

    m.cleanup(1)
    sys.exit(0)
  if sys.argv[i] == '--devices':
    m.print_devices()
    sys.exit(0)
  if sys.argv[i] == '--algos' or sys.argv[i] == '--algorithms':
    m.print_algorithms()
    sys.exit(0)
  if sys.argv[i] == '--mine':
    m.run()
    sys.exit(0)
  if sys.argv[i] == '--pin' and len(sys.argv) >5:
    args = sys.argv[2:6]
    if len(sys.argv) >6:
      args += [sys.argv[6]]
    else:
      args += [None]
    m.pin(*args)
    sys.exit(0)
  if sys.argv[i] == '--pin' and len(sys.argv) >3 and sys.argv[i+2] == 'idle':
    m.pin_idle(sys.argv[i+1])
    sys.exit(0)
  if sys.argv[i] == '--pin' and len(sys.argv) >3 and sys.argv[i+2] == 'calibration':
    m.pin_calibration(sys.argv[i+1])
    sys.exit(0)
  if sys.argv[i] == '--unpin' and len(sys.argv) >2:
    m.unpin(sys.argv[i+1])
    sys.exit(0)
  if sys.argv[i] == '--quickstart':
    m.calibrate('all', 'nicehash', 'all', 'equihash,neoscrypt,nist5,lyra2rev2,keccak', 'eu', True, False, False)
    m.run()
    sys.exit(0)
  if sys.argv[i] == '--stats':
    hours = 24
    if len(sys.argv) > 2 and sys.argv[i+1].isdigit():
      hours = int(sys.argv[i+1])
      if hours <1:
        hours = 1
    m.stats(hours)
    sys.exit(0)
  if sys.argv[i] == '--upgrade':
    m.upgrade()
    sys.exit(0)
  if sys.argv[i] == '--do-upgrade':
    m.do_upgrade()
    sys.exit(0)
  if sys.argv[i] == '--html' and len(sys.argv) > i+1:
    m = MinotaurGS()
    m.initialise()
    m.gs(None, sys.argv[i+1])
m.usage()
