import logging
import exporter
from vc_exporters.vc_utils import collect_properties
from vc_exporters.vc_exporter import VCExporter
from prometheus_client import Gauge
from pyVmomi import vim, vmodl

class Vcapiandversions(VCExporter):
    
    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.gauge = {}
        self.sessions_dict = {}
        self.host_properties =[
            "summary.config.name", "config.product.version",
            "config.product.build"
        ]
        self.gauge['vcenter_esx_node_info'] = Gauge('vcenter_esx_node_info',
                                                    'vcenter_esx_node_info',
                                                    ['hostname',
                                                     'version', 'build', 'region'])
        self.gauge['vcenter_vcenter_node_info'] = Gauge('vcenter_vcenter_node_info',
                                                        'vcenter_vcenter_node_info',
                                                        ['hostname',
                                                         'version', 'build', 'region'])
        self.gauge['vcenter_vcenter_api_session_info'] = Gauge('vcenter_vcenter_api_session_info',
                                                               'vcenter_vcenter_api_session_info',
                                                               ['session_key', 'hostname', 'userName', 
                                                                'ipAddress', 'userAgent'])

        self.gauge['vcenter_vcenter_api_active_count'] = Gauge('vcenter_vcenter_api_active_count',
                                                                'vcenter_vcenter_api_active_count',
                                                                ['hostname'])

        self.content = self.si.RetrieveContent()
        self.clusters = [cluster for cluster in
                         self.content.viewManager.CreateContainerView(
                             self.content.rootFolder, [vim.ComputeResource],
                             recursive=True).view
                         ]
        self.hosts = self.si.content.viewManager.CreateContainerView(
            container=self.content.rootFolder,
            type=[vim.HostSystem],
            recursive=True
        )
        
    
    def collect(self):
        region = self.vcenterInfo['hostname'].split('.')[2]
        self.metric_count = 0
        logging.debug('get clusters from content')

        logging.debug('removing old vcenter metrics')
        # Need list of keys becuase we can't iterate through dict and change size
        old_metric_list = [x for x in self.gauge['vcenter_vcenter_node_info']._metrics.keys()]
        for x in old_metric_list:
            self.gauge['vcenter_vcenter_node_info']._metrics.pop(x)

        logging.debug(self.vcenterInfo['hostname'] +
                      ": " + self.content.about.version)
        self.gauge['vcenter_vcenter_node_info'].labels(self.vcenterInfo['hostname'],
                                                       self.content.about.version,
                                                       self.content.about.build, region).set(1)
        self.metric_count += 1

        logging.debug('removing old esx metrics')
        # Need list of keys becuase we can't iterate through dict and change size
        old_metric_list = [x for x in self.gauge['vcenter_esx_node_info']._metrics.keys()]
        for x in old_metric_list:
            self.gauge['vcenter_esx_node_info']._metrics.pop(x)

        logging.debug('get version information for each esx host')

        host_data = collect_properties(self.si, self.hosts,
                                    vim.HostSystem, self.host_properties, True)
        for host in host_data:
            try:
                logging.debug(host['summary.config.name'] + ": " +
                                host['config.product.version'])
                self.gauge['vcenter_esx_node_info'].labels(host['summary.config.name'],
                                                            host['config.product.version'],
                                                            host['config.product.build'], region).set(1)
                self.metric_count += 1

            except Exception as e:
                logging.debug(
                    "Couldn't get information for a host: " + str(e))

        # Get current session information and check with saved sessions info
        logging.debug('getting api session information')

        try:
            self.current_sessions = [x for x in self.content.sessionManager.sessionList]
        except Exception as e:
            logging.debug('Error getting api session info' + str(e))

        for session in self.current_sessions:
            if self.sessions_dict.get(session.key):
                self.sessions_dict[session.key]['callsPerInterval'] = \
                    session.callCount - self.sessions_dict[session.key]['callsLastInterval']
                self.sessions_dict[session.key]['callsLastInterval'] = session.callCount
            else:
                dict_entry = {'userName': session.userName,
                                'ipAddress': session.ipAddress,
                                'userAgent': session.userAgent,
                                'callsPerInterval': 0,
                                'callsLastInterval': session.callCount}
                self.sessions_dict[session.key] = dict_entry
        

        # Cleanup ended sessions
        session_keys_current = [x.key for x in self.current_sessions]
        session_keys_in_dict = self.sessions_dict.keys()

        # Need to gather keys becuase we can't iterate through dict and remove items at the same time
        remove_keys=[]
        for key in session_keys_in_dict:
                if not key in session_keys_current:
                    remove_keys.append(key)
        for key in remove_keys:
            try:
                remove_data = self.sessions_dict.pop(key)
                self.gauge['vcenter_vcenter_api_session_info'].remove(key[0:8], 
                    self.vcenterInfo['hostname'],
                    remove_data['userName'], 
                    remove_data['ipAddress'],
                    remove_data['userAgent']
                )
            except Exception as e:
                logging.debug('Error removing gauge: ' + str(e))

    def export(self):
        for session in self.sessions_dict:
            self.gauge['vcenter_vcenter_api_session_info'].labels(session[0:8],
                        self.vcenterInfo['hostname'], 
                        self.sessions_dict[session]['userName'], 
                        self.sessions_dict[session]['ipAddress'],
                        self.sessions_dict[session]['userAgent']).set(self.sessions_dict[session]['callsPerInterval'])

        self.gauge['vcenter_vcenter_api_active_count'].labels(self.vcenterInfo['hostname']).set(
            len(self.current_sessions)
        )  