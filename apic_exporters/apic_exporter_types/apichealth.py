import re
from apic_exporters.apic_exporter import Apicexporter
from prometheus_client import Gauge, Counter

class Apichealth(Apicexporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.counter, self.gauge = {}, {}
        self.counter['network_apic_status'] = Counter('network_apic_status',
                                                      'network_apic_status',
                                                      ['hostname', 'code'])
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
                                                         'ip', 'mac', 'node_id', 'tn'])
                                    
    def collect(self):
        self.metric_count = 0
        for apicHost in self.apicHosts:
            self.apicHosts[apicHost]['physIf'] = []
            self.apicHosts[apicHost]['duplicateIps'] = []
            if self.apicHosts[apicHost]['canConnectToAPIC'] == False:
                continue

            apicHealthUrl =  "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/procEntity.json?"
            apicHealthInfo = self.apicGetRequest(apicHealthUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

            # apic is not responding
            if self.apicHosts[apicHost]['status_code'] != 200 or apicHealthInfo is None:
                continue

            # get apic health
            if self.isDataValid(self.apicHosts[apicHost]['status_code'], apicHealthInfo):
                self.apicHosts[apicHost]['apiMetrics_status'] = 200
                self.apicHosts[apicHost]['apicMetrics'] = apicHealthInfo['imdata'][0]['procEntity']['attributes']
                self.metric_count += 3
            else:
                self.apicHosts[apicHost]['apiMetrics_status'] = 0

            physIfUrl = "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/ethpmPhysIf.json?"
            physIfInfo = self.apicGetRequest(physIfUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'],apicHost)
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

            duplicateIpsUrl = 'https://' + self.apicHosts[apicHost]['name'] + '/api/node/class/fvIp.json?rsp-subtree=full&'
            duplicateIpsUrl += 'rsp-subtree-class=fvReportingNode&query-target-filter=and(ne(fvIp.debugMACMessage,""))'
            duplicateIpsInfo = self.apicGetRequest(duplicateIpsUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'],apicHost)
            if self.isDataValid(self.apicHosts[apicHost]['status_code'], duplicateIpsInfo):
                self.apicHosts[apicHost]['duplicateIpsInfo_status'] = 200
                for duplicateIp in duplicateIpsInfo['imdata']:
                    ipAddres = duplicateIp['fvIp']['attributes']['addr']
                    ipDn = duplicateIp['fvIp']['attributes']['dn']
                    ipMac = re.search(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", ipDn).group()
                    ipTenat = re.match(r"uni\/tn-(.+)\/ap.+", ipDn)[1]
                    #ipNode = duplicateIp['fvIp']['children'][0]['fvReportingNode']['attributes']['id']
                    #self.apicHosts[apicHost]['duplicateIps'].append({'ip':ipAddres, 'mac':ipMac, 'apicNode':ipNode})
                    ipNode = []
                    for child in duplicateIp['fvIp']['children']:
                        reporting_node_id = child['fvReportingNode']['attributes']['id']
                        ipNode.append(reporting_node_id)
                    if len(ipNode) > 1:
                        self.apicHosts[apicHost]['duplicateIps'].append({'ip': ipAddres, 'mac': ipMac, 'apicNode': str(ipNode[0] + "-" + ipNode[1]), 'tn': ipTenat})
                    else:
                        self.apicHosts[apicHost]['duplicateIps'].append({'ip': ipAddres, 'mac': ipMac, 'apicNode': str(ipNode[0]), 'tn': ipTenat})

                self.metric_count += 1
            else:
                self.apicHosts[apicHost]['duplicateIpsInfo_status'] = 0

    def export(self):
        for apicHost in self.apicHosts:
            self.counter['network_apic_status'].labels(self.apicHosts[apicHost]['name'],
                                                       self.apicHosts[apicHost]['status_code']).inc()

            # dont export metrics for apics not responding
            if self.apicHosts[apicHost]['status_code'] != 200:
                continue

            if self.apicHosts[apicHost]['apiMetrics_status'] == 200:
                self.gauge['network_apic_cpu_percentage'].labels(self.apicHosts[apicHost]['name']).set(self.apicHosts[apicHost]['apicMetrics']['cpuPct'])
                self.gauge['network_apic_maxMemAlloc'].labels(self.apicHosts[apicHost]['name']).set(self.apicHosts[apicHost]['apicMetrics']['maxMemAlloc'])
                self.gauge['network_apic_memFree'].labels(self.apicHosts[apicHost]['name']).set(self.apicHosts[apicHost]['apicMetrics']['memFree'])
            else:
                self.gauge['network_apic_cpu_percentage'].labels(self.apicHosts[apicHost]['name']).set(-1)
                self.gauge['network_apic_maxMemAlloc'].labels(self.apicHosts[apicHost]['name']).set(-1)
                self.gauge['network_apic_memFree'].labels(self.apicHosts[apicHost]['name']).set(-1)
                continue

            if self.apicHosts[apicHost]['physIfInfo_status'] == 200:
                for physIf in self.apicHosts[apicHost]['physIf']:
                    physIfLabel = self.apicHosts[apicHost]['name'] + "-" + physIf['dn']
                    self.gauge['network_apic_physcial_interface_resets'].labels(physIfLabel).set(physIf['resetCtr'])       

            if self.apicHosts[apicHost]['duplicateIpsInfo_status'] == 200:
                for duplicateIp in self.apicHosts[apicHost]['duplicateIps']:
                    self.gauge['network_apic_duplicate_ip'].labels(self.apicHosts[apicHost]['name'],
                                                                duplicateIp['ip'],
                                                                duplicateIp['mac'],
                                                                duplicateIp['apicNode'],
                                                                duplicateIp['tn']).set(1)

    def isDataValid(self, status_code, data):
        if status_code == 200 and isinstance(data, dict) and isinstance(data.get('imdata'), list):
            return True
        return False
                    