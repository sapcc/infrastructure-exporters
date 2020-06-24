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
                                                           ['region', 'name', 'type'])

        self.gauge['vcenter_datastore_maintenance'] = Gauge('vcenter_datastore_maintenance',
                                                           'vcenter_datastore_maintenance',
                                                           ['region', 'name', 'type'])

        self.gauge['vcenter_datastore_capacity_bytes'] = Gauge('vcenter_datastore_capacity_bytes',
                                                           'vcenter_datastore_capacity_bytes',
                                                           ['region', 'name', 'type'])

        self.gauge['vcenter_datastore_free_space_bytes'] = Gauge('vcenter_datastore_free_space_bytes',
                                                           'vcenter_datastore_free_space_bytes',
                                                           ['region', 'name', 'type'])

        self.gauge['vcenter_datastore_vm_stored'] = Gauge('vcenter_datastore_vm_stored',
                                                           'vcenter_datastore_vm_stored',
                                                           ['region', 'name', 'type'])


        self.datastore_properties =[
            "summary.name",
            "summary.type",
            "summary.url",
            "summary.accessible",
            "summary.maintenanceMode",
            "summary.capacity",
            "summary.freeSpace",
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
        region = self.vcenterInfo['hostname'].split('.')[2]

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
                    self.gauge['vcenter_datastore_accessible'].labels(region, datastore['summary.name'],
                                                                    datastore['summary.type']).set(0)
                else:
                    self.gauge['vcenter_datastore_accessible'].labels(region, datastore['summary.name'],
                                                                    datastore['summary.type']).set(1)

                # maintenance mode
                if datastore['summary.maintenanceMode'] == "normal":
                    self.gauge['vcenter_datastore_maintenance'].labels(region, datastore['summary.name'],
                                                                       datastore['summary.type']).set(0)
                else:
                    self.gauge['vcenter_datastore_maintenance'].labels(region, datastore['summary.name'],
                                                                       datastore['summary.type']).set(1)

                # capacity
                self.gauge['vcenter_datastore_capacity_bytes'].labels(region, datastore['summary.name'],
                                                                      datastore['summary.type']).set(str(datastore['summary.capacity']))

                # free space
                self.gauge['vcenter_datastore_free_space_bytes'].labels(region, datastore['summary.name'],
                                                                        datastore['summary.type']).set(str(datastore['summary.freeSpace']))


                # number of virtual machines associated to the host
                self.gauge['vcenter_datastore_vm_stored'].labels(region, datastore['summary.name'],
                                                                 datastore['summary.type']).set(len(datastore['vm']))


            except Exception as e:
                logging.debug('Could not get data for datastore %s' % str(e))