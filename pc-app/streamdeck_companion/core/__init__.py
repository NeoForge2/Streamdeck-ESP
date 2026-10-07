"""Core domain model for Streamdeck-ESP.

This package must stay independent from Flask, Windows, Home Assistant,
ESPHome and any concrete device or GUI implementation.
"""

from .actions import ActionCommand, ActionDefinition, ActionValidationError
from .device import DeviceCapability, DeviceDescriptor, DevicePort, DisplaySpec
from .engine import ActionEngine, MissingExecutorError
from .events import InputEvent, InputKind, TriggerBindings
from .navigation import Folder, GridRect, Page, Placement, Profile
from .protocol import MessageType, PROTOCOL_VERSION, ProtocolError, ProtocolMessage
from .registry import ActionRegistry, DuplicateActionError, UnknownActionError
from .state import StateStore, StateValue
from .triggers import ActionState, Trigger

__all__ = [
    "ActionCommand",
    "ActionDefinition",
    "ActionEngine",
    "ActionRegistry",
    "ActionState",
    "ActionValidationError",
    "DeviceCapability",
    "DeviceDescriptor",
    "DevicePort",
    "DisplaySpec",
    "DuplicateActionError",
    "Folder",
    "GridRect",
    "InputEvent",
    "InputKind",
    "MessageType",
    "MissingExecutorError",
    "PROTOCOL_VERSION",
    "Page",
    "Placement",
    "Profile",
    "ProtocolError",
    "ProtocolMessage",
    "StateStore",
    "StateValue",
    "Trigger",
    "TriggerBindings",
    "UnknownActionError",
]
