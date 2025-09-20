##A very simple wifimanager using Network Manager. Easy to setup in 4 simple steps.

When you want your headless raspberry project to be portable so that it is easy to connect to any wifi network, you need this.<br>

## how does it work
- At boot a service is started that runs wificonfig.py<br>
- This checks whether there is a wifi connection.<br>
- If not, it starts a hotspot and a flask server that serves a form on the configured location (wificonfig.py)
- We can connect to the hotspot and browse to the location to fill up and submit the form
- If the wificredentials are correct, the raspberry will connect and the page.
- we can find the ip by browsing to <hostname>.local:8000 e.g. rpi-domo.local:8000  or rpi_domo:8000<br>
  ![ipdisc](https://github.com/user-attachments/assets/0ab5b0d7-b675-4617-833e-1f81b9776904)

When the hotspot is up and nothing happens (no user attempts to connect), it times out after 5 minutes and then the rpi will reboot.  So in case of a grid failure it will always reconnect, even when your router comes up very slow.
**Important** if your system already runs a webserver, we need to change the portnumber of the flask server. Please see at the bottom of this page 
[additional server](#additional-server)

## the 4 mainsteps are
[download files](#download-files)
<br>[hotspot connection](#setup-hotspot)
<br>[setup flask](#setup-flask)
<br>[setup service](#setup-service)


What do we need: 
We need a modern raspberry linux that runs networkmanager (bookworm) with python3 flask installed.<br>
**apt install python3-flask**<br>

## download_files
Make a directory on your raspberry e.g. /home/<username> and download the 3 files into this location.
If you are in an ssh session be sure you are root (sudo su)
Check that the scripts have the needed permissions.<br>
 - chmod +x setup-hotspot.sh
 - chmod +x wificonfig.py

## setup hotspot
first of all we need to setup a hotspot connection in NetworkManager. We do that with a sequence of nmcli commands.<br>
You can issue these commands manually or using the script. Change ssid and passwd (psk) to your needs. 
<br>Beware that when you change the con-nane, you should also do that in wificonfig.py !<br>
When done, you can run the script **./setup_hotspot.sh**<br>
When this has run, we do  **ls /etc/NetworkManager/system-connections**. It should now contain HOTSPOT.nmconnection
With **cat /etc/NetworkManager/system-connections/<your_name>.nmconnection** you can inspect that it is what you wanted.
We can manually bring it up **nmcli connection up HOTSPOT** Check in your networks if it is there and inspect its properties.<br>
**nmcli connection down HOTSPOT** to bring it doen again.

## setup flask
The python script 'wificonfig.sh does the important things 
 - checks that there is a wifi connection
 - if not connected, put the led on, opens the hotspot and serves the wifi form
 - when a connection has made it closes the hotspot, the led goes out and it serves a webpage with the IP

When done you should test with **python3 wificonfig.py** for errors.

## setup service
The next thing to do is setup a service that starts at boot and does the following:
 - it starts /home/user/wificonfig.py<br>
 - after 6 minutes it is not needed anymore and stops
 - when it stops it kills the eventually running wificonfig.py
 - During this time we can discover the ip (rpi_domo:8000)

we should copy the file wificonfig.service in /etc/systemd/system/  <br>
check with **nano /etc/systemd/system/wificonfig.service** that the path to wificonfig.py is correct. 
We need to enable the service and make it run at boot with the following commands:
- **systemctl daemon-reload**
- **systemctl enable wificonfig.service**
- **systemctl start wificonfig.service**

## testing
It is important to test everything well. Be sure that the flask server is not pointed to the same port as an eventual other server in your system (see below). If there is an error you may need to put the sd card in a cardreader and use a linux system to edit.<br>
Always first run python3 wificonfig.py from the commandline to check for errors. 
check if the service is running **systemctl status wificonfig.service**
Now we can reboot. If the raspberry was connected before, it comes up and after some time you can browse to its ip:8000 or <yourhostname>.local:8000 to see the ip information page.

When everything works and you are connected to wifi, you can **nmcli connection show --active** to find the active connection. We are going to corrupt this, so that it cannot connect on reboot. Lets assume the active connection is hansiart.  You can **ls /etc/NetworkManager/system-connections** now you will see the name is hansiart.nmconnection. 

Now **nano /etc/NetworkManager/system-connection/hansiart.nmconnection** and edit the psk= to make it invalid to your wifi. Ctrl x to save and reboot. After a minute, the onboard led activity stops. Now the wifi connection is checked and after that, the led goes on. Now the hotspot shows up in the available networks. Connect to the hotspot and browse to 192.168.4.1:8000 (add :portnumber when it is not 80). Fill up the form and submit. Now after a lot of flashing the onboard led goes out. The rpi is are connected to your wifi.  

I this didnt work and your raspberry connected as usual, ther is probably anothee connection with the right credentials. you should repeat the step above.

## additional server
If you already have another server in your system that serves a homepage, you can point the last line in wificonfig.py to port 5000 instead of 80
so it doesn't conflict with your webserver.<br>
To prevent that you have to remember this portnumber, here is a smart trick that integrates the flask server and the other.<br>
Rename your index.html to index.php and ensure that you have php installed<br>
**sudo apt update**
**sudo apt install php libapache2-mod-php -y** 
**sudo systemctl restart apache2**
In the page you have on top: 
```
<?php
$server_ip = $_SERVER['SERVER_ADDR'];  // Apache's IP
?>
```
After the body tag you can have this  
```
<?php if ($server_ip === "192.168.4.1"): ?>
<!-- display a link to 192.168.4.1:5000 or an iframe with source="192.168.4.1:5000" -->
<center> <a href="http://192.168.4.1:5000/">Wi-Fi Config</a>
<?php else: ?>
    <!-- here comes your regular homepage -->
  <?php endif; ?>
```
Now when the hotspot is running you'l see the link to the wifiform and when normal connected<br>
you'l see your homepage.
