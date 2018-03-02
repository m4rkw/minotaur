
from log import Log
from singleton import Singleton
from config import Config
import re
import os

from excavator_api import ExcavatorAPI
from excavator_api import ExcavatorAPIError

class Ethminer(ExcavatorAPI):
  __metaclass__ = Singleton

  algo_remap = {
  }

  algo_disable = []

  def get_supported_algorithms(self):
    return [
      'daggerhashimoto'
    ]

  def supported_algorithms(self):
    return self.get_supported_algorithms()


  def update_supported_algorithms(self):
    pass
