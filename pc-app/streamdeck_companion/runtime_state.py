"""Shared V2 runtime state for the companion application.

The store lives in the application layer so existing producers (Home Assistant,
device connection, audio, plugins) can migrate independently while consuming
the same source of truth. The Core only defines ``StateStore`` itself.
"""

from .core import StateStore

STATE_STORE = StateStore()
