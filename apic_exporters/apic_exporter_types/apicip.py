import re, logging
from apic_exporters.apic_exporter import Apicexporter
from prometheus_client import Gauge, Counter

class ApicIp(Apicexporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.counter, self.gauge = {}, {}

        self.counter['network_apic_duplicate_ip'] = Counter('network_apic_duplicate_ip',
                                                         'network_apic_duplicate_ip',
                                                         ['apic_host', 'ip', 'mac', 'node_id', 'tenant'])


    def collect(self):
        self.metric_count = 0

        for apicHost in self.getActiveApicHosts():
            self.apicHosts[apicHost]['duplicateIps'] = []

            if self.apicHosts[apicHost]['canConnectToAPIC'] == False:
                continue

            # duplicate IPs
            duplicateIpsUrl = 'https://' + self.apicHosts[apicHost]['name'] + '/api/node/class/fvIp.json?rsp-subtree=full&'
            duplicateIpsUrl += 'rsp-subtree-class=fvReportingNode&query-target-filter=and(ne(fvIp.debugMACMessage,""))'
            duplicateIps = self.apicGetRequest(duplicateIpsUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'],apicHost)

            if not self.isDataValid(self.apicHosts[apicHost]['status_code'], duplicateIps):
                logging.debug("apic host %s is not responding", self.apicHosts[apicHost]['name'])
                continue

            for duplicateIp in duplicateIps['imdata']:
                ipAddres = duplicateIp['fvIp']['attributes']['addr']
                ipDn = duplicateIp['fvIp']['attributes']['dn']
                ipMac = re.search(r"([0-9A-F]{2}:){5}[0-9A-F]{2}", ipDn).group()
                ipTenat = re.match(r"uni\/tn-(.+)\/ap.+", ipDn)[1]
                #ipNode = duplicateIp['fvIp']['children'][0]['fvReportingNode']['attributes']['id']
                #self.apicHosts[apicHost]['duplicateIps'].append({'ip':ipAddres, 'mac':ipMac, 'apicNode':ipNode})
                ipNodes = []
                if 'children' in duplicateIp['fvIp']:
                    for child in duplicateIp['fvIp']['children']:
                        reporting_node_id = child['fvReportingNode']['attributes']['id']
                        ipNodes.append(str(reporting_node_id))

                if ipNodes:
                    self.apicHosts[apicHost]['duplicateIps'].append({
                            'ip': ipAddres,
                            'mac': ipMac,
                            'apicNode': '+'.join(ipNodes),
                            'tn': ipTenat
                    })
                    logging.debug("host: %s, ip: %s, mac: %s, nodes: %s", self.apicHosts[apicHost]['name'],
                                      ipAddres, ipMac, '+'.join(ipNodes))
                else:
                    self.apicHosts[apicHost]['duplicateIps'].append({
                            'ip': ipAddres,
                            'mac': ipMac,
                            'apicNode': 'none',
                            'tn': ipTenat
                    })
                    logging.debug("host: %s, ip: %s, mac: %s, nodes: %s", self.apicHosts[apicHost]['name'],
                                      ipAddres, ipMac, 'none')

                    self.metric_count += 1
                    logging.debug("apic host %s duplicate ip metric count: %s", self.apicHosts[apicHost]['name'], self.metric_count)

                    # all apic hosts are seeing the same nodes
                    break

    def export(self):
        for apicHost in self.getActiveApicHosts():

            # dont export metrics for apics not responding
            if self.apicHosts[apicHost]['canConnectToAPIC'] == False or self.apicHosts[apicHost]['status_code'] != 200:
                logging.debug("Host %s not responding - no duplicate ip metrics to export", self.apicHosts[apicHost]['name'])
                continue

            # export only existing metrics
            if not 'duplicateIps' in self.apicHosts[apicHost] or not self.apicHosts[apicHost]['duplicateIps']:
                logging.debug("Host %s has no duplicateIp to export", self.apicHosts[apicHost]['name'])
            else:
                for duplicateIp in self.apicHosts[apicHost]['duplicateIps']:
                    self.counter['network_apic_duplicate_ip'].labels(
                        self.apicHosts[apicHost]['name'],
                        duplicateIp['ip'],
                        duplicateIp['mac'],
                        duplicateIp['apicNode'],
                        duplicateIp['tn']).inc()

    def isDataValid(self, status_code, data):
        if data is None:
            return False
        if status_code != 200:
            return False
        if isinstance(data, dict) and isinstance(data.get('imdata'), list):
            return True
        return False