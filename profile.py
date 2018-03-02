
class Profile:
  keys = {
    "name": None,
    "device": None,
    "algorithm": None,
    "power_limit": None,
    "gpu_clock_offset": None,
    "memory_clock_offset": None
  }

  def __init__(self, name=None, data={}):
    for key in self.keys:
      setattr(self, key, self.keys[key]) 

    if not data:
      data = {}

    data['name'] = name

    for key in data.keys():
      setattr(self, key, data[key])
