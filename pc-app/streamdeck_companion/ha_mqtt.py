"""Pont MQTT vers Home Assistant : complement instantane a ha_poller.py
pour les emplacements barre/texte/couleur - au lieu d'attendre le prochain
sondage REST (jusqu'a POLL_INTERVAL secondes), on souscrit aux topics
publies par l'integration Home Assistant `mqtt_statestream` et on pousse
la valeur des qu'un message arrive. ha_poller.py continue de tourner en
parallele (voir tray.py) comme filet de securite si mqtt_statestream
n'est pas configure cote HA ou si un message est manque - ce module ne
fait rien tant que le broker n'est pas renseigne dans Reglages.

Cote Home Assistant (configuration.yaml), il faut activer :

    mqtt_statestream:
      base_topic: homeassistant/state
      publish_attributes: true

`base_topic` doit correspondre au reglage "Sujet de base" de la page
Reglages de cette appli - c'est ce prefixe que ce module ecoute (topic
wildcard) pour retrouver l'etat de chaque entite (mqtt_statestream publie
un topic par attribut, ex ".../light/salon/attributes/rgb_color", plutot
qu'un seul JSON - d'ou la reconstruction incrementale ci-dessous)."""

from __future__ import annotations

import json
import logging
import threading

from . import ha_client as ha
from . import profiles as profile_utils
from .device_client import DeviceClient
from .runtime_state import STATE_STORE
from .state_adapters import update_home_assistant_entity

LOG = logging.getLogger("streamdeck_ha_mqtt")

DEFAULT_BASE_TOPIC = "homeassistant/state"
DEFAULT_PORT = 1883
# mqtt_statestream publie l'etat et CHAQUE attribut d'une entite comme des
# messages MQTT separes (voir _parse_topic) - un seul changement genere donc
# une rafale de plusieurs messages coup sur coup. Sans temporisation, on
# pousserait une couleur/valeur intermediaire (souvent juste "on" sans les
# attributs de couleur encore arrives) avant la bonne, d'ou un flash blanc
# visible avant que la teinte reelle ne s'affiche.
DEBOUNCE_SECONDS = 0.2


def _parse_topic(base_topic: str, topic: str) -> tuple[str, str] | None:
    """('domain.object_id', sous-chemin) depuis un topic mqtt_statestream,
    ou None si le topic n'est pas sous base_topic ou pas assez profond
    pour etre exploitable (ex juste base_topic/domain)."""
    prefix = base_topic.rstrip("/") + "/"
    if not topic.startswith(prefix):
        return None
    parts = topic[len(prefix):].split("/")
    if len(parts) < 3 or not parts[0] or not parts[1]:
        return None
    return f"{parts[0]}.{parts[1]}", "/".join(parts[2:])


class MqttBridge:
    def __init__(self, device_client: DeviceClient, mqtt_conf: dict):
        self.device_client = device_client
        self.base_topic = mqtt_conf.get("base_topic") or DEFAULT_BASE_TOPIC
        self.host = mqtt_conf.get("host", "")
        self.port = int(mqtt_conf.get("port") or DEFAULT_PORT)
        self.username = mqtt_conf.get("username", "")
        self.password = mqtt_conf.get("password", "")
        # etat reconstruit par entite (mqtt_statestream fragmente state +
        # attributs sur plusieurs topics) - meme forme que l'API REST HA,
        # pour reutiliser telles quelles ha_client.format_widget_value /
        # ha_client.light_color_hex.
        self._states: dict[str, dict] = {}
        self._pending_timers: dict[str, threading.Timer] = {}
        self._client = None

    @property
    def configured(self) -> bool:
        return bool(self.host)

    def start(self) -> None:
        if not self.configured:
            return
        import paho.mqtt.client as mqtt

        client = mqtt.Client()
        if self.username:
            client.username_pw_set(self.username, self.password)
        client.on_connect = self._on_connect
        client.on_message = self._on_message
        client.reconnect_delay_set(min_delay=1, max_delay=30)
        self._client = client
        try:
            client.connect(self.host, self.port, keepalive=30)
        except Exception:
            LOG.exception(
                "Connexion MQTT initiale echouee (%s:%s) - nouvelles tentatives automatiques en fond",
                self.host, self.port,
            )
            return
        client.loop_start()

    def _on_connect(self, client, _userdata, _flags, rc, *_args) -> None:
        if rc != 0:
            LOG.warning("Connexion MQTT refusee (code %s) - verifiez identifiants/hote", rc)
            return
        topic = self.base_topic.rstrip("/") + "/#"
        client.subscribe(topic)
        LOG.info("MQTT connecte (%s:%s), abonne a %s", self.host, self.port, topic)

    def _on_message(self, _client, _userdata, msg) -> None:
        parsed = _parse_topic(self.base_topic, msg.topic)
        if not parsed:
            return
        entity_id, subpath = parsed
        payload = msg.payload.decode("utf-8", errors="replace")
        state = self._states.setdefault(entity_id, {"state": "", "attributes": {}})
        if subpath == "state":
            state["state"] = payload
        elif subpath == "unit_of_measurement":
            state["attributes"]["unit_of_measurement"] = payload
        elif subpath.startswith("attributes/"):
            attr_name = subpath[len("attributes/"):]
            try:
                state["attributes"][attr_name] = json.loads(payload)
            except ValueError:
                state["attributes"][attr_name] = payload
        else:
            return
        self._schedule_push(entity_id, state)

    def _schedule_push(self, entity_id: str, state: dict) -> None:
        """Regroupe les messages d'une meme rafale (etat + attributs d'un
        seul changement d'entite) avant de pousser - annule tout push deja
        programme pour cette entite et en reprogramme un, pour ne pousser
        qu'une fois que la rafale semble terminee."""
        existing = self._pending_timers.get(entity_id)
        if existing is not None:
            existing.cancel()
        timer = threading.Timer(DEBOUNCE_SECONDS, self._push_entity, args=(entity_id, state))
        timer.daemon = True
        self._pending_timers[entity_id] = timer
        timer.start()

    def _push_entity(self, entity_id: str, state: dict) -> None:
        """Publie l'etat reconstruit puis conserve le push ecran historique.

        Le StateStore est alimente meme si le Stream Deck est deconnecte :
        l'etat applicatif ne doit pas dependre de la disponibilite du renderer.
        La logique d'affichage existante reste ensuite strictement conditionnee
        par ``device_client.connected`` comme avant.
        """
        self._pending_timers.pop(entity_id, None)
        update_home_assistant_entity(STATE_STORE, entity_id, state)
        if not self.device_client.connected:
            return
        active = self.device_client.active_profile()
        values: dict[int, str] = {}
        colors: dict[int, str] = {}
        for idx in range(profile_utils.SLOT_COUNT):
            slot = profile_utils.resolve_slot(active, idx)
            slot_type = slot.get("type", "bouton")
            if slot_type in ("barre", "texte") and slot.get("ha_entity") == entity_id:
                values[idx] = ha.format_widget_value(state, slot_type)

            action = slot.get("action") or {}
            if action.get("type") == "home_assistant" and slot.get("show_light_color"):
                target = action.get("target") or {}
                if target.get("domain") == "light" and target.get("entity_id") == entity_id:
                    colors[idx] = ha.light_color_hex(state)

        if values:
            self.device_client.schedule_push_values(values)
        if colors:
            self.device_client.schedule_push_slot_colors(colors)


def start_in_thread(device_client: DeviceClient, mqtt_conf: dict) -> MqttBridge | None:
    """Demarre le pont MQTT dans son propre thread si un hote est renseigne
    dans Reglages, sinon ne fait rien (None) - ha_poller.py reste alors le
    seul mecanisme de mise a jour des widgets HA."""
    bridge = MqttBridge(device_client, mqtt_conf or {})
    if not bridge.configured:
        return None
    thread = threading.Thread(target=bridge.start, daemon=True)
    thread.start()
    return bridge
