import re, logging
from apic_exporters.apic_exporter import Apicexporter
from prometheus_client import Gauge, Counter

class ApicProcess(Apicexporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.counter, self.gauge = {}, {}

        self.gauge['network_apic_process_memory_used_min'] = Gauge('network_apic_process_memory_used_min',
                                                         'network_apic_process_memory_used_min', ['hostname', 'procType', 'procName'])

        self.gauge['network_apic_process_memory_used_max'] = Gauge('network_apic_process_memory_used_max',
                                                         'network_apic_process_memory_used_max', ['hostname', 'procType', 'procName'])

        self.gauge['network_apic_process_memory_used_avg'] = Gauge('network_apic_process_memory_used_avg',
                                                         'network_apic_process_memory_used_avg', ['hostname', 'procType', 'procName'])


    def collect(self):
        self.metric_count = 0
        for apicHost in self.apicHosts:
            self.apicHosts[apicHost]['apicProcMetrics'] = {}

            if self.apicHosts[apicHost]['canConnectToAPIC'] == False:
                continue

            # get nodes
            apicNodeUrl  = "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/fabricNode.json?"
            apicNodeList = (self.apicGetRequest(apicNodeUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost))['imdata']

            # apic is not responding
            if self.apicHosts[apicHost]['status_code'] != 200 or apicNodeList is None:
                continue

            for node in apicNodeList:

                # get nfm process is per node
                apicNfmProcessUrl = 'https://' + self.apicHosts[apicHost]['name'] + '/api/node/class/' \
                    + node['fabricNode']['attributes']['dn'] + '/procProc.json?query-target-filter=eq(procProc.name,"nfm")'
                apicNfmProcessList = self.apicGetRequest(apicNfmProcessUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

                if int(apicNfmProcessList['totalCount']) > 0:
#                    logging.info("nfm process id: %s", apicNfmProcessList['imdata'][0]['procProc']['attributes']['dn'])

                    apicNfmProcessMemoryUsedURL = 'https://' + self.apicHosts[apicHost]['name'] + '/api/node/mo/' \
                        + apicNfmProcessList['imdata'][0]['procProc']['attributes']['dn'] + '/HDprocProcMem5min-0.json'
                    apicNfmProcessMemoryUsed = self.apicGetRequest(apicNfmProcessMemoryUsedURL, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

                    if int(apicNfmProcessMemoryUsed['totalCount']) > 0:
                        logging.info("procType: %s, procName: %s, MemUsedMin: %s, MemUsedMax: %s, MemUsedAvg: %s",
                            "nfm",
                            apicNfmProcessList['imdata'][0]['procProc']['attributes']['dn'],
                            apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMin'],
                            apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMax'],
                            apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedAvg'])

                        self.apicHosts[apicHost]['apicProcMetrics'].update({'procType': 'nfm',
                            'procName': apicNfmProcessList['imdata'][0]['procProc']['attributes']['dn'],
                            'memUsedMin': apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMin'],
                            'memUsedMax': apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMax'],
                            'memUsedAvg': apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedAvg']})

    def export(self):
        for apicHost in self.apicHosts:

            # dont export metrics for apics not responding
            if self.apicHosts[apicHost]['status_code'] != 200:
                continue

            # export only existing metrics
            if self.apicHosts[apicHost]['apicProcMetrics'] == True:
                self.gauge['network_apic_process_memory_used_min'].labels(self.apicHosts[apicHost]['name'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procType'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procName']
                ).set(self.apicHosts[apicHost]['apicProcMetrics']['memUsedMin'])

                self.gauge['network_apic_process_memory_used_max'].labels(self.apicHosts[apicHost]['name'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procType'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procName']
                ).set(self.apicHosts[apicHost]['apicProcMetrics']['memUsedMax'])

                self.gauge['network_apic_process_memory_used_avg'].labels(self.apicHosts[apicHost]['name'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procType'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procName']
                ).set(self.apicHosts[apicHost]['apicProcMetrics']['memUsedAvg'])

    def isDataValid(self, status_code, data):
        if status_code == 200 and isinstance(data, dict) and isinstance(data.get('imdata'), list):
            return True
        return False
                    