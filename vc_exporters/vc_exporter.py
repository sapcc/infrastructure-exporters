import exporter
from abc import ABC, abstractmethod
from vc_exporters import vc_utils
from prometheus_client import start_http_server


# VCExporter class has information on what to collect,
# how to collect it and how to export it
class VCExporter(exporter.Exporter):

    def __init__(self, exporterType, vcenterExporterConfigFile):
        super().__init__(exporterType, vcenterExporterConfigFile)
        self.vcenterInfo = self.exporterConfig['device_information']
        self.exporterInfo = self.exporterConfig['exporter_types'][self.exporterType]
        self.duration = self.exporterInfo['collection_interval']
        self.si = vc_utils.connect_to_vcenter(self.vcenterInfo['hostname'],
                                             self.vcenterInfo['username'],
                                             self.vcenterInfo['password'],
                                             self.vcenterInfo['port'],
                                             self.vcenterInfo['ignore_ssl'],)
        start_http_server(self.exporterInfo['prometheus_port'])
      
    