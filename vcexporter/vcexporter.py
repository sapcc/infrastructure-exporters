from vcexporter import vcexporterconfig, vcutils
from yamlconfig import YamlConfig
import argparse
import os

# VCExporter class has information on what to collect,
# how to collect it and how to export it
class VCExporter():

    def __init__(self, vcenterConfigFile, exporterConfigFile):
        self.vcenterConfig = vcexporterconfig.VcenterExporterConfiguration(vcenterConfigFile)
        self.vcenterExporterConfig = vcexporterconfig.VcenterExporterConfiguration(exporterConfigFile)
        vcenterInfo = self.vcenterConfig.config['vcenter_information']
        self.si = vcutils.connect_to_vcenter(vcenterInfo['vcenter_hostname'],
                                             vcenterInfo['vcenter_username'],
                                             vcenterInfo['vcenter_password'],
                                             vcenterInfo['vcenter_port'],
                                             vcenterInfo['vcenter_ignore_ssl'],)



if __name__ == "__main__":

    # Take a list of exporter configs and runs their collectors and exporters
    parser = argparse.ArgumentParser(description='Arguments for vcexporter.py')
    parser.add_argument(
        "-c", "--vcenterconfig", help="Specify config file for vcenter conneciton", default="../samples/vcconfig.yaml")
    parser.add_argument(
        "-e", "--exporterconfig", help="Specify vcenter exporters config file", default="../samples/vcexporters.yaml")
    args, remaining_argv = parser.parse_known_args()
    