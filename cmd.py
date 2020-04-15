import time
import argparse
import logging
from threading import Thread
from datetime import datetime
from vc_exporters.vc_exporter_types import (vcapiandversions,
                                            vccustomervmmetrics,
                                            vccustomerdsmetrics,
                                            vchostmetrics)
from apic_exporters.apic_exporter_types import apichealth
from apic_exporters.apic_exporter_types import apicprocess

EXPORTERS = {
    'vcapiandversions': vcapiandversions.Vcapiandversions,
    'vccustomervmmetrics': vccustomervmmetrics.Vccustomervmmetrics,
    'vccustomerdsmetrics': vccustomerdsmetrics.Vccustomerdsmetrics,
    'apichealth': apichealth.Apichealth,
    'apicprocess': apicprocess.ApicProcess,
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

        total_loop_time = ((collect_end_time - collect_start_time) + (export_end_time - export_start_time))

        logging.info("%s: got %s metrics in %ss", exporterInstance.exporterType, exporterInstance.metric_count, total_loop_time)

        # this is the time we sleep to fill the loop
        # runtime until it reaches "interval"
        # the 0.9 makes sure we have some overlap to
        # the last interval to avoid gaps in
        # metrics coverage (i.e. we get the metrics
        # quicker than the averaging time)
        loop_sleep_time = 0.9 * int(exporterInstance.exporterConfig['exporter_types'][exporterInstance.exporterType]['collection_interval']) - total_loop_time
        logging.debug("%s: loop sleep time: %ss", exporterInstance.exporterType, loop_sleep_time)

        if loop_sleep_time < 0:
            logging.warning("%s: getting metrics takes around %ss or longer - please increase the collection intervall",
                exporterInstance.exporterType,
                exporterInstance.exporterConfig['exporter_types'][exporterInstance.exporterType]['collection_interval'])
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
        "-t", "--exportertype", nargs='+', help="Specify exporter type [vcapiandversions, vccustomervmmetrics, vccustomerdsmetrics, apichealth, apicprocess] Used with -f flag")
    args, remaining_argv = parser.parse_known_args()

    if args.singleconfifigfile is not None and args.exportertype is not None:
        if not args.singleconfifigfile.startswith("/"):
            print("Please use full path to configfile")
            exit(0)
        else:
            logging = logging.getLogger()

            # run each exporter type in a separate thread
            threads = []
            for exportertype in args.exportertype:
                infraExporter = EXPORTERS[exportertype.lower()](exportertype.lower(), args.singleconfifigfile)
                threads.append(Thread(target=run_loop, args=(infraExporter, infraExporter.duration)))

            for thread in threads:
                thread.start()

    else:
        parser.print_help()
