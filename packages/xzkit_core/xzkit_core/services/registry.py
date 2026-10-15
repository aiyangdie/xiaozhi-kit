from __future__ import annotations

from typing import Type

from .base import Service
from .health import HealthService
from .mqtt_probe import MqttProbeService
from .ota_probe import OtaProbeService
from .provision_assist import ProvisionAssistService

SERVICE_REGISTRY: dict[str, Type[Service]] = {
    HealthService.name: HealthService,
    ProvisionAssistService.name: ProvisionAssistService,
    MqttProbeService.name: MqttProbeService,
    OtaProbeService.name: OtaProbeService,
}


def list_services() -> list[dict[str, str]]:
    return [
        {"name": cls.name, "description": cls.description}
        for cls in SERVICE_REGISTRY.values()
    ]


def get_service(name: str) -> Service:
    cls = SERVICE_REGISTRY.get(name)
    if not cls:
        raise KeyError(f"Unknown service: {name}. Known: {', '.join(SERVICE_REGISTRY)}")
    return cls()
