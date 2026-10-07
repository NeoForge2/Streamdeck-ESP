# Cablage des encodeurs rotatifs

## Header d'extension utilise

D'apres les photos produit de la carte Guition JC1060P470C_I_W :

```
Colonne gauche              Colonne droite
3V3                          5V
3V3                          5V
GND                          GND
GPIO1                        NC
GPIO2                        GPIO47
GPIO3                        GPIO46
GPIO4                        GPIO45
GPIO5   <- reset LCD interne GND
GPIO20                       3V3
GPIO32                       C6_U0RXD
GPIO33                       C6_U0TXD
I2C_SDA                      C6_IO9
I2C_SDL                      C6_CHIP_PU
```

**GPIO5 est deliberement evite** : d'apres une config ESPHome communautaire
verifiee pour cette carte, ce GPIO sert de `reset_pin` interne a la dalle
MIPI-DSI. Meme s'il apparait sur le header, le reutiliser pour un encodeur
risque un conflit avec l'ecran. De meme, `I2C_SDA`/`I2C_SDL` du header ne
sont volontairement pas utilises ici (bus tactile deja actif sur un bus I2C
interne separe : GPIO7/GPIO8) - a reserver pour un capteur I2C externe si besoin.

**Ce mapping vient des photos produit + d'une configuration communautaire,
pas du schema officiel Guition. Verifiez-le au multimetre/continuite avant
de souder quoi que ce soit.**

## Mapping retenu dans `firmware/streamdeck.yaml` (3 encodeurs)

| Encodeur | CLK (pin_a) | DT (pin_b) | SW (bouton) |
|----------|-------------|------------|-------------|
| 1        | GPIO1       | GPIO2      | GPIO3       |
| 2        | GPIO4       | GPIO20     | GPIO32      |
| 3        | GPIO33      | GPIO45     | GPIO46      |

GPIO47 reste libre (4e encodeur sans bouton, ou capteur/bouton additionnel).

## Cablage d'un encodeur type KY-040

```
Encodeur KY-040      Header Stream Deck
--------------        ------------------
CLK       --------->  pin_a de l'encodeur (ex GPIO1)
DT        --------->  pin_b de l'encodeur (ex GPIO2)
SW        --------->  pin bouton (ex GPIO3)
+         --------->  3V3
GND       --------->  GND
```

`pin_a`/`pin_b` sont configures en entree avec pull-up interne par le
composant `rotary_encoder` d'ESPHome (pas besoin de resistances externes sur
la plupart des modules KY-040, qui ont deja leurs propres pull-ups). Le
bouton est configure `INPUT_PULLUP` + `inverted: true` : appui = contact a la
masse.

## Ajouter un 4e encodeur (ou plus)

1. Cabler sur GPIO47 + un GND/3V3 libre + un pin supplementaire pour le
   bouton (aucun ne reste dispo dans ce mapping - un encodeur sans bouton,
   ou libererez un pin en retirant l'un des trois existants).
2. Dans `firmware/streamdeck.yaml`, dupliquer un bloc `sensor: platform:
   rotary_encoder`, son `binary_sensor: platform: gpio` (bouton) et son
   `event: platform: template`, en changeant les `id:` et les pins.
3. Ajouter une carte dans la page LVGL (bas d'ecran) pour afficher sa valeur,
   et une entree dans `pc-app/config.yaml` pour mapper ses evenements.
