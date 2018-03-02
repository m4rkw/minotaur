
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

class Nicehash:
  __metaclass__ = Singleton

  supported_miners = ['ccminer', 'ccminer2', 'ethminer', 'excavator', 'xmrig_nvidia', 'ewbf']

  def __init__(self):
    self.data_path = os.getenv("HOME") + "/.minotaur"
    if not os.path.exists(self.data_path):
      os.mkdir(self.data_path, 0755)

    self.paying_file = self.data_path + "/nicehash.yml"
    self.paying = {}
    self.ports = {
      'scrypt': 3333,
      'sha256': 3334,
      'scryptnf': 3335,
      'x11': 3336,
      'x13': 3337,
      'keccak': 3338,
      'x15': 3339,
      'nist5': 3340,
      'neoscrypt': 3341,
      'lyra2re': 3342,
      'whirlpoolx': 3343,
      'qubit': 3344,
      'quark': 3345,
      'axiom': 3346,
      'lyra2rev2': 3347,
      'scryptjanenf16': 3348,
      'blake256r8': 3349,
      'blake256r14': 3350,
      'blake256r8vnl': 3351,
      'hodl': 3352,
      'daggerhashimoto': 3353,
      'decred': 3354,
      'cryptonight': 3355,
      'lbry': 3356,
      'equihash': 3357,
      'pascal': 3358,
      'x11gost': 3359,
      'sia': 3360
    }


  def shortened(self, region):
    return 'nh-%s' % (region)


  def refresh_data(self, save=True):
    """Retrieves pay rates and connection ports for every algorithm from the NiceHash API."""
    # 0 = europe
    # 1 = usa
    try:
      response = urllib2.urlopen('https://api.nicehash.com/api?method=simplemultialgo.info&location=0', None, Config().get('pools.nicehash.timeout'))
      query = json.loads(response.read().decode('ascii')) #json.load(response)
      paying = {
        "eu": {},
        "usa": {}
      }
      ports = {}

      for algorithm in query['result']['simplemultialgo']:
        name = algorithm['name']
        paying["eu"][name] = float(algorithm['paying'])
        ports[name] = int(algorithm['port'])

        if Config().get('pools.nicehash.pool_fee'):
          paying["eu"][name] -= (paying["eu"][name] / 100) * Config().get('pools.nicehash.pool_fee')

      response = urllib2.urlopen('https://api.nicehash.com/api?method=simplemultialgo.info&location=1', None, Config().get('pools.nicehash.timeout'))
      query = json.loads(response.read().decode('ascii')) #json.load(response)

      for algorithm in query['result']['simplemultialgo']:
        name = algorithm['name']
        paying["usa"][name] = float(algorithm['paying'])
        ports[name] = int(algorithm['port'])

        if Config().get('pools.nicehash.pool_fee'):
          paying["usa"][name] -= (paying["usa"][name] / 100) * Config().get('pools.nicehash.pool_fee')

      self.paying = paying
      self.ports = ports

      if save:
        self.save_paying_data()

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
    """Calculates the BTC/day amount for every algorithm.

    device -- device id for benchmarks
    paying -- algorithm pay information from NiceHash
    """

    if paying == 'cached':
      paying = yaml.load(open(self.paying_file).read())

    if not paying:
      paying = self.paying

    pay = lambda algo, region, speed: paying[region][algo]*float(speed)*(24*60*60)*1e-11
    pay_benched = lambda algo, region: pay(algo, region, benchmarks[algo])

    if paying != {}:
      if "daggerhashimoto_pascal" in benchmarks.keys():
        if "daggerhashimoto_pascal" in paying['eu'].keys():
          dual_dp_eu = pay('daggerhashimoto', 'eu', benchmarks['daggerhashimoto_pascal'][0]) + pay('pascal', 'eu', benchmarks['daggerhashimoto_pascal'][1])
        if "daggerhashimoto_pascal" in paying['usa'].keys():
          dual_dp_usa = pay('daggerhashimoto', 'usa', benchmarks['daggerhashimoto_pascal'][0]) + pay('pascal', 'usa', benchmarks['daggerhashimoto_pascal'][1])
      if "daggerhashimoto_decred" in benchmarks.keys():
        if "daggerhashimoto_decred" in paying['eu'].keys():
          dual_dd_eu = pay('daggerhashimoto', 'eu', benchmarks['daggerhashimoto_decred'][0]) + pay('decred', 'eu', benchmarks['daggerhashimoto_decred'][1])
        if "daggerhashimoto_decred" in paying['usa'].keys():
          dual_dd_usa = pay('daggerhashimoto', 'usa', benchmarks['daggerhashimoto_decred'][0]) + pay('decred', 'usa', benchmarks['daggerhashimoto_decred'][1])
      if "daggerhashimoto_sia" in benchmarks.keys():
        if "daggerhashimoto_sia" in paying['eu'].keys():
          dual_ds_eu = pay('daggerhashimoto', 'eu', benchmarks['daggerhashimoto_sia'][0]) + pay('sia', 'eu', benchmarks['daggerhashimoto_sia'][1])
        if "daggerhashimoto_sia" in paying['usa'].keys():
          dual_ds_usa = pay('daggerhashimoto', 'usa', benchmarks['daggerhashimoto_sia'][0]) + pay('sia', 'usa', benchmarks['daggerhashimoto_sia'][1])

    payrates = {
      "eu": {},
      "usa": {}
    }

    for algo in Config().get('algorithms.single'):
      if algo in benchmarks.keys():
        for region in ["eu","usa"]:
          if region in paying.keys() and algo in paying[region].keys():
            payrates[region][algo] = pay_benched(algo, region)

    try:
      if "daggerhashimoto_pascal" in benchmarks.keys():
        payrates["eu"]["daggerhashimoto_pascal"] = dual_dp_eu
        payrates["usa"]["daggerhashimoto_pascal"] = dual_dp_usa
      if "daggerhashimoto_decred" in benchmarks.keys():
        payrates["eu"]["daggerhashimoto_decred"] = dual_dd_eu
        payrates["usa"]["daggerhashimoto_decred"] = dual_dd_usa
      if "daggerhashimoto_sia" in benchmarks.keys():
        payrates["eu"]["daggerhashimoto_sia"] = dual_ds_eu
        payrates["usa"]["daggerhashimoto_sia"] = dual_ds_usa
    except:
      pass

    return payrates


  def get_best_miner_and_algorithm(self, device):
    hashrates = calibration.Calibration().get_hashrates(device)

    if hashrates == None:
      return [None, None, None, None]

    best_hashrates = calibration.Calibration().get_best_algorithm_benchmarks(hashrates)

    payrates = self.mbtc_per_day(best_hashrates)

    for region in payrates.keys():
      payrates[region] = pools.Pools().deduct_power_from_payrates(device, payrates[region])

    best_rate = 0
    best_algo = None
    best_region = None
    best_miner = None

    if Config().get('pools.nicehash.primary_region') == 'usa':
      regions = ["usa","eu"]
    else:
      regions = ["eu","usa"]

    for region in regions:
      for algo in payrates[region].keys():
        if payrates[region][algo] > best_rate:
          best_rate = payrates[region][algo]
          best_algo = algo
          best_region = region

          if best_algo == 'equihash':
            supported_miners = ['excavator', 'ewbf']
          else:
            supported_miners = self.supported_miners

          best_miner = device.get_best_miner_for_algorithm(best_algo, supported_miners)

          if best_miner == None:
            best_rate = 0
            best_algo = None
            best_region = None

    if payrates['eu'] == {} and payrates['usa'] == {}:
      device.log('warning', 'no nicehash payrate information - defaulting to %s' % (Config().get('pools.nicehash.default_algorithm')))

      best_algo = Config().get('pools.nicehash.default_algorithm')
      best_region = Config().get('pools.nicehash.primary_region')

    return [best_miner, best_algo, best_region, best_rate]


  def get_payrate(self, device, hashrates, miner_name, algo, region):
    benchmarks = {
      algo: hashrates[miner_name][algo]['hashrate']
    }

    payrates = self.mbtc_per_day(benchmarks)
    payrates[region] = pools.Pools().deduct_power_from_payrates(device, payrates[region])

    if payrates[region] == {}:
      return 0

    if '_' in algo:
      algo1, algo2 = algo.split('_')

      return payrates[region][algo1] + payrates[region][algo2]
    else:
      return payrates[region][algo]


  def get_endpoints(self, algo, region):
    return ["%s.nicehash.com" % (region)]
