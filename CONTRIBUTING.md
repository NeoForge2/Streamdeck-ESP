# Contributing to Streamdeck-ESP

Thanks for considering contributing to Streamdeck-ESP.

Bug reports, code reviews, architecture feedback, documentation improvements,
hardware testing and pull requests are all welcome.

## Where help is most useful

Contributions are especially welcome around:

- ESPHome / ESP32-P4 / ESP32-C6
- LVGL architecture and performance
- Python architecture and maintainability
- device communication and protocol reliability
- Home Assistant integration
- Windows integration
- plugin architecture
- security
- automated testing
- real hardware testing
- cross-platform support
- documentation

If something looks badly designed, fragile, over-engineered or unnecessarily
complicated, please say so.

Architectural criticism is welcome.

## Before contributing

For large architectural changes or major new features, please open an issue
first so the approach can be discussed before significant work is done.

Small fixes, documentation improvements and isolated bug fixes can be submitted
directly as pull requests.

## Development setup

Clone the repository:

```bash
git clone https://github.com/NeoForge2/Streamdeck-ESP.git
cd Streamdeck-ESP/pc-app
```

Create a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```powershell
.venv\Scripts\activate
```

On Linux/macOS:

```bash
source .venv/bin/activate
```

Install the development dependencies:

```bash
pip install -r requirements-dev.txt
```

## Tests

Run the full test suite:

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

GitHub Actions also runs the test suite on Python 3.11 and 3.12.

## Pull requests

Please:

1. Create a dedicated branch.
2. Keep the change focused on one topic.
3. Add or update tests when relevant.
4. Explain what problem the pull request solves.
5. Mention whether the change was tested on real hardware.
6. Never commit secrets or personal configuration.

Example branch names:

```text
fix/encoder-sync
feature/plugin-api
refactor/device-protocol
docs/setup-guide
```

## Hardware testing

If you test a change on real hardware, please include:

- hardware revision if known
- ESPHome version
- operating system
- whether Home Assistant was involved
- what functionality was tested
- any unexpected behavior

Real-device test reports are especially valuable.

## Security

Never commit:

- Wi-Fi credentials
- ESPHome API keys
- OTA passwords
- Home Assistant access tokens
- MQTT credentials
- personal paths
- private configuration files

Use the provided `.example` configuration files.

## AI-assisted contributions

AI-assisted contributions are allowed.

Contributors remain responsible for understanding, reviewing and testing any
code they submit.

## Language

English is preferred for issues, pull requests and technical discussions so
the project remains accessible to the widest possible community.
