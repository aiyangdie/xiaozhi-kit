from __future__ import annotations

from typing import Any

from ..serial_io import doctor, pick_port, read_for
from .base import Service, ServiceResult


class HealthService(Service):
    name = "health"
    description = "Aggregate doctor + short status sample"

    def run(self, **kwargs: Any) -> ServiceResult:
        port = kwargs.get("port")
        baud = int(kwargs.get("baud") or 115200)
        seconds = float(kwargs.get("seconds") or 6.0)
        doc = doctor(preferred_port=port, baud=baud)
        chosen = port or doc.get("suggested_port") or pick_port(esp_only=True)
        device = None
        if chosen and doc.get("preferred_openable") is not False:
            try:
                _lines, snap = read_for(str(chosen), baud, seconds)
                device = snap.to_dict()
            except Exception as e:  # noqa: BLE001
                return ServiceResult(
                    ok=False,
                    name=self.name,
                    data={"doctor": doc},
                    error=str(e),
                    hints=["Close other serial tools, then retry."],
                )
        ok = bool(doc.get("ok")) and not (device or {}).get("crash")
        return ServiceResult(
            ok=ok,
            name=self.name,
            data={"doctor": doc, "port": chosen, "device": device},
            hints=list(doc.get("hints") or []),
        )
