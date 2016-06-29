-   [Intro](#intro)
    -   [XL2 device autodetect and automount](#xl2-device-autodetect-and-automount)
    -   [XL2 umount](#xl2-umount)
    -   [Aktivieren des Remote Measurement](#aktivieren-des-remote-measurement)
    -   [Profil RBL herstellen](#profil-rbl-herstellen)

Intro
=====

------------------------------------------------------------------------

XL2 device autodetect and automount
-----------------------------------

Das erfolgt mit `udev` roules. Information on `udev` rules can be found [here](http://www.reactivated.net/writing_udev_rules.html)

With this rule we have the following results:

-   Fixed device name (`XL2`) if connected as serial device
-   Fixed device name (`XL2-sd`) if connected as mass storage device
-   automount to fixed path (`/media/XL2-sd`) if device connected as mass storage

\`\`\` 
    \#! /bin/sh

    #######################################
    #    XL2SLM device rules              #
    #######################################

    # Symlink 'XL2-sd' and auto mount if device mass storage mode
    #############################################################
    #mounting point
    ENV{mntDir}="/media/XL2-sd"
    # start at sdb to ignore the system hard drive
    ACTION == "add", KERNEL=="sd[b-z]?", ATTRS{idVendor}=="1a2b",ATTRS{idProduct}=="0003", GROUP="users", SYMLINK+="XL2-sd" ,RUN+="/bin/mkdir -p '%E{mntDir}'" ,RUN+="/bin/mount /dev/XL2-sd -t auto '%E{mntDir}'"

    # Symlink 'XL2' if device in serial mode
    ########################################
    ACTION == "add", KERNEL=="ttyA*", ATTRS{idVendor}=="1a2b",ATTRS{idProduct}=="0004", GROUP="users", SYMLINK+="XL2"

\`\`\`

XL2 umount
----------

todo

------------------------------------------------------------------------

Aktivieren des Remote Measurement
---------------------------------
