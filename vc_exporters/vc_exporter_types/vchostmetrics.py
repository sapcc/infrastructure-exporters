import logging
import exporter
import re
from vc_exporters.vc_exporter import VCExporter
from prometheus_client import Gauge
from datetime import datetime, timedelta
from pyVmomi import vim, vmodl


class VcHostMetrics(VCExporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)

        self.gauge = {}
        self.sessions_dict = {}
        self.host_properties =[
            "name",
            "runtime.inMaintenanceMode",
            "runtime.inQuarantineMode",
            "runtime.connectionState",
            "vm"
        ]

        self.gauge['vcenter_esx_node_connection_state'] = Gauge('vcenter_esx_node_connection_state',
                                                              'vcenter_esx_node_connection_state',
                                                              ['hostname', 'region'])

        self.gauge['vcenter_esx_node_in_maintenance'] = Gauge('vcenter_esx_node_in_maintenance',
                                                              'vcenter_esx_node_in_maintenance',
                                                              ['hostname', 'region'])

        self.gauge['vcenter_esx_node_in_quarantine'] = Gauge('vcenter_esx_node_in_quarantine',
                                                              'vcenter_esx_node_in_quarantine',
                                                              ['hostname', 'region'])

        self.gauge['vcenter_esx_node_vm_associated'] = Gauge('vcenter_esx_node_vm_associated',
                                                              'vcenter_esx_node_vm_associated',
                                                              ['hostname', 'region'])

        self.content = self.si.RetrieveContent()

        self.hosts = self.si.content.viewManager.CreateContainerView(
            container=self.content.rootFolder,
            type=[vim.HostSystem],
            recursive=True
        )

    def collect(self):

        self.data, self.mors = self.collect_properties(self.si, self.hosts, vim.HostSystem, self.host_properties, True)

    def export(self):

        region = self.vcenterInfo['hostname'].split('.')[2]

        for host in self.data:
            logging.debug('host: %s, inMaintenanceMode: %s, inQuarantineMode: %s, connectionState: %s' %(host['name'], host['runtime.inMaintenanceMode'], host['runtime.inQuarantineMode'], host['runtime.connectionState']))

            try:

                # connection state
                if host['runtime.connectionState'] == 'connected':
                    self.gauge['vcenter_esx_node_connection_state'].labels(host['name'], region).set(0)
                elif host['runtime.connectionState'] == 'disconnected':
                    self.gauge['vcenter_esx_node_connection_state'].labels(host['name'], region).set(1)
                elif host['runtime.connectionState'] == 'notResponding':
                    self.gauge['vcenter_esx_node_connection_state'].labels(host['name'], region).set(2)

                # maintenance mode
                if host['runtime.inMaintenanceMode'] == False:
                    self.gauge['vcenter_esx_node_in_maintenance'].labels(host['name'], region).set(0)
                else:
                    self.gauge['vcenter_esx_node_in_maintenance'].labels(host['name'], region).set(1)

                # quarantine mode
                if host['runtime.inQuarantineMode'] == False:
                    self.gauge['vcenter_esx_node_in_quarantine'].labels(host['name'], region).set(0)
                else:
                    self.gauge['vcenter_esx_node_in_quarantine'].labels(host['name'], region).set(1)

                # number of virtual machines associated to the host
                self.gauge['vcenter_esx_node_vm_associated'].labels(host['name'], region).set(len(host['vm']))


            except Exception as e:
                logging.debug('Could not get data for host %s' % str(e))