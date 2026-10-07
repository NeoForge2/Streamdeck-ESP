from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from .core.device import DeviceCapability, DeviceDescriptor, DisplaySpec
from .core.protocol import MessageType, ProtocolMessage

ProtocolReceiver = Callable[[ProtocolMessage], None]


@dataclass(slots=True)
class VirtualDeviceFaults:
    drop_responses_for: set[MessageType] = field(default_factory=set)
    error_responses_for: set[MessageType] = field(default_factory=set)


class VirtualStreamdeckDevice:
    """Deterministic DevicePort implementation for software-only E2E tests."""

    def __init__(self, *, faults: VirtualDeviceFaults | None = None) -> None:
        self._connected = True
        self._receiver: ProtocolReceiver | None = None
        self.faults = faults or VirtualDeviceFaults()
        self.sent_messages: list[ProtocolMessage] = []
        self.profile_id: str | None = None
        self.page_id: str | None = None
        self.buttons: dict[int, dict[str, object]] = {}
        self.widgets: dict[int, dict[str, object]] = {}
        self.states: dict[str, dict[str, object]] = {}

    @property
    def descriptor(self) -> DeviceDescriptor:
        return DeviceDescriptor(
            id="virtual-streamdeck",
            name="Virtual Streamdeck",
            model="virtual-1024x600-3e",
            display=DisplaySpec(1024, 600),
            encoder_count=3,
            button_count=36,
            capabilities=frozenset(
                {
                    DeviceCapability.DISPLAY,
                    DeviceCapability.TOUCH,
                    DeviceCapability.ENCODERS,
                    DeviceCapability.BUTTONS,
                }
            ),
        )

    @property
    def connected(self) -> bool:
        return self._connected

    def connect(self) -> None:
        self._connected = True

    def disconnect(self) -> None:
        self._connected = False

    def set_receiver(self, receiver: ProtocolReceiver | None) -> None:
        self._receiver = receiver

    def send(self, message: ProtocolMessage) -> None:
        if not self._connected:
            raise ConnectionError("virtual device is disconnected")
        self.sent_messages.append(message)
        self._apply(message)
        if message.type in (MessageType.ACK, MessageType.ERROR):
            return
        if message.type in self.faults.drop_responses_for:
            return
        if self._receiver is None:
            return
        if message.type in self.faults.error_responses_for:
            self._receiver(message.error("virtual_error", "injected virtual-device failure"))
            return
        self._receiver(message.ack({"device_id": self.descriptor.id}))

    def emit_button(self, slot_index: int, *, hold: bool = False) -> ProtocolMessage:
        message = ProtocolMessage(
            MessageType.BUTTON_HOLD if hold else MessageType.BUTTON_PRESS,
            {"slot_index": slot_index},
        )
        self._emit(message)
        return message

    def emit_encoder(self, encoder_index: int, *, direction: str | None = None) -> ProtocolMessage:
        if direction is None:
            message = ProtocolMessage(MessageType.ENCODER_PRESS, {"encoder_index": encoder_index})
        else:
            if direction not in {"cw", "ccw"}:
                raise ValueError("direction must be 'cw' or 'ccw'")
            message = ProtocolMessage(
                MessageType.ENCODER_ROTATE,
                {"encoder_index": encoder_index, "direction": direction},
            )
        self._emit(message)
        return message

    def emit_touch(self, x: int, y: int) -> ProtocolMessage:
        message = ProtocolMessage(MessageType.TOUCH, {"x": x, "y": y})
        self._emit(message)
        return message

    def _emit(self, message: ProtocolMessage) -> None:
        if not self._connected:
            raise ConnectionError("virtual device is disconnected")
        if self._receiver is not None:
            self._receiver(message)

    def _apply(self, message: ProtocolMessage) -> None:
        payload = dict(message.payload)
        if message.type == MessageType.SET_PROFILE:
            self.profile_id = self._string(payload, "profile_id")
        elif message.type == MessageType.SET_PAGE:
            self.page_id = self._string(payload, "page_id")
        elif message.type == MessageType.SET_BUTTON:
            self.buttons[self._slot(payload)] = payload
        elif message.type == MessageType.SET_WIDGET:
            self.widgets[self._slot(payload)] = payload
        elif message.type == MessageType.UPDATE_STATE:
            key = self._string(payload, "key")
            self.states[key] = payload
        elif message.type in {MessageType.SYNC, MessageType.PING}:
            return

    @staticmethod
    def _slot(payload: dict[str, object]) -> int:
        value = payload.get("slot_index")
        if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value < 36:
            raise ValueError("slot_index must be an integer in [0, 35]")
        return value

    @staticmethod
    def _string(payload: dict[str, object], key: str) -> str:
        value = payload.get(key)
        if not isinstance(value, str) or not value:
            raise ValueError(f"{key} must be a non-empty string")
        return value
