
from singleton import Singleton
from config import Config
from profile import Profile

class Profiles:
  __metaclass__ = Singleton


  def all(self):
    profiles = []

    if Config().get('device_profiles'):
      device_profiles = Config().get('device_profiles')

      for profile_name in device_profiles.keys():
        profiles.append(Profile(profile_name, device_profiles[profile_name]))

    return profiles


  def get(self, profile_name):
    if Config().get('device_profiles.%s' % (profile_name)):
      profile = Profile(profile_name, Config().get('device_profiles.%s' % (profile_name)))

      if profile_name == 'default':
        profile.gpu_clock_offset = None
        profile.memory_clock_offset = None

      return profile

    return False


  def get_for_device_algo(self, device, algorithm):
    for profile in self.all():
      if profile.device and str(profile.device).lower() == device.dclass.lower() and profile.algorithm and profile.algorithm.lower() == algorithm.lower():
        return profile

    for profile in self.all():
      if profile.device and str(profile.device).lower() == device.dclass.lower() and profile.algorithm and profile.algorithm.lower() == 'all':
        return profile

    for profile in self.all():
      if profile.device and str(profile.device).lower() == 'all' and profile.algorithm and profile.algorithm.lower() == 'all':
        return profile

    return self.get('default')
