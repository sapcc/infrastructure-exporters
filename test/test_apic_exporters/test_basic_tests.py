import unittest
import requests
import os
import json
from exporter import Exporter

class TestExporter(unittest.TestCase):


    def setUp(self):
        # Get credentials from file or use defaults
        apiConfigFile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/apicconfig.yaml"
        self.apicConfigs = Exporter.get_config(apiConfigFile)['apic_information']
        self.proxy = {'http': '', 'https': '', 'no': '*'}
        self.apicLoginUrl = "https://" + self.apicConfigs['apic_host'] + "/api/aaaLogin.json?"
        self.apicMetricsUrl = "https://" + self.apicConfigs['apic_host'] + "/api/node/class/procEntity.json?"
        self.loginPayload = {"aaaUser": {"attributes": {"name": self.apicConfigs['apic_user'], "pwd": self.apicConfigs['apic_password']}}}

    def test_can_read_config_file(self):
        self.assertEqual(self.apicConfigs['apic_user'], 'admin2')

    def test_can_get_login_cookie(self): 
        r = requests.post(self.apicLoginUrl, json=self.loginPayload, proxies=self.proxy, verify=False)
        result = json.loads(r.text)
        r.close()
        self.assertEqual('1', result['totalCount'])

    def test_can_get_metrics_with_cookie(self):
        r = requests.post(self.apicLoginUrl, json=self.loginPayload, proxies=self.proxy, verify=False)
        result = json.loads(r.text)
        apicCookie = result['imdata'][0]['aaaLogin']['attributes']['token']
        r.close()
        cookie = {"APIC-cookie": apicCookie}
        r = requests.get(self.apicMetricsUrl, cookies=cookie, proxies=self.proxy, verify=False)
        result = json.loads(r.text)
        self.assertEqual('2', result['totalCount'])




if __name__ == "__main__":
    unittest.main()