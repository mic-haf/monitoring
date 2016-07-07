import datetime
import os
import time
import subprocess
import ntixl2
from ntixl2.xl2 import XL2SLM
from ntixl2.message import *
path = os.path.realpath(__file__)
path = str(path).replace('.py', '.txt')

max_allowed_storage_percentage = 50


def write_to_file_timestamped(message):
    with open(path, "a") as logfile:
        logfile.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        logfile.write(' {0}\n'.format(message))


def mass_connected():
    pipe = subprocess.Popen("if [ -d /media/XL2-sd/Projects/RBL ]; then echo 'true'; else echo 'false'; fi", stdout=subprocess.PIPE, shell=True)
    found = 'true' in pipe.communicate()[0].decode()
    return found


def get_xl2_storage():
    pipe = subprocess.Popen(["df", "/media/XL2-sd/Projects/RBL"], stdout=subprocess.PIPE)
    storage_info = pipe.communicate()[0]
    storage_info = storage_info.split()
    storage_percentage = 0
    for item in storage_info:
        decoded = item.decode('utf-8')
        if '%' in decoded:
            try:
                storage_percentage = float(decoded.replace('%', ''))
            except ValueError:
                pass
    return storage_percentage

#try:

try:
    xl2 = XL2SLM()
    print(xl2.device_status+'\n')
    write_to_file_timestamped(xl2.device_status)
    if xl2.device_status != 'SERIAL':
        xl2.to_serial()
        i = 0
        while xl2.device_status != 'SERIAL' and i < 30:
            time.sleep(1)
            i += 1
        time.sleep(30)
except ntixl2.xl2.XL2Error:
    write_to_file_timestamped("No device found")
    quit()

xl2.serial_message(INITIATE.STOP())
time.sleep(3)

# dismiss Voice memo prompt
m = SYSTEM_KEY()
m.append_param('ENTER')
xl2.serial_message(m)

# switch to mass storage mode
print("device_status: ", xl2.device_status)
print("switch device status to MASS", xl2.to_mass())
i = 0
while not mass_connected() and i < 180:
    time.sleep(1)
    i += 1
# Get readout time and date and create folder
curr_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
os.system("mkdir ~/data/logs/{}".format(curr_time))
# Copy and delete spectrum and log files
os.system("find /media/XL2-sd/Projects/RBL -type f -name '*RTA_3rd_Log.txt' -exec cp '{{}}' ~/data/logs/{} ';'".format(curr_time))
os.system("find /media/XL2-sd/Projects/RBL -type f -name '*123_Log.txt' -exec cp '{{}}' ~/data/logs/{} ';'".format(curr_time))
os.system("sudo rm -f /media/XL2-sd/Projects/RBL/*.txt")
os.system("sudo rm -f /media/XL2-sd/Projects/RBL/*.XL2")

storage_percentage = get_xl2_storage()
write_to_file_timestamped(str(storage_percentage) + ' % of storage full\n')

while get_xl2_storage() > max_allowed_storage_percentage:
    os.system("ls -rt /media/XL2-sd/Projects/RBL/*.wav | tail -1 | xargs sudo rm -i -f")
    write_to_file_timestamped("deleted file, {0}% remaining".format(get_xl2_storage()))

xl2.to_serial()
i = 0
while xl2.device_status != 'SERIAL' and i < 30:
    time.sleep(1)
    i += 1

time.sleep(30)
while 'RUNNING' not in xl2.serial_message(QUERY_INITIATE_STATE())['state']:
    # make sure screen is blank
    m = SYSTEM_KEY()
    for x in range(0, 5):
        m.append_param('ESC')
    xl2.serial_message(m)

    xl2.select_profile(profile=5)
    time.sleep(3)
    xl2.serial_message(INITIATE.START())
    time.sleep(15)
    print("iteration finished \n")

#except Exception as e:
#    write_to_file_timestamped(str(e))
