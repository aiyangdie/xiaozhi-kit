"""Provision assist: detect SoftAP / configuring / connected from logs."""

from __future__ import annotations

import webbrowser
from typing import Any

from .parse import DeviceSnapshot
from .serial_io import PortError, pick_port, read_for


def provision_status_from_snap(snap: DeviceSnapshot) -> dict[str, Any]:
    status = snap.provision or "unknown"
    hints: list[str] = []
    if status == "configuring":
        hints.append(
            "Device SoftAP is up. Connect phone/PC to the hotspot, then open "
            f"{snap.ap_url or 'http://192.168.4.1'}."
        )
        if snap.softap_ssid:
            hints.append(f"SoftAP SSID: {snap.softap_ssid}")
        hints.append(
            "If you use phone-only hotspot, open the portal on the phone browser; "
            "this PC may not reach 192.168.4.1."
        )
    elif status == "connected":
        hints.append("WiFi looks connected.")
        if snap.ip:
            hints.append(f"STA IP: {snap.ip}")
        if snap.mqtt:
            hints.append(f"MQTT: {snap.mqtt}")
    elif status == "unprovisioned":
        hints.append("Device ready but no STA IP yet. Enter WiFi config mode on the board.")
    else:
        hints.append("Could not infer provision state. Capture more logs with: xzkit status -t 15")

    return {
        "ok": True,
        "status": status,
        "softap_ssid": snap.softap_ssid,
        "ap_url": snap.ap_url or ("http://192.168.4.1" if status == "configuring" else None),
        "ssid": snap.ssid,
        "ip": snap.ip,
        "mqtt": snap.mqtt,
        "state": snap.state,
        "hints": hints,
    }


def sample_provision(
    port: str | None = None,
    baud: int = 115200,
    seconds: float = 10.0,
) -> dict[str, Any]:
    chosen = port or pick_port(esp_only=True) or pick_port()
    if not chosen:
        raise PortError("No serial ports found. Plug in the board.")
    _lines, snap = read_for(chosen, baud, seconds)
    payload = provision_status_from_snap(snap)
    payload["port"] = chosen
    payload["baud"] = baud
    payload["device"] = snap.to_dict()
    return payload


def open_portal(url: str | None = None) -> dict[str, Any]:
    target = url or "http://192.168.4.1"
    try:
        opened = webbrowser.open(target)
    except Exception as e:  # noqa: BLE001
        return {
            "ok": False,
            "url": target,
            "opened": False,
            "error": str(e),
            "hints": [
                "Open the URL manually on a device connected to the SoftAP.",
                "Phone-only hotspot: use the phone browser, not this PC.",
            ],
        }
    return {
        "ok": opened,
        "url": target,
        "opened": opened,
        "hints": [
            "Browser open requested. Ensure this machine is connected to the SoftAP "
            "(e.g. Zhp-XXXX), otherwise the page will not load.",
            "If SoftAP is phone-only, open the portal on the phone instead.",
        ],
    }
