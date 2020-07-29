import re, logging
from osapi_exporters.osapi_exporter import OSAPIExporter
from prometheus_client import Gauge, Counter

class CinderBackend(OSAPIExporter):

    def __init__(self, exporterType, exporterConfig):
        super().__init__(exporterType, exporterConfig)

        self.volume_api = self.osapi.volume
        self.pool_data = dict()

        self.counter, self.gauge= {}, {}

        self.gauge['total_capacity_gb'] = Gauge(
            'total_capacity_gb', 'total_capacity_gb',
            ['vcenter_shard', 'volume_backend_name'])

        self.gauge['allocated_capacity_gb'] = Gauge(
            'allocated_capacity_gb', 'allocated_capacity_gb',
            ['vcenter_shard', 'volume_backend_name'])

        self.gauge['free_capacity_gb'] = Gauge(
            'free_capacity_gb', 'free_capacity_gb',
            ['vcenter_shard', 'volume_backend_name'])

        self.gauge['max_over_subscription_ratio'] = Gauge(
            'max_over_subscription_ratio', 'max_over_subscription_ratio',
            ['vcenter_shard', 'volume_backend_name'])

        self.gauge['overcommit_ratio'] = Gauge(
            'overcommit_ratio', 'overcommit_ratio',
            ['vcenter_shard', 'volume_backend_name'])

        self.gauge['free_until_overcommit'] = Gauge(
            'free_until_overcommit', 'free_until_overcommit',
            ['vcenter_shard', 'volume_backend_name'])


    def collect(self):
        """Collect the stats from the scheduler here."""
        logging.debug("Collect stats from ")
        self.metric_count = 0

        pools = self.volume_api.backend_pools()
        for pool in pools:
            caps = pool['capabilities']
            # Remove some unneeded keys
            pool_data = {
                'total_capacity_gb': caps['total_capacity_gb'],
                'allocated_capacity_gb': caps['allocated_capacity_gb'],
                'free_capacity_gb': caps['free_capacity_gb'],
                'max_over_subscription_ratio': caps['max_over_subscription_ratio'],
                'overcommit_ratio': None,
                'free_until_overcommit': None,
                'reserved_percentage': caps['reserved_percentage']
            }
            shard_name = caps['vcenter-shard']
            logging.debug("Got stats for pool {} ({}/{})".format(
                self.region,
                shard_name,
                caps['volume_backend_name']))

            if caps['total_capacity_gb']:
                pool_data['overcommit_ratio'] = caps['allocated_capacity_gb'] / caps['total_capacity_gb']
            else:
                pool_data['overcommit_ratio'] = 0

            free_until_overcommit = None
            if caps['total_capacity_gb'] and 'max_over_subscription_ratio' in caps:
                free_until_overcommit = (
                    caps['total_capacity_gb'] * float(caps['max_over_subscription_ratio'])
                    - caps['allocated_capacity_gb'] )
            pool_data['free_until_overcommit'] = free_until_overcommit

            logging.debug('({}/{})-total_capacity_gb = {}'.format(
                shard_name, caps['volume_backend_name'],
                caps['total_capacity_gb']
            ))
            logging.debug('({}/{})-free_capacity_gb = {}'.format(
                shard_name, caps['volume_backend_name'],
                caps['free_capacity_gb']
            ))
            logging.debug('({}/{})-allocated_capacity_gb = {}'.format(
                shard_name, caps['volume_backend_name'],
                caps['allocated_capacity_gb']
            ))
            logging.debug('({}/{})-free_until_overcommit = {}'.format(
                shard_name, caps['volume_backend_name'],
                free_until_overcommit
            ))
            logging.debug('({}/{})-max_over_subscription_ratio = {}'.format(
                shard_name, caps['volume_backend_name'],
                caps['max_over_subscription_ratio']
            ))
            logging.debug('({}/{})-overcommit_ratio = {}'.format(
                shard_name, caps['volume_backend_name'],
                pool_data['overcommit_ratio']
            ))
            self.metric_count += len(pool_data)

            if shard_name not in self.pool_data:
                self.pool_data[shard_name] = dict()

            if caps['volume_backend_name'] not in self.pool_data[shard_name]:
                self.pool_data[shard_name][caps['volume_backend_name']] = dict()

            self.pool_data[shard_name][caps['volume_backend_name']] = pool_data

        logging.debug("Pool data = {}".format(self.pool_data))

    def export(self):
        """Add the stats and export them."""
        for shard in self.pool_data.keys():
            logging.debug("shard = {}".format(shard))
            for backend in self.pool_data[shard].keys():
                logging.debug("  backend {}".format(backend))

                self.gauge['total_capacity_gb'].labels(
                    shard, backend
                ).set(self.pool_data[shard][backend]['total_capacity_gb'])

                self.gauge['allocated_capacity_gb'].labels(
                    shard, backend
                ).set(self.pool_data[shard][backend]['allocated_capacity_gb'])

                self.gauge['free_capacity_gb'].labels(
                    shard, backend
                ).set(self.pool_data[shard][backend]['free_capacity_gb'])

                self.gauge['max_over_subscription_ratio'].labels(
                    shard, backend
                ).set(self.pool_data[shard][backend]['max_over_subscription_ratio'])

                self.gauge['overcommit_ratio'].labels(
                    shard, backend
                ).set(self.pool_data[shard][backend]['overcommit_ratio'])

                self.gauge['free_until_overcommit'].labels(
                    shard, backend
                ).set(self.pool_data[shard][backend]['free_until_overcommit'])



    def isDataValid(self, status_code, data):
        if data is None:
            return False
        if status_code != 200:
            return False
        if isinstance(data, dict) and isinstance(data.get('imdata'), list):
            return True
        return False

