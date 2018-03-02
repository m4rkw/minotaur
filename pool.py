
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
from config import Config
import calibration
import yaml
import pools
import time

class Pool:
  def __init__(self, pool_name):
    self.data_path = os.getenv("HOME") + "/.minotaur"
    if not os.path.exists(self.data_path):
      os.mkdir(self.data_path, 0755)

    self.pool_name = pool_name

    for key in ['shortname','algorithm','whattomine_coin_no','endpoints','miners']:
      if not Config().get('pools.%s.%s' % (self.pool_name, key)):
        raise Exception("%s is not specified for pool: %s" % (key, self.pool_name))

    self.shortname = Config().get('pools.%s.shortname' % (self.pool_name))
    self.algorithm = Config().get('pools.%s.algorithm' % (self.pool_name))
    self.coin_no = Config().get('pools.%s.whattomine_coin_no' % (self.pool_name))
    self.pool_fee = Config().get('pools.%s.pool_fee' % (self.pool_name))
    self.endpoints = Config().get('pools.%s.endpoints' % (self.pool_name))
    self.supported_miners = Config().get('pools.%s.miners' % (self.pool_name))
    self.paying_file = self.data_path + "/%s.yml" % (pool_name)

    if os.path.exists(self.paying_file):
      self.last_refresh = os.stat(self.paying_file).st_mtime
      self.paying = yaml.load(open(self.paying_file).read())
    else:
      self.paying = {}
      self.last_refresh = None


  def shortened(self, region):
    return self.shortname


  def refresh_data(self, save=True):
    if self.last_refresh != None and (time.time() - self.last_refresh) < 300:
      return True

    try:
      opener = urllib2.build_opener()
      opener.addheaders = [('User-Agent', 'Mozilla/5.0')]
      response = opener.open("http://whattomine.com/coins/%d.json" % (self.coin_no))

      network = json.loads(response.read())

      base_block_time = float(1) / float(network['nethash'])

      daily = (float(86400) / float(network['block_time']) * base_block_time * float(network['block_reward']))
      self.paying = daily * float(network['exchange_rate']) * 1000

      if self.pool_fee:
        self.paying -= (self.paying / 100) * self.pool_fee

      self.save_paying_data()
      self.last_refresh = os.stat(self.paying_file).st_mtime

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

    if self.algorithm not in benchmarks.keys():
      return {
        None: {
          self.algorithm: 0
        }
      }

    return {
      None: {
        self.algorithm: paying * benchmarks[self.algorithm]
      }
    }


  def get_best_miner_and_algorithm(self, device):
    hashrates = calibration.Calibration().get_hashrates(device)

    if hashrates == None:
      return [None, None, None, None]

    best_hashrates = calibration.Calibration().get_best_algorithm_benchmarks(hashrates)

    if self.algorithm not in best_hashrates.keys():
      return [None, None, None, None]

    payrates = self.mbtc_per_day(best_hashrates)

    payrates[None] = pools.Pools().deduct_power_from_payrates(device, payrates[None])

    best_miner = device.get_best_miner_for_algorithm(self.algorithm, self.supported_miners)

    if best_miner == None:
      return [None, None, None, None]

    return [best_miner, self.algorithm, None, payrates[None][self.algorithm]]


  def get_payrate(self, device, hashrates, miner_name, algo, region):
    benchmarks = {
      algo: hashrates[miner_name][algo]['hashrate']
    }

    payrates = self.mbtc_per_day(benchmarks)
    payrates[None] = pools.Pools().deduct_power_from_payrates(device, payrates[None])

    return payrates[None][algo]


  def get_endpoints(self, algo, region):
    return self.endpoints
