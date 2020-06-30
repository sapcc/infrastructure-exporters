import re, logging
from apic_exporters.apic_exporter import Apicexporter
from prometheus_client import Gauge, Counter

class Apichealth(Apicexporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)

        self.counter, self.gauge = {}, {}

        self.gauge['network_apic_accessible'] = Gauge('network_apic_accessible',
                                                      'network_apic_accessible',
                                                      ['hostname', 'mode'])

        self.counter['network_apic_status'] = Counter('network_apic_status',
                                                      'network_apic_status',
                                                      ['hostname', 'mode', 'code'])

        self.gauge['network_apic_cpu_percentage'] = Gauge('network_apic_cpu_percentage',
                                                          'network_apic_cpu_percentage',
                                                          ['hostname', 'mode'])

        self.gauge['network_apic_maxMemAlloc'] = Gauge('network_apic_maxMemAlloc',
                                                          'network_apic_maxMemAlloc',
                                                          ['hostname', 'mode'])

        self.gauge['network_apic_memFree'] = Gauge('network_apic_memFree',
                                                          'network_apic_memFree',
                                                          ['hostname', 'mode'])

        self.gauge['network_apic_physcial_interface_resets'] = Gauge('network_apic_physcial_interface_resets',
                                                                    'network_apic_physcial_interface_resets',
                                                                    ['interfaceID'])

    def collect(self):
        self.metric_count = 0

        self.getCurrentApicToplogy()

        # collect health data only for active APIC nodes
        for apicHost in self.getActiveApicHosts():

            if self.apicHosts[apicHost]['canConnectToAPIC'] == False:
                continue

            apicHealthUrl =  "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/procEntity.json?"
            apicHealthInfo = self.apicGetRequest(apicHealthUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

            if self.isDataValid(self.apicHosts[apicHost]['status_code'], apicHealthInfo):
                self.apicHosts[apicHost]['apiMetrics_status'] = 200
                self.apicHosts[apicHost]['apicMetrics'] = apicHealthInfo['imdata'][0]['procEntity']['attributes']
                self.metric_count += 3
            else:
                self.apicHosts[apicHost]['apiMetrics_status'] = 0

            physIfUrl = "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/ethpmPhysIf.json?"
            physIfInfo = self.apicGetRequest(physIfUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'],apicHost)

            self.apicHosts[apicHost]['physIf'] = []
            if self.isDataValid(self.apicHosts[apicHost]['status_code'], physIfInfo):
                self.apicHosts[apicHost]['physIfInfo_status'] = 200
                for physIf in physIfInfo['imdata']:
                    resetCtr = physIf['ethpmPhysIf']['attributes']['resetCtr']
                    physIfDN = physIf['ethpmPhysIf']['attributes']['dn']
                    if int(resetCtr) > 0:
                        self.apicHosts[apicHost]['physIf'].append({'dn':physIfDN, 'resetCtr':resetCtr})
                        self.metric_count += 1
            else:
                self.apicHosts[apicHost]['physIfInfo_status'] = 0

    def export(self):
        for apicHost in self.getActiveApicHosts():

            # apic is accessible
            if self.apicHosts[apicHost]['canConnectToAPIC']:
                self.gauge['network_apic_accessible'].labels(self.apicHosts[apicHost]['name'],
                                                             self.apicHosts[apicHost]['apicMode']).set(0)
            else:
                self.gauge['network_apic_accessible'].labels(self.apicHosts[apicHost]['name'],
                                                             self.apicHosts[apicHost]['apicMode']).set(1)
                continue # do not export metrics for APIC's not accessible


            self.counter['network_apic_status'].labels(self.apicHosts[apicHost]['name'],
                                                       self.apicHosts[apicHost]['apicMode'],
                                                       self.apicHosts[apicHost]['status_code']).inc()


            if self.apicHosts[apicHost]['apiMetrics_status'] == 200:
                self.gauge['network_apic_cpu_percentage'].labels(self.apicHosts[apicHost]['name'],
                                                                 self.apicHosts[apicHost]['apicMode']).set(self.apicHosts[apicHost]['apicMetrics']['cpuPct'])

                self.gauge['network_apic_maxMemAlloc'].labels(self.apicHosts[apicHost]['name'],
                                                              self.apicHosts[apicHost]['apicMode']).set(self.apicHosts[apicHost]['apicMetrics']['maxMemAlloc'])

                self.gauge['network_apic_memFree'].labels(self.apicHosts[apicHost]['name'],
                                                          self.apicHosts[apicHost]['apicMode']).set(self.apicHosts[apicHost]['apicMetrics']['memFree'])
            else:
                self.gauge['network_apic_cpu_percentage'].labels(self.apicHosts[apicHost]['name'],
                                                                 self.apicHosts[apicHost]['apicMode']).set(-1)

                self.gauge['network_apic_maxMemAlloc'].labels(self.apicHosts[apicHost]['name'],
                                                              self.apicHosts[apicHost]['apicMode']).set(-1)

                self.gauge['network_apic_memFree'].labels(self.apicHosts[apicHost]['name'],
                                                          self.apicHosts[apicHost]['apicMode']).set(-1)
                continue

            if self.apicHosts[apicHost]['physIfInfo_status'] == 200:
                for physIf in self.apicHosts[apicHost]['physIf']:
                    physIfLabel = self.apicHosts[apicHost]['name'] + "-" + physIf['dn']
                    self.gauge['network_apic_physcial_interface_resets'].labels(physIfLabel).set(physIf['resetCtr'])       

    def isDataValid(self, status_code, data):
        if data is None:
            return False
        if status_code != 200:
            return False
        if isinstance(data, dict) and isinstance(data.get('imdata'), list):
            return True
        return False
                    