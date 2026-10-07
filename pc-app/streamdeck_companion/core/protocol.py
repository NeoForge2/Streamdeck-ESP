"""Versioned transport-neutral protocol primitives for PC <-> device messages.

The existing ESPHome transport remains untouched during the P0 migration. This
module defines the contract that future adapters can serialize over ESPHome,
WebSocket, MQTT, USB or another device transport without coupling the Core to
any of them.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping
from uuid import uuid4

PROTOCOL_VERSION = 1


class ProtocolError(ValueError):
    """Raised when a protocol message is malformed or incompatible."""


class MessageType(str, Enum):
    # PC -> device
    SET_PROFILE = "set_profile"
    SET_PAGE = "set_page"
    SET_BUTTON = "set_button"
    SET_WIDGET = "set_widget"
    UPDATE_STATE = "update_state"
    SYNC = "sync"
    PING = "ping"

    # Device -> PC
    BUTTON_PRESS = "button_press"
    BUTTON_HOLD = "button_hold"
    TOUCH = "touch"
    ENCODER_ROTATE = "encoder_rotate"
    ENCODER_PRESS = "encoder_press"
    DEVICE_STATUS = "device_status"

    # Bidirectional protocol control
    ACK = "ack"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ProtocolMessage:
    """Transport-neutral protocol envelope.

    ``reply_to`` links ACK/ERROR responses to the original message. ``payload``
    intentionally stays generic because validation of message-specific fields
    belongs to higher-level schemas/adapters added progressively.
    """

    type: MessageType
    payload: Mapping[str, Any] = field(default_factory=dict)
    message_id: str = field(default_factory=lambda: uuid4().hex)
    protocol_version: int = PROTOCOL_VERSION
    reply_to: str | None = None

    def __post_init__(self) -> None:
        if not self.message_id:
            raise ProtocolError("message_id cannot be empty")
        if self.protocol_version <= 0:
            raise ProtocolError("protocol_version must be positive")
        if not isinstance(self.payload, Mapping):
            raise ProtocolError("payload must be a mapping")
        if self.type in (MessageType.ACK, MessageType.ERROR) and not self.reply_to:
            raise ProtocolError(f"{self.type.value} requires reply_to")

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "protocol_version": self.protocol_version,
            "message_id": self.message_id,
            "type": self.type.value,
            "payload": dict(self.payload),
        }
        if self.reply_to is not None:
            data["reply_to"] = self.reply_to
        return data

    @classmethod
    def from_dict(cls, data: Mapping[str, Any], *, supported_version: int = PROTOCOL_VERSION) -> "ProtocolMessage":
        if not isinstance(data, Mapping):
            raise ProtocolError("message must be a mapping")
        version = data.get("protocol_version")
        if version != supported_version:
            raise ProtocolError(
                f"unsupported protocol_version {version!r}; expected {supported_version}"
            )
        try:
            message_type = MessageType(data.get("type"))
        except (TypeError, ValueError) as exc:
            raise ProtocolError(f"unknown message type: {data.get('type')!r}") from exc
        return cls(
            type=message_type,
            payload=data.get("payload") or {},
            message_id=str(data.get("message_id") or ""),
            protocol_version=version,
            reply_to=data.get("reply_to"),
        )

    def ack(self, payload: Mapping[str, Any] | None = None) -> "ProtocolMessage":
        return ProtocolMessage(
            MessageType.ACK,
            payload or {},
            reply_to=self.message_id,
            protocol_version=self.protocol_version,
        )

    def error(self, code: str, message: str, *, details: Mapping[str, Any] | None = None) -> "ProtocolMessage":
        if not code:
            raise ProtocolError("error code cannot be empty")
        payload: dict[str, Any] = {"code": code, "message": message}
        if details:
            payload["details"] = dict(details)
        return ProtocolMessage(
            MessageType.ERROR,
            payload,
            reply_to=self.message_id,
            protocol_version=self.protocol_version,
        )


def ping() -> ProtocolMessage:
    """Build a protocol-level liveness request."""
    return ProtocolMessage(MessageType.PING)


def sync(payload: Mapping[str, Any]) -> ProtocolMessage:
    """Build a full/incremental state synchronization request."""
    return ProtocolMessage(MessageType.SYNC, payload)
