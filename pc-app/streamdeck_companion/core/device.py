"""Hardware-independent device contracts for Streamdeck-ESP V2."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol

from .protocol import ProtocolMessage


class DeviceCapability(str, Enum):
    DISPLAY = "display"
    TOUCH = "touch"
    ENCODERS = "encoders"
    BUTTONS = "buttons"
    HAPTICS = "haptics"
    AUDIO = "audio"


@dataclass(frozen=True, slots=True)
class DisplaySpec:
    width: int
    height: int

    def __post_init__(self) -> None:
        if self.width <= 0 or self.height <= 0:
            raise ValueError("display dimensions must be positive")


@dataclass(frozen=True, slots=True)
class DeviceDescriptor:
    """Capabilities advertised by a physical or virtual Streamdeck device."""

    id: str
    name: str
    model: str = ""
    display: DisplaySpec | None = None
    encoder_count: int = 0
    button_count: int = 0
    capabilities: frozenset[DeviceCapability] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        if not self.id:
            raise ValueError("device id cannot be empty")
        if not self.name:
            raise ValueError("device name cannot be empty")
        if self.encoder_count < 0 or self.button_count < 0:
            raise ValueError("device input counts cannot be negative")
        if self.display is not None and DeviceCapability.DISPLAY not in self.capabilities:
            raise ValueError("a display specification requires DISPLAY capability")
        if self.encoder_count and DeviceCapability.ENCODERS not in self.capabilities:
            raise ValueError("encoder_count requires ENCODERS capability")
        if self.button_count and DeviceCapability.BUTTONS not in self.capabilities:
            raise ValueError("button_count requires BUTTONS capability")

    def supports(self, capability: DeviceCapability) -> bool:
        return capability in self.capabilities


class DevicePort(Protocol):
    """Transport-neutral boundary implemented by concrete device adapters."""

    @property
    def descriptor(self) -> DeviceDescriptor: ...

    @property
    def connected(self) -> bool: ...

    def send(self, message: ProtocolMessage) -> None: ...
