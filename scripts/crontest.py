import datetime
with open("test.txt", "a") as myfile:
    myfile.write(datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"))