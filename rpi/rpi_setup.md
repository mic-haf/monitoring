-   [Rpi Einrichten](#rpi-einrichten)
    -   [Betriebsystem auf SD Karte brennen](#betriebsystem-auf-sd-karte-brennen)
    -   [Tastatur layout korrigieren und internationalization optionen einstellen](#tastatur-layout-korrigieren-und-internationalization-optionen-einstellen)
    -   [Username wechseln](#username-wechseln)
    -   [Bildschirm Einstellungen](#bildschirm-einstellungen)
    -   [Wifi einrichten](#wifi-einrichten)
    -   [Betriebsystem update-upgrade](#betriebsystem-update-upgrade)
    -   [SSH Reverse tunnel einrichten](#ssh-reverse-tunnel-einrichten)
    -   [ykush USB-hub einrichten](#ykush-usb-hub-einrichten)

Rpi Einrichten
==============

Betriebsystem auf SD Karte brennen
----------------------------------

Betriebsystem auswahl:

-   `raspbian jessie ligth` (Ausgewählt) oder
-   `raspbian jessie`

[Raspbian installieren](https://www.raspberrypi.org/documentation/installation/installing-images/)

Tastatur layout korrigieren und internationalization optionen einstellen
------------------------------------------------------------------------

    sudo raspi-config

-   normal keyboard (105tasten) und ch-german
-   locale to`en_GB_utf-8`
-   Zeit
-   ...

dann `reboot`

Username wechseln
-----------------

Standard user: **pi**, pw: **raspberry**

> Wechseln zu neue user: **pi-rbl** pw: **akustik16**

Das erfolft mit folgende schtritten:

1.  root pw herstellen `sudo passwd root`
2.  logout and login in **root**
3.  username wechseln `usermod -l newname pi`
4.  home dir wechseln `usermod -m -d /home/newname newname`
5.  logout root login **pi-rbl**
6.  pw wechseln `sudo passwd`
7.  `sudo-visudo`
8.  `sudo groupmod -n pi-rbl pi`
9.  `sudo passwd -l root`

Bildschirm Einstellungen
------------------------

### Bildschirm drehen

1.  file öffnen und modifizieren: `sudo nano /boot/config.txt`
2.  hizufügen `display_rotate=2`

### Fontsize am terminal Einstellen

Den Bildschirm soll lesbar sein

Im File `/etc/default/console-setup` folgenden Zeilen Einfügen:

    # FONTFACE="" und FONTSIZE=""
    FONTFACE="Terminus" und FONTSIZE="16x32" 

Wifi einrichten
---------------

Das ist vorübergehend falls rpi noch kein funktionierendes USB-stick verfügt. [wifi](https://www.raspberrypi.org/documentation/configuration/wireless/wireless-cli.md)

Im File `/etc/default/console-setup` folgenden Zeilen Einfügen:

    network={
        ssid="The_ESSID_from_earlier"
        psk="Your_wifi_password"
    }

dann folgende Befehlen:

    sudo iwup wlan0
    sudo iwdown wlan0

Betriebsystem update-upgrade
----------------------------

    sudo apt-get update
    sudo apt-get upgrade

w\*\*\*\* \#\# Internetverbindung einrichten durch UMTS-stik

### HI-link alternative

den RPI verbindet sich am stick durch ip protokoll.

The Huawei modem is shown with device ID

-   **12d1:1f01** if mass storage
-   **12d1:14db** if Hi-link.

1.  Paket **sg3-utils** installieren: `sudo apt-get install sg3-utils`

2.  To automate the mode switch; File `/etc/udev/rules.d/10-Huawei.rules` erzeugen und folgenden Zeilen Einfügen:

        SUBSYSTEMS=="usb", ATTRS{modalias}=="usb:v12D1p1F01*", SYMLINK+="hwcdrom", RUN+="/usr/bin/sg_raw /dev/hwcdrom 11 06 20 00 00 00 00 00 01 00"

    jetzt sollte den UMTS-USB-stick im richtige Modus (richtige ID) sein.

3.  Network interfaces anpassen: Im File `/etc/network/interfaces` folgenden Zeilen Einfügen:

        allow-hotplug eth1
        iface eth1 inet dhcp

4.  reboot

Following the reboot, the Pi should now say "My IP address is xxx.xxx.xx.xx 192.168.1.100", where xxx.xxx.xx.xx = the IP address assigned by your setup to the RJ45 ethernet socket, and 192.168.1.100 is the address assigned to the Pi on the Huawei pseudo 'network adapter'.

------------------------------------------------------------------------

SSH Reverse tunnel einrichten
-----------------------------

> Ziel: remote zugriff auf `pi-rbl` über internet.

Remote Zugriff wird über ssh erfolgen. Das ermoglicht zugriff auf terminal und file transfer über sftp.

**[link](https://www.everythingcli.org/ssh-tunnelling-for-fun-and-profit-local-vs-remote/)**

Notwendig: - linux server mit bekannte fixes`server_ip` (oder hostname), `user` und `pw`. Diesem Server muss über Internet zugreifbar sein. - Für Window is ein ssh client notwendig. Eines davon ist `putty` - Für File Transfer über sftp ist `FileZilla` ein praktisches Client

### Reverse tunnel bauen und testen

> Es muss ein port ausgewält werden fur das forwarding. Wir wählen `2210`

    ssh -N -R 2210:localhost:22 user@server_ip

dann server pw eingeben. Die 2 ports sind frei zu wählen wobei 22 muss beim server offen sein. Dann beim server einloggen und

    ssh -p 2210 pi-rbl@localhost

um sich beim pi-rbl sich einzuloggen.

#### ssh key generieren

um pw less reverse tunnel aufbau muss ein key auf dem pi-rbl generiert werden

    ssh-keygen -t rsa

den public teil muss auf den file `~/.ssh/authorized_keys` auf server\_ip copiert werden. Zu beachten sind die korrekten file und ordner permisionen:

    chmod 700 ~/.ssh
    chmod 600 ~/.ssh/authorized_keys

### Reverse tunnel am startup automatisieren

Ein tool in Raspbian welches ermöglicht services am startup aufzubauen ist `systemd`. Damit wird das remote tunnel am startup automatisiert.

1.  Neues systemd unit file \`/etc/systemd/system/tunnel-RFCasa.service\`\` mit Inhalt:

        [Unit]
        Description= Create reverse tunnel from pi-rbl to casa. port forwarded 22 on 2210
        After=network.target

        [Service]
        Type=simple
        User=pi-rbl
        Environment="AUTOSSH_GATETIME=0"
        ExecStart=/usr/bin/autossh -M 0 -o ExitOnForwardFailure=yes  -o ServerAliveInterval=30 -o ServerAliveCountMax=3 -N -R 2210:localhost:22 esr@vc109.duckdns.org

        RestartSec=5
        Restart=always

        [Install]
        WantedBy=multi-user.target

2.  Befehle eingeben:

        sudo systemctl restart tunnel-RFCasa.service
        #Check to see if it started:
        sudo systemctl status -l tunnel-RFCasa.service

    ### Tipps/Usage

    #### Local port forwarding von server\_ip:2210 auf localhost:2210

Im putty eine verbindung herstellen welche entspricht

`ssh -L 2210 server_ip:2210`

dann befindet sich den pi-rbl auf localhost:22.

Mithilfe von key kann man passwortfreie verbindungen herstellen. Auf server\_ip müssen die zugehörigen public keys kopiert werden.

### rpi remote Verbindung mit putty

Mit putty eine verbindung herstellen welche entspricht

`ssh -p 2210 pi-rbl@localhost`

#### Sftp auf pi-rbl mit Filezilla

Verbindung mit sftp protokoll auf localhost:2210

`ssh -p 2210 pi-rbl@localhost`

------------------------------------------------------------------------

ykush USB-hub einrichten
------------------------

Installation ist im README file im ykush ordner beschrieben
