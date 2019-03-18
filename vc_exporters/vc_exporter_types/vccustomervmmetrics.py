import logging
import exporter
import re
from vc_exporters.vc_exporter import VCExporter
from prometheus_client import Gauge
from datetime import datetime, timedelta
from pyVmomi import vim, vmodl


class Vccustomervmmetrics(VCExporter):
    
    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.gauge = {}
        self.sessions_dict = {}
        self.counter_info = {}
        self.regexs = {}
        self.counter_ids_to_collect = []
        self.metric_count = 0
        # Removed "runtime.host" because it's a long expensive call
        self.vm_properties = [
            "runtime.powerState", "config.annotation", "config.name",
            "config.instanceUuid", "config.guestId", "summary.config.vmPathName"
        ]

        # compile a regex for trying to filter out openstack generated vms
        # they all have the "name:" field set
        self.regexs['openstack_match_regex'] = re.compile("^name")

        # Compile other regexs
        for regular_expression in ['shorter_names_regex', 'host_match_regex', 'ignore_vm_match_regex']:
            if self.exporterInfo.get(regular_expression):
                self.regexs[regular_expression] = re.compile(
                    self.exporterInfo[regular_expression]
                )
            else:
                self.regexs[regular_expression] = re.compile('')

        content = self.si.RetrieveContent()
        self.container = content.rootFolder
        datacenter = self.container.childEntity[0]
        self.datacentername = datacenter.name

        perf_manager = content.perfManager
        vm_counter_ids = perf_manager.QueryPerfCounterByLevel(level=4)

        # Store all counter information in self.counter_info and create gauges
        logging.debug('list of all available metrics and their counterids')
        for vm_counter_id in vm_counter_ids:

            full_name = '.'.join([vm_counter_id.groupInfo.key, vm_counter_id.nameInfo.key,
                                  vm_counter_id.rollupType])
            logging.debug(full_name + ": %s", str(vm_counter_id.key))
            self.counter_info[full_name] = vm_counter_id.key
        
                # get all the data regarding vcenter hosts
        self.host_view = content.viewManager.CreateContainerView(
            self.container, [vim.HostSystem], True)

        # get vm containerview
        self.view_ref = self.si.content.viewManager.CreateContainerView(
            container=self.container,
            type=[vim.VirtualMachine],
            recursive=True
        )
        selected_metrics = self.exporterInfo['vm_metrics']

        # Populate counter_ids_to_collect from config if specified
        if selected_metrics:
            self.counter_ids_to_collect = [self.counter_info[i] for i in selected_metrics
                                           if i in self.counter_info]
        else:
            self.counter_ids_to_collect = [i.key for i in self.counter_info]
        for counter_id in selected_metrics:
            # vc_gauge = 'vcenter_' + full_name.replace('.', '_')
            vc_gauge = 'vcenter_' + counter_id.replace('.', '_')
            self.gauge[vc_gauge] = Gauge(vc_gauge, vc_gauge, [
                'vmware_name', 'project_id', 'vcenter_name', 'vcenter_node',
                'instance_uuid', 'guest_id', 'datastore', 'metric_detail'
            ])

        self.counter_info_keys_list = list(self.counter_info.keys())
        self.counter_info_keys_underscore = [x.replace('.', '_') for x in self.counter_info_keys_list]
        self.counter_info_values_list = list(self.counter_info.values())

    def collect(self):
         # get data
        self.data, self.mors = self.collect_properties(self.si, self.view_ref, vim.VirtualMachine,
                                  self.vm_properties, True)
        self.metric_count = 0
 
    def export(self):
        # define the time range in seconds the metric data from the vcenter
        #  should be averaged across all based on vcenter time
        vch_time = self.si.CurrentTime()
        start_time = vch_time - \
            timedelta(seconds=(int(self.exporterInfo['collection_interval']) + 60))
        end_time = vch_time - timedelta(seconds=60)
        perf_manager = self.si.content.perfManager

        for item in self.data:

            try:
                if (item["runtime.powerState"] == "poweredOn" and
                        self.regexs['openstack_match_regex'].match(item["config.annotation"]) #and
                        #'production' in item["runtime.host"].parent.name
                        ) and not self.regexs['ignore_vm_match_regex'].match(item["config.name"]):
                    logging.debug('current vm processed - ' +
                                    item["config.name"])
                    #logging.debug('==> running on vcenter node: ' +
                    #                item["runtime.host"].name)

                    # split the multi-line annotation into a dict
                    # per property (name, project-id, ...)
                    annotation_lines = item["config.annotation"].split('\n')

                    # rename flavor: to flavor_, so that it does not break the split on : below
                    annotation_lines = [
                        w.replace('flavor:', 'flavor_')
                        for w in annotation_lines
                    ]

                    # the filter is for filtering out empty lines
                    annotations = dict(
                        s.split(':', 1)
                        for s in filter(None, annotation_lines))

                    # datastore name
                    datastore = item["summary.config.vmPathName"].split('[', 1)[1].split(']')[
                        0]

                    # get a list of metricids for this vm in preparation for the stats query
                    metric_ids = [
                        vim.PerformanceManager.MetricId(
                            counterId=i, instance="*") for i in self.counter_ids_to_collect
                    ]
                    vm_instance = self.mors[item["obj"]]
                    # query spec for the metric stats query, the intervalId is the default one
                    logging.debug(
                        '==> vim.PerformanceManager.QuerySpec start: %s' %
                        datetime.now())
                    spec = vim.PerformanceManager.QuerySpec(
                        maxSample=1,
                        entity=vm_instance,
                        metricId=metric_ids,
                        intervalId=20,
                        startTime=start_time,
                        endTime=end_time)
                    logging.debug(
                        '==> vim.PerformanceManager.QuerySpec end: %s' %
                        datetime.now())

                    # get metric stats from vcenter
                    logging.debug('==> perfManager.QueryStats start: %s' %
                                    datetime.now())
                    result = perf_manager.QueryStats(querySpec=[spec])
                    logging.debug(
                        '==> perfManager.QueryStats end: %s' % datetime.now())
                    self.metric_count += 1
                    logging.debug("Collected metrics for %d vms" % self.metric_count)

                    # loop over the metrics
                    logging.debug('==> gauge loop start: %s' % datetime.now())
                    # Create counter list for gauges
                    
                    for val in result[0].value:

                        # send gauges to prometheus exporter: metricname and value with
                        # labels: vm name, project id, vcenter name, vcneter
                        # node, instance uuid and metric detail (for instance a partition
                        # for io or an interface for net metrics) - we update the gauge
                        # only if the value is not -1 which means the vcenter has no value
                        if val.value[0] != -1:
                            if val.id.instance == '':
                                metric_detail = 'total'
                            else:
                                metric_detail = val.id.instance
                            
                            gauge_finder = self.counter_info_values_list.index(val.id.counterId)
                            gauge_title = self.counter_info_keys_underscore[gauge_finder]
                            gauge_title = 'vcenter_' + gauge_title
                            gauge_title = re.sub('\.', '_', gauge_title )
                            self.update_gauge(gauge_title, annotations, item, datastore, metric_detail, val.value[0])
                             
                    logging.debug('==> gauge loop end: %s' % datetime.now())
                    logging.debug("collected data for " + item['config.name'])
                else:
                    logging.debug("didn't collect info for " + item['config.name'] +
                                " didn't meet requirements")
            # some vms do not have config.name define - we are not interested in them and can ignore them
            except KeyError as e:
                logging.debug("property not defined for vm: " + str(e))
            except Exception as e:
                logging.info("couldn't get perf data: " + str(e))

    def update_gauge(self, gauge_title, annotations, item, datastore, metric_detail, metric_val):
        self.gauge[gauge_title].labels(
                annotations['name'],
                annotations['projectid'], self.datacentername,
                'ESX node no longer provided',
                item["config.instanceUuid"],
                item["config.guestId"],
                datastore,
                metric_detail).set(metric_val)