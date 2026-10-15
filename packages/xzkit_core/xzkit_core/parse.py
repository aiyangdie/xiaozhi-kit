"""Parse Xiaozhi / ESP-IDF serial log lines into structured events."""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

STATE_RE = re.compile(r"STATE:\s*(\w+)", re.I)
MQTT_RE = re.compile(r"MQTT:\s*(.+)")
IP_RE = re.compile(r"(?:Got IP:|sta ip:)\s*([\d.]+)", re.I)
SSID_RE = re.compile(
    r"(?:Found AP:|connected with|Connecting to WiFi|Access Point started with SSID)\s+([^\s,]+)",
    re.I,
)
SOFTAP_RE = re.compile(
    r"(?:Access Point started with SSID|SoftAP|hotspot)\s*:?\s*([A-Za-z0-9_-]+)",
    re.I,
)
AP_URL_RE = re.compile(r"https?://192\.168\.4\.1\S*", re.I)
DIALOG_RE = re.compile(r"Application:\s*(<<|>>)\s*(.+)")
READY_RE = re.compile(r"Device is ready!", re.I)
CRASH_RE = re.compile(
    r"ESP_ERROR_CHECK failed|abort\(\)\s+was called|Guru Meditation|Backtrace:",
    re.I,
)
# Distinguish USB chip reset chatter from real panic
USB_RESET_RE = re.compile(r"USB_UART_CHIP_RESET|usb_serial_jtag", re.I)
RESET_RE = re.compile(r"rst:(0x[0-9a-fA-F]+)\s*\(([^)]+)\)")
VERSION_RE = re.compile(r"App version:\s*(\S+)")
PROJECT_RE = re.compile(r"Project name:\s*(\S+)")
UUID_RE = re.compile(r"UUID:\s*([0-9a-fA-F-]{36})")
OTA_RE = re.compile(r"Ota:\s*(.+)")
OTA_HOST_RE = re.compile(r"(\d{1,3}(?:\.\d{1,3}){3}):(\d+)")
MQTT_HOST_RE = re.compile(
    r"(?:mqtt[s]?://)?([a-zA-Z0-9.-]+):(\d+)",
    re.I,
)
WIFI_NOT_STARTED_RE = re.compile(r"ESP_ERR_WIFI_NOT_STARTED", re.I)


@dataclass
class DeviceSnapshot:
    project: str | None = None
    version: str | None = None
    uuid: str | None = None
    ssid: str | None = None
    softap_ssid: str | None = None
    ap_url: str | None = None
    ip: str | None = None
    mqtt: str | None = None
    mqtt_endpoint: str | None = None
    state: str | None = None
    ready: bool = False
    crash: bool = False
    usb_reset_noise: bool = False
    last_reset: str | None = None
    ota: str | None = None
    ota_endpoint: str | None = None
    provision: str | None = None  # unprovisioned | configuring | connected | unknown
    dialog: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    lines_seen: int = 0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def decode_line(raw: bytes) -> str:
    for enc in ("utf-8", "gbk", "latin-1"):
        try:
            return raw.decode(enc).rstrip("\r\n")
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace").rstrip("\r\n")


def classify(line: str) -> str | None:
    if USB_RESET_RE.search(line) and not CRASH_RE.search(line):
        return "usb_reset"
    if CRASH_RE.search(line) or WIFI_NOT_STARTED_RE.search(line):
        return "crash"
    if READY_RE.search(line):
        return "ready"
    if DIALOG_RE.search(line):
        return "dialog"
    if STATE_RE.search(line):
        return "state"
    if SOFTAP_RE.search(line) or AP_URL_RE.search(line) or "configuring" in line.lower():
        return "provision"
    if "Got IP" in line or "MQTT: Connected" in line:
        return "net"
    if RESET_RE.search(line):
        return "reset"
    return None


def _infer_provision(snap: DeviceSnapshot) -> str:
    state = (snap.state or "").lower()
    if state == "configuring" or snap.softap_ssid or snap.ap_url:
        if snap.ip and snap.ip != "192.168.4.1" and snap.mqtt == "connected":
            return "connected"
        return "configuring"
    if snap.ip and snap.mqtt == "connected":
        return "connected"
    if snap.ip:
        return "connected"
    if snap.ready and not snap.ip:
        return "unprovisioned"
    if snap.ssid and not snap.ip:
        return "configuring"
    return "unknown"


def update_snapshot(snap: DeviceSnapshot, line: str) -> str | None:
    snap.lines_seen += 1
    tag = classify(line)
    if tag:
        snap.tags.append(tag)

    m = PROJECT_RE.search(line)
    if m:
        snap.project = m.group(1)
    m = VERSION_RE.search(line)
    if m:
        snap.version = m.group(1)
    m = UUID_RE.search(line)
    if m:
        snap.uuid = m.group(1)
    m = STATE_RE.search(line)
    if m:
        snap.state = m.group(1)
    m = IP_RE.search(line)
    if m:
        snap.ip = m.group(1)
    m = SSID_RE.search(line)
    if m:
        ssid = m.group(1)
        if ssid.upper().startswith("ZHP-") or "Access Point started" in line:
            snap.softap_ssid = ssid
        else:
            snap.ssid = ssid
    m = SOFTAP_RE.search(line)
    if m:
        snap.softap_ssid = m.group(1)
    m = AP_URL_RE.search(line)
    if m:
        snap.ap_url = m.group(0).rstrip(".,;)")
    elif "192.168.4.1" in line and not snap.ap_url:
        snap.ap_url = "http://192.168.4.1"

    if "MQTT: Connected" in line:
        snap.mqtt = "connected"
    else:
        m = MQTT_RE.search(line)
        if m and "Connecting" not in m.group(1):
            snap.mqtt = m.group(1).strip()
        mh = MQTT_HOST_RE.search(line)
        if mh and "mqtt" in line.lower():
            snap.mqtt_endpoint = f"{mh.group(1)}:{mh.group(2)}"

    if READY_RE.search(line):
        snap.ready = True
    if USB_RESET_RE.search(line) and not CRASH_RE.search(line):
        snap.usb_reset_noise = True
    if CRASH_RE.search(line) or WIFI_NOT_STARTED_RE.search(line):
        snap.crash = True
    m = RESET_RE.search(line)
    if m:
        snap.last_reset = f"{m.group(1)} ({m.group(2)})"
    m = OTA_RE.search(line)
    if m:
        snap.ota = m.group(1).strip()
        oh = OTA_HOST_RE.search(snap.ota)
        if oh:
            snap.ota_endpoint = f"{oh.group(1)}:{oh.group(2)}"
    m = DIALOG_RE.search(line)
    if m:
        snap.dialog.append(f"{m.group(1)} {m.group(2).strip()}")
        if len(snap.dialog) > 20:
            snap.dialog = snap.dialog[-20:]

    snap.provision = _infer_provision(snap)
    return tag


def parse_text(text: str) -> tuple[list[str], DeviceSnapshot]:
    """Parse pasted / file log text into lines + snapshot."""
    snap = DeviceSnapshot()
    lines: list[str] = []
    for raw in text.splitlines():
        line = raw.rstrip("\r\n")
        if not line:
            continue
        update_snapshot(snap, line)
        lines.append(line)
    return lines, snap
