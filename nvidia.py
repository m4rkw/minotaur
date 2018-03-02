import os
import re
from singleton import Singleton
from config import Config
from log import Log
import time
from device import Device
from profiles import Profiles
import yaml
import glob
import sys

class Nvidia(object):
  __metaclass__ = Singleton


  def __init__(self):
    if not os.path.exists("/var/run/gpustatd"):
      print "/var/run/gpustatd does not exist. gpustatd is required for fanotaur."
      print "see: https://github.com/m4rkw/gpustatd"
      sys.exit(1)

    if len(glob.glob("/var/run/gpustatd/*.yml")) == 0:
      print "error: gpustatd is not running. please install and run gpustatd first."
      print "see: https://github.com/m4rkw/gpustatd"
      sys.exit(1)

    os.environ['DISPLAY'] = ':%d' % (Config().get('xorg_display_no'))


  def get_nvidia_device_classes(self):
    device_classes = []

    for device in self.get_nvidia_devices():
      dclass = self.get_class_for_device(device.id, device.name)

      if dclass not in device_classes:
        device_classes.append(dclass)

    return device_classes


  def get_nvidia_devices(self, _all=False, silent=False):
    devices = {}
    ret = []

    for filename in glob.glob("/var/run/gpustatd/*.yml"):
      if not silent and self.is_stale(filename):
        Log().add('warning', 'gpustatd metrics file is stale (>5s): %s' % (filename))

      device = yaml.load(open(filename).read())

      if _all or device['id'] not in Config().get('ignore_devices'):
        device['dclass'] = self.get_class_for_device(device['id'], device['name'])

        if Config().get('power_limit.%s' % (device['dclass'])):
          device['max_power_limit'] = '%d W' % (Config().get('power_limit.%s' % (device['dclass'])))
          device['max_power_limit_f'] = Config().get('power_limit.%s' % (device['dclass']))

        devices[device['id']] = Device(device)

    for device_id in sorted(devices.keys()):
      ret.append(devices[device_id])

    return ret


  def get_total_power_draw(self):
    watts = 0

    for device in self.get_nvidia_devices(False, True):
      watts += device.power_f

    return watts


  def get_class_for_device(self, device_id, name):
    for device_class in Config().get('device_classes').keys():
      if device_id in Config().get('device_classes')[device_class]:
        return device_class

    return name


  def metrics_keys(self):
    return ['gpu_u', 'gpu_u_i', 'mem_u', 'mem_u_i', 'gpu_t', 'gpu_t_i', 'power', 'power_f', 'limit', 'limit_f', 'gpu_f', 'mem_f', 'ps']


  def get_nvidia_metrics_for_device(self, device_id, silent=False):
    filename = "/var/run/gpustatd/%d.yml" % (device_id)

    if os.path.exists(filename):
      if not silent and self.is_stale(filename):
        Log().add('warning', 'gpustatd metrics file is stale (>5s): %s' % (filename))
      return yaml.load(open(filename).read())


  def is_stale(self, filename):
    return (time.time() - os.stat(filename).st_mtime) >= 5


  def set_power_limit(self, device, watts):
    if Config().get('debug'):
      suppress = ''
    else:
      suppress = ' 1>/dev/null 2>/dev/null'

    if os.system("/usr/bin/nvidia-smi -i %d --power-limit=%d %s" % (device.id, watts, suppress)) == 0:
      with open("/var/run/minotaur/%d.powerlimit" % (device.id), "w") as f:
        f.write("%d" % (watts))
      return True

    return False


  def set_gpu_clock_offset(self, device, offset):
    if Config().get('debug'):
      suppress = ''
    else:
      suppress = ' 1>/dev/null 2>/dev/null'

    return os.system("/usr/bin/nvidia-settings -a '[gpu:%d]/GPUGraphicsClockOffset[3]=%d' %s" % (device.id, offset, suppress)) == 0


  def set_mem_clock_offset(self, device, offset):
    if Config().get('debug'):
      suppress = ''
    else:
      suppress = ' 1>/dev/null 2>/dev/null'

    return os.system("/usr/bin/nvidia-settings -a '[gpu:%d]/GPUMemoryTransferRateOffset[3]=%d' %s" % (device.id, offset, suppress)) == 0


  def set_default_profile(self, device):
    self.set_profile(device, Profiles().get('default'))


  def set_profile(self, device, profile):
    is_default = profile.name == 'default'

    if device.power_supported() and len(device.algos) >0:
      power_limit = device.get_power_limit_for_algorithm(device.algos[0]['miner'], device.algos[0]['algo'])

      if not power_limit:
        power_limit = device.default_power_limit_f

    # if overclocking, set the power limit first
    # if de-clocking, reduce the clocks first
    if is_default or profile.gpu_clock_offset == 0 or profile.memory_clock_offset == 0:
      self.set_profile_clocks(device, profile)

      if device.power_supported() and len(device.algos) >0:
        if not self.set_power_limit(device, power_limit):
          Log().add('warning', 'failed to set power limit on device %d (check we have +s on nvidia-smi)' % (device.id))
    else:
      if device.power_supported() and len(device.algos) >0:
        if not self.set_power_limit(device, power_limit):
          Log().add('warning', 'failed to set power limit on device %d (check we have +s on nvidia-smi)' % (device.id))

      self.set_profile_clocks(device, profile)


  def set_profile_clocks(self, device, profile):
    if not Config().get('leave_graphics_clocks_alone'):
      if profile.gpu_clock_offset != None:
        if not self.set_gpu_clock_offset(device, profile.gpu_clock_offset):
          Log().add('warning', 'failed to set GPU clock on device %d' % (device.id))
      else:
        if not self.set_gpu_clock_offset(device, 0):
          Log().add('warning', 'failed to set GPU clock on device %d' % (device.id))

      if profile.memory_clock_offset != None:
        if not self.set_mem_clock_offset(device, profile.memory_clock_offset):
          Log().add('warning', 'failed to set memory clock on device %d' % (device.id))
      else:
        if not self.set_mem_clock_offset(device, 0):
          Log().add('warning', 'failed to set memory clock on device %d' % (device.id))


  def set_default_clocks(self, device):
    if not self.set_gpu_clock_offset(device, 0):
      Log().add('warning', 'failed to set GPU default clock on device %d' % (device.id))

    if not self.set_mem_clock_offset(device, 0):
      Log().add('warning', 'failed to set memory default clock on device %d' % (device.id))


  def get_device_metrics(self, devices):
    all_metrics = self.get_nvidia_devices(1)

    total_power = 0
    total_power_limit = 0
    total_mbtc_per_day = 0

    for device in devices:
      device.update_metrics(all_metrics[device.id])

      total_power += device.power_f
      total_power_limit += device.limit_f

      if device.state == 'active' and not device.grub:
        total_mbtc_per_day += device.mbtc_per_day()

    return [total_power, total_power_limit, total_mbtc_per_day]
