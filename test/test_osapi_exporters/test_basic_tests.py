import unittest
import requests
import json
import os
import exporter

class TestExporter(unittest.TestCase):


    def setUp(self):
        # Get credentials from file or use defaults
        self.osapiConfigFile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/osapiconfig.yaml"
        self.osapiConfigs = exporter.Exporter.get_config(self.osapiConfigFile)['device_information']
        self.osapi_auth_url = self.osapiConfigs['auth_url']


    def test_can_read_config_file(self):
        self.assertEqual(self.osapiConfigs['username'], 'admin')

if __name__ == "__main__":
    unittest.main()
