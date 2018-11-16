import time
import argparse
from vc_exporters.vc_exporter import VCExporter
from vc_exporters import vc_utils

if __name__ == "__main__":

    # Take a list of exporter configs and runs their collectors and exporters
    parser = argparse.ArgumentParser(description='Arguments for vcexporter.py')
    parser.add_argument(
        "-c", "--vcenterconfig", help="Specify config file for vcenter conneciton", default="samples/vcconfig.yaml")
    parser.add_argument(
        "-e", "--exporterconfig", help="Specify vcenter exporters config file", default="samples/vcexporters.yaml")
    parser.add_argument(
        "-t", "--exportertype", help="Specify exporter type [apiandversions, customervmmetrics, customerdsmetrics]", default='apiandversions')
    args, remaining_argv = parser.parse_known_args()

    runningExporter = VCExporter(args.vcenterconfig, args.exporterconfig)
    runningExporter.create_exporter(args.exportertype)
    while True:
        runningExporter.vcExporter.collect()
        runningExporter.vcExporter.export()
        time.sleep(runningExporter.vcenterExporterConfig['vcenter_exporters'][runningExporter.vcExporterType]['collection_interval'])
        print("loop completed")