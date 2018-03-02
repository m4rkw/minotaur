
import os
import datetime
import sys
from singleton import Singleton
from config import Config
from units import Units
from dateutil import parser

class Stats:
  __metaclass__ = Singleton

  def __init__(self):
    self.log_file = Config().get('stats.stats_file')
    self.algos_file = Config().get('stats.algos_file')


  def add(self, device_id, device_class, pool, miner, algo, region, hashrate, gross_mbtc, net_mbtc, device_watts, total_watts):
    if not os.path.exists(self.log_file):
      with open(self.log_file, "w") as f:
        f.write("timestamp,device_id,device_class,pool,miner,algorithm,region,hashrate,gross_mbtc,net_mbtc,device_watts,total_watts\n")

    with open(self.log_file, "a+") as f:
      if net_mbtc == 0:
        net_s = ""
      else:
        net_s = "%.2f" % (net_mbtc)

      if '_' in algo:
        hashrate_s = Units().hashrate_str(hashrate)
      else:
        hashrate_s = Units().hashrate_str(hashrate[0])

      f.write("%s,%d,%s,%s,%s,%s,%s,%s,%.2f,%s,%.2f,%.2f\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), device_id, device_class, pool, miner, algo, region, hashrate_s, gross_mbtc, net_s, device_watts, total_watts))

    if os.path.getsize(self.log_file) >= (Config().get('stats.max_size_mb') * 1024 * 1024):
      self.rotate_logs(self.log_file)


  def rotate_logs(self, logfile):
    for i in reversed(range(1, Config().get('stats.max_file_count') - 1)):
      if os.path.exists(logfile + ".%d" % (i)):
        os.rename(logfile + ".%d" % (i), logfile + ".%d" % (i+1))

    os.rename(logfile, logfile + ".1")


  def log_algorithms(self, payrates):
    if not os.path.exists(self.algos_file):
      with open(self.algos_file, "w") as f:
        f.write("timestamp," + ",".join(sorted(payrates.keys())) + "\n")

    with open(self.algos_file, "a+") as f:
      line = ""
      for algorithm in sorted(payrates.keys()):
        if len(line) >0:
          line += ","
        line += "%.2f" % (payrates[algorithm])
      f.write("%s,%s\n" % (datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"), line))

    if os.path.getsize(self.algos_file) >= (Config().get('stats.max_size_mb') * 1024 * 1024):
      self.rotate_logs(self.algos_file)


  def get_logs_for_period(self, logfile, hours):
    since = datetime.datetime.now() - datetime.timedelta(hours=hours)

    logs = []
    keys = []

    with open(logfile) as f:
      for line in f:
        item = line.rstrip().split(",")

        if keys == []:
          keys = item
          continue 

        if parser.parse(item[0]) < since:
          continue

        obj = {}
        for i in range(0, len(item)):
          if len(keys) > (i+1):
            obj[keys[i]] = item[i]

        logs.append(obj)

    return logs
