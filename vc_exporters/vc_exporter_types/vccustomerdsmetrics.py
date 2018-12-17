import logging
import exporter
import re
from vc_exporters.vc_exporter import VCExporter
from prometheus_client import Gauge
from datetime import datetime, timedelta
from pyVmomi import vim, vmodl

class Vccustomerdsmetrics(VCExporter):
    
    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.gauge = {}
        self.regexs = {}
        self.datastore_properties = [
            "summary.accessible", "summary.capacity", "summary.freeSpace",
            "summary.maintenanceMode", "summary.name",
            "summary.type", "summary.url", "overallStatus"
        ]
        self.gauge['vcenter_datastore_accessible'] = Gauge('vcenter_datastore_accessible',
                                                           'vcenter_datastore_accessible',
                                                           ['datastore_name',
                                                            'datastore_type',
                                                            'datastore_url'])
        self.gauge['vcenter_datastore_capacity'] = Gauge('vcenter_datastore_capacity',
                                                         'vcenter_datastore_capacity',
                                                         ['datastore_name',
                                                          'datastore_type',
                                                          'datastore_url'])
        self.gauge['vcenter_datastore_freespace'] = Gauge('vcenter_datastore_freespace',
                                                          'vcenter_datastore_freespace',
                                                          ['datastore_name',
                                                           'datastore_type',
                                                           'datastore_url'])
        self.gauge['vcenter_datastore_maintenancemode'] = Gauge('vcenter_datastore_maintenancemode',
                                                                'vcenter_datastore_maintenancemode',
                                                                ['datastore_name',
                                                                 'datastore_type',
                                                                 'datastore_url'])
        self.gauge['vcenter_datastore_overallstatus'] = Gauge('vcenter_datastore_overallstatus',
                                                              'vcenter_datastore_overallstatus',
                                                              ['datastore_name',
                                                               'datastore_type',
                                                               'datastore_url'])
        self.content = self.si.RetrieveContent()
        self.view_ref = self.si.content.viewManager.CreateContainerView(
            container=self.content.rootFolder,
            type=[vim.Datastore],
            recursive=True
        )
        # compile a regex for trying to filter out openstack generated vms
        # they all have the "name:" field set
        self.regexs['openstack_match_regex'] = re.compile("^name")

        # Compile other regexs
        for regular_expression in ['shorter_names_regex', 'host_match_regex', 'ignore_ds_match_regex']:
            if self.exporterInfo.get(regular_expression):
                self.regexs[regular_expression] = re.compile(
                    self.exporterInfo[regular_expression]
                )
            else:
                self.regexs[regular_expression] = re.compile('')

    def collect(self):
        self.data = self.collect_properties(self.si, self.view_ref, vim.Datastore,
                                  self.datastore_properties, True)
        self.metric_count = 0
    def export(self):
        for item in self.data:
            if not self.regexs['ignore_ds_match_regex'].match(item["summary.name"]):
                try:
                    logging.debug('current datastore processed - ' +
                                item["summary.name"])

                    logging.debug('==> accessible: ' +
                                str(item["summary.accessible"]))
                    # convert strings to numbers, so that we can generate a prometheus metric from them
                    if item["summary.accessible"]:
                        number_accessible = 1
                    else:
                        number_accessible = 0
                    logging.debug('==> capacity: ' +
                                str(item["summary.capacity"]))
                    logging.debug('==> freeSpace: ' +
                                str(item["summary.freeSpace"]))
                    logging.debug('==> maintenanceMode: ' +
                                str(item["summary.maintenanceMode"]))
                    # convert strings to numbers, so that we can generate a prometheus metric from them
                    if item["summary.maintenanceMode"] == "normal":
                        number_maintenance_mode = 0
                    else:
                        # fallback to note if we do not yet catch a value
                        number_maintenance_mode = -1
                        logging.info(
                            'unexpected maintenanceMode for datastore ' + item["summary.name"])
                    logging.debug('==> type: ' +
                                str(item["summary.type"]))
                    logging.debug('==> url: ' +
                                str(item["summary.url"]))
                    logging.debug('==> overallStatus: ' +
                                str(item["overallStatus"]))
                    # convert strings to numbers, so that we can generate a prometheus metric from them
                    if item["overallStatus"] == "green":
                        number_overall_status = 0
                    elif item["overallStatus"] == "yellow":
                        number_overall_status = 1
                    elif item["overallStatus"] == "red":
                        number_overall_status = 2
                    else:
                        # fallback to note if we do not yet catch a value
                        number_overall_status = -1
                        logging.info(
                            'unexpected overallStatus for datastore ' + item["summary.name"])

                    # set the gauges for the datastore properties
                    logging.debug('==> gauge start: %s' % datetime.now())
                    self.gauge['vcenter_datastore_accessible'].labels(item["summary.name"],
                                                                    item["summary.type"],
                                                                    item["summary.url"]
                                                                    ).set(number_accessible)
                    self.gauge['vcenter_datastore_capacity'].labels(item["summary.name"],
                                                                    item["summary.type"],
                                                                    item["summary.url"]
                                                                    ).set(item["summary.capacity"])
                    self.gauge['vcenter_datastore_freespace'].labels(item["summary.name"],
                                                                    item["summary.type"],
                                                                    item["summary.url"]
                                                                    ).set(item["summary.freeSpace"])
                    self.gauge['vcenter_datastore_maintenancemode'].labels(item["summary.name"],
                                                                        item["summary.type"],
                                                                        item["summary.url"]
                                                                        ).set(number_maintenance_mode)
                    self.gauge['vcenter_datastore_overallstatus'].labels(item["summary.name"],
                                                                        item["summary.type"],
                                                                        item["summary.url"]
                                                                        ).set(number_overall_status)
                    logging.debug('==> gauge end: %s' % datetime.now())

                    self.metric_count += 1

                except Exception as e:
                    logging.info("Couldn't get perf data: " + str(e))