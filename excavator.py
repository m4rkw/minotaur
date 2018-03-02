
from log import Log
from singleton import Singleton
from config import Config

from excavator_api import ExcavatorAPI
from excavator_api import ExcavatorAPIError

class Excavator(ExcavatorAPI):
  __metaclass__ = Singleton


  algo_disable = []

  def get_supported_algorithms(self):
    return [
      "nist5",
      "neoscrypt",
      "equihash",
      "pascal",
      "decred",
      "sia",
      "lbry",
      "blake2s",
      "lyra2rev2",
      "cryptonight",
      "daggerhashimoto",
      "keccak",
      "daggerhashimoto_pascal",
      "daggerhashimoto_decred",
      "daggerhashimoto_sia"
    ]
