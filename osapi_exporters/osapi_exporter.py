import exporter
import openstack
from prometheus_client import start_http_server
import socket
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class OSAPIExporter(exporter.Exporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.exporterInfo = self.exporterConfig['exporter_types'][self.exporterType]
        self.duration = int(self.exporterInfo['collection_interval'])
        self.enabled  = bool(self.exporterInfo['enabled'])

        self.osInfo = self.exporterConfig['device_information']
        self.region = self.osInfo['region']
        # Create the connection to the OpenStack service
        self.osapi = self._connect(
            self.osInfo['auth_url'],
            self.osInfo['username'],
            self.osInfo['password'],
            self.osInfo['user_domain_name'],
            self.osInfo['project_domain_name'],
            self.osInfo['project_name']
        )

        # Now start the prometheus expected web server
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', int(self.exporterConfig['prometheus_port']))) != 0:
                start_http_server(int(self.exporterConfig['prometheus_port']))


    def _connect(self, auth_url, username, password,
                 user_domain_name, project_domain_name, project_name):
        """Connect to the OpenStack Service."""

        auth = dict(
            auth_url=auth_url,
            username=username,
            password=password,
            user_domain_name=user_domain_name,
            project_domain_name=project_domain_name,
            project_name=project_name,
        )

        return openstack.connection.Connection(
            region_name=self.region,
            auth=auth,
            debug=True
        )
