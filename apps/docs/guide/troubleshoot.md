# Troubleshooting

## Port busy (exit 2)

Close 安信可串口调试助手, Arduino Serial Monitor, another `xzkit serve`, or other tools.

## SoftAP portal won't open on PC

Connect the PC to `Zhp-XXXX`. If only the phone joins the SoftAP, open `http://192.168.4.1` on the phone.

## USB reset vs crash

`USB_UART_CHIP_RESET` alone is noise. Real faults show `ESP_ERROR_CHECK failed` / `abort()` / `Backtrace:`.

## MQTT / OTA

```bash
xzkit status --json   # read mqtt_endpoint / ota_endpoint
xzkit service run mqtt_probe --endpoint host:1883 --json
xzkit service run ota_probe --endpoint ip:port --json
```

These only TCP-probe reachability; they do not log in or flash firmware.
