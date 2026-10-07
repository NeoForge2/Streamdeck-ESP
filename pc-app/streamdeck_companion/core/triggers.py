"""Generic interaction and state primitives used by the Streamdeck Core."""

from __future__ import annotations

from enum import Enum


class Trigger(str, Enum):
    PRESS = "press"
    DOUBLE_PRESS = "double_press"
    HOLD = "hold"
    LONG_PRESS = "long_press"
    RELEASE = "release"
    ROTATE_CW = "rotate_cw"
    ROTATE_CCW = "rotate_ccw"


class ActionState(str, Enum):
    OFF = "off"
    ON = "on"
    ACTIVE = "active"
    INACTIVE = "inactive"
    LOADING = "loading"
    ERROR = "error"
    DISCONNECTED = "disconnected"
