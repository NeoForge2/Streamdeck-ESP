# Streamdeck-ESP

DIY touchscreen macro controller built with **ESP32-P4 / ESP32-C6**, **ESPHome**, **LVGL**, rotary encoders and a **Python companion application**.

The project runs on the **Guition JC1060P470C_I_W** 7" touchscreen and is designed as an open-source alternative to commercial macro pads, with native PC controls and optional Home Assistant integration.

> This project is under active development. Code reviews, architectural feedback, hardware testing and pull requests are very welcome.

## Features

- 7" 1024×600 touchscreen
- ESP32-P4 + ESP32-C6
- ESPHome + LVGL firmware
- 36 configurable button/widget slots
- 3 rotary encoders with rotation and push actions
- Python companion application
- Drag-and-drop layout editor
- Resizable widgets
- Multiple profiles
- Automatic profile switching based on the active PC application
- Keyboard shortcuts
- Media controls
- Application launcher
- Per-application volume control on Windows
- Real application icons
- Home Assistant entity and service control
- Live Home Assistant widgets
- Light color, brightness and temperature control
- MQTT support for faster Home Assistant updates
- Plugin architecture
- Automated tests and GitHub Actions CI

## Hardware

The current reference hardware is:

- **Guition JC1060P470C_I_W**
- ESP32-P4
- ESP32-C6
- GT911 touchscreen
- 3 rotary encoders

The current UI is designed for a 1024×600 display.

Wiring information is available in:

[`docs/WIRING.md`](docs/WIRING.md)

## Repository structure

```text
firmware/          ESPHome firmware and LVGL UI
pc-app/            Python companion application
home-assistant/    Home Assistant examples
docs/              Architecture, wiring and plugin documentation
scripts/           Firmware and UI generation utilities
