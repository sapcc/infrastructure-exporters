import unittest
import os
import urllib
import sys
from importlib import import_module
from vc_exporters import vc_utils, vc_exporter
from vc_exporters.vc_exporter_types import api_and_versions
from prometheus_client import start_http_server

class TestExporter(unittest.TestCase):


    def setUp(self):
        self.testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/vcconfig.yaml"
        self.vcenterConfig = vc_utils.get_config(self.testVCConfigfile)
        self.testExporterConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/vcexporters.yaml"


    def connect_to_vcenter(self):
        testVCConfig = self.vcenterConfig['vcenter_information']
        testSi = vc_utils.connect_to_vcenter(testVCConfig['vcenter_hostname'],
                                            testVCConfig['vcenter_username'],
                                            testVCConfig['vcenter_password'],
                                            testVCConfig['vcenter_port'],
                                            testVCConfig['vcenter_ignore_ssl'],)
        return testSi

    def test_vcexporterconfig_can_get_config(self):
        self.assertEqual("vc.test.local", self.vcenterConfig['vcenter_information']['vcenter_hostname'])

    def test_vcexporter_can_get_config(self):  
        self.assertEqual("vc.test.local", self.vcenterConfig['vcenter_information']['vcenter_hostname'])

    def test_can_log_into_vcenter(self):
        testSi = self.connect_to_vcenter()
        self.assertIn('sessionManager', dir(testSi.RetrieveServiceContent()))
        vc_utils.disconnect_from_vcenter(testSi)
        
    def tearDown(self):
        sys.modules.clear()


if __name__ == "__main__":
    unittest.main()