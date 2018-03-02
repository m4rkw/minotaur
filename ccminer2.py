
from log import Log
from singleton import Singleton
from config import Config
import re
import os

from excavator_api import ExcavatorAPI
from excavator_api import ExcavatorAPIError

class Ccminer2(ExcavatorAPI):
  __metaclass__ = Singleton

  algo_remap = {
    'whirlpoolx': 'whirlpool'
  }

  algo_disable = []

  def get_supported_algorithms(self):
    return [
      'x11gost',
      'blake2s',
      'keccak',
      'lyra2v2',
      'nist5',
      'quark',
      'qubit',
      'x11',
      'x13',
      'lbry',
      'neoscrypt',
      'skein',
      'groestl'
    ]

  def supported_algorithms(self):
    return self.get_supported_algorithms()


  def update_supported_algorithms(self):
    pass
