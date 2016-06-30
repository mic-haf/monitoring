import subprocess


def force_unplug_USB(ykushPort = 1, ykushPath = '/home/pi-rbl/XL2/YKUSH_V1.4.1/ykush'):
    """force power off and power on of a port on the Ykush USB-hub"""
    # power off USB port
    subprocess.call(ykushPath + "-d {}".format(ykushPort))
    # power on USB port
    subprocess.call(ykushPath + "-u {}".format(ykushPort))
    # list device files
    print(subprocess.call("ls -l /dev"))