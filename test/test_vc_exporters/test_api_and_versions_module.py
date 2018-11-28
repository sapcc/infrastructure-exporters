import unittest
import os
import sys
import exporter
from vc_exporters import vc_utils, vc_exporter
from vc_exporters.vc_exporter_types import vcapiandversions
from prometheus_client.core import REGISTRY

class TestVcexporters(unittest.TestCase):


    def setUp(self):

        self.testVCVersion = '6.5.0'
        self.testVCBuild = '7515524'
        self.testVCregion = 'local'

        self.testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/vcconfig.yaml"
        self.testExporter = vcapiandversions.Vcapiandversions('vcapiandversions', self.testVCConfigfile)



    def test_run_api_and_versions_module_from_vcexporter(self):
        self.testExporter.collect()
        self.testExporter.export()
        self.assertIn((self.testExporter.vcenterInfo['hostname'], 
                       self.testVCVersion, self.testVCBuild, self.testVCregion),
                       self.testExporter.gauge['vcenter_vcenter_node_info']._metrics)
        vc_utils.disconnect_from_vcenter(self.testExporter.si)

        # Clear out the prometheus REGISTRY
        collectors_to_unregister = [x for x in REGISTRY._names_to_collectors]
        for collector in collectors_to_unregister:
            if 'vcenter' in collector:
                REGISTRY.unregister(REGISTRY._names_to_collectors[collector])



if __name__ == "__main__":
    unittest.main()