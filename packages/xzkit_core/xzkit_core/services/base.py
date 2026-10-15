from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class ServiceResult:
    ok: bool
    name: str
    data: dict[str, Any] = field(default_factory=dict)
    hints: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Service(ABC):
    name: str = "base"
    description: str = ""

    @abstractmethod
    def run(self, **kwargs: Any) -> ServiceResult:
        raise NotImplementedError
