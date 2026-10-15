"""Pluggable read-only / assist services for Xiaozhi Kit."""

from .base import Service, ServiceResult
from .health import HealthService
from .mqtt_probe import MqttProbeService
from .ota_probe import OtaProbeService
from .provision_assist import ProvisionAssistService
from .registry import SERVICE_REGISTRY, get_service, list_services

__all__ = [
    "Service",
    "ServiceResult",
    "HealthService",
    "MqttProbeService",
    "OtaProbeService",
    "ProvisionAssistService",
    "SERVICE_REGISTRY",
    "get_service",
    "list_services",
]
