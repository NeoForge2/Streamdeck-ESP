# PC Companion Application

The PC companion is the main configuration and runtime application for
Streamdeck-ESP.

It runs in the system tray, connects directly to the ESPHome device and manages:

- profiles
- button layouts
- rotary encoders
- actions
- application launching
- Windows audio controls
- Home Assistant integration
- live widgets
- application icons
- plugins

Home Assistant is optional. The Stream Deck can be used as a standalone PC
macro controller.

## Installation

From the repository root:

```bash
cd pc-app
python -m venv .venv
```

Activate the virtual environment.

### Windows

```powershell
.venv\Scripts\activate
```

### Linux / macOS

```bash
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

No configuration file needs to be copied manually.

On first launch, the application automatically creates:

```text
dashboard_config.yaml
```

and opens the Settings page so you can configure the device connection.

`dashboard_config.yaml` contains local configuration and must not be committed.

---

## Recommended daily usage

Run the application in the system tray:

```powershell
pythonw -m streamdeck_companion.tray
```

On Windows, automatic startup can be installed with:

```powershell
powershell -ExecutionPolicy Bypass -File install_startup.ps1
```

Click the tray icon, or choose **Configure Stream Deck**, to open the dashboard:

```text
http://127.0.0.1:8080
```

### Run manually with terminal logs

For development or troubleshooting:

```bash
python -c "from streamdeck_companion.tray import main; main()"
```

---

# Interface

The companion application contains two main pages:

- **Home** — profiles, screen layout, buttons, widgets and encoders
- **Settings** — device connection, Home Assistant, MQTT and global settings

The Home page is designed to visually match the physical 1024×600 screen.

What you see in the browser is intended to closely represent what will be
displayed on the Stream Deck.

---

## Button library and physical slots

The firmware exposes **36 physical slots** arranged on an invisible 9×4 grid.

The PC application adds an unlimited button library on top of those physical
slots.

This means you can store as many configured buttons as you want while displaying
up to 36 at the same time.

Buttons that are not currently displayed remain available in the library.

You can:

- create buttons
- edit buttons
- drag buttons onto the screen
- move buttons around the grid
- resize buttons
- drag buttons back into the library
- permanently delete buttons

Removing a button from the screen does **not** delete it. It simply returns to
the library.

Press **Save and send to screen** to save the configuration and immediately push
the active layout to the device.

---

# Resizable grid

The screen uses an invisible grid made of:

```text
9 columns × 4 rows
```

A slot can occupy one or multiple cells.

### Move

Drag a displayed slot to another position.

The slot snaps to the grid.

### Add to screen

Drag a button from the library onto the screen.

The application assigns it to an available physical slot.

### Remove from screen

Drag the button back into the library.

### Resize

Use the resize handle in the bottom-right corner of a slot.

Slots can span multiple rows and columns.

### Collision protection

Two slots cannot occupy the same grid cells.

Moves or resizes that would create an overlap are rejected.

The new geometry is pushed to the firmware dynamically, so changing the layout
does not require reflashing the device.

---

# Profiles

Each profile has its own:

- grid layout
- buttons
- widgets
- three rotary encoders
- application trigger

Profiles are displayed as tabs above the screen preview.

A green indicator shows which profile is currently active on the physical
device.

## Automatic profile switching

A profile can be associated with a Windows process such as:

```text
obs64.exe
Discord.exe
Game.exe
```

When that application becomes the foreground window, the Stream Deck
automatically switches to the matching profile.

The active application is checked approximately every 1.5 seconds.

A profile without an application trigger acts as the default fallback profile.

## Creating a profile

When creating a profile, the application can display currently open
applications.

Selecting one automatically fills the executable/process name instead of
requiring you to find it manually.

## Manual profile override

A profile can also be forced manually.

Use **Force this profile** to keep it active regardless of the foreground
application.

Use **Automatic** to restore normal profile switching.

---

# Slot types

A slot can use one of three main types:

| Type | Description |
|---|---|
| `bouton` | Executes an action when pressed |
| `barre` | Displays a 0–100 value from Home Assistant |
| `texte` | Displays a Home Assistant state and unit |

Home Assistant-backed widgets are refreshed through the REST API approximately
every 15 seconds by default.

Optional MQTT integration can provide much faster updates.

---

# Actions

Supported actions include:

| Action | Description |
|---|---|
| `none` | No action |
| `keys` | Keyboard shortcut such as `ctrl+shift+s` |
| `launch` | Launch an application, executable or command |
| `url` | Open a URL or URI such as `steam://...` |
| `media` | Play/pause, next, previous, volume and mute |
| `home_assistant` | Call a Home Assistant service |
| `audio_output` | Change the default Windows audio output |
| `app_volume` | Change the volume of a specific Windows application |
| `app_mute` | Mute/unmute a specific Windows application |
| `ha_adjust` | Incrementally adjust a Home Assistant entity |

---

# Application library

When a button uses the `launch` action, the configuration popup provides an
application browser instead of requiring users to manually type executable
paths.

The library can include:

- currently running applications
- Start Menu applications
- manually added executables
- manually added shortcuts

A search field filters the application list.

Selecting an application automatically fills its launch target and can also
suggest a button label.

Custom applications are stored in:

```text
dashboard_config.yaml
```

Automatic application discovery currently targets Windows.

On other platforms, applications can still be added manually.

---

# Real application icons

Launch buttons can automatically display the real icon of an application or
game instead of a generic glyph.

On Windows:

```text
icon_extract.py
```

extracts icons from `.exe` and `.lnk` files using `icoextract` and Pillow.

The icons are served to the Stream Deck through:

```text
icon_server.py
```

on port:

```text
8081
```

The icon server is intentionally separate from the main dashboard.

The main configuration dashboard remains available only on:

```text
127.0.0.1:8080
```

while the icon server must be reachable by the physical device on the local
network.

---

# Rotary encoders

The current hardware configuration contains three rotary encoders.

Each encoder can configure:

- clockwise rotation
- counter-clockwise rotation
- push action

## Real value synchronization

When clockwise and counter-clockwise actions form a recognized symmetrical
pair, the encoder display can show the real controlled value instead of a raw
rotation counter.

Examples include:

| Configuration | Displayed value |
|---|---|
| `media` volume up/down | Windows master volume |
| `app_volume` | Volume of the selected application |
| `ha_adjust` | Current Home Assistant entity value |
| compatible `home_assistant` actions | Current Home Assistant entity value |

Supported Home Assistant domains include:

```text
light
media_player
fan
cover
climate
```

For Home Assistant entities, `ha_adjust` is usually preferred when the value
must actually be incremented or decremented.

For example:

```text
up:climate.living_room
down:climate.living_room
```

The application reads the current value and calculates the next step.

Typical steps are:

```text
1%   light / media player / fan / cover
0.5°C climate
```

Encoder state synchronization runs approximately every 2 seconds.

---

# Home Assistant integration

Home Assistant is optional.

When configured with a Home Assistant URL and long-lived access token, the
application can:

- read entity states
- display text widgets
- display numeric gauges
- call services
- control lights
- control media players
- control fans
- control covers
- control climate entities
- display weather information
- synchronize colors and values

The physical Stream Deck also remains available through Home Assistant's native
ESPHome integration.

---

## Entity picker

Users do not need to manually type most Home Assistant entity IDs.

The configuration popup provides a searchable entity list using:

```text
ha_client.py::list_entities()
```

Search examples:

```text
temperature
volume
living room
```

Selecting an entity automatically fills its `entity_id`.

For `home_assistant` actions, common services for the selected domain are also
offered.

Advanced users can still edit the compact action representation manually.

---

# Offline state detection

If a Home Assistant entity used by a text widget or weather card fails to
respond for at least two consecutive polling cycles, the screen displays an
offline state instead of silently keeping a stale value.

When communication succeeds again, the live value is restored automatically.

Bar widgets currently keep their last known value because their UI does not
contain a dedicated offline label.

---

# MQTT synchronization

REST polling is the default synchronization method.

Widgets and light colors are normally refreshed approximately every 15 seconds.

For near real-time updates, an MQTT broker can be configured in Settings.

The application then runs:

```text
streamdeck_companion/ha_mqtt.py
```

alongside REST polling.

Home Assistant can publish state changes through `mqtt_statestream`:

```yaml
mqtt_statestream:
  base_topic: homeassistant/state
  publish_attributes: true
```

The configured base topic must match the value used in the companion
application.

REST polling continues running as a fallback even when MQTT is enabled.

Changing MQTT settings currently requires restarting the companion application.

---

# Media player popup

A button targeting a Home Assistant `media_player` entity opens a dedicated
touchscreen control panel instead of immediately executing a single service.

The popup includes:

- play / pause
- previous
- next
- volume slider

The state is loaded from Home Assistant when the popup opens.

The popup automatically closes after approximately 15 seconds of inactivity or
when the close button is pressed.

Implementation:

```text
streamdeck_companion/ha_popup.py
firmware/ha_popup.yaml
firmware/ha_popup_panel.yaml
```

---

# Home Assistant light controls

Buttons targeting `light` entities can optionally display the current light
color as their background.

The displayed color can come from:

- actual RGB values
- color temperature converted to RGB
- a generic warm-white fallback

When the light is off, the button returns to its normal background.

Color state is handled through:

```text
ha_client.py::light_color_hex()
```

---

## Long-press light control

Long-pressing an eligible light button opens a dedicated control mode.

The three encoders become:

```text
Encoder 1 → Hue
Encoder 2 → Color temperature
Encoder 3 → Brightness
```

The same controls can also be manipulated directly on the touchscreen.

The panel contains:

- hue strip
- color-temperature strip
- brightness slider

Changes update the preview and Home Assistant in real time.

The update rate is limited to avoid unnecessarily flooding Home Assistant.

The mode closes:

- automatically after inactivity
- through the close button

Implementation:

```text
streamdeck_companion/color_mode.py
firmware/color_mode_panel.yaml
```

---

# Touch-adjustable bar widgets

A `barre` widget linked to a supported Home Assistant entity can be adjusted
directly from the touchscreen.

Touch:

```text
left half  → decrease by 5%
right half → increase by 5%
```

Supported domains currently include:

```text
light
media_player
fan
cover
```

Implementation:

```text
ha_client.py::adjust_entity_percent()
```

---

# Weather card

Each profile can contain one dedicated weather card.

It uses a Home Assistant:

```text
weather.*
```

entity.

The card displays:

- weather condition
- weather icon
- temperature
- condition-specific animation

Current animation behavior:

| Condition | Animation |
|---|---|
| `sunny` | animated sun rays |
| `clear-night` | blinking stars |
| `cloudy`, `partlycloudy`, `fog` | moving clouds |
| `rainy`, `pouring`, `hail`, `lightning`, `lightning-rainy` | falling rain |
| `snowy`, `snowy-rainy` | falling snow |
| `windy`, `windy-variant`, `exceptional` | static fallback |

Condition mapping is handled by:

```text
streamdeck_companion/weather.py
```

Firmware animation is implemented in:

```text
firmware/weather_card.yaml
```

Weather artwork is based on the
[amCharts animated weather icons](https://www.amcharts.com/free-animated-svg-weather-icons/)
licensed under CC BY 4.0.

The SVG sources and their license are preserved in:

```text
scripts/weather_icons_src/
```

---

# Icon catalog

The built-in icon picker currently contains approximately 172 Material Icons
glyphs.

The same font is used in the browser preview and on the physical device so the
preview closely matches the final result.

Relevant files:

```text
streamdeck_companion/icons.py
firmware/icon_font.yaml
```

When adding a new glyph to `icons.py`, it must also be included in the
`glyphs:` list in `firmware/icon_font.yaml`.

Otherwise the physical screen may display an empty square.

---

# Home Assistant → PC actions

Home Assistant can optionally ask the companion application to execute an
action on the PC.

Enable a receiver token in:

```text
dashboard_config.yaml
```

and use:

```text
home-assistant/rest_command.yaml.snippet
```

Examples are available in:

```text
home-assistant/example_automations.yaml
```

This feature is optional and is not required for normal Stream Deck operation.

---

# Plugins

The application contains a V2 plugin architecture.

Plugins can contribute:

- actions
- action executors
- widgets
- state providers
- events
- settings
- assets

See:

```text
../docs/PLUGIN_SDK.md
```

Reference plugins are available under:

```text
streamdeck_companion/example_plugins/
```

---

# Development

Install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run the complete test suite:

```bash
python -m unittest discover -s tests -v
```

Run Ruff:

```bash
ruff check streamdeck_companion
```

Run MyPy on the Core:

```bash
mypy streamdeck_companion/core
```

The GitHub Actions workflow runs:

- Python 3.11
- Python 3.12
- Ruff
- MyPy
- complete regression tests
- Core coverage checks

---

# Known limitations

The project is still under active development.

Important current limitations include:

- several PC integrations are Windows-specific
- automatic foreground-application profile switching currently targets Windows
- `keyboard` may require elevated permissions on some platforms
- the `keyboard` library does not work under Wayland
- macOS multimedia-key support is incomplete
- automatic application discovery currently targets the Windows Start Menu
- application audio control depends on Windows / `pycaw`
- the 9×4 physical grid is currently fixed
- custom arbitrary image uploads are not currently supported
- Home Assistant REST polling defaults to approximately 15-second intervals
- MQTT requires Home Assistant `mqtt_statestream` configuration
- some firmware features still need broader real-hardware testing
- application icon extraction currently targets Windows
- profile triggers match exact process names
- automatic profile switching is not instantaneous because the foreground
  application is polled periodically

Some functionality has been validated on real hardware, while other parts have
primarily been validated through automated tests or simulated environments.

Hardware test reports and bug reports are very welcome.

---

# Security

Never commit:

- `dashboard_config.yaml`
- Wi-Fi credentials
- ESPHome API keys
- OTA passwords
- Home Assistant access tokens
- MQTT credentials
- private paths or personal configuration

The dashboard itself listens only on:

```text
127.0.0.1:8080
```

The separate icon server listens on the local network because the ESP32 needs
to retrieve application icons.

It only serves resolved icon assets and does not expose the main configuration
dashboard.

---

# Related documentation

- [Main README](../README.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [Wiring](../docs/WIRING.md)
- [Plugin SDK](../docs/PLUGIN_SDK.md)
- [Contributing](../CONTRIBUTING.md)

Contributions and technical feedback are welcome.
