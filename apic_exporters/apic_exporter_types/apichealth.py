import re
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
        self.gauge['network_apic_physcial_interface_resets'] = Gauge('network_apic_physcial_interface_resets',
                                        'network_apic_physcial_interface_resets',
                                        ['interfaceID'])  
        self.gauge['network_apic_duplicate_ip'] = Gauge('network_apic_duplicate_ip',
                                                         'network_apic_duplicate_ip',
                                                         ['apic_host',
                                                         'ip', 'mac', 'node_id'])
                                    
    def collect(self):
        self.metric_count = 0
        for apicHost in self.apicHosts:
            self.apicHosts[apicHost]['physIf'] = []
            self.apicHosts[apicHost]['duplicateIps'] = []
            if self.apicHosts[apicHost]['canConnectToAPIC'] == False:
                continue

            apicHealthUrl =  "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/procEntity.json?"
            apicHealthInfo = self.apicGetRequest(apicHealthUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)
            if apicHealthInfo == "Renew Token":
                self.apicHosts[apicHost]['loginCookie'] = self.getApicCookie(apicHost,
                                                        self.apicInfo['username'],
                                                        self.apicInfo['password'],
                                                        self.apicInfo['proxy'])
                apicHealthInfo = self.apicGetRequest(apicHealthUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'],apicHost)
            
            if self.apicHosts[apicHost]['status_code'] == 200 and apicHealthInfo.get('imdata') != None:
                self.apicHosts[apicHost]['apicMetrics'] = apicHealthInfo['imdata'][0]['procEntity']['attributes']
                self.metric_count += 3
            
            physIfUrl = "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/ethpmPhysIf.json?"
            physIfInfo = self.apicGetRequest(physIfUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'],apicHost)
            if self.apicHosts[apicHost]['status_code'] == 200 and isinstance(physIfInfo['imdata'], list):
                for physIf in physIfInfo['imdata']:
                    resetCtr = physIf['ethpmPhysIf']['attributes']['resetCtr']
                    physIfDN = physIf['ethpmPhysIf']['attributes']['dn']
                    self.apicHosts[apicHost]['physIf'].append({'dn':physIfDN, 'resetCtr':resetCtr, 'status_code':200})
                    self.metric_count += 1

            duplicateIpsUrl = 'https://' + self.apicHosts[apicHost]['name'] + '/api/node/class/fvIp.json?rsp-subtree=full&'
            duplicateIpsUrl += 'rsp-subtree-class=fvReportingNode&query-target-filter=and(ne(fvIp.debugMACMessage,""))'
            duplicateIpsInfo = self.apicGetRequest(duplicateIpsUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'],apicHost)
            if self.apicHosts[apicHost]['status_code'] == 200 and isinstance(duplicateIpsInfo, dict) and duplicateIpsInfo is not None and int(duplicateIpsInfo.get('totalCount')) > 0:
                for duplicateIp in duplicateIpsInfo['imdata']:
                    ipAddres = duplicateIp['fvIp']['attributes']['addr']
                    ipMac = re.search(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", duplicateIp['fvIp']['attributes']['dn']).group()
                    ipNode = duplicateIp['fvIp']['children'][0]['fvReportingNode']['attributes']['id']
                    self.apicHosts[apicHost]['duplicateIps'].append({'ip':ipAddres, 'mac':ipMac, 'apicNode':ipNode, 'status_code':200})
                    self.metric_count += 1

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
                          
            for physIf in self.apicHosts[apicHost]['physIf']:
                if physIf['status_code'] == 200:
                    physIfLabel = self.apicHosts[apicHost]['name'] + "-" + physIf['dn']
                    self.gauge['network_apic_physcial_interface_resets'].labels(physIfLabel).set(physIf['resetCtr'])       
                else:
                    self.gauge['network_apic_physcial_interface_resets'].labels(physIfLabel).set(-1)

            for duplicateIp in self.apicHosts[apicHost]['duplicateIps']:
                if duplicateIp['status_code'] == 200:
                    self.gauge['network_apic_duplicate_ip'].labels(self.apicHosts[apicHost]['name'],
                                                                   duplicateIp['ip'],
                                                                   duplicateIp['mac'],
                                                                   duplicateIp['apicNode']).set(1)
                else:
                    self.gauge['network_apic_duplicate_ip'].labels(self.apicHosts[apicHost]['name'],ip,mac,node).set(-1)

                    