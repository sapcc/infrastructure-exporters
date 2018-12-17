import time
import argparse
import os
import exporter
import asyncio
import logging
from datetime import timedelta, datetime
from concurrent.futures import FIRST_COMPLETED
from yamlconfig import YamlConfig
from vc_exporters.vc_exporter_types import vcapiandversions, vccustomervmmetrics, vccustomerdsmetrics
from apic_exporters.apic_exporter_types import apichealth


EXPORTERS = {
    'vcapiandversions': vcapiandversions.Vcapiandversions,
    'vccustomervmmetrics': vccustomervmmetrics.Vccustomervmmetrics,
    'vccustomerdsmetrics': vccustomerdsmetrics.Vccustomerdsmetrics,
    'apichealth': apichealth.Apichealth
}

class ExporterFactory(object):
    @staticmethod
    def create_exporter(exportertype, **kwargs):
        try:
            return EXPORTERS[exportertype.lower()](**kwargs)
        except Exception as ex:
            print(str(ex))
            return None

#@asyncio.coroutine
async def run_loop(exporterInstance, duration):
#def run_loop(exporterInstance, duration):
        # Start infinite loop to get metrics
    logging.info('Starting run_loop: ' + exporterInstance.exporterType)
    while True:
        logging.debug('====> total loop start: %s' % datetime.now())
        # get the start time of the loop to be able to fill it to intervall exactly at the end
        
        collect_start_time = int(time.time())
        #asyncio.get_event_loop().create_task(exporterInstance.collect())
        exporterInstance.collect()
        collect_end_time = int(time.time())


        export_start_time = int(time.time())
        #asyncio.get_event_loop().create_task(exporterInstance.export())
        exporterInstance.export()
        export_end_time = int(time.time())



        total_loop_time = ((collect_end_time - collect_start_time) + (export_end_time - export_start_time))
        #loop_end_time = int(time.time())
        logging.info('number of ' + exporterInstance.exporterType + ' we got metrics for ' +
                    str(exporterInstance.metric_count) + " " +exporterInstance.exporterType +
                    '\'s - actual runtime: ' + str(total_loop_time) + 's')
                    #'\'s - actual runtime: ' + str(loop_end_time - loop_start_time) + 's')
                        
        # this is the time we sleep to fill the loop runtime until it reaches "interval"
        # the 0.9 makes sure we have some overlap to the last interval to avoid gaps in
        # metrics coverage (i.e. we get the metrics quicker than the averaging time)
        loop_sleep_time = 0.9 * \
            exporterInstance.exporterConfig['exporter_types'][exporterInstance.exporterType]['collection_interval'] - \
            (collect_end_time - collect_start_time) + (export_end_time - export_end_time)
            #(loop_end_time - loop_start_time)
            
        if loop_sleep_time < 0:
            logging.warn('getting the metrics takes around ' + str(
                exporterInstance.exporterConfig['exporter_types'][exporterInstance.exporterType]['collection_interval']) + ' seconds or longer - please increase the interval setting')
            loop_sleep_time = 0

        logging.debug('====> loop end before sleep: %s' % datetime.now())
        await asyncio.sleep(int(loop_sleep_time))
        logging.debug('====> total loop end: %s' % datetime.now())

        logging.info('Ending run_loop: ' + exporterInstance.exporterType)
        
        
if __name__ == "__main__":

    exporterConfigMapping = {}
    # Take a list of exporter configs and runs their collectors and exporters
    parser = argparse.ArgumentParser(description='Arguments for vcexporter.py')
    parser.add_argument(
        "-c", "--exporterconfigfiles", help="Specify config files for the exporters, comma separated, full path")
    parser.add_argument(
        "-f", "--singleconfifigfile", help="Specify full path to single config file to run only one exporter.  Must use -t flag also to specify type." )
    parser.add_argument(
        "-t", "--exportertype", help="Specify exporter type [vcapiandversions, vccustomervmmetrics, vccustomerdsmetrics, apichealth] Used with -f flag")
    args, remaining_argv = parser.parse_known_args()
    
    # Process arguments and create exporterConfigMapping
    if args.exporterconfigfiles is not None:
        configFiles = args.exporterconfigfiles.split(',')
        for configFile in configFiles:
            if not configFile.startswith("/"):
                print("Please use full path to config files")
                exit(0)
            else:
                exporterConfigs = exporter.Exporter.get_config(configFile)
                for exporterType in exporterConfigs['exporter_types']:
                    exporter_enabled = exporterConfigs.get('exporter_types', {}).get(exporterType, {}).get('enabled')
                    if exporter_enabled:
                        exporterConfigMapping[exporterType] = configFile
    
    elif args.singleconfifigfile is not None and args.exportertype is not None:
        if not args.singleconfifigfile.startswith("/"):
            print("Please use full path to configfile")
            exit(0)
        else:
            exporterConfigMapping[args.exportertype] = args.singleconfifigfile
    else:
        parser.print_help()

    logging = logging.getLogger()

    # Create an asynchronous exporter for each exporter in the exporterConfigMapping
    run_loops = []
    for exportertype in exporterConfigMapping:
        currentExporter = ExporterFactory.create_exporter(exportertype, exporterType=exportertype, exporterConfig=exporterConfigMapping[exportertype])
        if currentExporter != None:
            run_loops.append((run_loop, currentExporter, currentExporter.duration))
        else:
            print("Couldn't add exporter "  + exportertype)

    task_map = {}
    for task in run_loops:
        task_map[task] = asyncio.async(task[0](task[1], task[2]))
        #task_map[task] = task[0](task[1], task[2])
        #asyncio.get_event_loop().create_task(task_map[task])
    loop = asyncio.get_event_loop()
    loop.run_forever()
    