
from singleton import Singleton
from config import Config
from log import Log
import math

class Units:
  __metaclass__ = Singleton


  def hs_to_units(self, hs_sec):
    hs_sec = float(hs_sec)

    if hs_sec >= 1000000000:
      return ["%.2f" % (hs_sec / 1000000000), "GH/s"]
    elif hs_sec >= 1000000:
      return ["%.2f" % (hs_sec / 1000000), "MH/s"]
    elif hs_sec >= 1000:
      return ["%.2f" % (hs_sec / 1000), "kH/s"]
    else:
      return ["%.2f" % (hs_sec), "H/s"]


  def to_hs(self, value, unit):
    hs = value

    if unit.lower() == "kh":
      return hs * 1e3
    elif unit.lower() == "mh":
      return hs * 1e6
    elif unit.lower() == "gh":
      return hs * 1e9
    elif unit.lower() in ['h', 'sol']:
      return hs
    else:
      Log().add('fatal', "unknown hashrate unit: %s" % (unit))


  def hashrate_str(self, hashrate):
    if isinstance(hashrate, float) or isinstance(hashrate, int):
      rate_a_s, rate_a_unit = self.hs_to_units(hashrate)

      return '%s %s' % (rate_a_s, rate_a_unit)
    else:
      rate_a_s, rate_a_unit = self.hs_to_units(hashrate[0])
      rate_b_s, rate_b_unit = self.hs_to_units(hashrate[1])

      return '%s %s / %s %s' % (rate_a_s, rate_a_unit, rate_b_s, rate_b_unit)


  def seconds_to_string(self, seconds):
    if seconds >= 86400:
      if seconds == 86400:
        suffix = ""
      else:
        suffix = "s"
      return "%d day%s" % (seconds / 86400, suffix)
    elif seconds >= 3600:
      if seconds == 3600:
        suffix = ""
      else:
        suffix = "s"
      return "%d hour%s" % (seconds / 3600, suffix)
    elif seconds >= 60:
      if seconds == 60:
        suffix = ""
      else:
        suffix = "s"
      return "%d min%s" % (seconds / 60, suffix)
    else:
      return "%d seconds" % (seconds)


  def to_timestr(self, seconds):
    days = hours = mins = 0

    if seconds >= 86400:
      return "%dd" % (math.floor(seconds / 86400))

    if seconds >= 3600:
      return "%dh" % (math.floor(seconds / 3600))

    if seconds >= 60:
      return "%dm" % (math.floor(seconds / 60))

    return "%ds" % (seconds)
