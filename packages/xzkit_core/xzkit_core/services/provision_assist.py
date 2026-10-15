from __future__ import annotations

from typing import Any

from ..provision import open_portal, sample_provision
from .base import Service, ServiceResult


class ProvisionAssistService(Service):
    name = "provision"
    description = "Detect SoftAP / WiFi provision state from serial logs"

    def run(self, **kwargs: Any) -> ServiceResult:
        action = kwargs.get("action") or "status"
        if action == "open":
            data = open_portal(kwargs.get("url"))
            return ServiceResult(
                ok=bool(data.get("ok")),
                name=self.name,
                data=data,
                hints=list(data.get("hints") or []),
                error=data.get("error"),
            )
        data = sample_provision(
            port=kwargs.get("port"),
            baud=int(kwargs.get("baud") or 115200),
            seconds=float(kwargs.get("seconds") or 10.0),
        )
        return ServiceResult(
            ok=True,
            name=self.name,
            data=data,
            hints=list(data.get("hints") or []),
        )
