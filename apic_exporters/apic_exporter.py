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
        self.exporterInfo = self.exporterConfig['exporter_types'][self.exporterType]
        self.duration = self.exporterInfo['collection_interval']
        self.loginCookie = self.getApicCookie(self.apicInfo['hostname'],
                                                    self.apicInfo['username'],
                                                    self.apicInfo['password'],
                                                    self.apicInfo['proxy'])
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', int(self.exporterInfo['prometheus_port']))) != 0:
                start_http_server(int(self.exporterInfo['prometheus_port']))

    def getApicCookie(self, hostname, username, password, proxies):
        logging.debug("Getting cookie from https://" + hostname + "/api/aaaLogin.json?")
        apiLoginUrl = "https://" + hostname + "/api/aaaLogin.json?"
        loginPayload = {"aaaUser":{"attributes": {"name": username, "pwd": password}}}
        r = requests.post(apiLoginUrl, json=loginPayload, proxies=proxies, verify=False)
        result = json.loads(r.text)
        r.close()
        apiCookie = result['imdata'][0]['aaaLogin']['attributes']['token']
        return apiCookie

    def apicGetRequest(self, url, apicCookie, proxies):
        logging.debug("Making request to " + url)
        cookie = {"APIC-cookie": apicCookie}
        r = requests.get(url, cookies=cookie, proxies=proxies, verify=False)
        result = json.loads(r.text)
        r.close()
        return result