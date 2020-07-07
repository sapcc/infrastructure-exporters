import exporter
import socket
import requests
import logging
import json
from prometheus_client import start_http_server
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class Apicexporter(exporter.Exporter):

    CONNECTION_THRESHOLD = 100

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.apicInfo = self.exporterConfig['device_information']
        # Convert proxy none key to no (for compliance with api)
        self.apicInfo['proxy']['no'] = self.apicInfo['proxy'].pop('no_proxy')

        self.exporterInfo = self.exporterConfig['exporter_types'][self.exporterType]
        self.duration = int(self.exporterInfo['collection_interval'])
        self.enabled  = bool(self.exporterInfo['enabled'])

        self.apicHosts = {}
        for apicHost in self.apicInfo['hosts'].split(","):
            self.apicHosts[apicHost]                               = {}
            self.apicHosts[apicHost]['name']                       = apicHost
            self.apicHosts[apicHost]['canConnectToAPIC']           = True
            self.apicHosts[apicHost]['canConnectToAPICCounter']    = 0
            self.apicHosts[apicHost]['cannotConnectToAPICCounter'] = 0
            self.apicHosts[apicHost]['loginCookie'] = self.getApicCookie(apicHost, self.apicInfo['username'],
                                                        self.apicInfo['password'],
                                                        self.apicInfo['proxy'])   # Need to regex replce none with no

        # get the current APICs
        self.getCurrentApicToplogy()

        # start the prometheus
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', int(self.exporterConfig['prometheus_port']))) != 0:
                start_http_server(int(self.exporterConfig['prometheus_port']))

    def getApicCookie(self, apicHost, username, password, proxies):
        logging.debug("Getting cookie from https://" + apicHost + "/api/aaaLogin.json?")
        apiLoginUrl = "https://" + apicHost + "/api/aaaLogin.json?"
        loginPayload = {"aaaUser":{"attributes": {"name": username, "pwd": password}}}

        apiCookie = None

        try:
            r = requests.post(apiLoginUrl, json=loginPayload, proxies=proxies, verify=False, timeout=15)
        except requests.exceptions.ConnectionError as e:
            logging.error("Problem connecting to %s: %s", apiLoginUrl, repr(e))
            self.apicHosts[apicHost]['status_code'] = 500
            self.apicHosts[apicHost]['canConnectToAPIC'] = False
            self.apicHosts[apicHost]['cannotConnectToAPICCounter'] += 1
            return None

        self.apicHosts[apicHost]['canConnectToAPIC']           = True
        self.apicHosts[apicHost]['cannotConnectToAPICCounter'] = 0
        self.apicHosts[apicHost]['status_code']                = r.status_code

        if r.status_code == 200:
            result = json.loads(r.text)
            r.close()
            apiCookie = result['imdata'][0]['aaaLogin']['attributes']['token']
        else:
            logging.error("url %s responding with %s", apiLoginUrl, r.status_code)

        return apiCookie

    def apicGetRequest(self, url, apicCookie, proxies, apicHost):
        logging.debug("Making request to " + url)
        cookie = {"APIC-cookie": apicCookie}

        try:
            r = requests.get(url, cookies=cookie, proxies=proxies, verify=False, timeout=15)
        except Exception as e:
            logging.error("Problem connecting to %s: %s", url, repr(e))
            self.apicHosts[apicHost]['status_code'] = 500
            self.apicHosts[apicHost]['canConnectToAPIC'] = False
            self.apicHosts[apicHost]['cannotConnectToAPICCounter'] += 1
            return None

        self.apicHosts[apicHost]['canConnectToAPIC']           = True
        self.apicHosts[apicHost]['cannotConnectToAPICCounter'] = 0

        if r.status_code == 403 and ("Token was invalid" in r.text or "token" in r.text):
            apicCookie = self.getApicCookie(apicHost,
                                            self.apicInfo['username'],
                                            self.apicInfo['password'],
                                            self.apicInfo['proxy'])

            self.apicHosts[apicHost]['loginCookie'] = apicCookie

        try:
            r = requests.get(url, cookies=cookie, proxies=proxies, verify=False, timeout=15)
        except Exception as e:
            logging.error("Problem connecting to %s: %s", url, repr(e))
            self.apicHosts[apicHost]['status_code'] = 500
            self.apicHosts[apicHost]['canConnectToAPIC'] = False
            return None

        self.apicHosts[apicHost]['canConnectToAPIC']           = True
        self.apicHosts[apicHost]['cannotConnectToAPICCounter'] = 0
        self.apicHosts[apicHost]['status_code']                = r.status_code

        if r.status_code == 200:
            result = json.loads(r.text)
            r.close()
            return result
        else:
            logging.error("url %s responding with %s", url, r.status_code)
            return None

    def getCurrentApicToplogy(self):
        # remove apic hosts not responding for a long time
        #self.apicHosts = self.removeOpphanedApicHosts()

        # snapshot of apic host keys since new hosts will be discovered
        apicHosts = list(self.apicHosts.keys())

        for apicHost in apicHosts:

            url = "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/topSystem.json?query-target-filter=eq(topSystem.role,\"controller\")"
            res = self.apicGetRequest(url, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

            if res is not None:
                if isinstance(res, dict) and isinstance(res.get('imdata'), list):
                    for item in res['imdata']:
                        addr = item['topSystem']['attributes']['oobMgmtAddr']
                        if addr in self.apicHosts.keys():
                            self.apicHosts[addr]['apicMode']         = 'active'
                        else:
                            self.apicHosts[addr] = {}
                            self.apicHosts[addr]['name']             = addr
                            self.apicHosts[addr]['apicMode']         = 'active'
                            self.apicHosts[addr]['canConnectToAPIC'] = True
                            self.apicHosts[addr]['loginCookie']      = self.getApicCookie(addr,
                                                                                          self.apicInfo['username'],
                                                                                          self.apicInfo['password'],
                                                                                          self.apicInfo['proxy'])

            url = "https://" + self.apicHosts[apicHost]['name'] + "/api/node/class/infraSnNode.json"
            res = self.apicGetRequest(url, self.apicHosts[apicHost]['loginCookie'], self.apicInfo['proxy'], apicHost)

            if res is not None:
                if isinstance(res, dict) and isinstance(res.get('imdata'), list):
                    for item in res['imdata']:
                        addr = (item['infraSnNode']['attributes']['oobIpAddr']).split("/")[0]
                        if addr == "0.0.0.0":
                            continue
                        mode = item['infraSnNode']['attributes']['apicMode']
                        if addr in self.apicHosts.keys():
                            self.apicHosts[addr]['apicMode']         = mode
                        else:
                            self.apicHosts[addr] = {}
                            self.apicHosts[addr]['name']             = addr
                            self.apicHosts[addr]['apicMode']         = mode
                            self.apicHosts[addr]['canConnectToAPIC'] = True
                            self.apicHosts[addr]['loginCookie']      = self.getApicCookie(addr,
                                                                                          self.apicInfo['username'],
                                                                                          self.apicInfo['password'],
                                                                                          self.apicInfo['proxy'])

    def getActiveApicHosts(self):
        return {a: b for a, b in self.apicHosts.items() if b['apicMode'] == 'active'}

    def getStandbyApicHosts(self):
        return {a: b for a, b in self.apicHosts.items() if b['apicMode'] == 'standby'}

    def removeOpphanedApicHosts(self):
        return {a: b for a, b in self.apicHosts.items() if (b['canConnectToAPIC'] == True or (b['canConnectToAPIC'] == False and b['cannotConnectToAPICCounter'] < self.CONNECTION_THRESHOLD))}