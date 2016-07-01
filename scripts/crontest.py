import datetime
import os
import time
import ntixl2
from ntixl2.xl2 import XL2SLM
from ntixl2.message import *
path = os.path.realpath(__file__)
path = str(path).replace('.py','.txt')


def write_to_file_timestamped(message):
    with open(path, "a") as myfile:
        myfile.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        myfile.write(' {0}\n'.format(message))

try:
    xl2 = XL2SLM()
    print(xl2.device_status+'\n')
    write_to_file_timestamped(xl2.device_status)
    if(xl2.device_status != 'SERIAL'):
        xl2.to_serial()
except ntixl2.xl2.XL2Error:
    write_to_file_timestamped("No device found")
    quit()

xl2.select_profile(profile=5)
xl2.klock()
xl2.serial_message(INITIATE.START())
time.sleep(10)
xl2.serial_message(INITIATE.STOP())

print("device_status: ", xl2.device_status)
print("switch to device status to MASS", xl2.to_mass())
time.sleep(10)
folder = "Projects"
print("list dir in {}/{} folder\n ".format(str(xl2.mountDir), folder), xl2.list_dir(folder))
path = input("Please enter folder to list files: ")
print("files: \n", "\n".join(xl2.list_files(folder +'/'+ path)))
xl2.to_serial()
