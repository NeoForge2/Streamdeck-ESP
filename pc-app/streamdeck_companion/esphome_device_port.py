"""ESPHome-backed DevicePort for the current Streamdeck-ESP hardware.

This adapter exposes the existing runtime through the transport-neutral V2
DevicePort contract. It supports only protocol messages that can be projected
safely onto current runtime semantics; unsupported messages fail explicitly.
"""

from __future__ import annotations

from collections.abc import Callable

from .core.device import DeviceCapability, DeviceDescriptor, DevicePort, DisplaySpec
from .core.protocol import MessageType, ProtocolMessage


STREAMDECK_ESP_DESCRIPTOR = DeviceDescriptor(
    id="streamdeck-esp",
    name="Streamdeck-ESP",
    model="ESP32-P4/C6 7in",
    display=DisplaySpec(width=1024, height=600),
    encoder_count=3,
    capabilities=frozenset(
        {
            DeviceCapability.DISPLAY,
            DeviceCapability.TOUCH,
            DeviceCapability.ENCODERS,
        }
    ),
)


class UnsupportedDeviceMessageError(ValueError):
    """Raised when the legacy ESPHome transport cannot represent a V2 message."""


PayloadSender = Callable[[dict[str, object]], None]
AckSender = Callable[[str], None]


class ESPHomeDevicePort(DevicePort):
    """Expose a live DeviceClient through the V2 DevicePort contract."""

    def __init__(
        self,
        device_client: object,
        *,
        state_sender: PayloadSender | None = None,
        sync_sender: Callable[[], None] | None = None,
        profile_sender: PayloadSender | None = None,
        page_sender: PayloadSender | None = None,
        button_sender: PayloadSender | None = None,
        widget_sender: PayloadSender | None = None,
        ack_sender: AckSender | None = None,
    ) -> None:
        self._device_client = device_client
        self._state_sender = state_sender
        self._sync_sender = sync_sender
        self._profile_sender = profile_sender
        self._page_sender = page_sender
        self._button_sender = button_sender
        self._widget_sender = widget_sender
        self._ack_sender = ack_sender

    @property
    def descriptor(self) -> DeviceDescriptor:
        return STREAMDECK_ESP_DESCRIPTOR

    @property
    def connected(self) -> bool:
        return bool(getattr(self._device_client, "connected", False))

    def send(self, message: ProtocolMessage) -> None:
        """Project supported V2 messages onto the current runtime.

        Control/configuration messages are acknowledged only after their local
        projection succeeds. UPDATE_STATE remains intentionally unacknowledged
        because it can be high-frequency telemetry rather than a command.
        """
        payload = dict(message.payload)

        if message.type == MessageType.UPDATE_STATE:
            self._send_payload(self._state_sender, message.type, payload)
            return

        if message.type == MessageType.SET_PROFILE:
            self._send_payload(self._profile_sender, message.type, payload)
            self._ack(message.message_id)
            return

        if message.type == MessageType.SET_PAGE:
            self._send_payload(self._page_sender, message.type, payload)
            self._ack(message.message_id)
            return

        if message.type == MessageType.SET_BUTTON:
            self._send_payload(self._button_sender, message.type, payload)
            self._ack(message.message_id)
            return

        if message.type == MessageType.SET_WIDGET:
            self._send_payload(self._widget_sender, message.type, payload)
            self._ack(message.message_id)
            return

        if message.type == MessageType.SYNC:
            if self._sync_sender is None:
                raise UnsupportedDeviceMessageError("SYNC sender is not configured")
            self._sync_sender()
            self._ack(message.message_id)
            return

        if message.type == MessageType.PING:
            if self._ack_sender is None:
                raise UnsupportedDeviceMessageError("PING requires the V2 acknowledgement channel")
            self._ack(message.message_id)
            return

        raise UnsupportedDeviceMessageError(
            f"message {message.type.value!r} is not supported by the current ESPHome transport"
        )

    def _ack(self, message_id: str) -> None:
        # Older firmware has no acknowledgement entity. Keep configuration
        # commands backward compatible; callers that request a response will
        # then naturally exercise timeout/retry through ProtocolSession.
        if self._ack_sender is not None:
            self._ack_sender(message_id)

    @staticmethod
    def _send_payload(sender: PayloadSender | None, message_type: MessageType, payload: dict[str, object]) -> None:
        if sender is None:
            raise UnsupportedDeviceMessageError(f"{message_type.value} sender is not configured")
        sender(payload)
