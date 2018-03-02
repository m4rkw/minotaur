#!/usr/bin/env python

import sys
import os
import datetime
import yaml
import re
import time
from log import Log
import curses
import pickle
import urllib2
import signal
import nvidia
from log import Log
from config import Config
#import paramiko
import json
import math
from multiprocessing import Queue, Manager
import multiprocessing
import threading
from version import Version
from miners import Miners
from calibration import Calibration
from units import Units

from nicehash import Nicehash
from miningpoolhub import Miningpoolhub
from pool import Pool
from pools import Pools

# miners
from excavator import Excavator
from ccminer import Ccminer
from ccminer2 import Ccminer2
from xmrig_nvidia import Xmrig_Nvidia
from ethminer import Ethminer
from ewbf import Ewbf

class MinotaurGS:
  def __init__(self, mobile=False):
    self.data_path = os.getenv("HOME") + "/.minotaur"
    self.power_file = self.data_path + "/power.dat"
    self.profitability_file = self.data_path + "/profitability.dat"
    self.currency_rate_file = self.data_path + "/currencies.dat"
    self.last_line_length = 0
    self.mobile = mobile


  def sighup_handler(self, a, b):
    pass


  def initialise(self):
    Config().load()
    signal.signal(signal.SIGHUP, self.sighup_handler)

    Nicehash()

    self.local = True
    self.local_only = True

    self.ssh_connections = {}

    if Config().get('gs.hosts'):
      self.local_only = False

      for remote_host in Config().get('gs.hosts'):
        self.ssh_connections[remote_host['name']] = self.ssh_connect(remote_host)


  def gs(self, scr, html_file=None):
    signal.signal(signal.SIGINT, self.sigint_handler)

    if scr:
      scr.addstr(0, 0, 'minotaur %s by m4rkw' % (Version().get()))

    last_line = 0

    omit_fields = ["gpu_t","fan","power","gpu_u","mem_u","ps clocks"]

    while True:
      data = []

      if self.local:
        data, total_mbtc, net_mbtc, total_power, total_power_limit, power_draw_readings, profitability_readings = self.get_local_data()

        for i in range(0, len(data)):
          if data[i]['omit_fields']:
            for field in omit_fields:
              data[i][field] = ''

        electric_cost_mbtc = self.get_electricity_cost(total_power + Config().get('system_draw_watts'), True, Config().get('electricity_per_kwh'))
        electric_cost_gbp = self.get_electricity_cost(total_power + Config().get('system_draw_watts'), False, Config().get('electricity_per_kwh'))
      else:
        data = []
        total_mbtc = 0
        total_power = 0
        total_power_limit = 0
        power_draw_readings = []
        profitability_readings = []

        electric_cost_mbtc = 0
        electric_cost_gbp = 0

      fields = Config().get('live_data.fields')

      if not fields:
        fields = ["id","name","pool","miner"," algo","time","rate"," mBTC/day"]

        if not self.local_only:
          fields = ["host"] + fields

        if scr:
          fields += ["gpu_t","fan","power","gpu_u","mem_u","ps clocks"]
        else:
          fields += ["gpu_t","fan","power","ps clocks"]

      if scr:
        total_width, extra = self.gs_display(scr, data, fields)

        scr.addstr(len(data) + 4, 0, (" " * total_width) + extra)
      else:
        html = "<table class=\"cards\">" + self.gs_display_html(data, fields) + "</table>"

      total_gbp = self.mbtc_to_gbp(total_mbtc)

      summary_fields = [
        ["gross:", "%.2f" % (total_mbtc), "mBTC/day"],
        ["gross:", "%.2f" % (total_gbp), "%s/day" % (Config().get('electricity_currency'))]
      ]

      if electric_cost_mbtc != None:
        summary_fields[0].append("  power:")
        summary_fields[0].append("%.2f" % (electric_cost_mbtc))
        summary_fields[0].append("mBTC/day")

        net_mbtc = total_mbtc - electric_cost_mbtc

        summary_fields[0].append("  net:")
        summary_fields[0].append("%.2f" % (net_mbtc))
        summary_fields[0].append("mBTC/day")

        summary_fields[1].append("  power:")
        summary_fields[1].append("%.2f" % (electric_cost_gbp))
        summary_fields[1].append("%s/day" % (Config().get('electricity_currency')))

        net_gbp = total_gbp - electric_cost_gbp

        summary_fields[1].append("  net:")
        summary_fields[1].append("%.2f" % (net_gbp))
        summary_fields[1].append("%s/day" % (Config().get('electricity_currency')))

      if self.local:
        time_periods = self.get_profitability_average_time_periods()

        for seconds in sorted(time_periods.keys()):
          title = time_periods[seconds] + " avg:"
          average = self.get_average_reading(profitability_readings, seconds)

          summary_fields.append([title, "%.2f" % (average), "mBTC/day"])

      limit_1pc = total_power_limit / 100

      total_power += Config().get('system_draw_watts')

      if limit_1pc >0:
        total_power_pc = total_power / ((total_power_limit + Config().get('system_draw_watts')) / 100)
      else:
        total_power_pc = 0

      power_s1 = ("%d" % (total_power)).rjust(6)
      power_s2 = "W " + ("%.1f" % (total_power_pc)).rjust(5) + "%"

      summary_fields.append(["power draw now:", power_s1, power_s2])

      if self.local:
        time_periods = self.get_power_draw_average_time_periods()

        for seconds in sorted(time_periods.keys()):
          title = time_periods[seconds] + " avg:"
          average = self.get_average_reading(power_draw_readings, seconds)

          if total_power_limit == 0:
            average_pc = 0
          else:
            average_pc = average / (total_power_limit / 100)

          power_s1 = ("%d" % (average)).rjust(6)
          power_s2 = "W " + ("%.1f" % (average_pc)).rjust(5) + "%"

          summary_fields.append([title, power_s1, power_s2])

      if not self.mobile:
        if scr:
          self.display_summary_fields(scr, summary_fields, len(data) + 5, total_width, extra)
        else:
          html = self.append_summary_fields_html(summary_fields, html)

          with open(html_file + ".new", "w") as f:
            f.write(html)

          os.rename(html_file + ".new", html_file)
      else:
        summary_fields = []

      if scr:
        offset = len(data) + 3 + len(summary_fields)

        if last_line > (len(data) + offset + 1):
          for i in range(len(data) + offset + 1, last_line + 1):
            scr.addstr(i, 0, (" " * total_width) + extra)

        last_line = len(data) + offset

        if not self.mobile:
          scr.addstr(last_line, 0, (" " * total_width) + extra)
          scr.addstr(last_line, 0, "")
        else:
          scr.addstr(len(data) + 4, 0, "")

        scr.refresh()

      time.sleep(1)


  def display_summary_fields(self, scr, summary_fields, offset, total_width, extra):
    for i in range(0, len(summary_fields)):
      line = ""

      for j in range(0, len(summary_fields[i])):
        col_width = self.get_sf_col_width(summary_fields, j) + 1

        line += summary_fields[i][j].rjust(col_width)

      line += (" " * (total_width - len(line))) + extra

      scr.addstr(offset, 0, line)
      offset += 1

      if i in [1,len(Config().get('live_data.profitability_averages'))+1]:
        scr.addstr(offset, 0, (" " * (total_width)) + extra)
        offset += 1


  def append_summary_fields_html(self, summary_fields, html):
    html += "<table class=\"summary\">"

    for i in range(0, len(summary_fields)):
      html += "<tr>"
      for j in range(0, len(summary_fields[i])):
        if i == 5:
          html += "<td class=\"power\">%s</td>" % (summary_fields[i][j])
        else:
          html += "<td>%s</td>" % (summary_fields[i][j].strip())
      html += "</tr>\n"

    html += "</table>"

    return html


  def get_sf_col_width(self, summary_fields, col):
    width = 0

    for i in range(0, len(summary_fields)):
      if len(summary_fields[i]) > (col):
        if len(summary_fields[i][col]) >width:
          width = len(summary_fields[i][col])

    return width


  def get_local_data(self, minimal=False):
    data = []

    devices = nvidia.Nvidia().get_nvidia_devices(1, True)

    Miners().poll()

    if not minimal and os.path.exists(self.power_file) and os.path.getsize(self.power_file) >0:
      power_draw_readings = pickle.loads(open(self.power_file).read())
    else:
      power_draw_readings = []

    if not minimal and os.path.exists(self.profitability_file) and os.path.getsize(self.profitability_file) >0:
      profitability_readings = pickle.loads(open(self.profitability_file).read())
    else:
      profitability_readings = []

    Calibration().load()

    total_mbtc = 0
    total_power = 0
    total_power_limit = 0

    power_values = {}
    power_limit_values = {}

    for device in devices:
      device.algos = []
      Miners().get_device_state(device)

      mbtc_per_day_values = [0]

      algos = device.algos

      if len(algos) == 0:
        algos = ['IDLE']

      for algo_i in range(0, len(algos)):
        algo = algos[algo_i]

        if algo_i == 0:
          omit_fields = False
        else:
          omit_fields = True

        if algo == 'IDLE':
          algo = "IDLE"
          algo1 = "IDLE"
          rate_s = "-"
          mbtc_per_day = 0
          miner = '-'
          region = '-'
          pool = '-'
          _time = '-'
        else:
          algo1 = algo['algo']
          miner = algo['miner']
          region = algo['region']
          pool = algo['pool']
          _pool = Pools().pools[pool]

          if os.path.exists("/tmp/.minotaur.%d" % (device.id)):
            _time = Units().to_timestr(int(time.time() - os.stat("/tmp/.minotaur.%d" % (device.id)).st_mtime))
          else:
            _time = '-'

          rate_a, rate_b = algo['hashrate']

          if algo['algo'] in Config().get('algorithms')['double']:
            rate_s = Units().hashrate_str(rate_a)
            rate_s2 = Units().hashrate_str(rate_b)

            benchmarks = {
              algo['algo']: [rate_a, rate_b]
            }

            algo1, algo2 = algo['algo'].split("_")

            mbtc_per_day_values = [
              _pool.mbtc_per_day(benchmarks, 'cached')[algo['region']][algo['algo']]
            ]
          else:
            rate_s = Units().hashrate_str(rate_a)

            benchmarks = {
              algo['algo']: rate_a
            }

            if algo['algo'] in _pool.mbtc_per_day(benchmarks, 'cached')[algo['region']].keys():
              mbtc_per_day_values = [
                _pool.mbtc_per_day(benchmarks, 'cached')[algo['region']][algo['algo']]
              ]
            else:
              mbtc_per_day_values = [0]

        if pool != '-':
          pool = _pool.shortened(region)

        metrics = device.to_hash()
        metrics.pop('changed', None)
        metrics['miner'] = miner
        metrics['region'] = region
        metrics['pool'] = pool
        metrics['time'] = _time
        metrics['omit_fields'] = omit_fields

        if metrics['fan']:
          metrics['fan'] = str(metrics['fan']).rjust(3) + " %"

        if metrics['miner']:
          metrics['miner'] = metrics['miner'][0:5]
        else:
          metrics['miner'] = '-'

        if algo == "IDLE":
          if metrics['gpu_u_i'] and metrics['gpu_u_i'] >= 90:
            algo = ".pending."
            algo1 = ".pending."
            rate_s = ".."

        mbtc_per_day = mbtc_per_day_values[0]

        metrics['host'] = 'local'
        metrics['id'] = device.id
        metrics[" algo"] = algo1
        metrics["rate"] = rate_s

        metrics[" mBTC/day"] = ("%.2f" % (mbtc_per_day)).rjust(5)

        if not metrics['region']:
          metrics['region'] = '-'

        total_mbtc += sum(mbtc_per_day_values)

        if metrics['power_f']:
          power_values[metrics['id']] = metrics['power_f']
          margin = self.calculate_profit_margin_for_card(sum(mbtc_per_day_values), metrics['power_f'])

          net_mbtc = (mbtc_per_day / 100) * margin

          if margin <0:
            margin = 0

          margin_s = "%d%%" % (int(margin))

          metrics[" mBTC/day"] += "/"
          metrics[" mBTC/day"] += ("%.2f" % (net_mbtc)).rjust(5)
          metrics[" mBTC/day"] += " %s" % (margin_s.rjust(4))
        else:
          margin = 0

        if margin > 0:
          metrics["margin"] = "%.1f%%" % (margin)
        else:
          metrics["margin"] = "-"

        if metrics['limit_f']:
          power_limit_values[metrics['id']] = metrics['limit_f']

        if device.state == 'calibrating':
          metrics[' algo'] = '*' + metrics[' algo']
        elif device.get_pin() and 'algorithm' in device.get_pin().keys() and device.get_pin()['algorithm'] == metrics[' algo']:
          metrics[' algo'] = '+' + metrics[' algo']
        elif device.get_pin() and 'algorithm' in device.get_pin().keys() and '_' in device.get_pin()['algorithm'] and metrics[' algo'] in device.get_pin()['algorithm'].split('_'):
          metrics[' algo'] = '+' + metrics[' algo']
        else:
          metrics[' algo'] = ' ' + metrics[' algo']

        if metrics['gpu_f']:
          match = re.match("^([\d]+)", metrics['gpu_f'])
          if match:
            metrics['gpu_f'] = match.group(1)
          else:
            metrics['gpu_f'] = '-'
        else:
          metrics['gpu_f'] = '-'

        if metrics['mem_f']:
          match = re.match("^([\d]+)", metrics['mem_f'])
          if match:
            metrics['mem_f'] = match.group(1)
          else:
            metrics['mem_f'] = '-'
        else:
          metrics['mem_f'] = '-'

        metrics['ps clocks'] = "%s %s/%s MHz" % (metrics['ps'], metrics['gpu_f'], metrics['mem_f'])

        power = re.match("^([\d]+)", metrics['power'])
        limit = re.match("^([\d]+)", metrics['limit'])

        if power and limit:
          metrics['power'] = "%s/%s W" % (power.group(1), limit.group(1))
        else:
          metrics['power'] = '-'

        data.append(metrics)

        if algo not in ['IDLE', '.pending.'] and algo['algo'] in Config().get('algorithms.double'):
          mbtc_per_day = mbtc_per_day_values[1]

          metrics2 = metrics.copy()
          metrics2[" algo"] = algo2

          metrics2["rate"] = rate_s2

          metrics2[" mBTC/day"] = ("%.2f" % (mbtc_per_day)).rjust(5)

          net_mbtc = (mbtc_per_day / 100) * margin

          metrics2[" mBTC/day"] += "/"
          metrics2[" mBTC/day"] += ("%.2f" % (net_mbtc)).rjust(5)
          metrics2[" mBTC/day"] += " %s" % (margin_s.rjust(4))

          if device.state == 'calibrating':
            metrics2[" algo"] = '*' + metrics2[' algo']
          elif device.get_pin() and '_' in device.get_pin()['algorithm'] and metrics2[' algo'] in device.get_pin()['algorithm'].split('_'):
            metrics2[" algo"] = '+' + metrics2[' algo']
          else:
            metrics2[" algo"] = ' ' + metrics2[' algo']

          data.append(metrics2)

    total_power = sum(power_values.values())
    total_power_limit = sum(power_limit_values.values())

    electric_cost_mbtc = self.get_electricity_cost(total_power + Config().get('system_draw_watts'), True, Config().get('electricity_per_kwh'))
    net_mbtc = total_mbtc - electric_cost_mbtc

    return [data, total_mbtc, net_mbtc, total_power, total_power_limit, power_draw_readings, profitability_readings]


  def get_electricity_cost(self, watts, convert_to_mbtc, rate):
    if not os.path.exists(self.currency_rate_file):
      return False

    exchange_rate = pickle.loads(open(self.currency_rate_file).read())

    gbp = ((watts / 1000) * rate) * 24

    if not convert_to_mbtc:
      return gbp

    return (gbp / float(exchange_rate['rate'])) * 1000


  def mbtc_to_gbp(self, mbtc):
    if not os.path.exists(self.currency_rate_file):
      return False

    exchange_rate = pickle.loads(open(self.currency_rate_file).read())

    return (mbtc / 1000) * float(exchange_rate['rate'])


  def get_profitability_average_time_periods(self):
    data = {}

    for seconds in Config().get('live_data.profitability_averages'):
      data[seconds] = Units().seconds_to_string(seconds)

    return data


  def get_power_draw_average_time_periods(self):
    data = {}

    for seconds in Config().get('live_data.power_draw_averages'):
      data[seconds] = Units().seconds_to_string(seconds)

    return data


  def get_average_reading(self, readings, time_period):
    values = []

    for reading in readings:
      if int(time.time()) - reading["timestamp"] <= time_period:
        values.append(reading["reading"])

    if len(values) == 0:
      return 0

    return sum(values) / len(values)


  def gs_display(self, scr, data, keys):
    widths = self.get_column_widths(data, keys)

    total = 0

    keystr = ""

    for key in keys:
      keystr += key.ljust(widths[key] + 2)
      total += widths[key] + 2

    if total < self.last_line_length:
      extra = " " * (self.last_line_length - total)
    else:
      extra = ""

    scr.addstr(1, 0, ("-" * total) + extra)
    scr.addstr(2, 0, keystr + extra)
    scr.addstr(3, 0, ("-" * total) + extra)

    for i in range(0, len(data)):
      line = ""
      for key in keys:
        if key in ['name', 'miner', 'pool', ' algo', 'region', ' mBTC/day']:
          if key == ' algo':
            data[i][key] = data[i][key][0:10]
          line += str(data[i][key]).ljust(widths[key]) + "  "
        else:
          line += str(data[i][key]).rjust(widths[key]) + "  "
      scr.addstr(i + 4, 0, line + extra)

    self.last_line_length = total

    return [total, extra]


  def gs_display_html(self, data, keys):
    html = '<tr>'

    for key in keys:
      html += '<th>%s</th>' % (key)

    html += "</tr>\n"

    for i in range(0, len(data)):
      html += "<tr>"

      for key in keys:
        if key == 'algo':
          html += "<td>%s</td>" % (data[i][key][0:10])
        else:
          html += "<td>%s</td>" % (data[i][key])

      html += "</tr>\n"

    return html


  def get_column_widths(self, data, keys):
    widths = {}

    for key in keys:
      widths[key] = len(key)

    for item in data:
      for key in item.keys():
        if key in widths.keys() and len(str(item[key])) > widths[key]:
          widths[key] = len(str(item[key]))

    if widths[' algo'] >10:
      widths[' algo'] = 10

    return widths


  def calculate_profit_margin_for_card(self, mbtc_per_day, watts):
    if mbtc_per_day == 0:
      return 0

    electric_cost_mbtc = self.get_electricity_cost(watts, True, Config().get('electricity_per_kwh'))

    if electric_cost_mbtc == 0:
      return 100

    one_pc = mbtc_per_day / 100

    return 100 - (electric_cost_mbtc / one_pc)


  def gs_stat(self, minimal=False):
    print json.dumps(self.get_local_data(minimal))


  def sigint_handler(self, a, b):
    sys.exit(0)


#  def ssh_connect(self, remote_host):
#    ssh = paramiko.SSHClient()
#    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
#
#    user = os.getenv("USER")
#    key = os.getenv("HOME") + "/.ssh/id_rsa"
#    port = 22
#
#    if 'user' in Config().get('gs')['remote'].keys():
#      user = Config().get('gs')['remote']['user']
#    if 'key' in Config().get('gs')['remote'].keys():
#      key = Config().get('gs')['remote']['key']
#    if 'port' in Config().get('gs')['remote'].keys():
#      port = Config().get('gs')['remote']['port']
#
#    if "user" in remote_host.keys():
#      user = remote_host['user']
#    if "key" in remote_host.keys():
#      key = remote_host['key']
#    if "port" in remote_host.keys():
#      port = remote_host['port']
#
#    try:
#      ssh.connect(remote_host['hostname'], port=port, username=user, key_filename=key)
#      return ssh
#    except:
#      return None


#  def get_remote_data(self, remote_host):
#    if not self.ssh_connections[remote_host['name']]:
#      self.ssh_connections[remote_host['name']] = self.ssh_connect(remote_host)
#
#    if self.ssh_connections[remote_host['name']]:
#      ssh_stdin, ssh_stdout, ssh_stderr = self.ssh_connections[remote_host['name']].exec_command("/usr/bin/sudo /usr/local/bin/minotaur --gs-stat")
#
#      data = json.loads(ssh_stdout.read().rstrip())
#
#      for i in range(0, len(data[0])):
#        data[0][i]['host'] = remote_host['name']
#
#      return data
