# Appli compagnon PC

Deux pages, comme gerer les pages d'applications sur un telephone :

- **Accueil** : un ou plusieurs **profils** (onglets), chacun avec sa
  propre grille de 36 emplacements ET ses 3 encodeurs - chaque
  emplacement/encodeur se configure via sa propre popup (glisser-deposer
  pour reordonner les emplacements). L'ecran **bascule automatiquement**
  sur le bon profil selon l'application au premier plan sur le PC (ex : la
  grille change toute seule en passant sur OBS, Discord, un jeu...) - voir
  "Profils par application" plus bas. C'est la seule page dont vous avez
  besoin au quotidien.
- **Reglages** (icone &#9881;) : connexion a l'ecran, cle API, Home
  Assistant, forme des boutons - demandee automatiquement au tout premier
  lancement, puis on n'y revient quasiment plus.

Tourne en icone dans la barre des taches (pas de fenetre de terminal), se
connecte directement au Stream Deck (pas besoin de Home Assistant pour que
ca fonctionne - meme si HA continue de voir l'appareil nativement en
parallele, et peut en plus alimenter des widgets en temps reel, voir plus
bas).

## Installation

```bash
cd pc-app
python3 -m venv .venv
source .venv/bin/activate   # .venv\Scripts\activate sur Windows
pip install -r requirements.txt
```

Pas de fichier a copier a la main : au tout premier lancement, l'appli
cree `dashboard_config.yaml` automatiquement (vide) et vous redirige vers
la page **Reglages** pour renseigner l'IP de l'ecran et la cle API (meme
valeur que `firmware/secrets.yaml` ; l'IP se trouve dans Home Assistant :
l'appareil "Stream Deck" > Adresse IP). Une fois valide, vous arrivez sur
l'accueil et n'avez plus besoin d'y retoucher.

## Lancer au quotidien (recommande)

Icone de barre des taches, pas de terminal a garder ouvert :

```powershell
pythonw -m streamdeck_companion.tray
```

Pour qu'elle demarre automatiquement a l'ouverture de session Windows :

```powershell
powershell -ExecutionPolicy Bypass -File install_startup.ps1
```

Clic sur l'icone (ou "Configurer le Stream Deck" dans son menu) pour
ouvrir la page de configuration - `http://127.0.0.1:8080`.

## Lancer manuellement (sans icone, avec logs dans le terminal)

```bash
python -c "from streamdeck_companion.tray import main; main()"
```

## Les 2 pages

### Accueil (`/`)

Une maquette fidele de l'ecran (memes proportions 1024x600, meme
disposition header/grille/encodeurs/statut, tuiles carrees ou rondes selon
vos reglages) : ce que vous voyez dans le navigateur correspond vraiment a
ce qui s'affichera sur l'ecran physique, avant meme d'envoyer.

- Les boutons **affiches** apparaissent dans la maquette d'ecran, a la
  meme place qu'ils occuperont reellement.
- Sous la maquette, la **bibliotheque** liste tous les boutons enregistres
  qui ne sont pas actuellement affiches - PAS limitee, contrairement
  a l'ecran physique. Enregistrez-en autant que vous voulez (raccourcis,
  scenes HA, jeux...) pour les reutiliser plus tard, sans jamais etre
  bloque - seuls 36 au maximum peuvent etre affiches simultanement (limite
  materielle de l'ecran : 36 boutons physiques dans le firmware, un par
  case de la grille invisible 9x4).
- Cliquez une tuile (affichee ou dans la bibliotheque) pour ouvrir sa
  popup de reglages (libelle, icone, type, action) - un bouton "+" dans la
  bibliotheque pour en creer un nouveau.
- **Glissez-deposez** un bouton pour l'afficher/le retirer de l'ecran (le
  retirer ne le supprime pas, il retourne juste dans la bibliotheque) -
  bien plus direct qu'une case a cocher "Visible" a chercher dans une
  popup. Pour supprimer definitivement un bouton, ouvrez sa popup et
  cliquez "Supprimer".

"Enregistrer et envoyer a l'ecran" sauvegarde et pousse immediatement la
disposition (boutons affiches + encodeurs) vers l'ecran.

### Grille redimensionnable (facon "sections" Home Assistant)

L'ecran est decoupe en une grille **invisible** de cases carrees (9
colonnes x 4 lignes) : un emplacement peut occuper 1 ou plusieurs cases,
au lieu d'etre fige a une seule taille comme avant.

- **Deplacer** : glissez-deposez un bouton affiche n'importe ou sur la
  grille - il se repositionne a la case visee (aimante a la grille).
  Glissez-le sur la bibliotheque pour le retirer de l'ecran. Glissez un
  bouton de la bibliotheque sur la grille pour l'y afficher (assigne au
  premier emplacement physique libre).
- **Redimensionner** : tirez sur le petit repere en bas a droite d'un
  emplacement pour l'agrandir/reduire (en cases entieres), comme les
  widgets petit/moyen/grand d'un iPhone.
- **Pas de chevauchement** : deux emplacements ne peuvent pas occuper la
  meme case - un depot ou redimensionnement qui provoquerait un
  chevauchement est simplement refuse (l'emplacement reste ou il etait).

Cote firmware, chaque emplacement est repositionne/redimensionne en direct
(`firmware/slot_grid.yaml`, un lambda LVGL par emplacement) des que l'appli
PC pousse sa nouvelle disposition - aucun reflashage necessaire pour
changer l'agencement de l'ecran.

### Carte meteo (widget dedie, anime)

Au plus une par profil, elle partage la meme grille invisible que les 16
emplacements (glisser-deposer/redimensionner pareil) mais se configure a
part - cliquez la tuile "Meteo" (dans la maquette ou les emplacements
masques) pour choisir une entite `weather.*` Home Assistant.

Affiche, empiles verticalement et centres sur la carte : le libelle de
la condition en haut (ex "Pluie", "Ensoleille"), l'icone au milieu, puis
une grande temperature en bas (police 34pt) - agencement inspire a la
fois de `bramkragten/weather-card` (regroupement icone+temperature
compact plutot qu'ecarte aux extremites) et de `breezy-weather` (gros
chiffre "hero" sous un libelle de condition court), **animee selon la
condition** :

| condition Home Assistant | animation |
|---|---|
| `sunny` | soleil qui scintille (rayons) |
| `clear-night` | etoiles qui clignotent |
| `cloudy`/`partlycloudy`/`fog` | nuages qui derivent |
| `rainy`/`pouring`/`hail`/`lightning`/`lightning-rainy` | pluie qui tombe |
| `snowy`/`snowy-rainy` | neige qui tombe (avec une legere derive) |
| `windy`/`windy-variant`/`exceptional` | icone statique (pas d'animation dediee) |

La correspondance condition -> icone/animation est faite cote PC
(`streamdeck_companion/weather.py`, facile a etendre/corriger sans
reflasher), le firmware se contente d'afficher/animer selon le style
recu (`firmware/weather_card.yaml`) - une seule boucle `interval:` (90ms)
anime les elements (gouttes/flocons/rayons/etoiles/nuages) deja presents
sur l'ecran, en les deplacant/montrant/cachant selon la condition, sans
recourir a l'API d'animation LVGL (`lv_anim_t`) dont le comportement exact
est trop incertain sans pouvoir compiler/tester directement sur le
materiel.

**Icone** : illustration [amCharts](https://www.amcharts.com/free-animated-svg-weather-icons/)
(CC-BY 4.0) convertie une fois en PNG (`scripts/convert_weather_icons.py`,
sources dans `scripts/weather_icons_src/`) et servie par `icon_server.py` -
les animations SMIL/CSS de ces SVG ne peuvent pas s'executer sur l'ecran
(LVGL/ESP32 ne rend pas de SVG anime), seule l'illustration statique est
recuperee, notre propre animation (pluie/neige/rayons ci-dessus) tourne
autour. `sunny`/`clear-night`/`cloudy`/`partlycloudy`/`fog`/`rainy`/
`pouring`/`hail`/`lightning`/`lightning-rainy`/`snowy`/`snowy-rainy` ont
une illustration dediee ; `windy`/`windy-variant`/`exceptional` retombent
sur un glyphe simple (pas d'illustration adaptee dans ce pack).

Necessite une integration meteo configuree dans Home Assistant (ex
"Meteo-France", "OpenWeatherMap", "Pirate Weather"...) exposant une
entite `weather.*`.

Les 3 encodeurs de la maquette sont cliquables comme les emplacements :
leur popup regle l'action de chacun des 3 sens (horaire, antihoraire,
appui).

### La barre de l'encodeur affiche la vraie valeur

Si le sens horaire et le sens antihoraire d'un encodeur sont symetriques
(meme cible, sens opposes), sa barre/etiquette affiche automatiquement la
**vraie valeur pilotee** au lieu d'un simple compteur brut -
`streamdeck_companion/encoder_sync.py` deduit ce que l'encodeur represente
a partir de ses deux actions deja configurees, sans champ de config
supplementaire :

| configuration de l'encodeur (horaire / antihoraire)                          | ce que la barre affiche                  | tourner l'encodeur regle vraiment la valeur ? |
|--------------------------------------------------------------------------------|-------------------------------------------|-------------------------------------------|
| `media` `vol_up` / `vol_down`                                                  | volume general Windows                    | oui (touche multimedia)                    |
| `app_volume` `up:<processus>` / `down:<processus>` (meme processus)           | volume de cette application                | oui                                         |
| `ha_adjust` `up:<entite>` / `down:<entite>` (meme entite `light`/`media_player`/`fan`/`cover`/`climate`) | valeur reelle de l'entite | oui - ajustement par pas via `ha_client.py::adjust_encoder_entity()`, recommande pour ces domaines |
| `home_assistant` sur la meme entite (meme domaines)                            | valeur reelle de l'entite                  | seulement si le service configure ajuste bien la valeur (ex `light.toggle` ne fait qu'allumer/eteindre) |

Sans configuration symetrique reconnue, la barre reste neutre (aucune
valeur brute affichee). La synchronisation est relue toutes les ~2s
(`encoder_sync.run_forever`) - Windows uniquement pour `media`/`app_volume`
(pycaw), toutes plateformes pour `ha_adjust`/`home_assistant`.

**Pourquoi `ha_adjust` plutot que `home_assistant` pour fan/cover/climate ?**
Contrairement au volume (`media_player.volume_up`/`volume_down`, sans
parametre), la plupart des domaines HA n'ont pas de service "+/-" tout
fait - regler un volet ou un thermostat necessite d'envoyer une valeur
(ex `climate.set_temperature` avec un parametre `temperature`), ce que le
format compact `domaine.service:entite` de `home_assistant` ne permet pas
(aucune place pour une donnee). `ha_adjust` contourne ca : il lit la valeur
actuelle de l'entite et calcule lui-meme le nouveau palier (1% pour
light/media_player/fan/cover, 0.5°C pour climate) a chaque cran.

## Profils par application

Au-dessus de la maquette, une barre d'onglets liste vos **profils** - chacun
une grille de 36 emplacements + 3 encodeurs independante. Un point vert sur
un onglet indique le profil **reellement affiche sur l'ecran en ce moment**.

- **Creer un profil** : "+ Nouveau profil" - donnez-lui un nom et un
  **declencheur** (le nom du processus, ex `obs64.exe`). Un menu deroulant
  liste directement toutes les applications actuellement ouvertes sur
  votre PC (comme Alt+Tab) - choisissez la vôtre dedans, le declencheur et
  un nom de profil suggere se remplissent tout seuls. Pas besoin de
  connaitre le nom exact du `.exe`, ni de jongler entre cette page et
  l'application a detecter.
- **Bascule automatique** : des que l'application du declencheur passe au
  premier plan, l'ecran change de grille tout seul, sans intervention
  (`streamdeck_companion/profile_watcher.py`, sonde la fenetre active
  toutes les ~1.5s). Le profil sans declencheur (typiquement "Defaut")
  s'affiche quand aucun declencheur ne correspond.
  Le premier profil dont le declencheur correspond gagne, dans l'ordre
  de creation - evitez plusieurs profils avec le meme declencheur.
- **Forcer un profil manuellement** : le bouton "Forcer ce profil" fige
  l'ecran sur l'onglet actuellement affiche (pratique pour previsualiser un
  profil qu'on vient d'editer sans attendre que son application prenne le
  focus) ; "Automatique" a cote reprend la bascule normale.
- **Modifier/supprimer** un profil : cliquez l'icone crayon sur son onglet.
  Le profil sans declencheur ne peut pas etre supprime s'il ne reste que lui.

Chaque onglet garde ses propres modifications en memoire meme en changeant
d'onglet - "Enregistrer et envoyer a l'ecran" sauvegarde **tous les profils
d'un coup**, mais ne pousse vers l'ecran que celui reellement actif (les
autres sont juste enregistres, prets a s'activer a leur tour).

### Reglages (`/reglages`)

Connexion (IP/port/cle API), forme des boutons (carre/rond, s'applique aux
36 emplacements), Home Assistant (URL + jeton). Des reglages qu'on ne
touche presque jamais une fois l'ecran configure - a l'ecart de la page
qu'on utilise au quotidien.

### Type d'emplacement (`bouton` / `barre` / `texte`)

- **bouton** : declenche une action au clic (voir tableau ci-dessous).
- **barre** : jauge 0-100, alimentee par l'etat d'une entite Home
  Assistant numerique (volume, luminosite, batterie...) - choisie dans une
  liste recherchable (voir "Choisir une entite Home Assistant" ci-dessous),
  pas besoin de connaitre l'entity_id exact.
- **texte** : affiche la valeur brute d'une entite HA + son unite (ex
  "21.5°C") - meme reglage de source.

Les widgets (`barre`/`texte`) sont rafraichis toutes les ~15 secondes par
`streamdeck_companion/ha_poller.py`, qui interroge l'API REST de Home
Assistant en arriere-plan (pas de websocket, suffisant pour quelques
entites). Si un broker MQTT est renseigne dans **Reglages**, les mises a
jour deviennent quasi instantanees - voir "Synchronisation instantanee via
MQTT" plus bas.

Dans la maquette de l'accueil, une tuile `barre` affiche une petite jauge
sous le libelle et une tuile `texte` affiche un espace reserve pour la
valeur ("--") - de quoi voir tout de suite quel type est configure sur
chaque emplacement. La jauge/valeur affichee dans le navigateur est un
espace reserve (pas la vraie valeur HA en direct : seul l'ecran physique
la recoit, via `ha_poller.py`).

## Types d'actions (`type` / cible)

| type              | cible                             | effet                                    |
|-------------------|------------------------------------|-------------------------------------------|
| `none`            | -                                  | rien configure                             |
| `keys`            | ex `ctrl+shift+s`                 | envoie une combinaison clavier             |
| `launch`          | chemin ou commande (arguments acceptes) | lance une application/un jeu - voir "Choisir une application" ci-dessous, pas besoin de taper le chemin a la main |
| `url`             | URL ou URI (`steam://...`, `discord://...`) | ouverte via le gestionnaire par defaut du systeme |
| `media`           | `play_pause`/`next`/`previous`/`vol_up`/`vol_down`/`mute` | touche multimedia |
| `home_assistant`  | emplacement : entite + service choisis dans la popup (voir "Choisir une entite Home Assistant" ci-dessous) ; encodeurs : format compact `domaine.service:entite`, ex `light.toggle:light.bureau` | appelle un service Home Assistant (bascule une lumiere/prise/scene...) - **sauf** pour un emplacement cible `media_player` : un tap ouvre une popup adaptee au lieu d'appeler le service directement, voir "Popup tactile adaptee" ci-dessous. Les ampoules restent en tap = bascule directe (reglage fin sur l'appui long, voir "Reglage couleur...") |
| `audio_output`    | emplacement : peripheriques choisis dans la popup (liste recherchable, `streamdeck_companion/audio_devices.py`) - identifiant opaque, pas destine a etre tape a la main | bascule le peripherique de sortie audio par defaut (casque/enceintes...) - Windows uniquement |
| `app_volume`      | encodeurs : `up:<processus>`/`down:<processus>` (ex `up:chrome.exe`), choisi dans une liste deroulante des applications ayant une session audio active (`streamdeck_companion/app_volume.py`) | regle le volume d'une application precise (et non le volume general) en tournant l'encodeur - Windows uniquement (pycaw) |
| `app_mute`        | encodeurs : nom du processus (ex `chrome.exe`), meme liste deroulante que `app_volume` | bascule le son de cette application - pratique sur l'appui d'un encodeur dont la rotation est deja en `app_volume` - Windows uniquement (pycaw) |
| `ha_adjust`       | encodeurs : `up:<entite>`/`down:<entite>` (ex `up:climate.salon`) | ajuste vraiment par pas (1% ou 0.5°C selon le domaine) la luminosite/volume/vitesse/position/temperature d'une entite `light`/`media_player`/`fan`/`cover`/`climate` - utile quand le domaine n'a pas de service HA sans parametre equivalent a `vol_up`/`vol_down` (ex un volet ou un thermostat), voir "La barre de l'encodeur affiche la vraie valeur" plus bas |

## Bibliotheque d'applications (type d'action `launch`)

Pour eviter d'avoir a connaitre/taper un chemin (pas accessible au grand
public), la popup d'un emplacement affiche une vraie bibliotheque
d'applications - grille avec icones et recherche, comme un logiciel de
Stream Deck du commerce - des que le type d'action est `launch` :

- **Applications ouvertes en ce moment** (point vert) : meme source que le
  declencheur de profil (`profile_watcher.py::list_open_windows()`) - le
  chemin exact de l'executable est resolu automatiquement, pratique quand
  l'appli tourne deja et que vous voulez juste pointer dessus sans chercher
  son raccourci.
- **Applications detectees** : les raccourcis du menu Demarrer (utilisateur
  + tous les utilisateurs), listes automatiquement
  (`streamdeck_companion/app_library.py`).
- **Barre de recherche** : filtre la grille en tapant les premieres lettres
  du nom. Une meme application presente dans plusieurs sources n'apparait
  qu'une fois (priorite a la version "ouverte en ce moment").
- **Tuile "+ Ajouter..."** : ouvre l'explorateur de fichiers Windows pour
  choisir un `.exe`/`.lnk` non liste (jeu portable, appli sans raccourci
  Demarrer) - l'application choisie **rejoint durablement la bibliotheque**
  (persistee dans `dashboard_config.yaml`, cle `custom_apps`), plus besoin
  de rechercher son chemin une seconde fois. Un lien "Retirer" sur ces
  tuiles personnalisees permet de les enlever de la bibliotheque.

Cliquer une tuile remplit automatiquement le chemin de lancement et le
libelle de l'emplacement. Le champ texte en dessous reste modifiable
directement pour les utilisateurs avances (ex: ajouter des arguments de
ligne de commande apres avoir choisi une application dans la grille).

Windows uniquement pour la detection automatique (necessite
`pywin32`/`winshell`, deja dans `requirements.txt` pour cette plateforme).
Sur les autres systemes, seule la detection automatique est indisponible -
la tuile "+ Ajouter..." (via un selecteur de fichier natif, `tkinter`) et
le champ texte libre restent utilisables partout.

## Choisir une entite Home Assistant

Comme pour les applications, la popup d'un emplacement propose une
**liste recherchable de vos entites Home Assistant** (`streamdeck_companion/ha_client.py::list_entities()`)
plutot que de taper un entity_id a la main - inspire de
[cgiesche/streamdeck-homeassistant](https://github.com/cgiesche/streamdeck-homeassistant) :

- **Source d'un widget** (type `barre`/`texte`) : tapez quelques lettres
  du nom (ex "temp", "volume", "salon"), cliquez l'entite trouvee - son
  `entity_id` remplit le champ automatiquement.
- **Action `home_assistant`** (type `bouton`) : meme recherche, puis un
  menu deroulant **"Service"** propose les services courants pour le
  domaine de l'entite choisie (ex `light.*` -> toggle/turn_on/turn_off,
  `media_player.*` -> play/pause/volume...) - pas besoin de connaitre le
  nom exact d'un service Home Assistant. Le champ compact
  `domaine.service:entite` en dessous se remplit tout seul, et reste
  modifiable directement pour les cas avances.

Necessite Home Assistant configure dans **Reglages** (URL + jeton d'acces
longue duree). Si la connexion echoue, un message clair s'affiche
(URL injoignable / jeton refuse) au lieu d'une erreur technique brute.

Les 3 encodeurs ont le meme picker, pour les actions `home_assistant` ET
`ha_adjust` : cherchez l'entite, choisissez le service si besoin - le sens
horaire/antihoraire (`up`/`down` pour `ha_adjust`) est deduit automatiquement
de la direction editee, plus besoin de le deviner/taper a la main. Le champ
texte compact reste modifiable directement pour les cas avances.

## Indicateur "Hors ligne"

Si une entite liee a un widget `texte` ou a la carte meteo ne repond plus
(Home Assistant injoignable, entite supprimee/renommee...) pendant au moins
2 sondages consecutifs (~30s), l'ecran affiche "Hors ligne" a la place de la
derniere valeur au lieu de rester silencieusement fige dessus - des que la
lecture reussit a nouveau, la vraie valeur revient immediatement. Un widget
`barre` (jauge sans texte visible, voir plus bas) reste a sa derniere
position connue sans indicateur dedie, faute d'un moyen propre de signaler
"hors ligne" sur une simple barre sans ajouter une nouvelle entite firmware.

## Synchronisation instantanee via MQTT (facultatif)

Par defaut, les widgets `barre`/`texte` et la couleur d'ampoule sont
rafraichis par sondage REST (`ha_poller.py`, ~15s). Pour une mise a jour
quasi instantanee, renseignez un broker MQTT dans **Reglages** : l'appli
demarre alors aussi `streamdeck_companion/ha_mqtt.py`, qui pousse la
valeur des qu'un message arrive (le sondage REST continue de tourner en
parallele comme filet de securite - rien a desactiver).

Cote **Home Assistant**, il faut publier les changements d'etat sur MQTT
via l'integration native `mqtt_statestream` (`configuration.yaml`) :

```yaml
mqtt_statestream:
  base_topic: homeassistant/state
  publish_attributes: true
```

Le `base_topic` doit correspondre exactement au champ **"Sujet de base"**
de la page Reglages (meme valeur par defaut : `homeassistant/state`).
Sans `mqtt_statestream` configure cote HA, le champ "Hote du broker" peut
rester vide - l'appli fonctionne alors comme avant (sondage REST seul).

**Note** : un changement des reglages MQTT necessite de redemarrer
l'appli (icone barre des taches) pour etre pris en compte - contrairement
aux reglages de connexion a l'ecran, la connexion MQTT n'est pas
re-etablie automatiquement en cours de route.

## Popup tactile adaptee (lecteurs multimedia)

Pour un emplacement `bouton` dont l'action `home_assistant` cible une
entite du domaine **`media_player`**, un tap sur l'ecran n'appelle plus
directement le service configure dans la popup - il ouvre a la place un
**mini-panneau** (inspire des popups de
[GalusPeres/HomeTiles](https://github.com/GalusPeres/HomeTiles)) :
interrupteur lecture/pause + boutons precedent/suivant + curseur de
volume (glissable au doigt).

Les **ampoules** (`light`) restent en tap = bascule directe
allumer/eteindre, comme n'importe quel autre domaine - leur reglage fin
(couleur/chaleur/intensite) se fait uniquement via l'**appui long**, voir
"Reglage couleur..." ci-dessous.

Le panneau se preremplit avec l'etat actuel de l'entite (lu via l'API
REST HA a l'ouverture), se ferme tout seul apres 15s d'inactivite ou via
le bouton "X", et ne s'affiche jamais en meme temps que le panneau du
mode couleur (appui long) - voir `streamdeck_companion/ha_popup.py` pour
la logique cote PC (`firmware/ha_popup.yaml`/`ha_popup_panel.yaml` cote
firmware). Pour tout autre domaine (`light`, `switch`, `scene`,
`script`...), le tap continue d'appeler directement le service
configure, comme avant. **Necessite de reflasher le firmware** (nouvelles
entites `ha_popup_*` et
panneau LVGL).

## Couleur d'une ampoule sur le bouton

Pour un emplacement `bouton` dont l'action `home_assistant` cible une
entite du domaine `light`, une case **"Afficher la couleur de l'ampoule
sur le bouton"** apparait sous le choix du service. Une fois cochee :

- `ha_poller.py` lit l'etat de l'ampoule a chaque sondage (~15s, meme
  cycle que les widgets) et pousse une couleur hex vers l'ecran
  (`streamdeck_companion/ha_client.py::light_color_hex()`).
- **Ampoule RGB** : sa vraie couleur (`attributes.rgb_color`).
- **Ampoule "blanc variable"** (temperature de couleur, sans RGB propre) :
  couleur approximee depuis `color_temp_kelvin`/`color_temp` (algorithme
  de Tanner Helland - assez fidele pour un indicateur visuel, pas une
  reproduction exacte).
- **Ampoule on/off simple** (aucune info de couleur) : un blanc chaud
  generique tant qu'elle est allumee.
- **Eteinte** : le bouton revient a sa couleur par defaut.

Cote firmware, chaque emplacement expose une 5e entite `text` ("Slot N -
couleur", format `#RRGGBB`) qui met a jour le fond du bouton via
`lvgl.obj.update` (voir `firmware/slots_*.yaml`) - **necessite de
reflasher le firmware** pour beneficier de cette fonctionnalite, un
`git pull` cote appli PC ne suffit pas.

## Reglage couleur/chaleur/intensite par appui long

Sur un emplacement `bouton` eligible (meme condition que ci-dessus :
action `home_assistant` domaine `light` + case "Afficher la couleur..."
cochee), un **appui long** sur l'ecran ouvre un mode reglage en direct via
les 3 encodeurs **ou directement au doigt sur l'ecran** :

- **Encodeur 1** / glissement sur la bande "Teinte" : teinte (hue).
- **Encodeur 2** / glissement sur la bande "Chaleur" : temperature de couleur.
- **Encodeur 3** / glissement sur la barre "Intensite" : intensite (luminosite).

Un panneau apparait au centre de l'ecran pendant le reglage : une bande
arc-en-ciel pour la teinte et une bande chaude/froide pour la temperature
de couleur, plus une barre pour l'intensite - les 3 avec le **meme rendu**
(piste pleine largeur arrondie, meme epaisseur) et un curseur qui se
deplace en direct, que ce soit via un cran d'encodeur ou un **glissement
tactile direct** sur la bande/barre correspondante (slider LVGL superpose
a la bande, voir `firmware/color_mode_panel.yaml`). Chaque changement met
aussi a jour l'apercu couleur sur le bouton immediatement et appelle Home
Assistant en direct (limite a ~8 appels/s max par axe pour ne pas le
spammer - voir `color_mode.py::_send_update`/`handle_touch`). Le mode se
ferme tout seul apres 10s d'inactivite, ou en touchant le bouton "X" qui
apparait en haut a droite de l'ecran pendant le reglage - les 3 cartes
encodeurs du bas d'ecran sont masquees pendant ce temps pour ne pas
melanger leur % normal avec le panneau. LVGL envoie un "click" juste apres
le "long press" au relachement du doigt : `device_client.py` l'ignore
(`_pending_hold_slot`) pour eviter que l'appui long declenche AUSSI
l'action normale du bouton (ex: eteindre/allumer l'ampoule en plus
d'ouvrir le mode couleur). **Necessite de reflasher le firmware** (nouvel
evenement `hold_N` par emplacement, panneau + sliders + bouton "X"
flottant et switch `Mode couleur actif`/entites `number` dans
`firmware/package.yaml`/`firmware/color_mode_panel.yaml`).

## Ajustement tactile des widgets "barre"

Un emplacement de type `barre` avec une source Home Assistant configuree
(champ "Source Home Assistant") accepte maintenant le tactile directement
sur l'ecran : toucher la **moitie gauche** diminue la valeur de 5%,
la **moitie droite** l'augmente - via deux zones tactiles invisibles
superposees au widget (voir `firmware/slot_widgets.yaml`), actives
uniquement quand l'emplacement est bien de type `barre`. Domaines pris en
charge : `light` (luminosite), `media_player` (volume), `fan` (vitesse),
`cover` (position) - voir `ha_client.py::adjust_entity_percent()`.
**Necessite de reflasher le firmware.**

## Icones

Le selecteur d'icone (popup d'un emplacement) propose un catalogue curate
de 172 glyphes Material Icons (`streamdeck_companion/icons.py`) - meme
police chargee dans le navigateur et sur l'ecran (`gfonts://Material
Icons`, embarquee dans `firmware/icon_font.yaml`), donc l'apercu
correspond a ce qui s'affiche reellement. Une barre de recherche filtre le
catalogue par nom (ex "volet", "batterie", "wifi"), meme principe que le
picker d'icones de Home Assistant. Pas d'upload d'image personnalisee
arbitraire (voir Limitations).

Le catalogue couvre l'eclairage/le confort (volets, rideaux, garage,
capteurs de porte/fenetre, cheminee, jacuzzi...), le climat et la meteo
(orage, nuageux, humidite...), l'informatique et les peripheriques
(ordinateur, clavier, souris, casque, niveaux de batterie, USB, carte SD,
Bluetooth...), la securite, le multimedia et les taches courantes -
n'importe quel glyphe Material Icons peut etre ajoute en plus (il faut
l'ajouter a la fois a `icons.py` et au `glyphs:` de
`firmware/icon_font.yaml`, sinon il s'affiche comme une case vide sur
l'ecran).

### Vraies icones d'appli/jeu

Pour un emplacement de type `bouton` avec une action **launch** (lancer
une appli/jeu), l'ecran affiche desormais automatiquement la **vraie
icone** de l'executable (Discord, Steam, un jeu precis...) a la place du
glyphe generique - rien a configurer, ca remplace le glyphe des que la
cible pointe vers un `.exe`/`.lnk` valide (sinon le glyphe manuel reste
affiche en repli). Fonctionnement (Windows uniquement) :

- `icon_extract.py` extrait l'icone reelle via `icoextract` (resource
  icone de l'executable, ou de la cible resolue + `IconLocation` d'un
  raccourci `.lnk`), l'aplatit sur le fond des boutons avec Pillow (evite
  de gerer la transparence PNG cote firmware) et met en cache en memoire.
- `icon_server.py` est un **second serveur HTTP separe**, sur le port
  8081 et ecoutant sur toutes les interfaces (contrairement au dashboard
  principal qui reste en 127.0.0.1 uniquement) - il ne sert QUE ces
  icones deja resolues (rien de sensible), pour que l'ecran (sur le
  meme reseau local) puisse les telecharger sans exposer le reste de la
  configuration (raccourcis, jeton Home Assistant...) sur le reseau.
- Cote firmware, chaque emplacement a une entite `online_image` dediee
  (`firmware/slot_icons.yaml`) declenchee via `online_image.set_url`
  quand `Slot N - icone` recoit une valeur `REAL:<version>` plutot qu'un
  glyphe (voir `firmware/slots_*.yaml`) - `device_client.py` pousse aussi
  l'URL locale de l'appli PC (`PC - URL locale`) a chaque connexion.

**Necessite de reflasher le firmware** (nouveau composant `http_request:`,
16 entites `online_image`, widgets image par emplacement). C'est la partie
la plus consequente ajoutee a ce firmware a ce jour (nouveau composant
jamais utilise auparavant dans ce projet) - n'ayant pas pu compiler ce
firmware depuis ce sandbox (pas d'installation ESPHome ici), la config a
ete verifiee ligne a ligne contre le schema reel du composant (cle par
cle, valeurs d'enum, methodes C++ disponibles) mais un premier
`esphome run` pourrait remonter une erreur de configuration a corriger -
contrairement a un crash materiel, ce serait detecte et affiche
**avant** le flash, sans risque pour l'appareil.

## Integration Home Assistant

Comme l'ecran expose ses entites nativement (integration ESPHome), Home
Assistant les voit et peut declencher ses propres automatisations en
parallele de cette appli (aucune configuration necessaire cote HA pour ca).

En renseignant l'URL et un jeton d'acces longue duree dans la page de
configuration, vous debloquez en plus :
- les emplacements type **barre**/**texte** (etat en direct d'une entite HA)
- le type d'action **home_assistant** (un bouton qui appelle un service HA)

Independamment, si vous voulez que Home Assistant puisse demander une
action a ce PC (ex: depuis une automation HA sans rapport avec le Stream
Deck), activez `receiver.token` dans `dashboard_config.yaml` et utilisez
`home-assistant/rest_command.yaml.snippet` + les exemples dans
`home-assistant/example_automations.yaml`. Rien de tout ceci n'est
necessaire pour que les emplacements/encodeurs du Stream Deck fonctionnent
- c'est un bonus.

## Limitations connues

- **Batterie des peripheriques (Corsair iCUE)** : etudiee, pas implementee.
  Le SDK officiel iCUE (`cuesdk` sur PyPI) n'expose PAS le niveau de
  batterie - limitation confirmee, demandee de longue date par la
  communaute Corsair sans reponse officielle. Seul contournement connu :
  lire la valeur directement dans la memoire du processus iCUE en cours
  d'execution (comme un projet communautaire trouve en recherche), ce qui
  necessite de scanner cette memoire SUR LA MACHINE CIBLE (ex. via Cheat
  Engine) pour trouver l'adresse exacte - specifique a la version d'iCUE
  et aux peripheriques branches, et casse a chaque mise a jour d'iCUE. Pas
  d'implementation fiable possible sans acces a une machine reelle pour
  determiner cette adresse au prealable.
- Les combinaisons clavier et touches multimedia passent par le module
  `keyboard`, qui necessite les droits administrateur/root sur certaines
  plateformes (et ne fonctionne pas sous Wayland).
- Sur macOS, `keyboard` n'emule pas les touches multimedia : seul le volume
  systeme est gere nativement (`osascript`). Pour play/pause/next sur macOS,
  il faudra integrer un outil tiers (ex. `nowplaying-cli`) dans
  `streamdeck_companion/actions.py::_media_macos`.
- `tray.py` n'a pu etre teste que hors environnement graphique Windows reel
  (logique de connexion/config verifiee en detail ; le rendu de l'icone
  lui-meme necessite un vrai bureau Windows pour etre confirme).
- Le changement de sortie audio (`audio_devices.py`, interface COM non
  documentee `IPolicyConfig::SetDefaultEndpoint`) est **confirme fonctionnel**
  sur une vraie machine Windows.
- Le mode reglage couleur (appui long, panneau avec bandes teinte/chaleur/
  intensite) et l'ajustement tactile des widgets "barre" sont **confirmes
  fonctionnels sur l'appareil reel** (les 3 encodeurs, y compris 2 et 3
  dont les appuis parasites initiaux ont ete corriges par le filtre de
  debounce `delayed_on_off: 25ms`).
- Un changement d'IP/port/cle API est repris automatiquement au prochain
  essai de reconnexion (jusqu'a ~10s, `device_client.py::connect()` relit
  la config a chaque tentative) - pas besoin de redemarrer l'icone de la
  barre des taches.
- Les vraies icones d'appli/jeu (`icon_extract.py`/`icon_server.py`,
  composant firmware `online_image`) n'ont pas pu etre testees sur
  l'appareil reel depuis ce sandbox (ni compilation ESPHome, ni Windows
  pour `icoextract`/l'extraction d'icone) - schema/logique verifies contre
  la source du composant, mais c'est la partie la plus consequente
  ajoutee a ce firmware, a tester avec attention au premier reflash. Le
  serveur d'icones (`icon_server.py`, port 8081) ecoute sur toutes les
  interfaces reseau (necessaire pour que l'ecran le joigne) - separe du
  dashboard principal (127.0.0.1 uniquement) pour ne rien exposer d'autre.
- Le bouton "media" (`play_pause` etc.) envoie une touche multimedia - il
  n'affiche pas l'etat de lecture reel (recuperer l'etat "en cours de
  lecture" de facon fiable et multi-plateforme demanderait une integration
  bien plus lourde). Pour un vrai indicateur en direct, utilisez un
  emplacement type `texte`/`barre` avec une source Home Assistant (ex un
  media_player HA) a la place.
- La grille (9x4 cases) est une limite fixe : impossible d'avoir plus de
  4 lignes de cases ou un emplacement plus large que 9 cases - largement
  au-dela de ce qu'un ecran de cette taille peut afficher lisiblement, mais
  a garder en tete si vous changez CELL/GAP/PITCH/COLS dans
  `scripts/gen_slot_grid.py` (a resynchroniser avec
  `package.yaml::action_grid` et `profiles.py::GRID_COLS/GRID_ROWS`).
- Pas d'upload d'icone personnalisee : le catalogue est un jeu curate de
  glyphes Material Icons (`streamdeck_companion/icons.py`, 172 icones).
  Pour en ajouter, il faut aussi ajouter le point de code correspondant au
  `glyphs:` de `font_icons` dans `firmware/icon_font.yaml`, sinon il
  s'affiche comme une case vide sur l'ecran.
- Les widgets Home Assistant (`barre`/`texte`) sont sondes par polling
  REST toutes les ~15s (`ha_poller.py`), pas en temps reel instantane par
  defaut - meme cadence pour la couleur d'une ampoule liee a un bouton
  (jusqu'a ~15s de decalage). Voir "Synchronisation instantanee via MQTT"
  plus haut pour une mise a jour quasi instantanee (necessite de
  configurer `mqtt_statestream` cote Home Assistant).
- L'approximation de couleur pour les ampoules "blanc variable" (sans
  RGB propre, juste une temperature de couleur) est une conversion
  standard temperature -> RGB (Tanner Helland), pas une calibration
  fidele a un modele d'ampoule precis - suffisant comme indicateur visuel.
- La couleur de bouton necessite de **reflasher le firmware** (nouvelle
  entite `Slot N - couleur` par emplacement, voir `firmware/slots_*.yaml`)
  en plus de mettre a jour l'appli PC.
- Le picker d'entites Home Assistant charge **toutes** les entites de
  l'installation (`GET /api/states`, pas de filtre par domaine cote
  serveur) - fonctionne bien jusqu'a quelques centaines d'entites, la
  recherche est limitee aux 50 premiers resultats affiches par requete.
  Testee avec des donnees simulees (pas de vraie instance Home Assistant
  accessible depuis le sandbox de developpement) - a confirmer sur votre
  installation reelle.
- Les services proposes par domaine dans le picker d'action
  `home_assistant` sont une liste courante curatee
  (`ha_client.py::COMMON_SERVICES`), pas une introspection complete de
  l'API Home Assistant - pour un service plus specifique/rare, tapez
  directement le format compact `domaine.service:entite` dans le champ en
  dessous.
- La detection automatique (`app_library.py`) ne liste que les raccourcis
  du menu Demarrer (utilisateur + tous les utilisateurs) - les applications
  sans raccourci Demarrer (portables, certaines apps du Microsoft Store)
  n'y apparaissent pas ; ajoutez-les via la tuile "+ Ajouter...". Detection
  Windows uniquement (le reste de la bibliotheque - ajout manuel, recherche,
  applications personnalisees - fonctionne partout). Logique testee avec
  des donnees simulees dans le sandbox de developpement (qui n'a pas acces
  a `pywin32`/`winshell`), pas encore confirmee de bout en bout sur une
  vraie machine Windows.
- Les icones de la bibliotheque d'applications sont un glyphe generique
  (pas l'icone reelle extraite du `.exe`) - extraire une vraie miniature
  par application demanderait une integration plus lourde
  (`win32gui.ExtractIconEx`), envisageable dans un futur chantier.
- La page de configuration a ete testee de bout en bout avec un navigateur
  headless (rendu de la maquette d'ecran et des masques, popup emplacement
  et popup encodeur, glisser-deposer dans les deux sens et entre les deux,
  bibliotheque d'applications - recherche, selection, ajout/retrait
  personnalise -, picker d'entites Home Assistant - recherche, selection,
  choix de service -, creation/edition/suppression de profils, sauvegarde,
  persistance apres rechargement) mais pas visuellement sur l'ecran
  physique - verifiez apres un push que les icones/couleurs/tailles vous
  conviennent et signalez tout ce qui parait cassé (ex une icone qui
  s'affiche comme une case vide).
- La bascule automatique de profil (`profile_watcher.py`) est Windows
  uniquement (necessite `pywin32`+`psutil` pour identifier la fenetre au
  premier plan) - sur les autres systemes, seule la bascule manuelle
  ("Forcer ce profil"/"Automatique") est disponible. Non verifiee sur une
  vraie machine Windows (logique de correspondance testee unitairement
  dans le sandbox de developpement, qui n'a pas de fenetre/bureau reel).
- La correspondance d'un declencheur se fait par **nom de processus exact**
  (ex `obs64.exe`), pas par titre de fenetre ni par plusieurs criteres -
  simple et previsible, mais deux applications qui partagent le meme nom de
  processus ne peuvent pas avoir de profils distincts.
- Le sondage de la fenetre active a lieu toutes les ~1.5s : la bascule
  automatique n'est donc pas instantanee (delai perceptible mais bref en
  changeant d'application).
