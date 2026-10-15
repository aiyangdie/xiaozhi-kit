---
name: xiaozhi-kit
description: Drive ESP32 Xiaozhi boards via xzkit CLI (serial status, logs, reset, SoftAP provision). Use when debugging Xiaozhi/ESP32 serial, COM ports, WiFi provisioning, MQTT/OTA from device logs.
---

# Xiaozhi Kit Skill

Use the **`xzkit`** CLI. Prefer `--json`. Never open an infinite serial monitor.

## Rules

1. Run `xzkit doctor --json` before other serial commands.
2. Bound all reads: `-t` / `--timeout` (default seconds, never hang).
3. If exit code `2`, tell the user to close 安信可串口调试助手 / other monitors / Web console.
4. You cannot hear the mic or speak to the device — only serial logs and text send.
5. This is not an AT modem toolkit; Xiaozhi uses application log lines (`STATE:`, `MQTT:`, `>>`/`<<`).

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | OK |
| 1 | Unhealthy / crash in sample |
| 2 | Port missing / busy |
| 3 | Wait timeout |
| 4 | Missing dependency |
| 5 | Bad usage |

## Command templates

```bash
xzkit doctor --json
xzkit list --json
xzkit status -p COM3 -t 8 --json
xzkit read -p COM3 -t 15 --json
xzkit wait -p COM3 "Device is ready" -t 60 --json
xzkit send -p COM3 "ping" --json
xzkit reset -p COM3 --json
xzkit provision status -p COM3 --json
xzkit provision open -p COM3 --json
xzkit preset list --json
xzkit parse path/to/log.txt --json
xzkit service list --json
xzkit service run mqtt_probe --endpoint host:1883 --json
xzkit serve -p COM3
```

## Log cues

- SoftAP: `Access Point started with SSID Zhp-XXXX`, `http://192.168.4.1`, `STATE: configuring`
- Online: `Got IP`, `MQTT: Connected`, `Device is ready!`
- Crash: `ESP_ERROR_CHECK failed`, `abort()`, `Backtrace:`, `ESP_ERR_WIFI_NOT_STARTED`
- Noise (not panic): `USB_UART_CHIP_RESET` / `usb_serial_jtag`

## Install

```bash
pip install -e /path/to/xiaozhi-kit
# copy this folder to ~/.cursor/skills/xiaozhi-kit/
```
