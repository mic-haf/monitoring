#Readme yepkit ykush usb hub

##install on Rpi

1. To Build source first install `libusb-1.0-0-dev`, `libusb-1.0-0`  using `sudo apt-get install`
2. Download the source code with archive_name `fd484_ykush_v1.4.1.tar.gz` and unpack with `tar -xvzf archive_name`.This command extracted the source code files into YKUSH_V1.4.1 folder.
3. go to `YKUSH_V1.4.1` folder and run `make`. At this point the ykush binary command is built and available to control the devices connected to YKUSH board.

##The command structure

**sudo ykush option port_number**
option:
	- `-u` Turns the port up
	- `-d` Turns the pot down
port_number:
	- 1 Downstream port 1
	- 2 Downstream port 2
	- 3 Downstream port 3
	- a All downstream ports
