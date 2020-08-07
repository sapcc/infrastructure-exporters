import logging
from vc_exporters.vc_exporter import VCExporter
from prometheus_client import Gauge
from pyVmomi import vim
import math
from datetime import datetime, timedelta
import re
import socket
import errno
from threading import Thread
from threading import Semaphore

class Vcapiandversions(VCExporter):
    MEM_THRESHOLD = 1024   # in MB, used for offset of flavours and hv physical memory

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)
        self.gauge = {}
        self.sessions_dict = {}
        self.host_properties =[
            "summary.config.name", "config.product.version",
            "config.product.build", "summary.quickStats.overallMemoryUsage",
            "hardware.memorySize","vm"
        ]
        self.gauge['vcenter_esx_node_info'] = Gauge('vcenter_esx_node_info',
                                                    'vcenter_esx_node_info',
                                                    ['hostname',
                                                     'version', 'build', 'region'])
        self.gauge['vcenter_esx_node_maintenance'] = Gauge('vcenter_esx_node_maintenance',
                                                    'vcenter_esx_node_maintenance',
                                                    ['hostname'])
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

        self.gauge['vcenter_vms_on_failover_hosts'] = Gauge('vcenter_vms_on_failover_hosts',
                                                                'Count of VMs placed on failover hosts, they shouldn\'t be there',
                                                                ['hostname','vccluster','failover_host'])

        self.gauge['vcenter_failover_host'] = Gauge('vcenter_failover_host',
                                                        'Count of failover hosts in prod clusters',
                                                        ['hostname','vccluster'])

        self.gauge['vcenter_prod_cluster'] = Gauge('vcenter_prod_cluster',
                                                    'Count of prod cluster in a vcenter',
                                                    ['hostname'])

        self.gauge['vcenter_failover_nodes_set'] = Gauge('vcenter_failover_nodes_set',
                                                    'Count of configured failover nodes in the cluster',
                                                    ['hostname', 'vccluster'])

        self.gauge['vcenter_cluster_ha_configured'] = Gauge('vcenter_cluster_ha_configured',
                                                    'Cluster with correct HA policy set',
                                                    ['hostname', 'vccluster'])

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

        #foo we need for perfmgr
        self.counter_info = {}
        perf_manager = self.content.perfManager
        metrics = perf_manager.QueryPerfCounterByLevel(level=2)

        for metric in metrics:
            full_name = '.'.join([metric.groupInfo.key,
                                  metric.nameInfo.key,
                                  metric.rollupType])
            self.counter_info[full_name] = metric.key

        selected_metrics = self.exporterInfo['hv_metrics']
        if selected_metrics:
            self.counter_ids_to_collect = [self.counter_info[i] for i
                                           in selected_metrics
                                           if i in self.counter_info]
        else:
            self.counter_ids_to_collect = [i.key for i in self.counter_info]

        for counter_id in selected_metrics:
            vc_gauge = 'vcenter_esxi_' + counter_id.replace('.', '_')
            self.gauge[vc_gauge] = Gauge(vc_gauge, vc_gauge, [
                'hostname', 'esxi_host', 'metric_detail' ])

        self.counter_info_keys_list = list(self.counter_info.keys())
        self.counter_info_keys_underscore = [x.replace('.', '_')
                                             for x in self.counter_info_keys_list]
        self.counter_info_values_list = list(self.counter_info.values())

    def collect(self):
        region = self.vcenterInfo['hostname'].split('.')[2]
        self.metric_count = 0
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

        logging.debug('getting version information for each esx host')

        self.host_data, self.mors = self.collect_properties(self.si, self.hosts,
                                    vim.HostSystem, self.host_properties, True)

        for host in self.host_data:
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
            try:
                if self.mors[host['obj']].runtime.inMaintenanceMode:
                    self.gauge['vcenter_esx_node_maintenance'].labels(host['summary.config.name']).set(1)
                else:
                    self.gauge['vcenter_esx_node_maintenance'].labels(host['summary.config.name']).set(0)
                self.metric_count += 1
            except Exception as e:
                logging.debug(
                    "Couldn't get maintenance state for host: " + host['summary.config.name'] + " " + str(e))

        self.do_failover_metrics()

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


        vch_time = self.si.CurrentTime()
        start_time = vch_time - \
            timedelta(seconds=(int(self.exporterInfo['collection_interval'])
                               + 60))
        end_time = vch_time - timedelta(seconds=60)
        perf_manager = self.si.content.perfManager

        queryResult = []
        queryDict = {}

        for group in self.chuncker(self.host_data, 50):
            perfQueries = []
            for item in group:
                metric_ids = [
                        vim.PerformanceManager.MetricId(
                            counterId=i, instance="*") for i
                            in self.counter_ids_to_collect
                    ]
                hv_instance = self.mors[item["obj"]]
                spec = vim.PerformanceManager.QuerySpec(
                        maxSample=1,
                        entity=hv_instance,
                        metricId=metric_ids,
                        intervalId=20,
                        startTime=start_time,
                        endTime=end_time)
                perfQueries.append(spec)
                self.metric_count += 1
            if len(perfQueries) > 0:
                queryResult.append(perf_manager.QueryStats(querySpec=perfQueries))

        for group in queryResult:
            for hv in group:
                queryDict[hv.entity] = hv

        for item in self.host_data:
            try:
                logging.debug('current hv processed - ' +
                              item["summary.config.name"])

                hv_instance = self.mors[item["obj"]]

                for val in queryDict[hv_instance].value:

                    # send gauges to prometheus exporter: metricname and value with
                    # labels: vm name, project id, vcenter name, vcneter
                    # node, instance uuid and metric detail (for instance
                    # a partition for io or an interface for net metrics)
                    # - weupdate the gauge only if the value is not -1
                    # which means the vcenter has no value
                    if val.value[0] != -1:
                        if val.id.instance == '':
                            metric_detail = 'total'
                        else:
                            metric_detail = val.id.instance

                        gauge_finder = self.counter_info_values_list.index(val.id.counterId)
                        gauge_title = self.counter_info_keys_underscore[gauge_finder]
                        gauge_title = 'vcenter_esxi_' + gauge_title
                        gauge_title = re.sub('\.', '_', gauge_title)
                        try:
                            self.update_gauge(gauge_title,
                                              self.vcenterInfo['hostname'],
                                              item["summary.config.name"],
                                              metric_detail,
                                              val.value[0])
                        except socket.error as e:
                            if e.errno != errno.EPIPE:
                                raise
                            logging.info("Brokent pipe updating gauge")
                        except Exception as e:
                            logging.info("Unable to update gauge " + str(e))

                logging.debug('==> gauge loop end: %s' % datetime.now())
                logging.debug("collected data for " + item['summary.config.name'])
            except KeyError as e:
                logging.debug("property not defined for hv: " + str(e))
            except Exception as e:
                logging.info("couldn't get perf data: " + str(e))

    def chuncker(self, seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))

    def update_gauge(self, gauge_title, vcenter, esxi_host, metric_detail, metric_val):
        self.gauge[gauge_title].labels(
                vcenter,
                esxi_host,
                metric_detail).set(metric_val)



    def do_failover_metrics(self):
        collected_spare_hosts = dict()
        cluster_count = 0
        failoverLevel = dict()
        failoverHosts = dict()
        for cluster in self.clusters:
            if "prod" in cluster.name:
                cluster_count += 1
                self.gauge['vcenter_cluster_ha_configured'].labels(self.vcenterInfo['hostname'],cluster.name).set(0)
                try:
                    if cluster.configuration.dasConfig.admissionControlEnabled \
                        and cluster.configuration.dasConfig.admissionControlPolicy.failoverLevel >= 1 \
                        and len(cluster.configuration.dasConfig.admissionControlPolicy.failoverHosts) == 1:

                        failoverLevel[cluster.name] = cluster.configuration.dasConfig.admissionControlPolicy.failoverLevel
                        failoverHosts[cluster.name] = cluster.configuration.dasConfig.admissionControlPolicy.failoverHosts
                        logging.debug("cluster: %s failoverLevel: %s failoverHosts: %s", cluster.name, failoverLevel[cluster.name], len(failoverHosts[cluster.name]))

                        self.gauge['vcenter_cluster_ha_configured'].labels(self.vcenterInfo['hostname'],cluster.name).set(1)

                        for host in cluster.configuration.dasConfig.admissionControlPolicy.failoverHosts:
                            logging.debug("cluster: %s failoverHost: %s", cluster.name, host.name)
                            if host.runtime.connectionState == 'notResponding':
                                logging.info("cluster: %s, HA Host: %s not responding. Skipping", cluster.name, host.name)
                                continue
                            if host.runtime.inMaintenanceMode:
                                logging.info("cluster: %s, HA Host: %s is in maintenance, shouldn't be! Skipping", cluster.name, host.name)
                                continue
                            vms = list()
                            for vm in host.vm:
                                if vm.config is None:
                                    # VM does not have a configuration.
                                    logging.debug("cluster: %s host: %s - Leftover corpsed VM %s should not be there", cluster.name, host.name, vm.name)
                                    continue
                                elif vm.config.template:
                                    # VM is a template
                                    logging.debug("cluster: %s host %s - Ignoring VM template %s", cluster.name, host.name, vm.name)
                                    continue
                                elif vm.config.managedBy.type == 'volume':
                                    # VM is a shadow VM representing a Cinder volume
                                    logging.debug("cluster %s host %s - Ignoring shadow VM %s of type %s managed by %s", cluster.name, host.name, vm.name, vm.config.managedBy.type, vm.config.managedBy.extensionKey)
                                    continue
                                elif hasattr(vm.runtime, 'powerState'):
                                    if vm.runtime.powerState == 'poweredOff':
                                        logging.debug("cluster %s host %s - Ignoring powered off VM %s of type %s managed by %s", cluster.name, host.name, vm.name, vm.config.managedBy.type, vm.config.managedBy.extensionKey)
                                        continue
                                else:
                                    # A real VM which should not be on a HA host
                                    vms.append(vm)
                                    logging.info("cluster %s host %s - VM %s should not be there", cluster.name, host.name, vm.name)
                            if cluster.name in collected_spare_hosts.keys():
                                #add another element if we have this cluster and more than one spare
                                collected_spare_hosts[cluster.name].append({'name' : host.name, 'vms' : len(vms)})
                                logging.info(cluster.name + ": " + host.name + ": " + str(vms))
                            else:
                                collected_spare_hosts[cluster.name] = [{ 'name': host.name, 'vms': len(vms)}]
                                if len(vms):
                                    logging.info(cluster.name + ": " + host.name + ": " + str(vms))

                except Exception as e:
                    logging.debug(
                            cluster.name + ": AdmissionControlPolicy not properly configured, bailing out " + str(e))

        for clustername in collected_spare_hosts.keys():
            count_vms = 0
            count_failoverhosts = 0
            for pair in collected_spare_hosts[clustername]:
                self.gauge['vcenter_vms_on_failover_hosts'].labels(self.vcenterInfo['hostname'],clustername,pair['name']).set(pair['vms'])
                count_failoverhosts += 1
                self.metric_count += 1
            self.gauge['vcenter_failover_host'].labels(self.vcenterInfo['hostname'],clustername).set(count_failoverhosts)
            self.metric_count += 1

        self.gauge['vcenter_prod_cluster'].labels(self.vcenterInfo['hostname']).set(cluster_count)
        self.metric_count += 1

        for clustername in failoverLevel.keys():
            self.gauge['vcenter_failover_nodes_set'].labels(self.vcenterInfo['hostname'],clustername).set(failoverLevel[clustername])
            self.metric_count += 1
