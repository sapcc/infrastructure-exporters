import unittest
import os
from vc_exporters.vc_exporter_types import vccustomerdsmetrics
from prometheus_client.core import REGISTRY

class TestVcexporters(unittest.TestCase):


    def setUp(self):
        self.testVCVersion = '6.5.0'
        self.testVCBuild = '7515524'
        self.testVCregion = 'local'

        self.testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/vcconfig.yaml"
        self.testExporter = vccustomerdsmetrics.Vccustomerdsmetrics('vccustomerdsmetrics', self.testVCConfigfile)

    def test_run_customervm_module_from_vcexporter(self):
         self.testExporter.collect()
         self.testExporter.export()
         # Can't run test with no hosts or datastores, so if program doesn't crash, we are good
         self.assertEqual(1, 1)
         self.testExporter.disconnect_from_vcenter(self.testExporter.si)

         # Clear out the prometheus REGISTRY
         collectors_to_unregister = [x for x in REGISTRY._names_to_collectors]
         for collector in collectors_to_unregister:
             if 'vcenter' in collector:
                 REGISTRY.unregister(REGISTRY._names_to_collectors[collector])

if __name__ == "__main__":
    unittest.main()