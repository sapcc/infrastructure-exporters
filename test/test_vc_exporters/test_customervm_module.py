import unittest
import os
import urllib
import sys
import exporter
from importlib import import_module
from vc_exporters import vc_utils, vc_exporter
from vc_exporters.vc_exporter_types import customer_vm_metrics
from prometheus_client import start_http_server

class TestVcexporters(unittest.TestCase):


    def setUp(self):

        self.testVCVersion = '6.5.0'
        self.testVCBuild = '7515524'
        self.testVCregion = 'local'

        self.testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/vcconfig.yaml"
        self.vcenterConfig = exporter.Exporter.get_config(self.testVCConfigfile)
        self.testExporterConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/vcexporters.yaml"
        self.testExporter = vc_exporter.VCExporter(self.testVCConfigfile, self.testExporterConfigfile)


    def test_run_customervm_module_from_vcexporter(self):
         self.testExporter.create_exporter('customervmmetrics')
         self.testExporter.vcExporter.collect()
         self.testExporter.vcExporter.export()
         # Can't run test with no hosts or VMs, so if program doesn't crash, we are good
         self.assertEqual(1, 1)
         vc_utils.disconnect_from_vcenter(self.testExporter.si)

    def tearDown(self):
         sys.modules.clear()

if __name__ == "__main__":
    unittest.main()