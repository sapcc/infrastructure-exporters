
Exporters
============

Exporters is a package of classes that allow you to collect data from infrastructure devices and export the data how you choose.  The base Exporter class enforces collect, export, and run_loop methods to ensure consistency between the designs of specific exporter types.  The base Exporter class also exposes a get_config method to parse yaml files with 'device_information' and 'exporter_types' first level entries.  Exporters are designed to be run concurrently.  A cmd.py file is available to run the desired exporters either singularly, or concurrently if they are enabled in your config files.

Currently Available Exporters
-----------
* apichealth - Returns health metrics for apic host devices
* vcapiandversions - Returns versions for vSphere components
* vccustomervmmetrics - Returns metrics for customer vms running in vCenter
* vccustomerdsmetrics - Returns metrics for customer datstores in vCenter


Running an Exporter from cloned repo
------------
1. clone the repo https://github.wdf.sap.corp/i814196/exporters.git
2. cd to the exporters folder
3. modify the yaml files in samples/ to match your infrastructure
4. install the python environment
   1. ```pipenv install```
5. run a single exporter
   1. ```pipenv run python cmd.py -f <pathToConfig.yaml> -t <exporterType>```
6. run multiple exporters
   1. ```pipenv run python cmd.py -c <pathToConfigfile.yaml,pathToOtherconfigfile.yaml>```

Running the exporter container
------------
1. Clone the repo https://github.wdf.sap.corp/i814196/exporters.git
2. cd to the exporters folder
3. modify the yaml files in samples/ to match your infrastructure
3. build the container
   1. ```docker build -t my-exporters .```
4. run the container as single exporter
   1. ```docker run -p <portsToExpose>:<localPortsToListen> my-exporters "pipenv run python cmd.py -f $(pwd)/samples/<configfile> -t <exporterType>```
5. run the container as multiple exporters
   1.    ```docker run -p <portsToExpose>:<localPortsToListen> my-exporters "pipenv run python cmd.py -c <pathToConfigfile.yaml,pathToOtherconfigfile.yaml>```
  
Exporter files, classes and conventions
------------
* cmd.py - Command line interface to run existing exporters
* exporter.py - Base abstract class for exporters
   * requires collect() and export() methods
   * exposes concurrent run_loop() method for multiple asynchronous exporters
   * contains get_config() class method for reading yaml config files
   * requires an exportertype and configfile passed to it's initializer
* Pipfile and Pipfile.lock - package requirements using pipenv
* samples/ - directory containing sample yaml config files
* \<infrastructure>_exporters - directory containing exporters for \<infrastructure> type
* test - contains Unittest tests for exporters

Adding your own Exporter
------------
- clone the repo https://github.wdf.sap.corp/i814196/exporters.git
- cd to the exporters folder
- create a folder for your infrastructure type
   - i.e. ```mkdir mydevice_exporters```
   - create an \__init__.py folder in this folder
- create any shared utility modules in the myexporters folder
   - i.e. mydevice_exporters/mydevice_utils.py
- create a file for a shared infrastructure exporter
   - i.e. /mydevice_exporters/mydevice_exporter.py
   - in this file ```import exporters```
   - inherit the exporters.Exporter class in your class
      - ```class MydeviceExporter(exporter.Exporter)```
   - implement your \__init__() function which all exporters of this type will use
- create a folder to house each exporter of this type
   - i.e. ```mkdir mydevice_exporters/mydevice_exporter_types```
   - create an \__init__.py in this folder
- create files for your specific exporter types
   - i.e. mydevice_exporters/mydevice_exporter_types/mydevice_healthcheck.py
   - in this file import your exporter and utility modules
      - i.e.

      ```
      from mydevice_exporters.mydevice_exporter import MydeviceExporterfrom
      from mydevice_exporter.mydevice_utils import someSharedFunction
      ```
   - add super() call to \__init__() function
      - i.e. ```super().__init__(exporterType, exporterConfig)```
   - implement your code for the collect() and export() methods

Add your exporter to the CLI Interface
------------

- modify cmd.py
   - import your exporter types
     - i.e. ```from mydevice.exporters.mydevice_exporter_types import mydevice_healthcheck```
   - add your exporter to the 'EXPORTERS' class map
      - i.e. ```'mydevice_healthcheck': mydevice_healthcheck.Mydevice_healthcheck,```
   - EXPORTERS is a mapping of names of exporter types (passed via cli) and classes which implement these exporters
