# Rotary encoder wiring

## Expansion header used

Based on product photos of the Guition JC1060P470C_I_W board:

```text
Left column                  Right column
3V3                          5V
3V3                          5V
GND                          GND
GPIO1                        NC
GPIO2                        GPIO47
GPIO3                        GPIO46
GPIO4                        GPIO45
GPIO5   <- internal LCD reset GND
GPIO20                       3V3
GPIO32                       C6_U0RXD
GPIO33                       C6_U0TXD
I2C_SDA                      C6_IO9
I2C_SDL                      C6_CHIP_PU
```

**GPIO5 is intentionally avoided.**

According to a community ESPHome configuration verified for this board, GPIO5
is used internally as the MIPI-DSI display `reset_pin`.

Even though it is exposed on the header, reusing it for a rotary encoder could
conflict with the display.

The header pins `I2C_SDA` / `I2C_SDL` are also intentionally not used here.

The touchscreen already uses a separate internal I2C bus on GPIO7/GPIO8, so
these exposed I2C pins are better kept available for an external I2C sensor if
needed.

> **Warning**
>
> This pin mapping is based on product photos and a community configuration,
> not an official Guition schematic.
>
> Verify the pins with a multimeter / continuity test before soldering anything.

## Mapping used in `firmware/streamdeck.yaml`

The current configuration uses 3 rotary encoders:

| Encoder | CLK (`pin_a`) | DT (`pin_b`) | SW (button) |
|---|---|---|---|
| 1 | GPIO1 | GPIO2 | GPIO3 |
| 2 | GPIO4 | GPIO20 | GPIO32 |
| 3 | GPIO33 | GPIO45 | GPIO46 |

GPIO47 remains free.

It can potentially be used for:

- an additional button
- an external sensor
- part of a fourth encoder configuration

A full fourth encoder with push button would require more free GPIOs than are
available with the current mapping.

## KY-040 rotary encoder wiring

Example wiring for a KY-040-style rotary encoder:

```text
KY-040 encoder        Stream Deck header
--------------        ------------------
CLK       ----------> encoder pin_a (example: GPIO1)
DT        ----------> encoder pin_b (example: GPIO2)
SW        ----------> encoder button pin (example: GPIO3)
+         ----------> 3V3
GND       ----------> GND
```

`pin_a` and `pin_b` are configured as inputs using the ESPHome
`rotary_encoder` component.

The encoder button uses:

```text
INPUT_PULLUP
inverted: true
```

so pressing the button connects the input to ground.

Most KY-040 modules already include their own pull-up components, so additional
external resistors are usually not required.

## Adding a fourth encoder

A fourth encoder is possible, but the current GPIO mapping does not leave
enough free pins for a complete additional encoder with:

- CLK
- DT
- push button

GPIO47 is still available, so several alternatives are possible:

- add a fourth encoder without a push button
- use GPIO47 for an extra standalone button
- free one or more GPIOs by removing or changing an existing encoder
- use an external GPIO expander

If additional GPIOs become available, the firmware changes are conceptually:

1. Add another `rotary_encoder` sensor block in `firmware/streamdeck.yaml`.
2. Add the corresponding GPIO `binary_sensor` for the push button.
3. Add the associated template `event`.
4. Add a fourth encoder card to the LVGL interface.
5. Extend the PC companion configuration and event handling for the new encoder.

## Safety notes

Before connecting or soldering anything:

- verify the GPIO mapping on your own board revision
- use 3.3V logic for GPIO signals
- avoid GPIO5 because of its display-reset role
- do not assume every exposed header pin is safe for arbitrary use
- power off the board before changing wiring

Different revisions of the Guition board may expose or assign pins differently.
