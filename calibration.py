
from singleton import Singleton
from config import Config
import glob
import os
import yaml
from units import Units
from miners import Miners
from log import Log
import time
import datetime

class Calibration:
  __metaclass__ = Singleton

  def __init__(self):
    self.data_path = os.getenv("HOME") + "/.minotaur"


  def load(self):
    self.data = {}

    for filename in glob.glob("%s/calibration_*.yml" % (self.data_path)):
      segments = filename.replace('.yml', '').split("_")

      if len(segments) >4:
        if segments[3] == 'daggerhashimoto':
          segments[3] = "%s_%s" % (segments[3], segments[4])
          del segments[4]
        else:
          segments[2] = "%s_%s" % (segments[2], segments[3])
          segments[3] = segments[4]
          del segments[4]

      prefix, dclass, miner_name, algorithm = segments

      self.set("%s.%s.%s" % (dclass, miner_name, algorithm), yaml.load(open(filename).read()))


  def get(self, key, data=None):
    if data == None:
      data = self.data

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

      if segment in self.data.keys():
        segment_data = self.data[segment]
      else:
        segment_data = {}

      self.data[segment] = self.set_key(segment_data, key[len(segment)+1:], value)
      return
    else:
      self.data[key] = value


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


  def get_calibrated_algorithms_for_device(self, device):
    algorithms = {}

    for dclass in self.data.keys():
      if dclass == device.name or dclass == device.dclass:
        for miner_name in self.data[dclass].keys():
          if not miner_name in algorithms.keys():
            algorithms[miner_name] = []

          for algorithm in self.data[dclass][miner_name].keys():
            algorithms[miner_name].append(algorithm)

    return algorithms


  def get_hashrates(self, device):
    return self.get(device.dclass)


  def check_calibrated_algorithms(self, devices):
    device_classes = []

    for device in devices:
      if not device.dclass in device_classes:
        device_classes.append(device.dclass)

    total_algorithms = Miners().get_miner_algorithm_count() * len(device_classes)
    calibrated_algorithms = 0

    classes = []

    for device in devices:
      calibration = device.get_calibrated_algorithms()

      for miner_name in calibration.keys():
        calibrated_algorithms += len(calibration[miner_name])

      if not device.dclass in classes or len(calibration) == 0:
        self.display_calibrated_algorithms_for_device(device, calibration)
        classes.append(device.dclass)
      else:
        device.log('info', ' as above')

    if calibrated_algorithms == 0:
      Log().add('fatal', 'you have no calibration data, unable to mine. please see --calibrate')

    if calibrated_algorithms >= total_algorithms:
      Log().add('info', 'you have calibration data for all supported algorithms :)')
    else:
      Log().add('warning', 'you only have calibration data for %d/%d supported algorithm/device combinations' % (calibrated_algorithms, total_algorithms))


  def display_calibrated_algorithms_for_device(self, device, calibration):
    width = self.get_max_width(calibration.keys())

    for miner_name in calibration.keys():
      if len(calibration[miner_name]) == 0:
        device.log('info', '%s: NONE' % (miner_name.rjust(width)))
      else:
        algorithms = calibration[miner_name][:]
        segment = []

        while len(algorithms) >0:
          segment.append(algorithms.pop(0))

          if len(",".join(segment)) >= 60:
            device.log('info', '%s: %s' % (miner_name.rjust(width), ",".join(segment)))
            segment = []

        if len(segment) >0:
          device.log('info', '%s: %s' % (miner_name.rjust(width), ",".join(segment)))


  def get_max_width(self, data):
    width = 0

    for item in data:
      if len(item) > width:
        width = len(item)

    return width


  def get_miner_hashrate_for_algorithm_on_device(self, miner_name, algorithm, device_class):
    calibrated = self.get('%s.%s.%s' % (device_class, miner_name, algorithm))

    if calibrated:
      return Units().hashrate_str(calibrated['hashrate'])

    return " "


  def get_best_algorithm_benchmarks(self, calibration_data):
    benchmarks = {}

    for algo_type in Config().get('algorithms').keys():
      for algorithm in Config().get('algorithms')[algo_type]:
        if "_" in algorithm:
          best_hashrate = [0, 0]
        else:
          best_hashrate = 0

        if calibration_data:
          for miner_name in calibration_data.keys():
            if algorithm in calibration_data[miner_name].keys():
              if "_" in algorithm and calibration_data[miner_name][algorithm]["hashrate"][0] > best_hashrate[0]:
                best_hashrate = calibration_data[miner_name][algorithm]["hashrate"]
              elif "_" not in algorithm and calibration_data[miner_name][algorithm]["hashrate"] > best_hashrate:
                best_hashrate = calibration_data[miner_name][algorithm]["hashrate"]

        benchmarks[algorithm] = best_hashrate

    return benchmarks


  def get_best_hashrates(self):
    best = {}

    for algorithm in Config().get('algorithms.single') + Config().get('algorithms.double'):
      if '_' in algorithm:
        best[algorithm] = [0, 0]
      else:
        best[algorithm] = 0

    for dclass in self.data.keys():
      for miner_name in self.data[dclass].keys():
        for algorithm in self.data[dclass][miner_name].keys():
          if algorithm in Config().get('algorithms.single') or algorithm in Config().get('algorithms.double'):
            if '_' in algorithm:
              if algorithm in self.data[dclass][miner_name].keys():
                if self.data[dclass][miner_name][algorithm]['hashrate'][0] > best[algorithm][0]:
                  best[algorithm] = self.data[dclass][miner_name][algorithm]['hashrate']
            else:
              if algorithm in self.data[dclass][miner_name].keys():
                if self.data[dclass][miner_name][algorithm]['hashrate'] > best[algorithm]:
                  best[algorithm] = self.data[dclass][miner_name][algorithm]['hashrate']

    return best


  def handle_device_update(self, device):
    if (datetime.datetime.now() - device.changed).seconds < (Config().get('calibration.update_calibration_data_after_mins') * 60):
      return

    for algo in device.algos:
      # Max update once a minute
      if algo['calibration_updated_at'] and \
        (time.time() - algo['calibration_updated_at']) < 60:
        continue

      if len(algo['hashrate_readings']) >0:
        readings_a = []
        readings_b = []

        for reading in algo['hashrate_readings']:
          readings_a.append(reading[0])
          readings_b.append(reading[1])

        if '_' in algo['algo']:
          variance, n = self.get_variance(readings_a, readings_b)
        else:
          variance, n = self.get_variance(readings_a)

        if self.is_stable(variance, n):
          calibrated_data = self.get('%s.%s.%s' % (device.dclass, algo['miner'], algo['algo']))

          if '_' in algo['algo']:
            nominal = [self.get_nominal_hashrate_from_range(readings_a), self.get_nominal_hashrate_from_range(readings_b)]
          else:
            nominal = self.get_nominal_hashrate_from_range(readings_a)

          if self.within_update_threshold(nominal, calibrated_data['hashrate']) and \
            self.hashrate_is_visibly_different(nominal, calibrated_data['hashrate']):
              device.log('info', '%s[%s]: new calibrated rate: %s' % (algo['algo'], algo['miner'], Units().hashrate_str(nominal)))

              calibrated_data['hashrate'] = nominal

              self.update_calibration_data(device.dclass, algo['miner'], algo['algo'], nominal, calibrated_data['power_limit'])

              self.set("%s.%s.%s" % (device.dclass, algo['miner'], algo['algo']), calibrated_data)
              algo['calibration_updated_at'] = time.time()


  def get_variance(self, readings_a, readings_b = None):
    n = Config().get('calibration.hashrate_stabilisation_consecutive_readings_required')

    _min = min(readings_a[-n:])
    _max = max(readings_a[-n:])

    variances = [self.get_variance_value(_min, _max)]

    if readings_b:
      _min = min(readings_b[-n:])
      _max = max(readings_b[-n:])

      variances.append(self.get_variance_value(_min, _max))

    return [max(variances), len(readings_a[-n:])]


  def get_variance_value(self, a, b):
    if a > b:
      d = a - b
    else:
      d = b - a

    if (a / 100) == 0:
      return 100

    return d / (a / 100)


  def is_stable(self, variance_pc, n_readings):
    return variance_pc != None and variance_pc <= Config().get('calibration.hashrate_stabilisation_tolerance') and n_readings >= Config().get('calibration.hashrate_stabilisation_consecutive_readings_required')


  def get_nominal_hashrate_from_range(self, readings):
    n = Config().get('calibration.hashrate_stabilisation_consecutive_readings_required')
    selection = readings[-n:]
    return (min(selection) + max(selection)) / 2


  def within_update_threshold(self, new_hashrate, calibrated_hashrate):
    if isinstance(new_hashrate, list):
      return self.within_update_threshold(new_hashrate[0], calibrated_hashrate[0]) and \
        self.within_update_threshold(new_hashrate[1], calibrated_hashrate[1])

    variance = self.get_variance_value(new_hashrate, calibrated_hashrate)

    return variance >= Config().get('calibration.calibration_update_threshold_min_pc') and \
      variance <= Config().get('calibration.calibration_update_threshold_max_pc')
      


  def hashrate_is_visibly_different(self, new_hashrate, calibrated_hashrate):
    if isinstance(new_hashrate, list):
      return self.hashrate_is_visibly_different(new_hashrate[0], calibrated_hashrate[0]) or \
        self.hashrate_is_visibly_different(new_hashrate[1], calibrated_hashrate[1])

    return "%.2f" % (new_hashrate) != "%.2f" % (calibrated_hashrate)


  def load_calibration(self, device_class, miner_name, algorithm):
    calibration_file = self.data_path + "/calibration_" + device_class + "_" + miner_name + "_" + algorithm + ".yml"

    if os.path.exists(calibration_file):
      calibration = yaml.load(open(calibration_file).read())
    else:
      calibration = {}

    return calibration


  def save_calibration(self, device_class, miner_name, algorithm, calibration):
    calibration_file = self.data_path + "/calibration_" + device_class + "_" + miner_name + "_" + algorithm + ".yml"

    with open(calibration_file + ".new", "w") as f:
      f.write(yaml.dump(calibration))

    os.rename(calibration_file + ".new", calibration_file)


  def update_calibration_data(self, device_class, miner_name, algorithm, hashrate, power_limit):
    calibration = self.load_calibration(device_class, miner_name, algorithm)

    calibration = {
      "hashrate": hashrate,
      "power_limit": power_limit
    }

    self.save_calibration(device_class, miner_name, algorithm, calibration)
