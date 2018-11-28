import unittest
import os
import exporter
from vc_exporters import vc_utils, vc_exporter
from vc_exporters.vc_exporter_types import vcapiandversions

class TestExporter(unittest.TestCase):


    def setUp(self):
        self.testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/vcconfig.yaml"
        self.vcenterConfig = exporter.Exporter.get_config(self.testVCConfigfile)
        self.testExporterConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/vcexporters.yaml"


    def connect_to_vcenter(self):
        testVCConfig = self.vcenterConfig['device_information']
        testSi = vc_utils.connect_to_vcenter(testVCConfig['hostname'],
                                            testVCConfig['username'],
                                            testVCConfig['password'],
                                            testVCConfig['port'],
                                            testVCConfig['ignore_ssl'],)
        return testSi

    def test_vcexporter_can_get_config(self):  
        self.assertEqual("vc.test.local", self.vcenterConfig['device_information']['hostname'])

    def test_can_log_into_vcenter(self):
        testSi = self.connect_to_vcenter()
        self.assertIn('sessionManager', dir(testSi.RetrieveServiceContent()))
        vc_utils.disconnect_from_vcenter(testSi)
        


if __name__ == "__main__":
    unittest.main()