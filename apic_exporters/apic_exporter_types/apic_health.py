import exporter
import requests
from apic_exporters.apic_utils import getApicCookie, apicGetRequest

class Apichealth(exporter.Exporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.apicInfo = self.exporterConfig['device_information']
        self.exporterInfo = self.exporterConfig['exporter_types'][self.exporterType]
        self.loginCookie = getApicCookie(self.apicInfo['hostname'],
                                                    self.apicInfo['username'],
                                                    self.apicInfo['password'],
                                                    self.apicInfo['proxy'])

    def collect(self):
        self.apicHealthUrl =  "https://" + self.apicInfo['hostname'] + "/api/node/class/procEntity.json?"
        self.apicHealthInfo = apicGetRequest(self.apicHealthUrl, self.loginCookie, self.apicInfo['proxy'])

    def export(self):
        pass