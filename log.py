
import os
import datetime
import sys
from singleton import Singleton
from config import Config

class Log:
  __metaclass__ = Singleton

  def __init__(self, log_file=None):
    if log_file:
      self.log_file = log_file
    else:
      self.log_file = Config().get('logging.log_file')


  def set_log_file(self, log_file):
    self.log_file = log_file


  def add(self, level, message, silent=False):
    if not os.path.exists(os.path.dirname(self.log_file)):
      os.mkdir(os.path.dirname(self.log_file))

    now = datetime.datetime.now()

    with open(self.log_file, "a+") as f:
      f.write("%s: [%s] %s\n" % (now.strftime("%Y-%m-%d %H:%M:%S"), level, message))

      if not silent:
        sys.stdout.write("%s: %s\n" % (level, message))
        sys.stdout.flush()

    if os.path.getsize(self.log_file) >= (Config().get('logging.max_size_mb') * 1024 * 1024):
      self.rotate_logs()

    if level == "fatal":
      sys.exit(1)


  def rotate_logs(self):
    logfile = self.log_file

    for i in reversed(range(1, Config().get('logging.log_file_count') - 1)):
      os.rename(logfile + ".%d" % (i), logfile + ".%d" % (i+1))

    os.rename(logfile, logfile + ".1")
