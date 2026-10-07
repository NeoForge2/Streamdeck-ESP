"""Mode reglage couleur/chaleur/intensite par appui long sur un emplacement
lie a une ampoule Home Assistant (voir device_client.py::on_state) :
encodeur 1 = teinte, encodeur 2 = temperature de couleur, encodeur 3 =
luminosite, appliques en direct sur l'ampoule (limite en frequence pour ne
pas spammer Home Assistant), avec un apercu couleur pousse sur le bouton
lui-meme et 3 barres affichees sur l'ecran (voir firmware/package.yaml).
Sort automatiquement apres TIMEOUT secondes d'inactivite, ou via le bouton
"X" flottant (evenement 'close_color_mode').

Extrait de device_client.py (limite de lignes par fichier) : opere sur
l'instance DeviceClient qui le possede (`dc`), via ses attributs deja
publics (client/connected/entity_keys/config/push_slot_colors...).
"""

from __future__ import annotations

import colorsys
import logging
import time

from . import ha_client
from . import profiles as profile_utils

LOG = logging.getLogger("streamdeck_client")

SWITCH_NAME = "Mode couleur actif"
# Entites number pilotant les 3 barres du panneau affiche a l'ecran - jamais
# lues, seulement ecrites (voir firmware/package.yaml).
NUMBER_NAMES = {
    "hue": "Mode couleur - teinte (valeur)",
    "kelvin": "Mode couleur - chaleur (valeur)",
    "brightness": "Mode couleur - intensite (valeur)",
}
# Sens inverse - pour retrouver l'axe depuis le nom d'entite recu dans un
# NumberState (voir device_client.py::on_state et handle_touch ci-dessous).
NUMBER_NAME_TO_AXIS = {name: axis for axis, name in NUMBER_NAMES.items()}

TIMEOUT = 10.0
MIN_INTERVAL = 0.12
HUE_STEP = 10
KELVIN_STEP = 100
KELVIN_MIN, KELVIN_MAX = 2000, 6500
BRIGHTNESS_STEP = 5


class ColorModeController:
    """Une instance par DeviceClient (voir DeviceClient.__init__), detient
    l'etat du mode couleur en cours (ou son inactivite)."""

    def __init__(self, dc):
        self.dc = dc
        self.slot: int | None = None
        self.entity: str | None = None
        self.hue = 0.0
        self.kelvin = 3000.0
        self.brightness = 100.0
        self.last_activity = 0.0
        self._last_sent: dict[str, float] = {}

    def enter(self, slot_idx: int) -> None:
        """Appui long sur un emplacement lie a une ampoule (action
        home_assistant, domaine light, "Afficher la couleur..." coche) :
        les 3 encodeurs pilotent alors teinte/temperature/luminosite en
        direct, jusqu'a fermeture (bouton "X" ou timeout, voir
        check_timeout)."""
        active = self.dc._active_profile()
        if not (0 <= slot_idx < profile_utils.SLOT_COUNT):
            return
        slot = profile_utils.resolve_slot(active, slot_idx)
        action = slot.get("action") or {}
        target = action.get("target") or {}
        if action.get("type") != "home_assistant" or target.get("domain") != "light" or not slot.get("show_light_color"):
            return
        entity_id = target.get("entity_id")
        if not entity_id:
            return
        self.dc.ha_popup.close()  # les deux panneaux ne s'affichent jamais ensemble

        hue, kelvin, brightness = 0.0, 3000.0, 100.0
        ha_conf = self.dc.config.get("home_assistant") or {}
        client = ha_client.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))
        try:
            state = client.get_state(entity_id)
            if state:
                attrs = state.get("attributes") or {}
                hs = attrs.get("hs_color")
                if hs:
                    hue = float(hs[0])
                kelvin = float(attrs.get("color_temp_kelvin") or kelvin)
                raw_brightness = attrs.get("brightness")
                if raw_brightness is not None:
                    brightness = max(0.0, min(100.0, float(raw_brightness) / 255 * 100))
        except Exception:
            LOG.exception("Echec de lecture de l'etat initial pour le mode couleur (%s)", entity_id)

        self.slot = slot_idx
        self.entity = entity_id
        self.hue = hue
        self.kelvin = kelvin
        self.brightness = brightness
        self.last_activity = time.monotonic()
        self._last_sent = {}
        self._push_bars()
        self._push_switch(True)

    def exit(self) -> None:
        self.slot = None
        self.entity = None
        self._push_switch(False)

    def _push_switch(self, active: bool) -> None:
        if self.dc.client is None or not self.dc.connected:
            return
        key = self.dc.entity_keys.get(SWITCH_NAME)
        if key is not None:
            self.dc.client.switch_command(key, active)

    def _push_bars(self) -> None:
        """Met a jour les 3 barres du panneau affiche a l'ecran - appelee a
        l'entree du mode et a chaque cran d'encodeur, jamais limitee en
        frequence (juste une entite number optimiste, pas d'appel reseau HA
        derriere)."""
        if self.dc.client is None or not self.dc.connected:
            return
        values = {"hue": self.hue, "kelvin": self.kelvin, "brightness": self.brightness}
        for axis, value in values.items():
            key = self.dc.entity_keys.get(NUMBER_NAMES[axis])
            if key is not None:
                self.dc.client.number_command(key, value)

    def handle_touch(self, axis: str, value: float) -> None:
        """Reagit a un glissement tactile direct sur un slider du panneau
        (voir firmware/color_mode_panel.yaml) : l'ecran pousse sa propre
        valeur via number.set, recue ici comme un NumberState (voir
        device_client.py::on_state). Ignore les echos de nos propres
        _push_bars() (encodeur ou entree en mode couleur) - seul un ecart
        reel avec la valeur connue signale un vrai geste tactile, sinon
        chaque cran d'encodeur enverrait un appel HA en double via
        l'aller-retour de l'API."""
        if self.slot is None or self.entity is None:
            return
        current = {"hue": self.hue, "kelvin": self.kelvin, "brightness": self.brightness}.get(axis)
        if current is None or abs(value - current) < 0.5:
            return
        self.last_activity = time.monotonic()
        if axis == "hue":
            self.hue = value % 360
        elif axis == "kelvin":
            self.kelvin = max(KELVIN_MIN, min(KELVIN_MAX, value))
        else:
            self.brightness = max(0.0, min(100.0, value))
        self._push_preview()
        self._send_update(axis)

    def handle_encoder(self, enc_idx: int, direction: str) -> None:
        if direction not in ("clockwise", "anticlockwise"):
            return
        sign = 1 if direction == "clockwise" else -1
        axis = {0: "hue", 1: "kelvin", 2: "brightness"}.get(enc_idx)
        if axis is None:
            return
        self.last_activity = time.monotonic()
        if axis == "hue":
            self.hue = (self.hue + sign * HUE_STEP) % 360
        elif axis == "kelvin":
            self.kelvin = max(KELVIN_MIN, min(KELVIN_MAX, self.kelvin + sign * KELVIN_STEP))
        else:
            self.brightness = max(0.0, min(100.0, self.brightness + sign * BRIGHTNESS_STEP))
        self._push_preview()
        self._push_bars()
        self._send_update(axis)

    def _push_preview(self) -> None:
        """Apercu local immediat sur le bouton lui-meme (teinte + luminosite
        - la temperature de couleur n'est pas combinee dans l'apercu, un
        vrai bulbe RGB et un bulbe "blanc variable" ne melangent pas les
        deux, simplification volontaire pour ce petit indicateur)."""
        if self.slot is None:
            return
        r, g, b = colorsys.hsv_to_rgb(self.hue / 360, 1.0, max(0.15, self.brightness / 100))
        hex_color = f"#{int(r * 255):02X}{int(g * 255):02X}{int(b * 255):02X}"
        self.dc.push_slot_colors({self.slot: hex_color})

    def _send_update(self, axis: str) -> None:
        """Appelle Home Assistant pour l'axe modifie, limite en frequence
        (MIN_INTERVAL) pour ne pas le spammer si l'encodeur tourne vite -
        les crans sautes restent visibles dans l'apercu local (_push_preview,
        jamais limite) mais pas forcement repercutes individuellement sur
        l'ampoule reelle."""
        if self.entity is None:
            return
        now = time.monotonic()
        if now - self._last_sent.get(axis, 0.0) < MIN_INTERVAL:
            return
        self._last_sent[axis] = now
        ha_conf = self.dc.config.get("home_assistant") or {}
        client = ha_client.HomeAssistantClient(ha_conf.get("url", ""), ha_conf.get("token", ""))
        try:
            if axis == "hue":
                client.call_service("light", "turn_on", entity_id=self.entity, data={"hs_color": [self.hue, 100]})
            elif axis == "kelvin":
                client.call_service("light", "turn_on", entity_id=self.entity, data={"color_temp_kelvin": int(self.kelvin)})
            else:
                client.call_service("light", "turn_on", entity_id=self.entity, data={"brightness_pct": int(self.brightness)})
        except Exception:
            LOG.exception("Echec de la mise a jour %s pour %s", axis, self.entity)

    def check_timeout(self) -> None:
        if self.slot is None:
            return
        if time.monotonic() - self.last_activity > TIMEOUT:
            self.exit()
