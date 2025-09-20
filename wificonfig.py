#!/usr/bin/env python3 
from flask import Flask, request, render_template_string
import subprocess
import time
import threading
import os

app = Flask(__name__)

CON_NAME = "HOTSPOT"
PORT = 8000

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
  <br><br><br><b>after submission, please browse to rpi-domo:8000
  <br>or rpi-domo.local:8000 to see the IP address</b>
  {% if message %}
  <p>{{ message }}</p>
  {% endif %}
</body>
</html>
"""
LED_PATH = "/sys/class/leds/ACT/brightness"

def log_debug(msg):
    """Append a message with timestamp to wifidebug.txt"""
    with open("/home/hans/wifidebug.txt", "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")

def set_led(state: bool):
    value = "1" if state else "0"
    try:
        with open(LED_PATH, "w") as f:
            f.write(value)
    except Exception as e:
        print(f"[WARN] Could not set LED: {e}")


def check_wifi_connection():
    """Return connection name if connected, None otherwise"""
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
    """Wait 5 minutes, then reboot if still not Wi-Fi connected"""
    log_debug("Monitor thread started. Waiting for 5 minutes.")
    time.sleep(300)  # 5 minutes
    print("[INFO] 5 minutes timed out.")

    #subprocess.run(["nmcli", "connection", "down", "HOTSPOT"], check=False)
    log_debug("5 minutes timeout reached.")

    # Check Wi-Fi connection
    conn_name = check_wifi_connection()
    #if not conn_name or conn_name == "HOTSPOT":
    if not conn_name or conn_name == CON_NAME:
        log_debug("Wi-Fi not connected after 5 minutes. Rebooting now...")
        print("[INFO] Wi-Fi not connected after 5 minutes, rebooting.")
        try:
            # Direct Python reboot
            subprocess.run(["systemctl", "reboot"], check=True)
            log_debug("Systemctl reboot command executed successfully.")
        except Exception as e:
            log_debug(f"Failed to execute reboot: {e}")
    else:
        log_debug("Wi-Fi connected ({conn_name}), no reboot needed.")
        print(f"[INFO] Wi-Fi connected ({conn_name}), no reboot needed.")

@app.route("/", methods=["GET", "POST"])
def index():
    conn_name = check_wifi_connection()
    if conn_name and conn_name != "HOTSPOT":
        return f"<center><h1>Raspberry Pi IP:</h1><p>{get_ip()}</p></center>"
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
                log_debug("a connection was made")
                #subprocess.run(["nmcli", "connection", "down", "HOTSPOT"], check=False)
                set_led(False)  # Turn LED off when Wi-Fi connects
            else:
                message = f"Failed to connect to {ssid}."
        except subprocess.CalledProcessError:
            message = "Error configuring Wi-Fi."

    return render_template_string(html_form, message=message)

def get_ip():
    import socket
    ip = "Unknown"
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
    except Exception:
        pass
    return ip

if __name__ == "__main__":

    #clear the log
    open("/home/hans/wifidebug.txt", "w").close()
    log_debug("* * * * * start wificonfig * * * * *")
    try:
        with open("/sys/class/leds/ACT/trigger", "w") as f:
            f.write("none")
    except Exception as e:
        print(f"[WARN] Could not disable LED trigger: {e}")

    # Wait a bit for Wi-Fi to initialize
    for _ in range(10):  # 10 attempts, 1 sec apart
        conn_name = check_wifi_connection()
        #if conn_name and conn_name != "HOTSPOT":
        if conn_name and conn_name != CON_NAME:
       
            set_led(False)
            log_debug("we were connected at start")
            break

        time.sleep(1)
    else:
        # Wi-Fi still not connected, keep LED on
        set_led(True)
        log_debug("we were not connected at start")

    # Start timeout monitor thread
    threading.Thread(target=monitor_wifi_and_timeout, daemon=True).start()
    #app.run(host="0.0.0.0", port=8000)
    app.run(host="0.0.0.0", port=PORT)
