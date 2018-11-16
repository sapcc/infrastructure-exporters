import os
import time
import exporter
from vc_exporters import vc_utils
from yamlconfig import YamlConfig
from importlib import import_module
from vc_exporters.vc_exporter_types import api_and_versions, customer_vm_metrics
from prometheus_client import start_http_server


# VCExporter class has information on what to collect,
# how to collect it and how to export it
class VCExporter():

    def __init__(self, vcenterConfigFile, exporterConfigFile):
        self.vcenterConfig = exporter.Exporter.get_config(vcenterConfigFile)
        self.vcenterExporterConfig = exporter.Exporter.get_config(exporterConfigFile)
        self.vcenterInfo = self.vcenterConfig['vcenter_information']
        self.si = vc_utils.connect_to_vcenter(self.vcenterInfo['vcenter_hostname'],
                                             self.vcenterInfo['vcenter_username'],
                                             self.vcenterInfo['vcenter_password'],
                                             self.vcenterInfo['vcenter_port'],
                                             self.vcenterInfo['vcenter_ignore_ssl'],)
    
    def create_exporter(self, exporterType):
        # Select the exporter type to run
        if exporterType == "apiandversions":
            self.vcExporter = api_and_versions.Apiandversions(self.si, self.vcenterInfo, self.vcenterExporterConfig)
            self.vcExporterType = "apiandversions"
        elif exporterType == "customervmmetrics":
            self.vcExporter = customer_vm_metrics.Customervmmetrics(self.si, self.vcenterInfo, self.vcenterExporterConfig)
            self.vcExporterType = "customervmmetrics"
        elif exporterType == "customerdsmetrics":
            pass
        start_http_server(self.vcenterExporterConfig['vcenter_exporters'][self.vcExporterType]['prometheus_port'])
      
    