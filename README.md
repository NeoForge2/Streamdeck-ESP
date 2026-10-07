# Stream Deck maison (ESP32-P4/C6 + encodeurs)

Firmware et outils pour transformer un ecran tactile Guition JC1060P470C_I_W
(7", 1024x600, ESP32-P4 + ESP32-C6) et des encodeurs rotatifs en Stream Deck
maison, pilotable a la fois depuis un PC et depuis Home Assistant.

## Structure du repo

```
firmware/          Config ESPHome (ecran, tactile, encodeurs, API native)
pc-app/            Appli compagnon Python (raccourcis, media, lancement d'applis)
home-assistant/    Exemples d'automations
docs/              Architecture et guide de cablage des encodeurs
```

## Demarrage rapide

Le hardware/l'UI vivent dans `firmware/package.yaml` (aucun secret, aucune
identite d'appareil). Deux facons de l'utiliser :

1. **Depuis un PC, en ligne de commande** (le depot est clone en local) :
   ```bash
   cd firmware
   cp secrets.yaml.example secrets.yaml   # remplir wifi + generer une cle API
   pip install esphome
   esphome run streamdeck.yaml            # inclut package.yaml en local
   ```
2. **Depuis l'add-on ESPHome Builder de Home Assistant** (pas besoin de
   cloner le depot) : collez `firmware/ha-device.yaml.example` dans
   l'editeur de l'appareil, avec vos identifiants Wi-Fi et une cle API.
   Ce fichier recupere `package.yaml` directement depuis GitHub
   (`packages: url/file/ref/refresh: 0s`) a chaque compilation : pour
   mettre a jour le firmware plus tard, il suffit de recompiler depuis HA,
   sans rien recopier.
3. **Appli PC** : voir `pc-app/README.md`. **C'est le seul endroit ou vous
   configurez** quoi (36 emplacements bouton/widget + 3 encodeurs, actions,
   icones, libelles, forme carre/rond) - apercu visuel glisser-deposer,
   un clic pour envoyer a l'ecran.
4. **Home Assistant** (facultatif) : l'appareil est decouvert automatiquement
   (integration ESPHome native, meme cle API que dans le fichier utilise
   ci-dessus) et peut faire ses propres automations en parallele - voir
   `home-assistant/example_automations.yaml`. En renseignant une URL/jeton
   HA dans l'appli PC, vous debloquez aussi des widgets a etat live
   (temperature, volume...) et des boutons qui pilotent directement vos
   appareils HA (lumieres, prises, scenes). Rien de tout ceci n'est
   necessaire pour que l'appli PC fonctionne.

Details d'architecture : `docs/ARCHITECTURE.md`. Cablage des encodeurs et
mapping des GPIO : `docs/WIRING.md`.

## Materiel

- Ecran Guition JC1060P470C_I_W (ESP32-P4 + ESP32-C6, tactile GT911)
- 36 emplacements carres/ronds (bouton, jauge ou texte) + 3 encodeurs
  rotatifs, ajustable dans `firmware/package.yaml`/`slots_*.yaml` et
  `docs/WIRING.md`


## A propos de `ruflo`

Le meta-framework d'orchestration multi-agents
[`ruvnet/ruflo`](https://github.com/ruvnet/ruflo) a ete initialise dans ce
depot a la demande explicite du proprietaire (`npx ruflo init`, dossiers
`.claude/`, `.claude-flow/`, `CLAUDE.md`, `.mcp.json`). Le developpement de ce
projet a ete fait directement, sans passer par son systeme de swarm/agents
(inutile pour un firmware ESPHome + un script Python). Ses hooks
(`.claude/settings.json`) interceptent chaque appel Bash/Write/Edit d'un
futur assistant sur ce depot et injectent parfois une pub pour un service
tiers ("sponsored capacity") - a desactiver si non souhaite.
