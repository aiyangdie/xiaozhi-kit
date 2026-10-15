# CLI

Entry point: `xzkit`. Always prefer `--json` for agents.

## Commands

| Command | Purpose |
|---------|---------|
| `list` | Enumerate COM / tty ports |
| `doctor` | Deps + openability check |
| `status` | Sample logs, health + provision summary |
| `read` | Capture N seconds of logs |
| `wait PATTERN` | Wait until regex matches |
| `send TEXT` | Write one line |
| `reset` | DTR/RTS reset (`--bootloader`) |
| `provision status\|open` | SoftAP / WiFi assist |
| `preset list\|run NAME` | Named shortcuts |
| `parse FILE` | Offline log parse |
| `service list\|run NAME` | Plugins (health, mqtt_probe, ota_probe…) |
| `serve` | Local Web UI |

## Exit codes

`0` ok · `1` crash/unhealthy · `2` port · `3` timeout · `4` dep · `5` usage
