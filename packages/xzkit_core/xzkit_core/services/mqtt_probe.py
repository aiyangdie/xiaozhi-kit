"""TCP reachability check for MQTT broker (no MQTT client login)."""

from __future__ import annotations

import socket
from typing import Any

from .base import Service, ServiceResult


class MqttProbeService(Service):
    name = "mqtt_probe"
    description = "TCP connect probe to MQTT host:port from logs or args"

    def run(self, **kwargs: Any) -> ServiceResult:
        host = kwargs.get("host")
        port = kwargs.get("port")
        endpoint = kwargs.get("endpoint")
        if endpoint and ":" in str(endpoint):
            host, port_s = str(endpoint).rsplit(":", 1)
            port = int(port_s)
        if not host or not port:
            return ServiceResult(
                ok=False,
                name=self.name,
                error="Need host+port or endpoint like host:1883",
                hints=["Pass --endpoint from device mqtt_endpoint, e.g. botelv115200.com:1883"],
            )
        port = int(port)
        timeout = float(kwargs.get("timeout") or 3.0)
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return ServiceResult(
                    ok=True,
                    name=self.name,
                    data={"host": host, "port": port, "reachable": True, "timeout": timeout},
                    hints=["TCP open. MQTT login/auth is not verified."],
                )
        except OSError as e:
            return ServiceResult(
                ok=False,
                name=self.name,
                data={"host": host, "port": port, "reachable": False, "timeout": timeout},
                error=str(e),
                hints=["Broker unreachable from this PC (firewall/DNS/network)."],
            )
