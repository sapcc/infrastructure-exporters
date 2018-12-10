import os
import sys
import logging
import time
import asyncio
from datetime import timedelta, datetime
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
            self.logger.setLevel(self.exporterConfig['device_information']['log_level'])
        else:
            self.logger.setLevel("INFO")
        format = '[%(asctime)s] [%(levelname)s] %(message)s'
        logging.basicConfig(stream=sys.stdout, format=format)    

    @abstractmethod
    def collect(self):
        pass

    @abstractmethod
    def export(self):
        pass

    @asyncio.coroutine
    def run_loop(self, duration):
         # Start infinite loop to get metrics
        while True:
            logging.debug('====> total loop start: %s' % datetime.now())
            # get the start time of the loop to be able to fill it to intervall exactly at the end
            
            yield None
            collect_start_time = int(time.time())
            self.collect()
            collect_end_time = int(time.time())
   
            yield None
            export_start_time = int(time.time())
            self.export()
            export_end_time = int(time.time())

            total_loop_time = ((collect_end_time - collect_start_time) + (export_end_time - export_start_time))
            #loop_end_time = int(time.time())
            logging.info('number of ' + self.exporterType + ' we got metrics for ' +
                        str(self.metric_count) + " " + self.exporterType +
                        '\'s - actual runtime: ' + str(total_loop_time) + 's')
                        #'\'s - actual runtime: ' + str(loop_end_time - loop_start_time) + 's')
                         
            # this is the time we sleep to fill the loop runtime until it reaches "interval"
            # the 0.9 makes sure we have some overlap to the last interval to avoid gaps in
            # metrics coverage (i.e. we get the metrics quicker than the averaging time)
            loop_sleep_time = 0.9 * \
                self.exporterConfig['exporter_types'][self.exporterType]['collection_interval'] - \
                (collect_end_time - collect_start_time) + (export_end_time - export_end_time)
                #(loop_end_time - loop_start_time)
                
            if loop_sleep_time < 0:
                logging.warn('getting the metrics takes around ' + str(
                    self.exporterConfig['exporter_types'][self.exporterType]['collection_interval']) + ' seconds or longer - please increase the interval setting')
                loop_sleep_time = 0

            logging.debug('====> loop end before sleep: %s' % datetime.now())
            time.sleep(int(loop_sleep_time))
            logging.debug('====> total loop end: %s' % datetime.now())

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