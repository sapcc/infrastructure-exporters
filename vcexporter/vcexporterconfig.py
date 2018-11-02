# vcconfig.py will handle getting all of the required configurations
# and presenting them in an object that can be used by the vcexporter
import os
from yamlconfig import YamlConfig


defaults = {}

class VcenterExporterConfiguration():

    def __init__(self, configurationfile):
        if os.path.exists(configurationfile):
            try:
                self.config = YamlConfig(configurationfile, defaults)
            except IOError as e:
                print("Couldn't open configuration file: " + str(e))
