import os
import sys
import logging
import time
from abc import ABC, abstractmethod
from yamlconfig import YamlConfig

class Exporter(ABC):

    def __init__(self, exporterType, exporterConfig):
        super().__init__()
        self.exporterConfig = self.get_config(exporterConfig)
        self.exporterType = exporterType
        self.metric_count = 0
        self.logger = logging.getLogger()
        if self.exporterConfig['device_information']['log_level']:
            self.logger.setLevel(logging.getLevelName(
                    self.exporterConfig['device_information']['log_level'].upper()))
        else:
            self.logger.setLevel(logging.getLevelName("INFO"))
        format = '[%(asctime)s] [%(levelname)s] %(message)s'
        logging.basicConfig(stream=sys.stdout, format=format)    

    @abstractmethod
    def collect(self):
        pass

    @abstractmethod
    def export(self):
        pass

    @classmethod
    def get_config(self, configurationfile):
        defaults = {}
        if os.path.exists(configurationfile):
            try:
                config = YamlConfig(configurationfile, defaults)
            except IOError as e:
                print("Couldn't open configuration file: " + str(e))
            return config
        else:
            logging.error("Config file doesn't exist: " + configurationfile)
            exit(0)