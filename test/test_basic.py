import unittest
import os
import urllib
from vcexporter import vcexporterconfig, vcutils, vcexporter
from vcexporter.exporters import apiandversions
from prometheus_client import start_http_server

class TestExporter(unittest.TestCase):


    def setUp(self):
        self.testVCVersion = '6.5.0'
        self.testVCBuild = '7515524'
        self.testVCregion = 'local'

        testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../samples/vcconfig.yaml"
        self.vcenterConfig = vcexporterconfig.VcenterExporterConfiguration(testVCConfigfile)
        testExporterConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../samples/vcexporters.yaml"
        self.testExporter = vcexporter.VCExporter(testVCConfigfile, testExporterConfigfile)

    def connect_to_vcenter(self):
        testVCConfig = self.vcenterConfig.config['vcenter_information']
        testSi = vcutils.connect_to_vcenter(testVCConfig['vcenter_hostname'],
                                            testVCConfig['vcenter_username'],
                                            testVCConfig['vcenter_password'],
                                            testVCConfig['vcenter_port'],
                                            testVCConfig['vcenter_ignore_ssl'],)
        return testSi

    def test_vcexporterconfig_can_get_config(self):
        self.assertEqual("vc.test.local", self.vcenterConfig.config['vcenter_information']['vcenter_hostname'])

    def test_vcexporter_can_get_config(self):  
        self.assertEqual("vc.test.local", self.vcenterConfig.config['vcenter_information']['vcenter_hostname'])
        self.assertEqual(True, self.testExporter.vcenterExporterConfig.config['vcenter_exporters']['versions_and_apis']['enabled'])

    def test_can_log_into_vcenter(self):
        testSi = self.connect_to_vcenter()
        self.assertIn('sessionManager', dir(testSi.RetrieveServiceContent()))

    def test_can_do_an_apiandversions_export(self):
        testSi = self.connect_to_vcenter()
        testExporter = apiandversions.apiandversions(testSi, self.vcenterConfig.config['vcenter_information'])
        testExporter.collect()
        testExporter.export()
        self.assertIn((self.vcenterConfig.config['vcenter_information']['vcenter_hostname'], 
                       self.testVCVersion, self.testVCBuild, self.testVCregion),
                       testExporter.gauge['vcenter_vcenter_node_info']._metrics)
        

    def test_load_exporter(self):
        pass

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()