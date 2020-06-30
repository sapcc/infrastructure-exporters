import re, logging
from apic_exporters.apic_exporter import Apicexporter
from prometheus_client import Gauge, Counter

class ApicProcess(Apicexporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.counter, self.gauge = {}, {}

        self.gauge['network_apic_process_memory_used_min'] = Gauge('network_apic_process_memory_used_min',
                                                         'network_apic_process_memory_used_min', ['apicHost', 'procName', 'nodeId'])

        self.gauge['network_apic_process_memory_used_max'] = Gauge('network_apic_process_memory_used_max',
                                                         'network_apic_process_memory_used_max', ['apicHost', 'procName', 'nodeId'])

        self.gauge['network_apic_process_memory_used_avg'] = Gauge('network_apic_process_memory_used_avg',
                                                         'network_apic_process_memory_used_avg', ['apicHost', 'procName', 'nodeId'])


    def collect(self):
        self.metric_count = 0

        for apicHost in self.getActiveApicHosts():
            self.apicHosts[apicHost]['procMetrics'] = []

            if self.apicHosts[apicHost]['canConnectToAPIC'] == False:
                continue

            # get nodes
            apicNodeUrl  = "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/fabricNode.json?"
            apicNodes    = self.apicGetRequest(apicNodeUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

            # apic is not responding
            if self.apicHosts[apicHost]['status_code'] != 200 or apicNodes is None:
                logging.debug("apic host %s is not responding", self.apicHosts[apicHost]['name'])
                continue

            for node in apicNodes['imdata']:
                logging.debug("fabricNode: %s", node['fabricNode']['attributes']['dn'])

                # get nfm process is per node
                apicNfmProcessUrl = 'https://' + self.apicHosts[apicHost]['name'] + '/api/node/class/' \
                    + node['fabricNode']['attributes']['dn'] + '/procProc.json?query-target-filter=eq(procProc.name,"nfm")'
                apicNfmProcess = self.apicGetRequest(apicNfmProcessUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

                if apicNfmProcess is None:
                    logging.debug("Node %s has No nfm process", node['fabricNode']['attributes']['dn'])
                    continue

                if int(apicNfmProcess['totalCount']) > 0:
                    logging.debug("nfmProcess: %s", apicNfmProcess['imdata'][0]['procProc']['attributes']['dn'])

                    apicNfmProcessMemoryUsedURL = 'https://' + self.apicHosts[apicHost]['name'] + '/api/node/mo/' \
                        + apicNfmProcess['imdata'][0]['procProc']['attributes']['dn'] + '/HDprocProcMem5min-0.json'
                    apicNfmProcessMemoryUsed = self.apicGetRequest(apicNfmProcessMemoryUsedURL, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

                    if apicNfmProcessMemoryUsed is None:
                        logging.debug("Process %s has no used memory info", apicNfmProcess['imdata'][0]['procProc']['attributes']['dn'])
                        continue

                    if int(apicNfmProcessMemoryUsed['totalCount']) > 0:
                        nodeId = self.parseNodeId(apicNfmProcess['imdata'][0]['procProc']['attributes']['dn'])
                        logging.debug("procName: %s, nodeId: %s, MemUsedMin: %s, MemUsedMax: %s, MemUsedAvg: %s",
                            apicNfmProcess['imdata'][0]['procProc']['attributes']['name'], nodeId,
                            apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMin'],
                            apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMax'],
                            apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedAvg'])

                        self.apicHosts[apicHost]['procMetrics'].append({
                            'procName':   apicNfmProcess['imdata'][0]['procProc']['attributes']['name'],
                            'nodeId':     nodeId,
                            'memUsedMin': apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMin'],
                            'memUsedMax': apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMax'],
                            'memUsedAvg': apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedAvg']
                        })

                        self.metric_count += 3
                        logging.debug("proc metric count: %s", self.metric_count)

            # skip the other apic hosts since we already collected the metrics data from one host
            break

    def export(self):
        for apicHost in self.apicHosts:

            # dont export metrics for apics not responding
            if self.apicHosts[apicHost]['status_code'] != 200:
                logging.debug("Host %s not responding - no metrics to export", self.apicHosts[apicHost]['name'])
                continue

            # export only existing metrics
            if not 'procMetrics' in self.apicHosts[apicHost] or not self.apicHosts[apicHost]['procMetrics']:
                logging.debug("Host % has no metrics to export", self.apicHosts[apicHost]['name'])
            else:
                for metric in self.apicHosts[apicHost]['procMetrics']:
                    self.gauge['network_apic_process_memory_used_min'].labels(
                        self.apicHosts[apicHost]['name'],
                        metric['procName'],
                        metric['nodeId']
                    ).set(metric['memUsedMin'])

                    self.gauge['network_apic_process_memory_used_max'].labels(
                        self.apicHosts[apicHost]['name'],
                        metric['procName'],
                        metric['nodeId']
                    ).set(metric['memUsedMax'])

                    self.gauge['network_apic_process_memory_used_avg'].labels(
                        self.apicHosts[apicHost]['name'],
                        metric['procName'],
                        metric['nodeId']
                    ).set(metric['memUsedAvg'])

    def isDataValid(self, status_code, data):
        if status_code == 200 and isinstance(data, dict) and isinstance(data.get('imdata'), list):
            return True
        return False

    def parseNodeId(self, procDn):
        nodeId =''
        matchObj = re.match(u".+node-([0-9]*).+", procDn)
        if matchObj:
            nodeId = matchObj.group(1)
        return nodeId