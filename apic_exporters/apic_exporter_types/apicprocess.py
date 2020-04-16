import re, logging
from apic_exporters.apic_exporter import Apicexporter
from prometheus_client import Gauge, Counter

class ApicProcess(Apicexporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.counter, self.gauge = {}, {}

        self.gauge['network_apic_process_memory_used_min'] = Gauge('network_apic_process_memory_used_min',
                                                         'network_apic_process_memory_used_min', ['apicHost', 'procName', 'procDn'])

        self.gauge['network_apic_process_memory_used_max'] = Gauge('network_apic_process_memory_used_max',
                                                         'network_apic_process_memory_used_max', ['apicHost', 'procName', 'procDn'])

        self.gauge['network_apic_process_memory_used_avg'] = Gauge('network_apic_process_memory_used_avg',
                                                         'network_apic_process_memory_used_avg', ['apicHost', 'procName', 'procDn'])


    def collect(self):
        self.metric_count = 0
        for apicHost in self.apicHosts:
            self.apicHosts[apicHost]['apicProcMetrics'] = {}

            if self.apicHosts[apicHost]['canConnectToAPIC'] == False:
                continue

            # get nodes
            apicNodeUrl  = "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/fabricNode.json?"
            apicNodes    = self.apicGetRequest(apicNodeUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

            # apic is not responding
            if self.apicHosts[apicHost]['status_code'] != 200 or apicNodes is None:
                continue

            # get apic health
            if self.isDataValid(self.apicHosts[apicHost]['status_code'], apicNodes):
                self.apicHosts[apicHost]['apiMetrics_status'] = 200
            else:
                self.apicHosts[apicHost]['apiMetrics_status'] = 0

            for node in apicNodes['imdata']:

                # get nfm process is per node
                apicNfmProcessUrl = 'https://' + self.apicHosts[apicHost]['name'] + '/api/node/class/' \
                    + node['fabricNode']['attributes']['dn'] + '/procProc.json?query-target-filter=eq(procProc.name,"nfm")'
                apicNfmProcessList = self.apicGetRequest(apicNfmProcessUrl, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

                if apicNfmProcessList is None:
                    continue

                if int(apicNfmProcessList['totalCount']) > 0:

                    apicNfmProcessMemoryUsedURL = 'https://' + self.apicHosts[apicHost]['name'] + '/api/node/mo/' \
                        + apicNfmProcessList['imdata'][0]['procProc']['attributes']['dn'] + '/HDprocProcMem5min-0.json'
                    apicNfmProcessMemoryUsed = self.apicGetRequest(apicNfmProcessMemoryUsedURL, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

                    if apicNfmProcessMemoryUsed is None:
                        continue

                    if int(apicNfmProcessMemoryUsed['totalCount']) > 0:
                        logging.debug("procName: %s, procDn: %s, MemUsedMin: %s, MemUsedMax: %s, MemUsedAvg: %s",
                            apicNfmProcessList['imdata'][0]['procProc']['attributes']['name'],
                            apicNfmProcessList['imdata'][0]['procProc']['attributes']['dn'],
                            apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMin'],
                            apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMax'],
                            apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedAvg'])

                        self.apicHosts[apicHost]['apicProcMetrics'].update({
                            'procName':   apicNfmProcessList['imdata'][0]['procProc']['attributes']['name'],
                            'procDn':     apicNfmProcessList['imdata'][0]['procProc']['attributes']['dn'],
                            'memUsedMin': apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMin'],
                            'memUsedMax': apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedMax'],
                            'memUsedAvg': apicNfmProcessMemoryUsed['imdata'][0]['procProcMemHist5min']['attributes']['usedAvg']
                        })

                        self.metric_count += 3
                        logging.debug("proc metric count: %s", self.metric_count)

    def export(self):
        for apicHost in self.apicHosts:

            # dont export metrics for apics not responding
            if self.apicHosts[apicHost]['status_code'] != 200:
                continue

            # export only existing metrics
            if self.apicHosts[apicHost]['apiMetrics_status'] == 200:
                self.gauge['network_apic_process_memory_used_min'].labels(self.apicHosts[apicHost]['name'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procName'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procDn']
                ).set(self.apicHosts[apicHost]['apicProcMetrics']['memUsedMin'])

                self.gauge['network_apic_process_memory_used_max'].labels(self.apicHosts[apicHost]['name'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procName'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procDn']
                ).set(self.apicHosts[apicHost]['apicProcMetrics']['memUsedMax'])

                self.gauge['network_apic_process_memory_used_avg'].labels(self.apicHosts[apicHost]['name'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procName'],
                    self.apicHosts[apicHost]['apicProcMetrics']['procDn']
                ).set(self.apicHosts[apicHost]['apicProcMetrics']['memUsedAvg'])

    def isDataValid(self, status_code, data):
        if status_code == 200 and isinstance(data, dict) and isinstance(data.get('imdata'), list):
            return True
        return False
                    