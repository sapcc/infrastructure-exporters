import exporter
import socket
import requests
import logging
import os
import json
from prometheus_client import start_http_server

class Apicexporter(exporter.Exporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.apicInfo = self.exporterConfig['device_information']
        # Convert proxy none key to no (for compliance with api)
        self.apicInfo['proxy']['no'] = self.apicInfo['proxy'].pop('no_proxy')
        self.exporterInfo = self.exporterConfig['exporter_types'][self.exporterType]
        self.duration = int(self.exporterInfo['collection_interval'])
        self.apicHosts = {}
        for apicHost in self.apicInfo['hosts'].split(","):
            self.apicHosts[apicHost] = {}
            self.apicHosts[apicHost]['name'] = apicHost
            self.apicHosts[apicHost]['canConnectToAPIC'] = True
            self.apicHosts[apicHost]['loginCookie'] = self.getApicCookie(apicHost,
                                                        self.apicInfo['username'],
                                                        self.apicInfo['password'],
                                                        self.apicInfo['proxy'])   # Need to regex replce none with no
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', int(self.exporterConfig['prometheus_port']))) != 0:
                start_http_server(int(self.exporterConfig['prometheus_port']))

    def getApicCookie(self, apicHost, username, password, proxies):
        logging.debug("Getting cookie from https://" + apicHost + "/api/aaaLogin.json?")
        apiLoginUrl = "https://" + apicHost + "/api/aaaLogin.json?"
        loginPayload = {"aaaUser":{"attributes": {"name": username, "pwd": password}}}
        try:
            r = requests.post(apiLoginUrl, json=loginPayload, proxies=proxies, verify=False, timeout=15)
        except requests.exceptions.ConnectionError as e:
            logging.error("Can't connect to apic at " + apicHost)
            self.apicHosts[apicHost]['canConnectToAPIC'] = False
            self.apicHosts[apicHost]['status_code'] = 0
            return None

        if r.status_code != 200:
            logging.info("Unable to get cookie at URL: " + apiLoginUrl)
            self.apicHosts[apicHost]['status_code'] = 0
        else:
            result = json.loads(r.text)
            r.close()
            apiCookie = result['imdata'][0]['aaaLogin']['attributes']['token']
            self.apicHosts[apicHost]['status_code'] = 200
            return apiCookie

    def apicGetRequest(self, url, apicCookie, proxies, apicHost):
        logging.debug("Making request to " + url)
        cookie = {"APIC-cookie": apicCookie}
        try:
            r = requests.get(url, cookies=cookie, proxies=proxies, verify=False, timeout=15)
        except Exception as e:
            logging.error("Problem getting cookie for apic at " + apicHost)
            return None


        if r.status_code == 403 and "Token was invalid" in r.text:
            return "Renew Token"
        if r.status_code != 200:
            logging.info("Unable to get data from URL: " + url)
            self.apicHosts[apicHost]['status_code'] = 0
        else:
            result = json.loads(r.text)
            r.close()
            self.apicHosts[apicHost]['status_code']= 200
            return result