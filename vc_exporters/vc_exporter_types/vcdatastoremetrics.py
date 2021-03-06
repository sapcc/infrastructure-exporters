import logging
from vc_exporters.vc_exporter import VCExporter
from prometheus_client import Gauge
from pyVmomi import vim


class VcDatastoreMetrics(VCExporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)

        self.gauge = {}

        self.gauge['vcenter_datastore_accessible'] = Gauge('vcenter_datastore_accessible',
                                                           'vcenter_datastore_accessible',
                                                           ['region', 'datacenter', 'name', 'type'])

        self.gauge['vcenter_datastore_maintenance'] = Gauge('vcenter_datastore_maintenance',
                                                           'vcenter_datastore_maintenance',
                                                           ['region', 'datacenter', 'name', 'type'])

        self.gauge['vcenter_datastore_capacity_bytes'] = Gauge('vcenter_datastore_capacity_bytes',
                                                           'vcenter_datastore_capacity_bytes',
                                                           ['region', 'datacenter', 'name', 'type'])

        self.gauge['vcenter_datastore_free_space_bytes'] = Gauge('vcenter_datastore_free_space_bytes',
                                                           'vcenter_datastore_free_space_bytes',
                                                           ['region', 'datacenter', 'name', 'type'])

        self.gauge['vcenter_datastore_accessible_from_host'] = Gauge('vcenter_datastore_accessible_from_host',
                                                           'vcenter_datastore_accessible_from_host',
                                                           ['region', 'datacenter', 'name', 'type', 'host'])


        self.gauge['vcenter_datastore_vm_stored'] = Gauge('vcenter_datastore_vm_stored',
                                                           'vcenter_datastore_vm_stored',
                                                           ['region', 'datacenter', 'name', 'type'])

        self.datastore_properties =[
            "summary.name",
            "summary.type",
            "summary.url",
            "summary.accessible",
            "summary.maintenanceMode",
            "summary.capacity",
            "summary.freeSpace",
            "host",
            "vm"
        ]

        self.content = self.si.RetrieveContent()

        self.datastores = self.si.content.viewManager.CreateContainerView(
            container=self.content.rootFolder,
            type=[vim.Datastore],
            recursive=True
        )

    def collect(self):

        self.data, self.mors = self.collect_properties(self.si, self.datastores, vim.Datastore, self.datastore_properties, True)

    def export(self):

        self.metric_count = 0
        region      = self.vcenterInfo['hostname'].split('.')[2]
        datacenter  = region + (self.vcenterInfo['hostname'].split('.')[0]).split('-')[1]


        for datastore in self.data:
            # discard management datastores

            if 'Management' in datastore['summary.name']:
                continue

            logging.debug('datastore: %s %s, maintenanceMode: %s, accessible: %s' %(datastore['summary.type'],
                                                                                    datastore['summary.name'],
                                                                                    datastore['summary.maintenanceMode'],
                                                                                    datastore['summary.accessible']))

            self.metric_count += 1

            try:

                # accessible state
                if datastore['summary.accessible']:
                    self.gauge['vcenter_datastore_accessible'].labels(region, datacenter, datastore['summary.name'],
                                                                    datastore['summary.type']).set(1)
                else:
                    self.gauge['vcenter_datastore_accessible'].labels(region, datacenter, datastore['summary.name'],
                                                                    datastore['summary.type']).set(0)

                # maintenance mode
                if datastore['summary.maintenanceMode'] == "normal":
                    self.gauge['vcenter_datastore_maintenance'].labels(region, datacenter, datastore['summary.name'],
                                                                       datastore['summary.type']).set(1)
                else:
                    self.gauge['vcenter_datastore_maintenance'].labels(region, datacenter, datastore['summary.name'],
                                                                       datastore['summary.type']).set(0)

                # capacity
                self.gauge['vcenter_datastore_capacity_bytes'].labels(region, datacenter, datastore['summary.name'],
                                                                      datastore['summary.type']).set(str(datastore['summary.capacity']))

                # free space
                self.gauge['vcenter_datastore_free_space_bytes'].labels(region, datacenter, datastore['summary.name'],
                                                                        datastore['summary.type']).set(str(datastore['summary.freeSpace']))


                # number of virtual machines associated to the host
                self.gauge['vcenter_datastore_vm_stored'].labels(region, datacenter, datastore['summary.name'],
                                                                 datastore['summary.type']).set(len(datastore['vm']))

                # access from mounted host
                for host in datastore['host']:
                    logging.debug("Mounted host: %s, inMaintenance: %s, can access ds: %s" %(host.key.name,
                                                                                             host.key.runtime.inMaintenanceMode,
                                                                                             host.mountInfo.accessible))

                    if not host.key.runtime.inMaintenanceMode: # only hosts which are not in maintenance
                        if host.mountInfo.accessible:
                            self.gauge['vcenter_datastore_accessible_from_host'].labels(region, datacenter,
                                                                                        datastore['summary.name'],
                                                                                        datastore['summary.type'],
                                                                                        host.key.name).set(1)
                        else:
                            self.gauge['vcenter_datastore_accessible_from_host'].labels(region, datacenter,
                                                                                        datastore['summary.name'],
                                                                                        datastore['summary.type'],
                                                                                        host.key.name).set(0)

            except Exception as e:
                logging.debug('Could not get data for datastore %s' % str(e))