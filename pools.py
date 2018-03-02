
from singleton import Singleton
from config import Config
from log import Log
import re
import datetime
from profiles import Profiles
import nvidia
from multiprocessing import Process
import urllib2
import json
import pickle
import os
import calibration
from stats import Stats

import nicehash
import miningpoolhub
from pool import Pool

class Pools:
  __metaclass__ = Singleton


  def __init__(self):
    self.data_path = os.getenv("HOME") + "/.minotaur"
    self.currency_rate_file = self.data_path + "/currencies.dat"
    self.pools = {}
    self.payrates = {}

    self.load_config()
    self.update_exchange_rate()


  def load_config(self):
    for pool_name in Config().get('pools').keys():
      if Config().get('pools.%s.enable' % (pool_name)):
        try:
          self.pools[pool_name] = eval("%s.%s()" % (pool_name, pool_name.title()))
        except NameError:
          self.pools[pool_name] = Pool(pool_name)

        self.pools[pool_name].refresh_data()

    if len(self.pools) == 0:
      Log().add('fatal', 'no pools enabled - the config file format for pools has changed, please see minotaur.conf.example')


  def refresh(self):
    for pool_name in self.pools.keys():
      if not self.pools[pool_name].refresh_data():
        Log().add('warning', 'failed to refresh data for pool: %s' % (pool_name))

    if Config().get('stats.enable'):
      best_hashrates = calibration.Calibration().get_best_hashrates()

      payrates = {}

      for pool_name in self.pools.keys():
        pool_rates = self.pools[pool_name].mbtc_per_day(best_hashrates)

        for region in pool_rates.keys():
          for algorithm in pool_rates[region].keys():
            if not algorithm in payrates.keys() or pool_rates[region][algorithm] > payrates[algorithm]:
              payrates[algorithm] = pool_rates[region][algorithm]

      if payrates != self.payrates:
        Stats().log_algorithms(payrates)

    self.update_exchange_rate()


  def enabled(self, pool_name):
    return Config().get('pools.%s.enable' % (pool_name))


  def get_exchange_rate(self):
    json_ = urllib2.urlopen("https://api.coinbase.com/v2/prices/spot?currency=%s" % (Config().get('electricity_currency'))).read()

    try:
      resp = json.loads(json_)

      if "data" in resp.keys():
        return {
          "rate": resp["data"]["amount"],
          "timestamp": datetime.datetime.now()
        }
    except:
      pass

    return None


  def update_exchange_rate(self):
    if os.path.exists(self.currency_rate_file):
      self.exchange_rate = pickle.loads(open(self.currency_rate_file).read())
    else:
      self.exchange_rate = self.get_exchange_rate()

      if self.exchange_rate:
        with open(self.currency_rate_file,"w") as f:
          f.write(pickle.dumps(self.exchange_rate))


  def should_switch(self, device):
    if device.is_optimal():
      return False

    current_payrate = device.get_current_payrate()
    best_payrate = device.get_best_payrate()

    if len(device.algos) >0:
      pool = device.algos[0]['pool']
      if not Config().get('pools.%s.enable' % (device.algos[0]['pool'])):
        return True

    if current_payrate == 0 and best_payrate == 0:
      device.log('warning', 'both current and best algorithms are not paying :(')
      return False

    if current_payrate <= 0:
      device.log('info', 'current algorithm is not paying - initiating switch')
      return True

    benefit_threshold_reached = best_payrate / current_payrate >= 1.0 + Config().get('profit_switch_threshold')

    if benefit_threshold_reached:
      device.log('info', 'benefit threshold reached - initiating switch')
      return True

    if not benefit_threshold_reached:
      device.log('info', 'benefit threshold not reached - not switching')
      return False


  def get_most_profitable_action(self, device):
    best_rate = 0
    best_miner = None
    best_pool = None
    best_algo = None
    best_region = None

    for pool_name in self.pools.keys():
      p_best_miner, p_best_algo, p_best_region, p_best_rate = self.pools[pool_name].get_best_miner_and_algorithm(device)

      if p_best_rate > best_rate:
        best_rate = p_best_rate
        best_pool = pool_name
        best_miner = p_best_miner
        best_algo = p_best_algo
        best_region = p_best_region

    return [best_pool, best_miner, best_algo, best_region]


  def deduct_power_from_payrates(self, device, payrates):
    if Config().get('electricity_per_kwh') and Config().get('electricity_per_kwh') >0:
      if not self.exchange_rate or (datetime.datetime.now() - self.exchange_rate['timestamp']).seconds >= 3600:
        new_exchange_rate = self.get_exchange_rate()

        if new_exchange_rate:
          self.exchange_rate = new_exchange_rate

          with open(self.currency_rate_file,"w") as f:
            f.write(pickle.dumps(self.exchange_rate))

      default_power_limit = device.default_power_limit_f

      if default_power_limit:
        if self.exchange_rate:
          for algo in payrates.keys():
            if payrates[algo] >0:
              miner_name = device.get_best_miner_for_algorithm(algo)
              power_limit = device.get_power_limit_for_algorithm(miner_name, algo)

              if not power_limit:
                power_limit = default_power_limit

              cost_per_day = (float(power_limit) / 1000) * Config().get('electricity_per_kwh') * 24
              mbtc_per_day = (cost_per_day / float(self.exchange_rate['rate'])) * 1000

              payrates[algo] -= mbtc_per_day
        else:
          Log().add('warning', 'no exchange rate for power consumption calculation')

    return payrates


  def get_payrate(self, device, hashrates, pool_name, miner_name, algo, region):
    if not pool_name in self.pools.keys():
      Log().add('warning', 'request for payrates for inactive pool %s' % (pool_name))

      pool = eval("%s.%s()" % (pool_name, pool_name.title()))
      pool.refresh_data()

      return pool.get_payrate(device, hashrates, miner_name, algo, region)

    return self.pools[pool_name].get_payrate(device, hashrates, miner_name, algo, region)


  def get_pool_and_region_from_endpoint(self, endpoint):
    pool = None
    region = None

    if "nicehash" in endpoint:
      pool = 'nicehash'

      match = re.search("\.([a-z]{2,3})\.nicehash\.com", endpoint)

      if match:
        region = match.group(1)
    elif "miningpoolhub" in endpoint:
      pool = "miningpoolhub"
    else:
      pool = None

      for pool_name in Config().get('pools').keys():
        if pool_name not in ['nicehash','miningpoolhub']:
          if endpoint in Config().get('pools.%s.endpoints' % (pool_name)):
            pool = pool_name

    if pool == None:
      raise Exception("unknown pool endpoint: %s" % (endpoint))

    return [pool, region]
