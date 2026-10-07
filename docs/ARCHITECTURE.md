# Architecture

```text
                         +-------------------------+
                         |  Stream Deck (ESP32-P4) |
                         |  ESPHome + LVGL         |
                         |  - 1024x600 touchscreen |
                         |  - 36 slots + 3 encoders|
                         |  - Wi-Fi via ESP32-C6   |
                         +------------+------------+
                                      |
                         ESPHome native API
                         (encrypted, Noise Protocol,
                         port 6053)
                                      |
                +---------------------+---------------------+
                |                                           |
     +----------v-----------+                    +----------v-----------+
     |   Home Assistant     |                    |   PC App (Python)    |
     |   native ESPHome     |                    |   streamdeck_companion/
     |   integration        |                    |   device_client.py   |
     |   optional for its   |                    |   direct persistent  |
     |   own automations    |                    |   connection         |
     +------------+---------+                    +------------+---------+
                  |                                           |
                  | optional HA REST API          dashboard.py (visual
                  | live state + services         config, port 8080)
                  |                               + tray.py (system tray)
                  v                                           |
     +------------+-------------------------------------------+
     |  ha_client.py / ha_poller.py (REST polling ~15s)       |
     |  + ha_mqtt.py (optional, instant via mqtt_statestream) |
     |  bar/text widgets + 'home_assistant' actions           |
     +--------------------------------------------------------+
                                                             |
                                                   local actions:
                                                   keyboard shortcuts,
                                                   app/game launching,
                                                   media, URLs
```

## PC application as the single configuration point

Everything is configured through the PC application
(`http://127.0.0.1:8080`), using two pages to avoid unnecessary complexity:

- **Home** (`/`): one or more **profiles** displayed as tabs. Each profile
  contains a faithful preview of the physical screen, using the same proportions
  and layout as the firmware, with its own configurable slots and 3 encoders.

  Up to 36 slots can be configured as buttons, bars or text widgets, with their
  own icon and action. Hidden slots are displayed separately below the screen
  preview.

  Visible slots can be moved and resized by drag-and-drop on an invisible grid
  of square cells. See the "Resizable invisible grid" section below.

  The screen automatically switches to the profile whose trigger matches the
  foreground application on the PC. See "Application-based profiles".

  The `launch` action provides an application library with search, detected
  applications and custom applications instead of requiring users to manually
  enter executable paths.

- **Settings** (`/reglages`): device connection, square/round button shape and
  Home Assistant configuration.

  This page is automatically requested on first launch. `tray.py` creates an
  empty `dashboard_config.yaml`, so there is no need to manually copy an
  `.example` file.

A single "Save and send to screen" action saves the current page and pushes its
changes. Each page only modifies its own part of `dashboard_config.yaml`.

### Main components

- `device_client.py` maintains a permanent direct connection to the screen.

  The device IP is configured once; mDNS is not used.

  The same connection is used both to listen for slot/encoder events and to
  push the active profile configuration, including labels, icons, types,
  visibility and widget values.

  The connection is not recreated every time the configuration or active
  profile changes.

- `dashboard.py`, together with:

  - `templates/base.html`
  - `templates/home.html`
  - `templates/settings.html`
  - `static/dashboard.js`

  implements the two web pages.

  Flask runs in a separate thread and communicates with `device_client.py`
  through `asyncio.run_coroutine_threadsafe()` to remain thread-safe.

- `profiles.py` contains the profile data model, legacy-format migration and
  trigger-to-profile matching.

  It is shared by `dashboard.py` and `device_client.py`.

- `profile_watcher.py` polls the foreground PC window approximately every
  1.5 seconds on Windows and switches the active profile accordingly.

- `ha_client.py` and `ha_poller.py` optionally poll the Home Assistant REST API
  approximately every 15 seconds.

  They update widget-type slots and execute `home_assistant` actions through
  service calls.

  `ha_client.py::list_entities()` also feeds the searchable entity picker used
  in slot configuration popups, both for widget sources and
  `home_assistant` action targets.

  Common services are curated by domain through `COMMON_SERVICES`.

### Home Assistant light color support

For a button targeting a Home Assistant `light` entity with
"Show light color" enabled, the same polling loop also pushes a background
color using:

```text
ha_client.py::light_color_hex()
```

The displayed color is derived from:

- the actual RGB value when available
- color temperature when RGB is unavailable
- a generic warm white fallback

Each slot exposes an additional entity:

```text
Slot N - color
```

See `firmware/slots_*.yaml`.

A long press on the same light button generates a `hold_N` event and opens a
live control mode using the 3 encoders or the touchscreen.

The three axes control:

- hue
- color temperature
- brightness

The implementation lives in:

```text
color_mode.py::ColorModeController
```

This logic was extracted from `device_client.py` to keep individual files
manageable.

The firmware displays a dedicated panel containing one LVGL slider for each
axis. All sliders use the same visual style and can be manipulated directly
with touch.

See:

```text
firmware/color_mode_panel.yaml
```

The firmware `number` entities:

```text
Mode couleur - */valeur
```

remain the single source of truth.

Encoder changes are written through `number_command` from PC to screen.

Touch changes are written with `number.set` on the device and travel in the
opposite direction, from screen to PC.

They are received as `NumberState` events by:

```text
device_client.py::on_state
```

and routed to:

```text
color_mode.py::handle_touch
```

The controller ignores echoes of its own writes so Home Assistant does not
receive duplicate updates.

The mode closes either after a timeout or through the floating
`close_color_mode` button.

### Direct adjustment of Home Assistant values

A `bar` slot backed by a Home Assistant entity can also be adjusted directly
from the touchscreen.

Touching the left or right side decreases or increases its value through:

```text
ha_client.py::adjust_entity_percent()
```

using:

```text
bar_inc_N
bar_dec_N
```

events.

The same concept is used for encoders configured with the `ha_adjust` action:

```text
up:<entity>
down:<entity>
```

The flow is:

```text
device_client.py::_run_ha_adjust
    ->
ha_client.py::adjust_encoder_entity()
```

This provides incremental adjustment for domains that do not expose simple
Home Assistant "+" / "-" services.

For example, climate entities use 0.5°C increments instead of percentages.

This allows `fan`, `cover` and `climate` entities to be genuinely controlled
with an encoder rather than only displayed.

See `encoder_sync.py` below.

### Media player popup

`ha_popup.py` implements the touchscreen popup used by a button whose
`home_assistant` action targets a `media_player`.

A normal tap opens a panel through `HaPopupController` instead of immediately
calling the configured service.

The popup provides:

- play / pause
- previous
- next
- volume slider

Firmware files:

```text
firmware/ha_popup.yaml
firmware/ha_popup_panel.yaml
```

The popup is initialized with the current Home Assistant entity state when it
opens.

It closes after 15 seconds of inactivity or through the `close_ha_popup`
button.

The media popup and color-control mode are mutually exclusive and are never
displayed at the same time.

Lights and other Home Assistant domains keep their normal tap behavior. Only a
long press opens the light color-control panel.

### MQTT bridge

`ha_mqtt.py` is an optional complement to `ha_poller.py`.

When an MQTT broker is configured in Settings, it subscribes to topics
published by the Home Assistant `mqtt_statestream` integration.

Example:

```text
<base_topic>/light/living_room/attributes/rgb_color
```

It reconstructs each entity state from incoming messages and reuses:

```text
ha_client.format_widget_value()
ha_client.light_color_hex()
```

Updates can therefore be pushed almost immediately instead of waiting for the
next REST polling cycle.

`ha_poller.py` continues running in parallel as a fallback.

If MQTT is not configured, or if a message is missed, the normal REST polling
mechanism continues working.

### Per-application audio

`app_volume.py` handles Windows system volume and per-application volume using
`pycaw`.

`AudioUtilities.GetAllSessions()` is queried on each operation because audio
sessions appear and disappear dynamically.

It powers the encoder actions:

```text
app_volume
```

with targets such as:

```text
up:<process>
down:<process>
```

and:

```text
app_mute
```

which toggles the audio of a specific application.

A common configuration is:

- encoder rotation → `app_volume`
- encoder press → `app_mute`

The corresponding application picker uses the `/audio-sessions` route exposed
by `dashboard.py`.

### Encoder state synchronization

`encoder_sync.py` makes an encoder display the real value it controls instead
of a raw local rotation counter.

`encoder_source()` determines what the encoder represents from its already
configured clockwise and counter-clockwise actions.

When the pair is symmetrical and targets the same source, it can represent:

- Windows master volume
- per-application volume
- Home Assistant `light`
- Home Assistant `media_player`
- Home Assistant `fan`
- Home Assistant `cover`
- Home Assistant `climate`

Home Assistant-backed encoders can use either:

```text
home_assistant
```

or:

```text
ha_adjust
```

See:

```text
ha_client.py::_ENCODER_DISPLAY
ha_client.py::read_entity_level()
```

The value is refreshed approximately every 2 seconds and pushed to:

```text
Encoder N - real value
Encoder N - display
```

defined in:

```text
firmware/encoder_sync.yaml
```

These values drive:

```text
bar_encoderN
lbl_encoderN
```

The firmware no longer updates these UI elements from the raw rotation counter.

The existing `on_clockwise` and `on_anticlockwise` events remain unchanged and
continue triggering configured actions.

### Icon catalog

`icons.py` contains a catalog of 172 Material Icons glyphs.

The code points match the `font_icons` font defined in:

```text
firmware/icon_font.yaml
```

The catalog was expanded from an initial set of 22 icons to cover categories
similar to the Home Assistant icon picker.

Any icon added to `icons.py` must also be added to the `glyphs:` section of
`icon_font.yaml`.

Otherwise it will appear as an empty square on the device.

The slot popup icon selector:

```text
dashboard.js::renderIconPicker
```

filters the catalog using a search bar.

### Real application icons

`icon_extract.py` and `icon_server.py` allow a `button` slot using a `launch`
action to display the real application icon from an `.exe` or `.lnk` file.

This feature currently targets Windows and uses:

- `icoextract`
- Pillow

instead of always displaying a generic glyph.

`icon_server.py` starts a **second HTTP server** on port `8081`.

It listens on all interfaces, but only serves already-resolved application
icons.

The main dashboard remains bound to:

```text
127.0.0.1
```

This separation lets the Stream Deck download icons over the local network
without exposing the rest of the dashboard configuration.

On the firmware side, every slot has its own `online_image` entity in:

```text
firmware/slot_icons.yaml
```

using ESPHome's `http_request` component.

The icon URL is updated through:

```text
online_image.set_url
```

when:

```text
Slot N - icon
```

receives a:

```text
REAL:<version>
```

value instead of a font glyph.

### Application library

The application picker is implemented by:

```text
app_library.py
custom_apps.py
browse.py
```

It combines:

- Windows Start Menu shortcut discovery
- custom applications stored in `dashboard_config.yaml`
- a native file picker for manually adding applications

### System tray orchestration

`tray.py` orchestrates:

- the device connection
- dashboard
- icon server
- Home Assistant REST polling
- optional MQTT bridge
- profile watcher
- encoder synchronization

The application runs as a system tray icon without requiring a visible terminal
window.

The tray menu also displays the currently active profile.

A single-instance lock:

```text
_acquire_single_instance_lock
```

uses a local TCP bind on a fixed port to prevent multiple instances from
running simultaneously.

Without this lock, multiple instances would open independent device
connections and could execute every action multiple times.

Home Assistant can still discover the device through the native ESPHome
integration and run its own automations independently.

Home Assistant is **not required** for the Stream Deck to operate with the PC.

---

## The 36 slots

LVGL and ESPHome layouts are defined at compile time.

Changing the number of widgets dynamically would normally require reflashing
the device.

The chosen compromise is to permanently define **36 physical slots** in the
firmware.

There is one slot for each cell of the invisible 9×4 grid.

They are defined through:

```text
firmware/slots_*.yaml
firmware/slot_widgets.yaml
```

Each slot can be reconfigured at runtime without reflashing.

A physical slot exposes configuration entities for:

- label text
- widget value text
- icon text
- type selector (`button`, `bar`, `text`)
- visibility switch
- grid position and size

The firmware only knows these 36 physical slots.

The unlimited PC-side button library described below is an abstraction above
them and is invisible to the firmware.

The number 36 comes from:

```text
GRID_COLS * GRID_ROWS
9 * 4
```

This is the maximum capacity of the grid when every slot occupies one cell.

`SLOT_COUNT` was increased from 16 to 36 so the firmware slot count no longer
creates an artificial limit below the grid capacity.

Related generators:

```text
scripts/gen_slot_entities.py
scripts/gen_slot_grid.py
scripts/gen_slot_widgets.py
scripts/gen_slot_icons.py
```

### Unlimited library + physical-slot assignment

Originally, a physical slot was responsible for both:

1. storing button configuration
2. displaying that button

This meant it was impossible to keep more configured buttons than there were
physical slots.

These responsibilities are now separated in `profiles.py`.

### `profile["library"]`

This is an unlimited library of stored buttons.

Each entry created through:

```text
default_library_entry()
```

has a stable `id` and stores:

- label
- icon
- type
- action
- Home Assistant entity
- light-color display setting

Entries can be freely created, edited and deleted from the button popup.

The "+" button in `dashboard.js` creates a new library entry.

### `profile["slots"]`

This always contains exactly `SLOT_COUNT` physical slots.

Each slot mirrors one LVGL object in the firmware.

It now stores only:

- grid position
- grid size
- which library entry is currently assigned

Assignment is represented by:

```text
library_id
```

or:

```text
None
```

when the slot is unused.

### Slot resolution

```text
profiles.py::resolve_slot(profile, idx)
```

combines the physical slot and its library entry into a resolved slot using the
old all-in-one format.

Visibility is derived from:

```text
library_id is not None
```

This resolved representation is used by:

```text
device_client.py
ha_poller.py
ha_mqtt.py
icon_server.py
color_mode.py
```

This keeps most consumers independent from the new storage model.

### Profile library migration

```text
profiles.py::migrate_profile_library()
```

transparently migrates profiles from the old slot format.

The old format used:

```text
_LEGACY_SLOT_COUNT = 16
```

Each legacy slot becomes a library entry.

If it was visible, it is assigned to the equivalent physical slot.

This preserves existing configuration.

Migration only runs once and is guarded by the presence of:

```text
"library" in profile
```

### Slot-count expansion

```text
profiles.py::ensure_slot_count()
```

extends `profile["slots"]` to `SLOT_COUNT` with empty physical slots:

```text
library_id: None
```

This is separate from the legacy migration.

It ensures profiles that had already been migrated before the slot count was
increased from 16 to 36 also receive the additional physical slots without
duplicating library entries.

It is called on each load through:

```text
migrate_profiles()
```

### Browser-side assignment

In `dashboard.js`, displaying or removing a button from the screen is done
through drag-and-drop instead of a "Visible" checkbox.

Dragging a library entry onto the screen assigns its `library_id`.

Dragging it back to the library releases the physical slot.

The library section displays entries that are not currently assigned.

The screen displays physical slots that have an assigned library entry.

Deleting an entry through:

```text
removeLibraryEntry()
```

automatically frees any physical slot referencing it.

---

## Resizable invisible grid

The original layout used a fixed 4×4 grid of identical tiles.

The current screen instead uses an invisible grid of:

```text
9 columns × 4 rows
```

with square cells.

Current geometry:

```text
cell: 96px
gap: 12px
grid area: 960×420
screen: 1024×600
```

The grid is centered on the screen.

Configuration is defined through:

```text
firmware/package.yaml::action_grid
```

A slot can occupy one or more cells using:

```text
colspan
rowspan
```

Slots are moved and resized through drag-and-drop in `dashboard.js`.

The browser uses native CSS Grid through:

```text
grid-column
grid-row: span N
```

Each tile also exposes a resize handle.

Collisions are detected in JavaScript before a move or resize is accepted.

See:

```text
hasCollision()
```

### Data model

Each slot has:

```text
grid = {
    col,
    row,
    colspan,
    rowspan
}
```

created by:

```text
profiles.py::default_grid()
```

The default layout fills cells in reading order using 1×1 slots.

The following constants must stay synchronized between the firmware and
browser code:

```text
GRID_COLS
GRID_ROWS
```

### Sending geometry to the screen

`device_client.py::push_config()` sends one compact text entity per slot:

```text
Slot N - grid
```

Format:

```text
column,row,width_in_cells,height_in_cells
```

Example:

```text
2,1,3,2
```

### Firmware-side resizing

The firmware implementation is generated into:

```text
firmware/slot_grid_1.yaml
firmware/slot_grid_2.yaml
```

by:

```text
scripts/gen_slot_grid.py
```

The files are split to keep each generated file below approximately 500 lines
with 36 slots.

Each entity's `on_value` lambda:

1. parses the CSV value
2. computes pixel position and size
3. moves the LVGL slot
4. resizes the LVGL slot
5. updates its child widgets proportionally

This includes:

- title
- bar widget
- left touch zone
- right touch zone

The main primitives are:

```text
lv_obj_set_pos
lv_obj_set_size
```

All of this happens live without reflashing.

`firmware/slot_widgets.yaml`, generated by:

```text
scripts/gen_slot_widgets.py
```

only defines an initial 1×1 position and size before the first PC push.

`action_grid` no longer uses a flex layout.

Each slot is positioned independently using:

```text
align: top_left
x
y
width
height
```

---

## Weather card

The weather card is an independent widget rather than a generic slot.

Each profile can contain at most one weather card through the profile's
`weather` key.

See:

```text
profiles.py::default_weather()
```

It shares the same invisible grid and therefore uses the same position and
size mechanism as normal slots.

However, it has its own content and configuration popup.

The configured Home Assistant entity must be a:

```text
weather.*
```

entity.

### PC side

`streamdeck_companion/weather.py` translates Home Assistant weather conditions
such as:

```text
sunny
rainy
snowy
```

into:

```text
(icon, animation_style)
```

through:

```text
_CONDITION_MAP
```

The temperature is read from the entity's `temperature` attribute.

The entity state itself contains the textual weather condition and is not used
as the numeric temperature.

`ha_poller.py` polls the configured weather entity when the card is visible.

It uses the same polling interval as normal Home Assistant widgets.

It pushes:

- icon
- animation style
- temperature

through:

```text
device_client.py::push_weather_display()
```

This is intentionally separate from `push_config()` so geometry is not
re-sent on every weather refresh.

### Firmware side

The firmware implementation lives in:

```text
firmware/weather_card.yaml
```

and is generated by:

```text
scripts/gen_weather_card.py
```

The weather-card button itself is placed in `slot_widgets.yaml` as an
additional widget inside `action_grid`.

See the comment in `gen_weather_card.py` for the implementation rationale.

The firmware does not communicate directly with Home Assistant.

It only displays and animates the style sent by the PC through:

```text
Weather - animation
```

A pool of pre-created LVGL objects represents:

- rain drops
- snow flakes
- sun rays
- stars
- clouds

A single `interval:` loop running every 90ms moves, shows or hides these
objects.

State is stored through globals such as:

```text
weather_tick
weather_style
weather_w
weather_h
```

The LVGL animation API `lv_anim_t` was intentionally avoided because its exact
availability and signature can depend on the LVGL version bundled with
ESPHome.

Instead, the implementation relies on primitives already used elsewhere in the
firmware:

```text
lv_obj_set_pos
lv_obj_set_size
lv_obj_set_style_bg_opa
lv_obj_add_flag
lv_obj_clear_flag(LV_OBJ_FLAG_HIDDEN)
```

### Peripheral battery support

Peripheral battery reporting was investigated but is not currently
implemented.

The Corsair iCUE SDK does not officially expose battery level.

Known workarounds require reading values directly from iCUE process memory,
which would require scanning the target machine to find version- and
device-specific memory addresses.

See the known limitations section in the PC application documentation.

---

## Application-based profiles

A commercial Stream Deck typically changes its controls depending on the
foreground application.

This project reproduces that behavior with profiles.

Each profile stored under the `profiles` key in `dashboard_config.yaml` has:

```text
name
trigger
slots
encoders
```

A trigger is either:

```text
{process: "name.exe"}
```

or:

```text
null
```

The first profile without a trigger acts as the fallback profile.

### Profile watcher

```text
profile_watcher.py::run_forever()
```

runs in its own thread on Windows.

Approximately every 1.5 seconds it determines the process owning the foreground
window using:

```text
win32gui.GetForegroundWindow()
win32process.GetWindowThreadProcessId()
psutil
```

The process is matched against profile triggers through:

```text
profiles.match_profile()
```

When the profile changes, the watcher calls:

```text
device_client.schedule_set_active_profile()
```

The new profile configuration is then pushed to the screen using the same
mechanism as `push_config()`.

Action resolution through:

```text
_resolve_action()
```

is also redirected to the new active profile.

This ensures physical buttons execute the actions belonging to the profile
currently displayed.

### Manual override

```text
device_client.manual_override
```

contains either:

```text
profile name
```

or:

```text
None
```

The web interface updates it through:

```text
/profiles/force
/profiles/auto
```

When a manual override is active, `profile_watcher.py` does not change the
profile until automatic mode is restored.

### Profile status

The web interface polls:

```text
/profiles/status
```

approximately every 3 seconds.

This is used to display which profile is actually active on the physical
screen, independently from the profile tab currently being edited.

### Legacy configuration migration

```text
profiles.migrate_profiles()
```

converts older configurations where:

```text
slots
encoders
```

were stored directly at the root.

They are migrated into a single default profile on first load.

---

## Flow: screen slot → PC

1. The user touches a `button` slot on the LVGL screen or rotates an encoder.

2. The firmware triggers an ESPHome `event` entity.

3. `device_client.py` receives the state through its permanent
   `subscribe_states` connection.

4. It resolves the configured action for the current slot or encoder direction
   from `dashboard_config.yaml`.

5. The action is executed either locally through `actions.py`:

   - keyboard shortcut
   - application launch
   - media action
   - URL

   or through Home Assistant using:

   ```text
   ha_client.py::call_service
   ```

   for `home_assistant` actions.

6. Home Assistant can independently listen to the same ESPHome event entity for
   its own automations.

See:

```text
home-assistant/example_automations.yaml
```

---

## Flow: PC → screen

### Slot configuration and shape

The "Save and send to screen" action in `dashboard.py` calls:

```text
device_client.schedule_push()
```

which sends the active profile's:

- labels
- icons
- types
- visibility
- shape

to the device.

### Widget values

For `bar` and `text` widgets, `ha_poller.py` polls Home Assistant approximately
every 15 seconds and calls:

```text
device_client.schedule_push_values()
```

Only the relevant:

```text
text.slot_N_value
```

entities are updated.

The rest of the configuration is not resent.

If MQTT is configured, `ha_mqtt.py` calls the same mechanism immediately when
a `mqtt_statestream` message is received.

REST polling and MQTT coexist.

MQTT simply provides a faster update path.

### Generic status from Home Assistant

Home Assistant can also directly call:

```text
text.set_value
```

on:

```text
text.streamdeck_pc_status
```

See:

```text
home-assistant/example_automations.yaml
```

---

## Design

The LVGL interface uses the project's visual design system.

Main palette:

```text
navy background:   #0B1929
ocean cards:       #0F2942
slate borders:     #1A3A52
signal accent:     #00B4D8
```

Typography:

- **Space Grotesk** for headings
- **Inter** for body text
- **JetBrains Mono** for numerical values such as voltages and encoder values
- **Material Icons** for slot icons

The interface is designed as a personal tools dashboard with a restrained
technical visual style.
