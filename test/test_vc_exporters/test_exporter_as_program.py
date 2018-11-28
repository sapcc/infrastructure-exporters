import unittest
import os
import sys
from vc_exporters import vc_exporter, vc_utils
from prometheus_client.core import REGISTRY


class TestExporterProgram(unittest.TestCase):
    
    def setUp(self):

        self.testVCVersion = '6.5.0'
        self.testVCBuild = '7515524'
        self.testVCregion = 'local'

    def test_program_from_cli(self):
        testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../samples/vcconfig.yaml"
        testExporterConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../samples/vcexporters.yaml"
        runningExporter = vc_exporter.VCExporter(testVCConfigfile, testExporterConfigfile)
        runningExporter.create_exporter('apiandversions')
        runningExporter.vcExporter.collect()
        runningExporter.vcExporter.export()
        self.assertIn((runningExporter.vcenterConfig['vcenter_information']['vcenter_hostname'], 
                       self.testVCVersion, self.testVCBuild, self.testVCregion),
                       runningExporter.vcExporter.gauge['vcenter_vcenter_node_info']._metrics)
        vc_utils.disconnect_from_vcenter(runningExporter.si)

        # Clear out the prometheus REGISTRY
        collectors_to_unregister = [x for x in REGISTRY._names_to_collectors]
        for collector in collectors_to_unregister:
            if 'vcenter' in collector:
                REGISTRY.unregister(REGISTRY._names_to_collectors[collector])

    def tearDown(self):
        sys.modules.clear()

if __name__ == "__main__":
    unittest.main()