import unittest
import os
import exporter
import gc
from apic_exporters.apic_exporter_types import apichealth
from prometheus_client.core import REGISTRY


class TestApicHealthExporter(unittest.TestCase):

    def setUp(self):
        # Get credentials from file or use defaults
        apicConfigFile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/apicconfig.yaml"

    def test_can_get_cookie_with_apic_health_exporter(self):
        testExporter = apichealth.Apichealth('apichealth', self.apicConfigfile)
        self.assertGreater(len(testExporter.loginCookie), 40)
        
        # Clear out the prometheus REGISTRY
        collectors_to_unregister = [x for x in REGISTRY._names_to_collectors]
        for collector in collectors_to_unregister:
            if 'apic' in collector:
                REGISTRY.unregister(REGISTRY._names_to_collectors[collector])

    def test_can_get_metrics_with_apic_health_exporter(self):
        testExporter = apichealth.Apichealth('apichealth', self.apicConfigfile)
        testExporter.collect()
        self.assertIn('cpuPct', testExporter.apicMetrics)
        
        # Clear out the prometheus REGISTRY
        collectors_to_unregister = [x for x in REGISTRY._names_to_collectors]
        for collector in collectors_to_unregister:
            if 'apic' in collector:
                REGISTRY.unregister(REGISTRY._names_to_collectors[collector])

if __name__ == "__main__":
    unittest.main()