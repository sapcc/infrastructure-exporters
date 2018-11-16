import os
from abc import ABC, abstractmethod
from yamlconfig import YamlConfig


class Exporter(ABC):

    def __init__(self):
        super().__init__()

    @abstractmethod
    def collect(self):
        pass

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