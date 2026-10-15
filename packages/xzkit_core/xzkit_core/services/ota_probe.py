"""TCP reachability check for OTA HTTP host:port parsed from logs."""

from __future__ import annotations

import socket
from typing import Any

from .base import Service, ServiceResult


class OtaProbeService(Service):
    name = "ota_probe"
    description = "TCP connect probe to OTA host:port from logs or args"

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
                error="Need host+port or endpoint like 139.224.114.243:8002",
                hints=["Run xzkit status --json and use device.ota_endpoint"],
            )
        port = int(port)
        timeout = float(kwargs.get("timeout") or 3.0)
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return ServiceResult(
                    ok=True,
                    name=self.name,
                    data={"host": host, "port": port, "reachable": True, "timeout": timeout},
                    hints=["TCP open. OTA HTTP content/version is not fetched in v1."],
                )
        except OSError as e:
            return ServiceResult(
                ok=False,
                name=self.name,
                data={"host": host, "port": port, "reachable": False, "timeout": timeout},
                error=str(e),
                hints=["OTA host unreachable from this PC."],
            )
