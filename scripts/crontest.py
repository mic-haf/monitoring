import datetime
import os
path = os.path.realpath(__file__)
path = str(path).replace('.py','.txt')
print(path)
with open(path, "a") as myfile:
    myfile.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))