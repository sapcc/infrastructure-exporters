import exporter
import requests
from apic_exporters.apic_exporter import Apicexporter
from prometheus_client import Gauge

class Apichealth(Apicexporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.gauge = {}
        self.gauge['network_apic_cpu_percentage'] = Gauge('network_apic_cpu_percentage',
                                                          'network_apic_cpu_percentage',
                                                          ['hostname'])
        self.gauge['network_apic_maxMemAlloc'] = Gauge('network_apic_maxMemAlloc',
                                                          'network_apic_maxMemAlloc',
                                                          ['hostname'])
        self.gauge['network_apic_memFree'] = Gauge('network_apic_memFree',
                                                          'network_apic_memFree',
                                                          ['hostname'])                                                 
                                    
    def collect(self):
        self.metric_count = 0
        for apicHost in self.apicHosts:
            if self.apicHosts[apicHost]['canConnectToAPIC'] == False:
                continue

            apicHealthUrl =  "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/procEntity.json?"
            apicHealthInfo = self.apicGetRequest(apicHealthUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)
            if apicHealthInfo == "Renew Token":
                self.apicHosts[apicHost]['loginCookie'] = self.getApicCookie(apicHost,
                                                        self.apicInfo['username'],
                                                        self.apicInfo['password'],
                                                        self.apicInfo['proxy'])
                apicHealthInfo = self.apicGetRequest(apicHealthUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'])
            if apicHealthInfo.get('imdata') != None and self.apicHosts[apicHost]['status_code'] == 200:
                self.apicHosts[apicHost]['apicMetrics'] = apicHealthInfo['imdata'][0]['procEntity']['attributes']
                self.metric_count += 3

    def export(self):
        for apicHost in self.apicHosts:
            if self.apicHosts[apicHost]['status_code'] != 200:
                self.gauge['network_apic_cpu_percentage'].labels(self.apicHosts[apicHost]['name']).set(-1)
                self.gauge['network_apic_maxMemAlloc'].labels(self.apicHosts[apicHost]['name']).set(-1)
                self.gauge['network_apic_memFree'].labels(self.apicHosts[apicHost]['name']).set(-1)
                continue

            else:
                self.gauge['network_apic_cpu_percentage'].labels(self.apicHosts[apicHost]['name']).set(self.apicHosts[apicHost]['apicMetrics']['cpuPct'])
                self.gauge['network_apic_maxMemAlloc'].labels(self.apicHosts[apicHost]['name']).set(self.apicHosts[apicHost]['apicMetrics']['maxMemAlloc'])
                self.gauge['network_apic_memFree'].labels(self.apicHosts[apicHost]['name']).set(self.apicHosts[apicHost]['apicMetrics']['memFree'])
                                                                                               