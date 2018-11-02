import ssl
from pyVmomi import vim, vmodl
from pyVim.connect import SmartConnect, Disconnect


def connect_to_vcenter(host, user, pwd, port, ignore_ssl):

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