import time
import argparse
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

    # Take a list of exporter configs and runs their collectors and exporters
    parser = argparse.ArgumentParser(description='Arguments for vcexporter.py')
    parser.add_argument(
        "-c", "--exporterconfig", help="Specify config file for the exporter", default="samples/vcconfig.yaml")
    parser.add_argument(
        "-t", "--exportertype", help="Specify exporter type [vcapiandversions, vccustomervmmetrics, vccustomerdsmetrics]", default='vcapiandversions')
    args, remaining_argv = parser.parse_known_args()

    # create specified exporter type and run_loop
    runningExporter = ExporterFactory.create_exporter(args.exportertype, exporterType=args.exportertype, exporterConfig=args.exporterconfig)
    runningExporter.run_loop(runningExporter.duration)