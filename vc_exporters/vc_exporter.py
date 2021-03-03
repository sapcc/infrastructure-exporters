import exporter
import socket
import ssl
import master_password
from pyVmomi import vmodl
from pyVim.connect import SmartConnect, Disconnect
from prometheus_client import start_http_server


# VCExporter class has init routines and shared functions for all VCExporters
class VCExporter(exporter.Exporter):

    def __init__(self, exporterType, vcenterExporterConfigFile):
        super().__init__(exporterType, vcenterExporterConfigFile)
        self.vcenterInfo = self.exporterConfig['device_information']
        self.exporterInfo = self.exporterConfig['exporter_types'][self.exporterType]
        self.duration = int(self.exporterInfo['collection_interval'])
        self.vcenterInfo['password'] = self.generate_pw(self.vcenterInfo['username'], self.vcenterInfo['password'],
                                                        self.vcenterInfo['hostname'])
        self.si = self.connect_to_vcenter(self.vcenterInfo['hostname'],
                                          self.vcenterInfo['username'],
                                          self.vcenterInfo['password'],
                                          self.vcenterInfo['port'],
                                          self.vcenterInfo['ignore_ssl'],)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(('localhost', int(self.exporterConfig['prometheus_port']))) != 0:
                start_http_server(int(self.exporterConfig['prometheus_port']))

    def generate_pw(self, user, mpw, url):
        handle = master_password.MPW(user, mpw)
        return handle.password(url).replace('/', '')

    def connect_to_vcenter(self, host, user, pwd, port, ignore_ssl):

        # vCenter preparations
        # check for insecure ssl option
        context = None
        if ignore_ssl and \
                hasattr(ssl, "_create_unverified_context"):
            context = ssl._create_unverified_context()

        # connect to vcenter
        try:
            si = SmartConnect(
                host=host,
                user=user,
                pwd=pwd,
                port=port,
                sslContext=context)
        except IOError as e:
            raise SystemExit("Unable to connect to host with supplied info. Error %s: " % str(e))
        return si

    def disconnect_from_vcenter(self, si):
        Disconnect(si)

    def collect_properties(self, service_instance, view_ref, obj_type, path_set=None,
                           include_mors=False):
        """
        Collect properties for managed objects from a view ref
        Check the vSphere API documentation for example on retrieving
        object properties:
            - http://goo.gl/erbFDz
        Args:
            si          (ServiceInstance): ServiceInstance connection
            view_ref (vim.view.*): Starting point of inventory navigation
            obj_type      (vim.*): Type of managed object
            path_set               (list): List of properties to retrieve
            include_mors           (bool): If True include the managed objects
                                        refs in the result
        Returns:
            A list of properties for the managed objects
        """
        collector = service_instance.content.propertyCollector

        # Create object specification to define the starting point of
        # inventory navigation
        obj_spec = vmodl.query.PropertyCollector.ObjectSpec()
        obj_spec.obj = view_ref
        obj_spec.skip = True

        # Create a traversal specification to identify the path for collection
        traversal_spec = vmodl.query.PropertyCollector.TraversalSpec()
        traversal_spec.name = 'traverseEntities'
        traversal_spec.path = 'view'
        traversal_spec.skip = False
        traversal_spec.type = view_ref.__class__
        obj_spec.selectSet = [traversal_spec]

        # Identify the properties to the retrieved
        property_spec = vmodl.query.PropertyCollector.PropertySpec()
        property_spec.type = obj_type

        if not path_set:
            property_spec.all = True

        property_spec.pathSet = path_set
        # Add the object and property specification to the
        # property filter specification
        filter_spec = vmodl.query.PropertyCollector.FilterSpec()
        filter_spec.objectSet = [obj_spec]
        filter_spec.propSet = [property_spec]

        # Retrieve properties
        props = collector.RetrieveContents([filter_spec])
        data = []
        mors = {}
        for obj in props:
            properties = {}
            for prop in obj.propSet:
                properties[prop.name] = prop.val

            if include_mors:
                properties['obj'] = str(obj.obj)
                mors[str(obj.obj)] = obj.obj

            data.append(properties)
        return data, mors
