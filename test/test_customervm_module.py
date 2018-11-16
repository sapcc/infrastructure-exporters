import unittest
import os
import urllib
import sys
from importlib import import_module
from vc_exporters import vc_utils, vc_exporter
from vc_exporters.vc_exporter_types import customer_vm_metrics
from prometheus_client import start_http_server

class TestVcexporters(unittest.TestCase):


    def setUp(self):

        self.testVCVersion = '6.5.0'
        self.testVCBuild = '7515524'
        self.testVCregion = 'local'

        self.testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../samples/vcconfig.yaml"
        self.vcenterConfig = vc_utils.get_config(self.testVCConfigfile)
        self.testExporterConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../samples/vcexporters.yaml"
        self.testExporter = vc_exporter.VCExporter(self.testVCConfigfile, self.testExporterConfigfile)


    # def test_run_customervm_module_from_vcexporter(self):
    #     self.testExporter.create_exporter('customervmmetrics')
    #     self.testExporter.vcExporter.collect()
    #     self.testExporter.vcExporter.export()
    #     self.assertIn((self.vcenterConfig['vcenter_information']['vcenter_hostname'], 
    #                    self.testVCVersion, self.testVCBuild, self.testVCregion),
    #                    self.testExporter.vcExporter.gauge['vcenter_vcenter_node_info']._metrics)
    #     vc_utils.disconnect_from_vcenter(self.testExporter.si)

    # def tearDown(self):
    #     sys.modules.clear()
    def test_something(self):
        pass


if __name__ == "__main__":
    unittest.main()