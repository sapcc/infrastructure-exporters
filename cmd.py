import time
import argparse
import os
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
            print("couldn't create object")
            return None

if __name__ == "__main__":

    # Take a list of exporter configs and runs their collectors and exporters
    parser = argparse.ArgumentParser(description='Arguments for vcexporter.py')
    parser.add_argument(
        "-c", "--exporterconfig", help="Specify config file for the exporter", default=os.getcwd() + "/samples/vcconfig.yaml")
    parser.add_argument(
        "-t", "--exportertype", help="Specify exporter type [vcapiandversions, vccustomervmmetrics, vccustomerdsmetrics]", default='vcapiandversions')
    args, remaining_argv = parser.parse_known_args()
    if not args.exporterconfig.startswith("/"):
        print("Please specify full path to config file")
        exit(0)

    # create specified exporter type and run_loop
    try:
        runningExporter = ExporterFactory.create_exporter(args.exportertype, exporterType=args.exportertype, exporterConfig=args.exporterconfig)
    except Exception as ex:
        print(str(ex))
    if runningExporter != None:
        runningExporter.run_loop(runningExporter.duration)
    else:
        print("Couldn't create exporter type: " + args.exportertype)