import exporter
import socket
from apic_exporters.apic_utils import getApicCookie
from prometheus_client import start_http_server

class Apicexporter(exporter.Exporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.apicInfo = self.exporterConfig['device_information']
        self.exporterInfo = self.exporterConfig['exporter_types'][self.exporterType]
        self.duration = self.exporterInfo['collection_interval']
        self.loginCookie = getApicCookie(self.apicInfo['hostname'],
                                                    self.apicInfo['username'],
                                                    self.apicInfo['password'],
                                                    self.apicInfo['proxy'])
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', int(self.exporterInfo['prometheus_port']))) != 0:
                start_http_server(int(self.exporterInfo['prometheus_port']))