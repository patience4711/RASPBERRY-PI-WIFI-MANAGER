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