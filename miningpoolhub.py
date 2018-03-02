
import json
import logging
import signal
import socket
import sys
import urllib2
import httplib
import datetime
from log import Log
import os
import re
import pickle
from singleton import Singleton
from config import Config
import calibration
import yaml
import pools
import time

class Miningpoolhub:
  __metaclass__ = Singleton

  supported_miners = ['ewbf', 'ccminer', 'ccminer2', 'xmrig_nvidia', 'ethminer']

  algos = {
    "cryptonight": {
      "endpoint": "europe.cryptonight-hub.miningpoolhub.com",
      "port": 12024,
      "wtm": [213, 101]
    },
    "equihash": {
      "endpoint": "europe.equihash-hub.miningpoolhub.com",
      "port": 12023,
      "wtm": [167, 185, 166, 214]
    },
    "daggerhashimoto": {
      "endpoint": "europe.ethash-hub.miningpoolhub.com",
      "port": 12020,
      "wtm": [151, 162, 154, 178]
    },
    "lyra2rev2": {
      "endpoint": "hub.miningpoolhub.com",
      "port": 12018,
      "wtm": [148, 5]
    },
    "neoscrypt": {
      "endpoint": "hub.miningpoolhub.com",
      "port": 12012,
      "wtm": [8]
    },
    "keccak": {
      "endpoint": "hub.miningpoolhub.com",
      "port": 12003,
      "wtm": [73]
    },
    "skein": {
      "endpoint": "hub.miningpoolhub.com",
      "port": 12016,
      "wtm": [114,67]
    },
    "groestl": {
      "endpoint": "hub.miningpoolhub.com",
      "port": 12004,
      "wtm": [48]
    }
  }

  algo_map = {
    "ethash": "daggerhashimoto",
    "Lyra2RE2": "lyra2rev2"
  }

  def __init__(self):
    self.data_path = os.getenv("HOME") + "/.minotaur"
    if not os.path.exists(self.data_path):
      os.mkdir(self.data_path, 0755)

    if Config().get('pools.miningpoolhub.enable_excavator'):
      self.supported_miners.append('excavator')

    self.paying_file = self.data_path + "/miningpoolhub.yml"
    self.paying = {}

    if os.path.exists(self.paying_file):
      self.last_refresh = os.stat(self.paying_file).st_mtime
      self.paying = yaml.load(open(self.paying_file).read())
    else:
      self.paying = {}
      self.last_refresh = None


  def shortened(self, region):
    return 'mph'


  def refresh_data(self, save=True):
    if self.last_refresh != None and (time.time() - self.last_refresh) < 300:
      return True

    try:
      opener = urllib2.build_opener()
      opener.addheaders = [('User-Agent', 'Mozilla/5.0')]

      paying = {}

      for algo in self.algos.keys():
        for wtm in self.algos[algo]['wtm']:
          response = opener.open("http://whattomine.com/coins/%d.json" % (wtm))

          network = json.loads(response.read())

          base_block_time = float(1) / float(network['nethash'])

          daily = (float(86400) / float(network['block_time']) * base_block_time * float(network['block_reward']))
          rate = daily * float(network['exchange_rate']) * 1000

          if Config().get('pools.miningpoolhub.pool_fee'):
            rate -= (rate / 100) * Config().get('pools.miningpoolhub.pool_fee')

          if not algo in paying.keys() or rate > paying[algo]:
            paying[algo] = rate

      self.paying = paying
      self.save_paying_data()
      self.last_refresh = time.time()

      return True
    except urllib2.HTTPError, e:
      return False
    except urllib2.URLError, e:
      return False
    except httplib.HTTPException, e:
      return False
    except Exception:
      return False


  def save_paying_data(self):
    with open(self.paying_file + ".new", "w") as f:
      f.write(yaml.dump(self.paying))
    os.rename(self.paying_file + ".new", self.paying_file)


  def mbtc_per_day(self, benchmarks, paying=False):
    if paying == 'cached':
      paying = yaml.load(open(self.paying_file).read())

    if not paying:
      paying = self.paying

    payrates = {
      None: {}
    }

    for algo in paying.keys():
      if algo in benchmarks.keys():
        payrates[None][algo] = paying[algo] * benchmarks[algo]

    return payrates


  def get_best_miner_and_algorithm(self, device):
    hashrates = calibration.Calibration().get_hashrates(device)

    if hashrates == None:
      return [None, None, None, None]

    best_hashrates = calibration.Calibration().get_best_algorithm_benchmarks(hashrates)
    payrates = self.mbtc_per_day(best_hashrates)
    payrates[None] = pools.Pools().deduct_power_from_payrates(device, payrates[None])

    best_rate = 0
    best_algo = None
    best_miner = None

    for algo in payrates[None]:
      if payrates[None][algo] > best_rate:
        best_rate = payrates[None][algo]
        best_algo = algo
        best_miner = device.get_best_miner_for_algorithm(best_algo, self.supported_miners)

        if best_miner == None:
          best_rate = 0
          best_algo = None
          best_region = None

    if payrates[None] == {}:
      device.log('warning', 'no miningpoolhub payrate information - defaulting to %s' % (Config().get('pools.miningpoolhub.default_algorithm')))

      best_algo = Config().get('pools.miningpoolhub.default_algorithm')
      best_region = Config().get('pools.miningpoolhub.primary_region')

    return [best_miner, best_algo, None, best_rate]


  def get_payrate(self, device, hashrates, miner_name, algo, region):
    benchmarks = {
      algo: hashrates[miner_name][algo]['hashrate']
    }

    payrates = self.mbtc_per_day(benchmarks)
    payrates[None] = pools.Pools().deduct_power_from_payrates(device, payrates[None])

    return payrates[None][algo]


  def get_endpoints(self, algo, region):
    return ["%s:%d" % (self.algos[algo]['endpoint'], self.algos[algo]['port'])]
