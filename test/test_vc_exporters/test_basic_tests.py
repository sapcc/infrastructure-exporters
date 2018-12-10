import unittest
import os
import ssl
import exporter
from pyVim.connect import SmartConnect, Disconnect
from vc_exporters import vc_exporter
from vc_exporters.vc_exporter_types import vcapiandversions

class TestExporter(unittest.TestCase):


    def setUp(self):
        self.testVCConfigfile = os.path.dirname(os.path.realpath(__file__)) + "/../../samples/vcconfig.yaml"
        self.vcenterConfig = exporter.Exporter.get_config(self.testVCConfigfile)

    def connect_to_vcenter(self):
        testVCConfig = self.vcenterConfig['device_information']
        # check for insecure ssl option
        context = None
        if testVCConfig['ignore_ssl'] and \
                hasattr(ssl, "_create_unverified_context"):
            context = ssl._create_unverified_context()

        # connect to vcenter
        try:
            si = SmartConnect(
                host=testVCConfig['hostname'],
                user=testVCConfig['username'],
                pwd=testVCConfig['password'],
                port=testVCConfig['port'],
                sslContext=context)
        except IOError as e:
            raise SystemExit("Unable to connect to host with supplied info. Error %s: " % str(e))
        return si

    def test_vcexporter_can_get_config(self):  
        self.assertEqual("vc.test.local", self.vcenterConfig['device_information']['hostname'])

    def test_can_log_into_vcenter(self):
        testSi = self.connect_to_vcenter()
        self.assertIn('sessionManager', dir(testSi.RetrieveServiceContent()))
        Disconnect(testSi)
        
if __name__ == "__main__":
    unittest.main()