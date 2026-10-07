# Architecture

```
                         +-------------------------+
                         |  Stream Deck (ESP32-P4)  |
                         |  ESPHome + LVGL          |
                         |  - ecran tactile 1024x600|
                         |  - 36 emplacements + 3 encodeurs|
                         |  - Wi-Fi via ESP32-C6     |
                         +------------+-------------+
                                      |
                         API native ESPHome (chiffree,
                         Noise Protocol, port 6053)
                                      |
                +---------------------+---------------------+
                |                                           |
     +----------v-----------+                    +----------v-----------+
     |   Home Assistant       |                    |   Appli PC (Python)    |
     |   (integration ESPHome  |                    |   streamdeck_companion/|
     |    native - facultatif   |                    |   device_client.py     |
     |    pour ses propres      |                    |   (connexion directe   |
     |    automations)          |                    |    et permanente)       |
     +------------+-------------+                    +------------+------------+
                  |                                                |
                  | API REST HA (facultatif)          dashboard.py (config
                  | (etat live + services)             visuelle, port 8080)
                  |                                    + tray.py (icone barre
                  v                                    des taches)
     +------------+-------------+                                  |
     |  ha_client.py / ha_poller.py (sondage REST ~15s) -------------+
     |  + ha_mqtt.py (facultatif, instantane via mqtt_statestream)   |
     |  widgets barre/texte + action 'home_assistant'                |
     +--------------------------------------------------------------+
                                                                    |
                                                       actions locales :
                                                       raccourcis clavier,
                                                       lancement d'appli/jeu,
                                                       media, url
```

## L'appli PC comme point de configuration unique

Tout se regle dans l'appli PC (`http://127.0.0.1:8080`), en 2 pages pour
eviter la surcharge (esprit "gerer ses pages d'applications sur un
telephone") :
- **Accueil** (`/`) : un ou plusieurs **profils** (onglets), chacun une
  maquette fidele de l'ecran (memes proportions et disposition que le
  firmware) avec ses propres emplacements (36 possibles, bouton/barre/texte, icone,
  action) et 3 encodeurs, configurables via popup - les emplacements
  masques sont a part sous la maquette. Les emplacements affiches se
  deplacent/redimensionnent par glisser-depose sur une grille invisible de
  cases carrees (voir "Grille invisible redimensionnable" plus bas) - la
  seule page du quotidien.
  L'ecran bascule automatiquement sur le profil dont le declencheur
  correspond a l'application au premier plan sur le PC (voir "Profils par
  application" plus bas). Le type d'action `launch` propose une
  bibliotheque d'applications (grille avec recherche, applications
  detectees + personnalisees) plutot que de taper un chemin.
- **Reglages** (`/reglages`) : connexion, forme carre/rond, Home
  Assistant - demandee automatiquement au tout premier lancement
  (`dashboard_config.yaml` est cree vide par `tray.py`, plus besoin de
  copier un fichier `.example` a la main), puis rarement revisitee.

Un seul clic ("Enregistrer et envoyer a l'ecran") sauvegarde et pousse les
changements de la page courante (chaque page ne touche que sa portion de
`dashboard_config.yaml`, jamais les autres).

- `device_client.py` maintient une connexion permanente et directe a
  l'ecran (IP configuree une fois, pas de mDNS) : elle ecoute les
  emplacements/encodeurs ET sert a pousser la config du **profil actif**
  (libelle, icone, type, visibilite, valeur des widgets) - meme connexion,
  pas de reconnexion a chaque changement (de config comme de profil).
- `dashboard.py` (+ `templates/base.html`+`home.html`+`settings.html`,
  `static/dashboard.js`) sont les 2 pages web (thread Flask separe), qui
  communiquent avec `device_client.py` via `asyncio.run_coroutine_threadsafe`
  pour rester thread-safe.
- `profiles.py` : modele des profils (migration de l'ancien format,
  correspondance declencheur -> profil) - partage par `dashboard.py` et
  `device_client.py`.
- `profile_watcher.py` : sonde la fenetre au premier plan sur le PC toutes
  les ~1.5s (Windows uniquement) et bascule le profil actif en consequence.
- `ha_client.py`/`ha_poller.py` sondent l'API REST de Home Assistant
  (facultatif) toutes les ~15s pour rafraichir les emplacements type
  widget, et executent le type d'action `home_assistant` (appel de
  service). `ha_client.py::list_entities()` alimente aussi le picker
  d'entites recherchable de la popup d'emplacement (source d'un widget,
  cible d'une action `home_assistant`), avec des services courants
  curates par domaine (`COMMON_SERVICES`). Pour un bouton cible une
  ampoule (domaine `light`) avec "Afficher la couleur de l'ampoule"
  coche, le meme sondage pousse aussi une couleur de fond
  (`ha_client.py::light_color_hex()` - RGB reel, ou approxime depuis la
  temperature de couleur, ou blanc chaud generique) vers une 5e entite
  par emplacement (`Slot N - couleur`, voir `firmware/slots_*.yaml`). Un
  appui long sur ce meme bouton (evenement `hold_N`) ouvre un mode
  reglage en direct via les 3 encodeurs OU le tactile (teinte/chaleur/
  intensite, limite en frequence - `color_mode.py::ColorModeController`,
  extrait de `device_client.py` pour rester sous la limite de lignes par
  fichier), affichant un panneau a l'ecran avec un slider LVGL par axe -
  meme rendu (piste arrondie, meme epaisseur) et directement glissable au
  doigt, voir `firmware/color_mode_panel.yaml`. Les entites `number`
  `Mode couleur - */valeur` (`firmware/package.yaml`) restent la source
  de verite unique : les encodeurs les ecrivent via `number_command`
  (sens PC -> ecran), un glissement tactile les ecrit via `number.set`
  cote ecran (sens ecran -> PC, recu comme `NumberState` par
  `device_client.py::on_state` puis route vers
  `color_mode.py::handle_touch`, qui ignore les echos de ses propres
  ecritures pour ne pas dupliquer les appels a Home Assistant). Ferme par
  timeout ou par le bouton "X" flottant (`close_color_mode`). Un
  emplacement `barre` avec une source HA accepte aussi le tactile
  gauche/droite pour l'augmenter/diminuer directement
  (`ha_client.py::adjust_entity_percent()`, evenements
  `barre_inc_N`/`barre_dec_N`). Meme principe pour un encodeur configure en
  action `ha_adjust` (cible `up:<entite>`/`down:<entite>`,
  `device_client.py::_run_ha_adjust` -> `ha_client.py::adjust_encoder_entity()`)
  - etend l'ajustement par pas aux domaines sans service HA "+/-" tout fait
  (climate : pas de 0.5Â°C plutot que de pourcentage), pour que fan/cover/
  climate soient reellement reglables par un encodeur et pas seulement
  affiches (voir `encoder_sync.py` plus bas).
- `ha_popup.py` : popup tactile pour une action `home_assistant` de type
  `bouton` ciblant un `media_player` - un simple tap (pas un appui long)
  ouvre un panneau (`HaPopupController`, meme esprit que
  `ColorModeController`) au lieu d'appeler directement le service
  configure : interrupteur lecture/pause + precedent/suivant + curseur de
  volume (`firmware/ha_popup.yaml`/`ha_popup_panel.yaml`). Prerempli avec
  l'etat lu via l'API REST a l'ouverture, ferme par timeout (15s) ou "X"
  (`close_ha_popup`) ; s'exclut mutuellement avec le mode couleur (les
  deux panneaux ne s'affichent jamais ensemble). Les ampoules (`light`) et
  tout autre domaine gardent le tap = appel direct du service - seul
  l'appui long ouvre un panneau pour une ampoule (mode couleur ci-dessus).
- `ha_mqtt.py` : complement facultatif a `ha_poller.py` - si un broker
  MQTT est renseigne dans **Reglages**, souscrit aux topics publies par
  l'integration Home Assistant `mqtt_statestream` (un topic par etat/
  attribut, ex `<base_topic>/light/salon/attributes/rgb_color`) et
  reconstruit l'etat de chaque entite au fil des messages pour reutiliser
  telles quelles `ha_client.format_widget_value()`/`light_color_hex()`,
  poussant la valeur des la reception (latence quasi nulle) au lieu
  d'attendre le prochain sondage REST. `ha_poller.py` continue de tourner
  en parallele comme filet de securite (aucune regression si MQTT n'est
  pas configure ou si un message est manque).
- `app_volume.py` : volume par application et volume general Windows
  (pycaw) - `AudioUtilities.GetAllSessions()` reparcourue a chaque appel
  (pas de nom de session par executable directement, et les sessions
  vont/viennent avec les fenetres ouvertes). Alimente les actions d'encodeur
  `app_volume` (`actions.py::_app_volume`, cible `up:<processus>`/
  `down:<processus>`) et `app_mute` (`actions.py::_app_mute`, bascule le son
  de l'appli - typiquement sur l'appui en complement de `app_volume` sur la
  rotation) et le picker correspondant de la popup encodeur (route
  `/audio-sessions` de `dashboard.py`, partage entre les deux types).
- `encoder_sync.py` : fait correspondre la barre/etiquette d'un encodeur a
  la vraie valeur qu'il pilote, au lieu du compteur brut local de rotation
  (`encoder_source()` deduit ce que l'encodeur represente a partir de ses
  actions horaire/antihoraire deja configurees - si elles sont symetriques
  - meme cible, sens opposes - volume general Windows, volume d'une
  application, ou une entite Home Assistant `light`/`media_player`/`fan`/
  `cover`/`climate` (via `home_assistant` OU `ha_adjust`), cf
  `ha_client.py::_ENCODER_DISPLAY`/`read_entity_level()`). Relit la source
  toutes les ~2s et pousse pourcentage + etiquette vers deux nouvelles
  entites par encodeur (`Encodeur N - valeur reelle`/`- affichage`,
  `firmware/encoder_sync.yaml`) qui pilotent `bar_encoderN`/`lbl_encoderN` -
  le firmware n'ecrit plus ces
  widgets depuis le compteur brut de rotation (`on_clockwise`/
  `on_anticlockwise`, eux, restent inchanges et continuent de declencher
  les actions configurees).
- `icons.py` : catalogue de 172 icones (glyphes Material Icons, memes
  points de code que la police `font_icons` de `firmware/icon_font.yaml`,
  extraite de `package.yaml` - limite de lignes par fichier - une fois le
  catalogue etendu depuis un jeu initial de 22 pour couvrir des categories
  comparables au picker d'icones de Home Assistant) - repli pour les
  emplacements sans icone reelle disponible. Toute icone ajoutee dans
  `icons.py` doit aussi l'etre au `glyphs:` de `icon_font.yaml`, sinon elle
  s'affiche comme une case vide sur l'ecran. Le selecteur d'icone de la
  popup d'emplacement (`dashboard.js::renderIconPicker`) filtre ce
  catalogue par une barre de recherche (nom/libelle).
- `icon_extract.py`/`icon_server.py` : pour un emplacement `bouton` avec
  une action `launch`, l'ecran affiche automatiquement la vraie icone de
  l'executable (`.exe`/`.lnk`, via `icoextract` + Pillow, Windows
  uniquement) plutot qu'un glyphe generique. `icon_server.py` est un
  **second serveur HTTP separe** (port 8081, toutes interfaces) qui sert
  uniquement ces icones deja resolues - isole du dashboard principal
  (127.0.0.1 uniquement) pour que l'ecran (reseau local) puisse les
  telecharger sans exposer le reste de la configuration. Cote firmware,
  une entite `online_image` par emplacement (`firmware/slot_icons.yaml`,
  composant `http_request:`) est declenchee via `online_image.set_url`
  quand `Slot N - icone` recoit `REAL:<version>` plutot qu'un glyphe.
- `app_library.py`/`custom_apps.py`/`browse.py` : bibliotheque
  d'applications du picker "launch" - detection des raccourcis du menu
  Demarrer, applications personnalisees persistees dans
  `dashboard_config.yaml`, selecteur de fichier natif pour les ajouter.
- `tray.py` orchestre le tout (connexion, dashboard, serveur d'icones,
  sondeur HA REST, pont MQTT facultatif, sondeur de profil, sondeur de
  synchronisation des encodeurs) dans une icone de barre des taches, sans
  fenetre de terminal - le menu affiche le profil actuellement actif. Un
  verrou mono-instance (`_acquire_single_instance_lock`, simple bind TCP
  local sur un port fixe) empeche de lancer deux instances en meme temps -
  sinon chacune ouvre sa propre connexion a l'ecran et execute chaque
  action en double/triple.
- Home Assistant continue de voir l'appareil nativement (integration
  ESPHome auto-decouverte) et peut faire ses propres automations en
  parallele, mais ce n'est **pas necessaire** pour que le Stream Deck
  fonctionne avec le PC.

## Les 36 emplacements (au lieu de boutons fixes)

LVGL/ESPHome fige la disposition a la compilation - impossible de changer
le nombre de widgets sans reflasher. Le compromis retenu : 36 emplacements
PHYSIQUES (un par case de la grille invisible 9x4, voir plus bas) sont
toujours presents dans le firmware (`firmware/slots_*.yaml` +
`slot_widgets.yaml`), chacun reconfigurable a chaud (sans reflasher) via
5 entites :

- `text` libelle, `text` valeur (widgets), `text` icone (glyphe brut)
- `select` type (`bouton`/`barre`/`texte`)
- `switch` visible
- `text` grille (position/taille - voir "Grille invisible redimensionnable"
  plus bas)

Le firmware ne voit toujours QUE ces 36 emplacements - la bibliotheque
illimitee ci-dessous est une couche PC-side au-dessus, invisible pour lui.
36 = `GRID_COLS * GRID_ROWS` (9x4), la capacite maximale de la grille avec
des emplacements 1x1 - au-dela, il n'y a de toute facon plus de place a
l'ecran (`SLOT_COUNT` a ete porte de 16 a 36 pour ne plus etre une limite
artificielle plus basse que la grille elle-meme, voir
`scripts/gen_slot_entities.py`/`gen_slot_grid.py`/`gen_slot_widgets.py`/
`gen_slot_icons.py`).

### Bibliotheque illimitee + assignation (au lieu de boutons figes)

A l'origine, les emplacements physiques etaient a la fois le STOCKAGE
(libelle/icone/action) et l'AFFICHAGE (position, visible ou non) d'un
bouton - la seule facon d'avoir plus de boutons configures que
d'emplacements physiques etait... de ne pas pouvoir. Depuis, ces deux
roles sont separes (`profiles.py`) :

- **`profile["library"]`** : bibliotheque de boutons enregistres, PAS
  limitee - chaque entree (`default_library_entry()`) a un `id`
  stable et porte tout le contenu (libelle/icone/type/action/ha_entity/
  show_light_color). Creee/modifiee/supprimee librement depuis la popup
  d'un bouton (bouton "+" de `dashboard.js` pour en creer une).
- **`profile["slots"]`** : exactement `SLOT_COUNT` (36) emplacements
  PHYSIQUES (miroir 1:1 des objets LVGL du firmware), chacun ne stockant
  plus que sa position/taille de grille et **quelle entree de
  bibliotheque y est actuellement assignee** (`library_id`, ou `None` si
  l'emplacement est libre/invisible).
- **`profiles.py::resolve_slot(profile, idx)`** : combine les deux pour
  produire un emplacement "resolu" dans l'ANCIEN format tout-en-un (avec
  `visible` derive de `library_id is not None`) - c'est la seule fonction
  que `device_client.py` (`push_config`, `_resolve_action`,
  `_adjust_barre`), `ha_poller.py`, `ha_mqtt.py`, `icon_server.py` et
  `color_mode.py` utilisent pour lire un emplacement, ce qui a limite le
  changement a un point unique plutot que de toucher chaque consommateur
  independamment.
- **`profiles.py::migrate_profile_library()`** : migre transparemment un
  profil de l'ancien format (`_LEGACY_SLOT_COUNT` = 16 emplacements
  tout-en-un, fige independamment de `SLOT_COUNT`) vers le nouveau au
  premier chargement - chaque ancien emplacement devient une entree de
  bibliotheque, assignee au meme emplacement physique s'il etait visible
  (aucune perte de configuration existante). Ne s'execute qu'une fois
  (garde sur `"library" in profile`).
- **`profiles.py::ensure_slot_count()`** : complete `profile["slots"]`
  jusqu'a `SLOT_COUNT` avec des emplacements vides (`library_id: None`) -
  independant de la migration ci-dessus, pour que les profils DEJA migres
  (avant que `SLOT_COUNT` ne passe de 16 a 36) recuperent les emplacements
  physiques supplementaires sans dupliquer d'entrees de bibliotheque.
  Appele a chaque chargement (`migrate_profiles()`).
- **Cote JS** (`dashboard.js`) : afficher/retirer un bouton de l'ecran se
  fait par glisser-depose (assigne/libere un `library_id` sur
  `slots[i]`), plus par une case a cocher "Visible" dans la popup (jugee
  peu pratique) - `library` est rendue comme la section "bibliotheque"
  (les entrees NON assignees a un emplacement), l'ecran comme les
  emplacements AVEC une entree assignee. Supprimer une entree
  (`removeLibraryEntry()`) libere automatiquement l'emplacement physique
  qui la referencait.

### Grille invisible redimensionnable (facon "sections" Home Assistant)

Plutot qu'une grille figee a une seule taille de tuile (l'ancien systeme,
4 colonnes x 4 lignes de tuiles identiques), l'ecran est decoupe en une
grille invisible de **9 colonnes x 4 lignes de cases carrees** (96px,
espacement 12px - `firmware/package.yaml::action_grid`, 960x420, centree
sur l'ecran de 1024x600). Un emplacement peut occuper 1 ou plusieurs cases
(`colspan`/`rowspan`), deplace/redimensionne par glisser-depose dans
`dashboard.js` (grille CSS native `grid-column`/`grid-row: span N`, plus
un repere de redimensionnement par tuile - collision detectee cote JS
avant tout depot/redimensionnement, voir `hasCollision()`).

- **Modele de donnees** : chaque `slot` a un champ `grid` = `{col, row,
  colspan, rowspan}` (`profiles.py::default_grid()` - disposition par
  defaut : range dans l'ordre de lecture, 1x1 case ; `GRID_COLS`/
  `GRID_ROWS` doivent rester coherents avec le firmware et
  `dashboard.js`).
- **Poussee vers l'ecran** : `device_client.py::push_config()` envoie une
  seule entite texte compacte par emplacement (`Slot N - grille`, format
  "colonne,ligne,largeur_cases,hauteur_cases", ex "2,1,3,2").
- **Cote firmware** (`firmware/slot_grid_1.yaml`/`slot_grid_2.yaml`, deux
  fichiers generes par `scripts/gen_slot_grid.py` pour rester sous 500
  lignes chacun avec 36 emplacements) : le lambda `on_value` de chaque entite
  parse ce CSV, calcule la position/taille en pixels (case=96px,
  espacement=12px) et repositionne/redimensionne le bouton de
  l'emplacement (`lv_obj_set_pos`/`lv_obj_set_size`) ainsi que ses
  sous-widgets (titre, barre, zones tactiles gauche/droite) en proportion
  - tout ceci en direct, sans reflasher. `firmware/slot_widgets.yaml`
  (genere par `scripts/gen_slot_widgets.py`) ne fixe plus qu'une position/
  taille par defaut (1x1, avant le premier push du PC) ; `action_grid` n'a
  plus de `layout: flex` (chaque bouton est positionne individuellement
  via `align: top_left` + x/y/width/height explicites).

### Carte meteo (widget dedie, anime)

Widget independant des emplacements generiques (au plus un par
profil, cle `weather` du profil - voir `profiles.py::default_weather()`),
partageant la meme grille invisible (meme mecanisme de position/taille
compact que les emplacements) mais avec son propre contenu/sa propre
popup de configuration (entite HA `weather.*`).

- **PC** (`streamdeck_companion/weather.py`) : traduit la condition d'une
  entite `weather.*` (`sunny`/`rainy`/`snowy`/... - vocabulaire standard
  Home Assistant) en `(icone, style d'animation)` via `_CONDITION_MAP`,
  et l'attribut `temperature` (PAS l'etat lui-meme, qui est la condition
  textuelle) en texte forme. `ha_poller.py` sonde l'entite configuree
  (si la carte est visible) a la meme cadence que les widgets `barre`/
  `texte` et pousse icone/style/temperature via
  `device_client.py::push_weather_display()` - separe de `push_config()`
  (position/visibilite) pour ne pas re-pousser la geometrie a chaque
  rafraichissement.
- **Firmware** (`firmware/weather_card.yaml`, genere par
  `scripts/gen_weather_card.py` ; le bouton de la carte lui-meme vit dans
  `slot_widgets.yaml` en tant que 17e widget de `action_grid` - voir le
  commentaire de `gen_weather_card.py` pour le pourquoi, `!include` ne
  remplacant qu'une seule cle) : ne connait pas Home Assistant, se
  contente d'afficher/animer selon le style recu (`Meteo - animation`).
  Un pool d'objets LVGL pre-declares (gouttes de pluie, flocons, rayons de
  soleil, etoiles, nuages) est deplace/montre/cache par une unique boucle
  `interval:` (90ms, `globals: weather_tick/weather_style/weather_w/
  weather_h`) plutot que par l'API d'animation LVGL (`lv_anim_t`),
  volontairement evitee : sa disponibilite/signature exacte depend trop
  precisement de la version LVGL packagee par ESPHome pour etre fiable
  sans pouvoir compiler/tester directement sur le materiel - seules des
  primitives deja eprouvees ailleurs dans ce firmware sont utilisees
  (`lv_obj_set_pos`/`lv_obj_set_size`, `lv_obj_set_style_bg_opa`,
  `lv_obj_add_flag`/`clear_flag(LV_OBJ_FLAG_HIDDEN)`).
- **Batterie des peripheriques** (demande dans la meme discussion) :
  etudiee, non implementee - voir "Limitations connues" du README pc-app
  (le SDK Corsair iCUE n'expose pas la batterie officiellement, et le
  contournement par lecture memoire necessite un acces a la machine
  cible pour trouver l'adresse exacte).

## Profils par application

Un Stream Deck du commerce change de grille selon l'application active -
c'est le principal ecart avec une solution maison basique, comble ici par
un systeme de profils :

- Chaque profil (`dashboard_config.yaml`, cle `profiles`) a un `name`, un
  `trigger` optionnel (`{process: "nom.exe"}` ou `null`) et sa propre paire
  `slots`/`encoders`. Le premier profil sans `trigger` sert de repli.
- `profile_watcher.py::run_forever()` tourne dans son propre thread
  (Windows uniquement) : toutes les ~1.5s, il identifie le processus de la
  fenetre au premier plan (`win32gui.GetForegroundWindow()` +
  `win32process.GetWindowThreadProcessId()` + `psutil`), le compare aux
  declencheurs via `profiles.match_profile()`, et appelle
  `device_client.schedule_set_active_profile()` si le profil correspondant
  a change - qui pousse alors sa config vers l'ecran (meme mecanisme que
  `push_config()`) et redirige la resolution des actions (`_resolve_action`)
  vers ce nouveau profil, pour que les boutons physiques declenchent bien
  les actions du profil affiche.
- **Bascule manuelle** : `device_client.manual_override` (nom de profil ou
  `None`) est mis a jour par les boutons "Forcer ce profil"/"Automatique"
  de la page web (`/profiles/force`, `/profiles/auto`) ; quand il est
  renseigne, `profile_watcher.py` n'y touche plus jusqu'a "Automatique".
- La page web sonde `/profiles/status` toutes les ~3s pour afficher (point
  vert sur l'onglet, texte de statut) quel profil est reellement actif sur
  l'ecran, independamment de l'onglet en cours d'edition.
- Migration transparente : `profiles.migrate_profiles()` convertit une
  config pre-profils (`slots`/`encoders` a la racine, format d'avant ce
  chantier) en un unique profil "Defaut" au premier chargement.

## Flux "emplacement -> PC"

1. L'utilisateur touche un emplacement de type `bouton` sur l'ecran (LVGL)
   ou tourne un encodeur.
2. Le firmware declenche une entite `event:` (`event.trigger`).
3. `device_client.py` recoit l'etat via sa connexion permanente
   (`subscribe_states`), retrouve l'action configuree (emplacement ou
   sens/appui d'encodeur) dans `dashboard_config.yaml` et l'execute soit
   localement (`actions.py` : raccourcis/lancement/media/url), soit via
   Home Assistant (`ha_client.py::call_service` pour le type d'action
   `home_assistant`).
4. En bonus, Home Assistant peut aussi ecouter la meme entite `event:`
   pour ses propres automations, independamment (voir
   `home-assistant/example_automations.yaml`).

## Flux "PC -> ecran"

- **Config des emplacements + forme** : `dashboard.py` (page "Enregistrer
  et envoyer a l'ecran") appelle `device_client.schedule_push()`, qui
  pousse libelle/icone/type/visibilite de chaque emplacement du **profil
  actif** + la forme (voir "Profils par application").
- **Valeur des widgets** (`barre`/`texte`) : `ha_poller.py` sonde Home
  Assistant toutes les ~15s et appelle
  `device_client.schedule_push_values()` pour ne rafraichir que les
  entites `text.slot_N_valeur` concernees (sans re-pousser tout le reste).
  Si un broker MQTT est configure, `ha_mqtt.py` appelle la meme methode
  des la reception d'un message `mqtt_statestream` (voir plus haut) - les
  deux mecanismes coexistent, MQTT n'etant qu'un raccourci plus rapide.
- **Statut / info generique depuis Home Assistant** : HA peut aussi
  appeler directement le service `text.set_value` sur
  `text.streamdeck_statut_pc` (voir `home-assistant/example_automations.yaml`).

## Design

L'interface LVGL reprend la palette et les typographies du design system
du projet : fond navy `#0B1929`, cartes ocean
`#0F2942`/bordures slate `#1A3A52`, accent signal unique `#00B4D8`,
Space Grotesk pour les titres, Inter pour le corps, JetBrains Mono pour les
valeurs numeriques (volts, valeurs d'encodeurs...), Material Icons pour
les icones d'emplacement. Contexte "Outils perso" : pas de couleur ember
(reservee au sport), statuts en green-tech.

