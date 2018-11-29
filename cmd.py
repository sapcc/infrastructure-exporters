import time
import argparse
import os
import exporter
import asyncio
from concurrent.futures import FIRST_COMPLETED
from yamlconfig import YamlConfig
from vc_exporters.vc_exporter_types import vcapiandversions, vccustomervmmetrics
from apic_exporters.apic_exporter_types import apichealth


EXPORTERS = {
    'vcapiandversions': vcapiandversions.Vcapiandversions,
    'vccustomervmmetrics': vccustomervmmetrics.Vccustomervmmetrics,
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

    # Create an asynchronous exporter for each exporter in the exporterConfigMapping
    run_loops = []
    for exportertype in exporterConfigMapping:
        currentExporter = ExporterFactory.create_exporter(exportertype, exporterType=exportertype, exporterConfig=exporterConfigMapping[exportertype])
        if currentExporter != None:
            run_loops.append((currentExporter.run_loop, currentExporter.duration))
        else:
            print("Couldn't add exporter "  + exportertype)

    task_map = {}
    for task in run_loops:
        task_map[task] = asyncio.async(task[0](task[1]))
    loop = asyncio.get_event_loop()
    loop.run_forever()


    # if not args.exporterconfig.startswith("/"):
    #     print("Please specify full path to config file")
    #     exit(0)

    # # create specified exporter type and run_loop
    # try:
    #     runningExporter = ExporterFactory.create_exporter(args.exportertype, exporterType=args.exportertype, exporterConfig=args.exporterconfig)
    # except Exception as ex:
    #     print(str(ex))
    # if runningExporter != None:
    #     runningExporter.run_loop(runningExporter.duration)
    # else:
    #     print("Couldn't create exporter type: " + args.exportertype)