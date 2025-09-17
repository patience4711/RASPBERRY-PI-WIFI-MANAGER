A very simple wifimanager using Network Manager

When you want your raspberry project to be portable so that it is easy to connect to any wifi network, you want to try this.<br>
When powered up, the rpi tries to connect and if it failes, it opens a hotspot with ip 192.168.4.1. <br>
If you connect to that and browse to this address you'l get a form to fill up the wificrecdentials. <br>
When done, click submit and your raspberry is connected. Very simple and fast.

The hotspot times out after 5 minutes and then the rpi will reboot.  So in case of a grid failure it will always reconnect, even when your router comes up very slow.
**Important** if your system runs a webserver, we need to change the portnumber of the flask server, please see at the bottom of this page 
[additional server](#additional-server)

So what do we need. 
We need a modern raspberry linux bookworm with flask and Perl installed.
**apt install python3-flask**
**apt install perl**
**apt install libcgi-pm-perl**

first of all we need a hotspot connection. We do that with a sequence of nmcli commands.
**nano setup_hotspot.sh**<br>
```
#!/usr/bin/env bash<br>
set -e
echo "[INFO] Creating Wi-Fi hotspot profile: HOTSPOT"
# Delete any existing HOTSPOT profile first <br>
if nmcli connection show | grep -q "HOTSPOT"; then<br>
    echo "[INFO] Removing old HOTSPOT connection..."<br>
    nmcli connection delete HOTSPOT<br>
fi<br>
# Create new hotspot connection<br>
nmcli connection add type wifi ifname wlan0 con-name HOTSPOT ssid RPI-HOTSPOT<br>
nmcli connection modify HOTSPOT 802-11-wireless.mode ap<br>
nmcli connection modify HOTSPOT 802-11-wireless.band bg<br>
nmcli connection modify HOTSPOT ipv4.method shared<br>
nmcli connection modify HOTSPOT ipv4.addresses 192.168.4.1/24<br>
nmcli connection modify HOTSPOT wifi-sec.key-mgmt wpa-psk<br>
nmcli connection modify HOTSPOT wifi-sec.psk "RPIHOTSPOT123"<br>
nmcli connection modify HOTSPOT connection.autoconnect yes<br>
nmcli connection modify HOTSPOT connection.autoconnect-priority -999<br>
echo "[INFO] Hotspot setup complete."<br>
echo "[INFO] Start it manually with: nmcli connection up HOTSPOT"'<br>
```
Edit this script to your needs and make it executable **chmod +x setup_hotspot.sh**

When this has run, we do  **ls /etc/NetworkManager/system-connections**. It should now contain HOTSPOT.nmconnection

We need a python script that checks the wifi connection and, if needed, opens the accesspoint and serves the form.
**nano /home/user/wificonfig.py**
```
#!/usr/bin/env python3 
from flask import Flask, request, render_template_string
import subprocess
import time
import threading
import os

app = Flask(__name__)
logfile = "/home/hans/wificonfig_reboot.txt"

# Write a startup entry
#with open(logfile, "a") as f:
#    f.write(f"[STARTUP] Script started at {time.ctime()}\n")

html_form = """
<!DOCTYPE html>
<html>
<head><title>Wi-Fi Setup</title></head>
<body><center><br><br><br>
  <h2>Hansiart Wi-Fi Credentials</h2>
  <form method="post">
    SSID: <input type="text" name="ssid"><br><br>
    Password: <input type="password" name="password"><br><br>
    <input type="submit" value="Connect">
  </form>
  {% if message %}
  <p>{{ message }}</p>
  {% endif %}
</body>
</html>
"""
LED_PATH = "/sys/class/leds/ACT/brightness"

def set_led(state):
    """Turn the green ACT LED on/off"""
    value = "1" if state else "0"
    try:
        subprocess.run(["bash", "-c", f"echo {value} > {LED_PATH}"], check=True)
    except Exception as e:
        print(f"[WARN] Could not set LED: {e}")

def check_wifi_connection():
    """Return SSID if connected, None otherwise"""
    try:
        result = subprocess.run(
            ["nmcli", "-t", "-f", "DEVICE,STATE,CONNECTION", "device"],
            capture_output=True, text=True, check=True
        )
        for line in result.stdout.splitlines():
            parts = line.split(":")
            if len(parts) == 3 and parts[1] == "connected" and parts[2] != "--":
                return parts[2]
    except subprocess.CalledProcessError:
        return None
    return None

def monitor_wifi_and_timeout():
    """Wait 5 minutes, then reboot if still no Wi-Fi connected"""
    time.sleep(300)  # 5 minutes
    ssid = check_wifi_connection()
    if not ssid or ssid == "HOTSPOT":
        # with open("/home/hans/wificonfig_reboot.txt", "a") as f:
        #     f.write(f"[INFO] Wi-Fi not connected, rebooting at {time.ctime()}\n")
        print("[INFO] Wi-Fi not connected after 5 minutes, rebooting.")
        subprocess.run(["perl", "/usr/lib/cgi-bin/reboot.pl"])

@app.route("/", methods=["GET", "POST"])
def index():
    message = None
    if request.method == "POST":
        ssid = request.form["ssid"]
        password = request.form["password"]

        # Get existing profiles
        existing = subprocess.run(
            ["nmcli", "-t", "-f", "NAME", "connection", "show"],
            capture_output=True, text=True
        )
        existing_profiles = existing.stdout.splitlines()

        try:
            if ssid in existing_profiles:
                subprocess.run(
                    ["nmcli", "connection", "modify", ssid, "wifi-sec.psk", password],
                    check=True
                )
            else:
                subprocess.run([
                    "nmcli", "connection", "add", "type", "wifi", "ifname", "wlan0",
                    "con-name", ssid, "ssid", ssid,
                    "wifi-sec.key-mgmt", "wpa-psk", "wifi-sec.psk", password
                ], check=True)

            subprocess.run(["nmcli", "connection", "up", ssid], check=True)
            time.sleep(5)
            connected = check_wifi_connection()
            if connected == ssid:
                message = f"Connected to {ssid}. The setup server will shut down shortly."
                subprocess.run(["nmcli", "connection", "down", "HOTSPOT"], check=False)
                set_led(False)  # Turn LED off when Wi-Fi connects
            else:
                message = f"Failed to connect to {ssid}."
        except subprocess.CalledProcessError:
            message = "Error configuring Wi-Fi."

    return render_template_string(html_form, message=message)

if __name__ == "__main__":
    set_led(True)
    # Start timeout monitor thread
    threading.Thread(target=monitor_wifi_and_timeout, daemon=True).start()
    app.run(host="0.0.0.0", port=80)
```
Ctrl x

The next thing to do is setup a service that runs at boot and starts /home/user/wificonfig.py
**nano /etc/systemd/system/wificonfig.service**
```
[Unit]
Description=Wi-Fi Setup Flask Server
After=network.target
Wants=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/home/hans
ExecStart=/usr/bin/python3 /home/hans/wificonfig.py
Restart=no
# Make sure service is killed cleanly if something hangs
TimeoutStopSec=5
KillMode=process

[Install]
WantedBy=multi-user.target
```
Ctrl x
we need to enable the service
**systemctl daemon-reload**
**systemctl enable wificonfig.service**
**systemctl start wificonfig.service**

and finally we need a script that reboots the raspberry when the portal times out (after 5 minutes)
**nano /usr/lib/cgi-bin/reboot.pl**
```
 #!/usr/bin/perl
 use strict;
 use warnings;

 use CGI;
 print CGI::header();
 print "";
 print "<html>";
 print "<head>";

 print "</head>";
 print "<body><span style='font-size:12px; font-family: arial;'>";

 $| = 1;

 my $rebootcmd = "sudo /sbin/reboot";
 print "<br>system going to reboot...<br>\n";
 print "\n<br> WARNING: this may take some time !";
 print "\n<br> the ECU is not reponsive during this time !";
 #sleep(5);
  system($rebootcmd);
 print "\n\n<h3>after a minute, click \"X\" (right above)</h3>";

 print "HTTP/1.1 200 OK";
```
make this script executable **chmod +x /usr/lib/cgi-bin/reboot.pl**

## test
run ./wificonfig.py from the commandline to check for errors. 
check if the service is running **systemctl status wificonfig.service**

## additional server
If you don't have another server in your system, you can point the last line in wificonfig.py to port 5000 instead of 80
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
