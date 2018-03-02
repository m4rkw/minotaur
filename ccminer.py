
from log import Log
from singleton import Singleton
from config import Config
import re
import os

from excavator_api import ExcavatorAPI
from excavator_api import ExcavatorAPIError

class Ccminer(ExcavatorAPI):
  __metaclass__ = Singleton

  algo_remap = {
    "blake256r8": "blakecoin",
    "x11gost": "sib",
    "lyra2rev2": "lyra2v2"
  }

  algo_disable = []

  def get_supported_algorithms(self):
    pass


  def supported_algorithms(self):
    return [
      'blake256r8','blake2s','cryptonight','decred','keccak','lbry',
      'lyra2rev2','neoscrypt','nist5','quark','qubit','x11gost',
      'skunk', 'skein', 'groestl'
    ]


  def update_supported_algorithms(self):
    pass
