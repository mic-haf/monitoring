import datetime
import os
import time
import subprocess
from ntixl2 import *
log_path = os.path.realpath(__file__)
log_path = str(log_path).replace('.py', '.txt')
log_directory = '/home/pi-rbl/data/logs'


def write_to_file_timestamped(msg):
    print(msg)
    with open(log_path, "a") as logfile:
        logfile.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
        logfile.write(' {0}\n'.format(msg))

try:
    directories = [os.path.join(log_directory, directory) for directory in next(os.walk(log_directory))[1] if "PROCESSED" not in directory]

    for directory in directories:
        paths = [os.path.join(directory, file) for file in next(os.walk(directory))[2]]
        write_to_file_timestamped("working on {}".format(directory))
        if len(paths) < 2:
            # TODO: rename to something like EMPTY_PROCESSED
            pass
        level_path = [path for path in paths if '123_Log.txt' in path][0]
        spectrum_path = [path for path in paths if '3rd_Log.txt' in path][0]

        level_dict = xl2parser.parse_broadband_file(level_path)
        spectrum_dict = xl2parser.parse_spectrum_file(spectrum_path)

except Exception as e:
    write_to_file_timestamped(str(e))
