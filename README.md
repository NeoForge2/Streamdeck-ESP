# Streamdeck-ESP

An open-source DIY Stream Deck built around the **Guition JC1060P470C_I_W**
7" touchscreen, **ESP32-P4 / ESP32-C6**, **ESPHome**, **LVGL**, rotary encoders
and a Python companion application.

The goal is to build a flexible and hackable alternative to commercial macro
pads, with native PC controls and optional Home Assistant integration.

> This project is under active development. Code reviews, architectural feedback,
> hardware testing and pull requests are very welcome.

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
- Automatic profile switching based on the active application
- Keyboard shortcuts and media controls
- Application launcher
- Per-application volume control on Windows
- Audio output switching
- Real application icons
- Optional Home Assistant integration
- Home Assistant live widgets and service calls
- Light, media player, fan, cover and climate controls
- MQTT support for faster Home Assistant updates
- Plugin architecture
- Automated tests and GitHub Actions CI

## Hardware

The current reference hardware is:

- Guition JC1060P470C_I_W
- ESP32-P4
- ESP32-C6
- GT911 touchscreen
- 3 rotary encoders

The UI currently targets a **1024×600** display.

See [`docs/WIRING.md`](docs/WIRING.md) for wiring information.

## Repository structure

```text
firmware/          ESPHome firmware and LVGL UI
pc-app/            Python companion application
home-assistant/    Home Assistant examples
docs/              Architecture, wiring and plugin documentation
scripts/           Firmware and UI generation utilities
```

## Architecture

The project is split into three main layers:

```text
┌──────────────────────────────┐
│       PC Companion App       │
│            Python            │
└──────────────┬───────────────┘
               │
               │ device protocol
               ▼
┌──────────────────────────────┐
│      ESP32-P4 / ESPHome      │
│           LVGL UI            │
└──────────────┬───────────────┘
               │
               │ optional
               ▼
┌──────────────────────────────┐
│       Home Assistant         │
│     REST / MQTT / ESPHome    │
└──────────────────────────────┘
```

The PC companion manages profiles, layouts, actions and dynamic data.

The ESP32 device handles the touchscreen interface, rotary encoders and
communication with the companion application.

Home Assistant is optional. The device can still be used as a PC macro
controller without it.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for more details.

## Quick start

### Firmware

Clone the repository:

```bash
git clone https://github.com/NeoForge2/Streamdeck-ESP.git
cd Streamdeck-ESP/firmware
```

Create your local secrets file:

```bash
cp secrets.yaml.example secrets.yaml
```

Fill it with your own:

- Wi-Fi SSID
- Wi-Fi password
- ESPHome API encryption key
- OTA password

Then install ESPHome and flash the device:

```bash
pip install esphome
esphome run streamdeck.yaml
```

> `secrets.yaml` is ignored by Git and must never be committed.

A Home Assistant ESPHome Builder example is also available:

[`firmware/ha-device.yaml.example`](firmware/ha-device.yaml.example)

### PC companion

```bash
cd pc-app
python -m venv .venv
```

Windows:

```powershell
.venv\Scripts\activate
```

Linux/macOS:

```bash
source .venv/bin/activate
```

Install the dependencies:

```bash
pip install -r requirements.txt
```

Run the companion application:

```bash
python -c "from streamdeck_companion.tray import main; main()"
```

For more information, see [`pc-app/README.md`](pc-app/README.md).

## Profiles

Each profile can have its own:

- button layout
- widgets
- encoder configuration
- application trigger

Profiles can automatically switch when a specific application becomes the
foreground window.

This makes it possible to automatically display different controls for OBS,
Discord, games or other applications.

## Home Assistant

Home Assistant integration is optional.

When configured, the companion application can use Home Assistant entities for
controls and live widgets.

The project currently supports use cases such as:

- lights
- media players
- fans
- covers
- climate entities
- numeric gauges
- text states
- service calls
- MQTT state updates

The ESPHome device can also be discovered natively by Home Assistant.

## Plugin system

The companion application contains a plugin architecture intended to make new
actions and integrations easier to add without tightly coupling them to the
core application.

See [`docs/PLUGIN_SDK.md`](docs/PLUGIN_SDK.md).

## Development

The PC companion currently targets **Python 3.11+**.

Development tooling includes:

- Ruff
- MyPy
- unittest
- coverage
- GitHub Actions

Run the complete test suite from `pc-app/`:

```bash
python -m unittest discover -s tests -v
```

Run Ruff:

```bash
ruff check streamdeck_companion
```

Run type checking on the core:

```bash
mypy streamdeck_companion/core
```

CI currently runs the test suite on Python **3.11 and 3.12**.

## Help wanted

This project would benefit greatly from experienced developers reviewing the
codebase.

Feedback and contributions are especially welcome around:

- ESPHome architecture
- ESP32-P4 / ESP32-C6
- LVGL performance
- firmware structure
- Python architecture and maintainability
- device protocol reliability
- plugin architecture
- Home Assistant integration
- Windows integration
- cross-platform support
- security
- automated testing
- real hardware testing
- documentation

If something looks badly designed, fragile, over-engineered or unnecessarily
complicated, please open an issue.

**Architectural criticism is welcome.**

The goal is not only to add features, but also to improve the overall quality,
reliability and maintainability of the project.

## Project status

This is an active hobby/open-source project and should not yet be considered a
finished commercial product.

Some functionality has been tested on real hardware while other parts still
need wider testing.

Real-device test reports are especially valuable.

## Contributing

Contributions are welcome.

You can help through:

- bug reports
- code reviews
- architecture discussions
- documentation
- hardware testing
- feature proposals
- pull requests

Please read [`CONTRIBUTING.md`](CONTRIBUTING.md) before submitting significant
changes.

AI-assisted contributions are welcome, but contributors are expected to
understand, review and test the code they submit.

## Security

Never commit:

- Wi-Fi credentials
- ESPHome API keys
- OTA passwords
- Home Assistant access tokens
- MQTT credentials
- private configuration files

Use the provided `.example` files instead.

## Documentation

- [Architecture](docs/ARCHITECTURE.md)
- [Wiring](docs/WIRING.md)
- [Plugin SDK](docs/PLUGIN_SDK.md)
- [PC companion](pc-app/README.md)

The remaining documentation is progressively being translated to English.

## Language

English is preferred for issues, pull requests and technical discussions so the
project remains accessible to the widest possible community.

The maintainer is also French-speaking.

## License

Streamdeck-ESP is released under the [MIT License](LICENSE).

Some third-party assets use their own licenses. Their original attribution and
license files are preserved in the repository.
