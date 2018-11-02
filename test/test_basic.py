import unittest
import os
from vcexporter import vcexporter
from vcexporter import vcexporterconfig

class TestExporter(unittest.TestCase):

    def setUp(self):
        testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../samples/vcconfig.yaml"
        self.vcenterConfig = vcexporterconfig.VcenterExporterConfiguration(testVCConfigfile)
        testExporterConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../samples/vcexporters.yaml"
        self.testExporter = vcexporter.VCExporter(testVCConfigfile, testExporterConfigfile)

    def test_vcexporterconfig_can_get_config(self):
        self.assertEqual("vc.test.local", self.vcenterConfig.config['vcenter_information']['vcenter_hostname'])

    def test_vcexporter_can_get_config(self):  
        self.assertEqual("vc.test.local", self.vcenterConfig.config['vcenter_information']['vcenter_hostname'])
        self.assertEqual(True, self.testExporter.vcenterExporterConfig.config['vcenter_exporters']['versions_and_apis']['enabled'])

    def test_can_log_into_vcenter(self):
        pass

    def test_can_do_an_export(self):
        pass

    def test_load_exporter(self):
        pass

    def tearDown(self):
        pass


if __name__ == "__main__":
    unittest.main()