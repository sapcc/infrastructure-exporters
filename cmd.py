import time
import argparse
import logging
from datetime import datetime
from vc_exporters.vc_exporter_types import (vcapiandversions,
                                            vccustomervmmetrics,
                                            vccustomerdsmetrics,
                                            vchostmetrics)
from apic_exporters.apic_exporter_types import apichealth


EXPORTERS = {
    'vcapiandversions': vcapiandversions.Vcapiandversions,
    'vccustomervmmetrics': vccustomervmmetrics.Vccustomervmmetrics,
    'vccustomerdsmetrics': vccustomerdsmetrics.Vccustomerdsmetrics,
    'apichealth': apichealth.Apichealth,
    'vchostmetrics': vchostmetrics.VcHostMetrics
}


def run_loop(exporterInstance, duration):
    # Start infinite loop to get metrics
    while True:
        logging.info('====> Starting run_loop: ' +
                     exporterInstance.exporterType + ": " +
                     str(datetime.now()))
        # get the start time of the loop to be
        # able to fill it to intervall exactly at the end

        collect_start_time = int(time.time())
        exporterInstance.collect()
        collect_end_time = int(time.time())

        export_start_time = int(time.time())
        exporterInstance.export()
        export_end_time = int(time.time())

        total_loop_time = ((collect_end_time - collect_start_time) +
                           (export_end_time - export_start_time))
        logging.info('number of ' + exporterInstance.exporterType +
                     ' we got metrics for ' +
                     str(exporterInstance.metric_count) + " " +
                     exporterInstance.exporterType +
                     '\'s - actual runtime: '
                     + str(total_loop_time) + 's')

        # this is the time we sleep to fill the loop
        # runtime until it reaches "interval"
        # the 0.9 makes sure we have some overlap to
        # the last interval to avoid gaps in
        # metrics coverage (i.e. we get the metrics
        # quicker than the averaging time)
        loop_sleep_time = 0.9 * \
            int(exporterInstance.exporterConfig['exporter_types'][exporterInstance.exporterType]['collection_interval']) - \
            (collect_end_time - collect_start_time) + \
            (export_end_time - export_end_time)

        if loop_sleep_time < 0:
            logging.warn('getting the metrics takes around ' + str(
                exporterInstance.exporterConfig['exporter_types'][exporterInstance.exporterType]['collection_interval']) +
                ' seconds or longer - please increase the interval setting')
            loop_sleep_time = 0

        logging.debug('====> loop end before sleep: %s' % datetime.now())

        # Sleep until collection duration
        # await asyncio.sleep(int(loop_sleep_time))
        time.sleep(int(loop_sleep_time))
        logging.info('====> Ending run_loop: ' +
                     exporterInstance.exporterType + ": " + str(datetime.now()))


if __name__ == "__main__":

    exporterConfigMapping = {}
    # Take a list of exporter configs and runs their collectors and exporters
    parser = argparse.ArgumentParser(description='Arguments for vcexporter.py')
    parser.add_argument(
        "-f", "--singleconfifigfile", help="Specify full path to single config file to run only one exporter.  Must use -t flag also to specify type.")
    parser.add_argument(
        "-t", "--exportertype", help="Specify exporter type [vcapiandversions, vccustomervmmetrics, vccustomerdsmetrics, apichealth] Used with -f flag")
    args, remaining_argv = parser.parse_known_args()

    if args.singleconfifigfile is not None and args.exportertype is not None:
        if not args.singleconfifigfile.startswith("/"):
            print("Please use full path to configfile")
            exit(0)
        else:
            logging = logging.getLogger()
            infraExporter = EXPORTERS[args.exportertype.lower()](
                args.exportertype.lower(), args.singleconfifigfile)
            run_loop(infraExporter, infraExporter.duration)

    else:
        parser.print_help()
