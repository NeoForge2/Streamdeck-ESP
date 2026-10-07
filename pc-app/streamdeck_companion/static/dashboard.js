/* Fichier principal (state partage + maquette d'ecran + popups
 * emplacement/encodeur) - voir aussi app-library.js (bibliotheque
 * d'applications du picker "launch") et profiles.js (onglets de profils),
 * charges apres ce fichier et qui referencent son state/ses fonctions.
 *
 * Maquette fidele de l'ecran (memes proportions/disposition que le
 * firmware) : les emplacements visibles s'affichent dans la grille de
 * l'ecran, les masques dans une "tray" a part (rien de tout ca n'apparait
 * sur l'ecran reel). Popup de config par emplacement/encodeur, glisser-
 * deposer (echange) entre n'importe quels deux emplacements. Plusieurs
 * profils (onglets) - chacun sa propre grille - basculent automatiquement
 * selon l'application au premier plan sur le PC (voir profile_watcher.py).
 * Pas de framework - vanilla JS. */

let profiles = JSON.parse(JSON.stringify(INITIAL_PROFILES));
let activeEditIndex = Math.max(0, profiles.findIndex((p) => p.name === ACTIVE_PROFILE_NAME));
let liveActiveProfileName = ACTIVE_PROFILE_NAME;
let manualOverride = MANUAL_OVERRIDE;
/* `slots`/`encoders` referencent toujours le profil en cours d'edition
 * (activeEditIndex) - memes tableaux, pas une copie : les mutations faites
 * via les popups s'appliquent donc directement a `profiles[activeEditIndex]`.
 * switchProfileTab() les re-pointe vers le profil choisi. */
let slots = profiles[activeEditIndex].slots;
let library = profiles[activeEditIndex].library;
let encoders = profiles[activeEditIndex].encoders;
let weather = profiles[activeEditIndex].weather;
/* Source du glisser-depose en cours (voir renderGrid()) :
 * {kind: "slot", index} (emplacement physique deja affiche, 0-15),
 * {kind: "library", id} (bouton de la bibliotheque, pas encore affiche),
 * {kind: "weather"}, ou null si aucun glisser en cours. */
let dragSrc = null;
let currentLibraryId = null;
let isNewLibraryEntry = false;
let currentEncoderIndex = null;
let editingProfileIndex = null;

const screenGrid = document.getElementById("slot-grid");
const hiddenTray = document.getElementById("hidden-tray");
const encoderMock = document.getElementById("encoder-mock");
const modal = document.getElementById("slot-modal");
const encoderModal = document.getElementById("encoder-modal");
const profileModal = document.getElementById("profile-modal");
const iconPicker = document.getElementById("icon-picker");

function renderIconPicker(selectedIcon, query) {
  iconPicker.innerHTML = "";
  const noneChoice = document.createElement("div");
  noneChoice.className = "icon-choice none-choice" + (selectedIcon ? "" : " selected");
  noneChoice.textContent = "Aucune";
  noneChoice.dataset.icon = "";
  noneChoice.addEventListener("click", () => selectIcon(""));
  iconPicker.appendChild(noneChoice);

  const q = (query || "").trim().toLowerCase();
  const choices = q
    ? ICON_CHOICES.filter((c) => c.label.toLowerCase().includes(q) || c.key.toLowerCase().includes(q))
    : ICON_CHOICES;

  choices.forEach((choice) => {
    const el = document.createElement("div");
    el.className = "icon-choice" + (choice.key === selectedIcon ? " selected" : "");
    el.textContent = choice.char;
    el.title = choice.label;
    el.dataset.icon = choice.key;
    el.addEventListener("click", () => selectIcon(choice.key));
    iconPicker.appendChild(el);
  });

  if (q && choices.length === 0) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = "Aucune icone trouvee.";
    iconPicker.appendChild(empty);
  }
}

function selectIcon(key) {
  document.querySelectorAll(".icon-choice").forEach((el) => {
    el.classList.toggle("selected", el.dataset.icon === key);
  });
  modal.dataset.selectedIcon = key;
}

function iconChar(key) {
  const found = ICON_CHOICES.find((c) => c.key === key);
  return found ? found.char : "";
}

/* Grille invisible de cases carrees (9 colonnes x 4 lignes - voir
 * firmware/slot_grid.yaml, package.yaml::action_grid et
 * profiles.py::GRID_COLS/GRID_ROWS, ces 3 endroits doivent rester
 * coherents) : un emplacement occupe 1 ou plusieurs cases ("colspan"/
 * "rowspan"), facon "sections" de Home Assistant, au lieu d'une grille
 * fixe a une seule taille de tuile. */
const GRID_COLS = 9;
const GRID_ROWS = 4;

function slotGrid(slot) {
  const g = slot.grid || {};
  return {
    col: Math.max(0, Math.min(GRID_COLS - 1, g.col ?? 0)),
    row: Math.max(0, Math.min(GRID_ROWS - 1, g.row ?? 0)),
    colspan: Math.max(1, Math.min(GRID_COLS, g.colspan ?? 1)),
    rowspan: Math.max(1, Math.min(GRID_ROWS, g.rowspan ?? 1)),
  };
}

function rectsOverlap(a, b) {
  return a.col < b.col + b.colspan && a.col + a.colspan > b.col &&
         a.row < b.row + b.rowspan && a.row + a.rowspan > b.row;
}

/* La carte meteo (widget dedie, au plus un par profil - voir weather.py)
 * participe a la meme grille que les emplacements physiques : on la
 * traite comme un emplacement "virtuel" d'index -1 partout ou la logique
 * de grille (collision, glisser-depose, redimensionnement) doit la
 * prendre en compte, pour eviter de dupliquer cette logique en deux
 * versions. Un emplacement physique (0-15) est "visible" s'il a une
 * entree de bibliotheque assignee (library_id) - la visibilite n'est
 * plus un booleen stocke separement (voir profiles.py::resolve_slot). */
function gridItem(index) {
  return index === -1 ? weather : slots[index];
}

function isPhysVisible(index) {
  return index === -1 ? !!weather.visible : !!slots[index].library_id;
}

/* True si `rect` (candidat de position/taille) chevauche un AUTRE
 * emplacement/la carte meteo visible que celui d'index `excludeIndex` -
 * empeche de deposer/redimensionner une carte par-dessus une autre. */
function hasCollision(excludeIndex, rect) {
  const indices = [-1, ...slots.map((_, i) => i)];
  return indices.some((i) => {
    if (i === excludeIndex) return false;
    return isPhysVisible(i) && rectsOverlap(rect, slotGrid(gridItem(i)));
  });
}

/* Premiere case libre (ordre de lecture) pour un emplacement colspan x
 * rowspan - utilise quand on rend un emplacement visible autrement que par
 * glisser-depose (ex: case a cocher "Visible" de la popup), pour eviter
 * qu'il chevauche silencieusement un autre emplacement deja affiche a la
 * meme position enregistree. */
function findFreeCell(excludeIndex, colspan, rowspan) {
  for (let row = 0; row <= GRID_ROWS - rowspan; row++) {
    for (let col = 0; col <= GRID_COLS - colspan; col++) {
      if (!hasCollision(excludeIndex, { col, row, colspan, rowspan })) return { col, row };
    }
  }
  return { col: 0, row: 0 };
}

function pointToCell(clientX, clientY) {
  const rect = screenGrid.getBoundingClientRect();
  const col = Math.floor(((clientX - rect.left) / rect.width) * GRID_COLS);
  const row = Math.floor(((clientY - rect.top) / rect.height) * GRID_ROWS);
  return {
    col: Math.max(0, Math.min(GRID_COLS - 1, col)),
    row: Math.max(0, Math.min(GRID_ROWS - 1, row)),
  };
}

function attachResizeHandle(tile, index) {
  const handle = document.createElement("div");
  handle.className = "tile-resize-handle";
  handle.draggable = false;
  handle.title = "Glisser pour redimensionner";
  handle.addEventListener("mousedown", (e) => {
    e.preventDefault();
    e.stopPropagation();
    const startX = e.clientX;
    const startY = e.clientY;
    const gridRect = screenGrid.getBoundingClientRect();
    const cellW = gridRect.width / GRID_COLS;
    const cellH = gridRect.height / GRID_ROWS;
    const g0 = slotGrid(gridItem(index));
    let finalColspan = g0.colspan;
    let finalRowspan = g0.rowspan;

    function onMove(ev) {
      const dCols = Math.round((ev.clientX - startX) / cellW);
      const dRows = Math.round((ev.clientY - startY) / cellH);
      let colspan = Math.max(1, Math.min(GRID_COLS - g0.col, g0.colspan + dCols));
      let rowspan = Math.max(1, Math.min(GRID_ROWS - g0.row, g0.rowspan + dRows));
      while (colspan > 1 && hasCollision(index, { col: g0.col, row: g0.row, colspan, rowspan })) colspan--;
      while (rowspan > 1 && hasCollision(index, { col: g0.col, row: g0.row, colspan, rowspan })) rowspan--;
      finalColspan = colspan;
      finalRowspan = rowspan;
      tile.style.gridColumn = `${g0.col + 1} / span ${colspan}`;
      tile.style.gridRow = `${g0.row + 1} / span ${rowspan}`;
    }
    function onUp() {
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
      gridItem(index).grid = { col: g0.col, row: g0.row, colspan: finalColspan, rowspan: finalRowspan };
      renderGrid();
    }
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  });
  tile.appendChild(handle);
}

/* Bibliotheque de boutons enregistres (voir profiles.py, module docstring)
 * - PAS limitee : on peut en enregistrer autant qu'on veut, seuls
 * GRID_COLS*GRID_ROWS (36) au maximum peuvent etre assignes a un
 * emplacement visible a la fois (limite materielle du firmware, un
 * emplacement physique par case de la grille). Un emplacement physique
 * (slots[i]) ne
 * stocke qu'une position/taille + QUELLE entree y est affichee
 * (library_id) - le contenu (libelle/icone/action...) vit uniquement
 * dans `library`, modifiable une seule fois et reutilisable partout. */
function libraryEntry(id) {
  return library.find((e) => e.id === id) || null;
}

function assignedLibraryIds() {
  return new Set(slots.map((s) => s.library_id).filter(Boolean));
}

function removeLibraryEntry(entryId) {
  const idx = library.findIndex((e) => e.id === entryId);
  if (idx !== -1) library.splice(idx, 1);
  slots.forEach((s) => { if (s.library_id === entryId) s.library_id = null; });
}

function makeSlotTile(entry, physIndex, isGrid) {
  const tile = document.createElement("div");
  tile.className = "slot-tile shape-" + (SHAPE === "rond" ? "rond" : "carre");
  if (entry.type && entry.type !== "bouton") tile.classList.add("has-widget");
  tile.draggable = true;

  if (isGrid) {
    const g = slotGrid(slots[physIndex]);
    tile.style.gridColumn = `${g.col + 1} / span ${g.colspan}`;
    tile.style.gridRow = `${g.row + 1} / span ${g.rowspan}`;
  }

  const icon = document.createElement("div");
  icon.className = "icon";
  const launchTarget = entry.action && entry.action.type === "launch" ? entry.action.target : "";
  if (launchTarget) {
    const img = document.createElement("img");
    img.src = "/preview-icon.png?target=" + encodeURIComponent(launchTarget);
    img.alt = "";
    img.onerror = () => { img.replaceWith(document.createTextNode(iconChar(entry.icon))); };
    icon.appendChild(img);
  } else {
    icon.textContent = iconChar(entry.icon);
  }
  tile.appendChild(icon);

  const label = document.createElement("div");
  label.className = "label";
  label.textContent = entry.label || "Bouton";
  tile.appendChild(label);

  /* Sur le vrai ecran, "barre"/"texte" affichent une jauge ou une valeur
   * en bas du bouton (masquees pour "bouton") - meme logique ici pour que
   * l'apercu distingue vraiment les 3 types. Pas de valeur live dans le
   * navigateur (c'est ha_poller.py qui pousse la vraie valeur a l'ecran) :
   * on affiche juste un espace reserve pour montrer OU et COMMENT elle
   * s'affichera. */
  if (entry.type === "barre") {
    const bar = document.createElement("div");
    bar.className = "widget-bar";
    bar.appendChild(document.createElement("span"));
    tile.appendChild(bar);
  } else if (entry.type === "texte") {
    const value = document.createElement("div");
    value.className = "widget-value";
    value.textContent = entry.ha_entity ? "--" : "";
    tile.appendChild(value);
  }

  tile.addEventListener("click", () => openModal(entry.id));
  tile.addEventListener("dragstart", () => {
    dragSrc = isGrid ? { kind: "slot", index: physIndex } : { kind: "library", id: entry.id };
  });
  tile.addEventListener("dragend", () => { dragSrc = null; });

  if (isGrid) attachResizeHandle(tile, physIndex);

  return tile;
}

function makeAddTile() {
  const tile = document.createElement("div");
  tile.className = "slot-tile add-tile";
  tile.title = "Ajouter un nouveau bouton a la bibliotheque";
  const plus = document.createElement("div");
  plus.className = "icon";
  plus.textContent = "+";
  tile.appendChild(plus);
  const label = document.createElement("div");
  label.className = "label";
  label.textContent = "Ajouter";
  tile.appendChild(label);
  tile.addEventListener("click", () => {
    const id = `lib-${Date.now()}-${Math.floor(Math.random() * 100000)}`;
    library.push({
      id, label: "Nouveau bouton", icon: "", icon_char: "", type: "bouton",
      action: { type: "none", target: "" }, action_field: "", ha_entity: "", show_light_color: false,
    });
    openModal(id, true);
  });
  return tile;
}

/* Deplacer/redimensionner se fait au niveau du CONTENEUR (grille ou tray)
 * plutot que par tuile : deposer un emplacement/la meteo deja affiche
 * change juste sa position ; deposer un bouton de la bibliotheque
 * l'assigne au premier emplacement physique libre. */
screenGrid.addEventListener("dragover", (e) => { e.preventDefault(); screenGrid.classList.add("drag-over"); });
screenGrid.addEventListener("dragleave", (e) => { if (e.target === screenGrid) screenGrid.classList.remove("drag-over"); });
screenGrid.addEventListener("drop", (e) => {
  e.preventDefault();
  screenGrid.classList.remove("drag-over");
  if (!dragSrc) return;
  const src = dragSrc;
  dragSrc = null;
  const target = pointToCell(e.clientX, e.clientY);

  if (src.kind === "library") {
    const freeIdx = slots.findIndex((s) => !s.library_id);
    if (freeIdx === -1) {
      alert("Tous les emplacements physiques de l'ecran sont deja utilises - retirez-en un d'abord (glissez-le vers la bibliotheque).");
      return;
    }
    let candidate = { col: target.col, row: target.row, colspan: 1, rowspan: 1 };
    if (hasCollision(freeIdx, candidate)) candidate = { ...findFreeCell(freeIdx, 1, 1), colspan: 1, rowspan: 1 };
    slots[freeIdx] = { library_id: src.id, grid: candidate };
    renderGrid();
    return;
  }

  const idx = src.kind === "weather" ? -1 : src.index;
  const item = gridItem(idx);
  const g = slotGrid(item);
  const candidate = {
    col: Math.min(target.col, GRID_COLS - g.colspan),
    row: Math.min(target.row, GRID_ROWS - g.rowspan),
    colspan: g.colspan,
    rowspan: g.rowspan,
  };
  if (hasCollision(idx, candidate)) return;
  if (idx === -1) weather.visible = true;
  item.grid = candidate;
  renderGrid();
});

hiddenTray.addEventListener("dragover", (e) => { e.preventDefault(); hiddenTray.classList.add("drag-over"); });
hiddenTray.addEventListener("dragleave", (e) => { if (e.target === hiddenTray) hiddenTray.classList.remove("drag-over"); });
hiddenTray.addEventListener("drop", (e) => {
  e.preventDefault();
  hiddenTray.classList.remove("drag-over");
  if (!dragSrc) return;
  if (dragSrc.kind === "weather") weather.visible = false;
  else if (dragSrc.kind === "slot") slots[dragSrc.index].library_id = null;
  dragSrc = null;
  renderGrid();
});

/* Carte meteo (widget dedie, voir weather.py/firmware/weather_card.yaml) -
 * meme grille/collision que les emplacements (voir gridItem(-1)), mais
 * contenu et popup de configuration distincts (pas d'action/type/icone a
 * choisir, juste une entite HA weather.* et une visibilite - c'est une
 * carte unique, pas un choix parmi une bibliotheque). */
function makeWeatherTile(isGrid) {
  const tile = document.createElement("div");
  tile.className = "slot-tile weather-tile shape-" + (SHAPE === "rond" ? "rond" : "carre");
  tile.draggable = true;

  if (isGrid) {
    const g = slotGrid(weather);
    tile.style.gridColumn = `${g.col + 1} / span ${g.colspan}`;
    tile.style.gridRow = `${g.row + 1} / span ${g.rowspan}`;
  }

  const icon = document.createElement("div");
  icon.className = "icon";
  icon.textContent = iconChar("wb_sunny");
  tile.appendChild(icon);

  const label = document.createElement("div");
  label.className = "label";
  label.textContent = weather.entity ? "Meteo" : "Meteo (non configuree)";
  tile.appendChild(label);

  const value = document.createElement("div");
  value.className = "widget-value";
  value.textContent = weather.entity ? "--°" : "";
  tile.appendChild(value);

  tile.addEventListener("click", openWeatherModal);
  tile.addEventListener("dragstart", () => { dragSrc = { kind: "weather" }; });
  tile.addEventListener("dragend", () => { dragSrc = null; });

  if (isGrid) attachResizeHandle(tile, -1);

  return tile;
}

function renderGrid() {
  screenGrid.innerHTML = "";
  hiddenTray.innerHTML = "";

  slots.forEach((phys, index) => {
    if (!phys.library_id) return;
    const entry = libraryEntry(phys.library_id);
    if (entry) screenGrid.appendChild(makeSlotTile(entry, index, true));
  });

  if (weather.visible) screenGrid.appendChild(makeWeatherTile(true));

  const assignedIds = assignedLibraryIds();
  library.forEach((entry) => {
    if (!assignedIds.has(entry.id)) hiddenTray.appendChild(makeSlotTile(entry, null, false));
  });

  if (!weather.visible) hiddenTray.appendChild(makeWeatherTile(false));

  hiddenTray.appendChild(makeAddTile());
}

function renderEncoderMock() {
  encoderMock.innerHTML = "";
  for (let i = 0; i < 3; i++) {
    const card = document.createElement("div");
    card.className = "encoder-mock-card";
    card.addEventListener("click", () => openEncoderModal(i));

    const icon = document.createElement("div");
    icon.className = "icon";
    icon.textContent = ""; /* volume_up, matche le firmware */
    card.appendChild(icon);

    const title = document.createElement("div");
    title.className = "title";
    title.textContent = `ENCODEUR ${i + 1}`;
    card.appendChild(title);

    const bar = document.createElement("div");
    bar.className = "encoder-mock-bar";
    const fill = document.createElement("span");
    bar.appendChild(fill);
    card.appendChild(bar);

    encoderMock.appendChild(card);
  }
}

function updateModalFieldsVisibility() {
  const type = document.getElementById("modal-type").value;
  document.getElementById("modal-action-fields").style.display = type === "bouton" ? "block" : "none";
  document.getElementById("modal-source-fields").style.display = type === "bouton" ? "none" : "block";
  updateLaunchPickerVisibility();
  updateHaSourceVisibility();
}

function updateLaunchPickerVisibility() {
  const isLaunch = document.getElementById("modal-action-type").value === "launch";
  document.getElementById("modal-app-library").style.display = isLaunch ? "block" : "none";
  document.getElementById("modal-action-target").placeholder = isLaunch
    ? "Choisissez une application ci-dessus, ou tapez une commande"
    : "ctrl+shift+s / https://... / vol_up / light.toggle:light.bureau";
  if (isLaunch) loadAppLibraryIfNeeded();
  updateHaActionVisibility();
  updateAudioPickerVisibility();
}

/* Edite une entree de bibliotheque (pas un emplacement physique - un
 * bouton se configure une fois et peut etre affiche/retire de l'ecran
 * librement par glisser-depose, voir renderGrid()). `isNew` : l'entree
 * vient d'etre creee par le bouton "+" (makeAddTile) - annuler la supprime
 * au lieu de la laisser trainer vide dans la bibliotheque. */
/* Ajoute temporairement `value` comme option d'un select s'il n'y est pas
 * deja - pour un bouton configure avant que le menu ne soit elague (voir
 * SLOT_ACTION_TYPES cote Python : ha_adjust/app_volume retires des choix
 * proposes sur un bouton, restent valides sur les encodeurs) : sans ca,
 * le navigateur affiche silencieusement une AUTRE option, et "Appliquer"
 * ecraserait le reglage existant sans que l'utilisateur y touche. */
function ensureSelectHasOption(selectId, value) {
  if (!value) return;
  const select = document.getElementById(selectId);
  if ([...select.options].some((o) => o.value === value)) return;
  const opt = document.createElement("option");
  opt.value = value;
  opt.textContent = `${value} (ancien reglage)`;
  select.insertBefore(opt, select.firstChild);
}

function openModal(entryId, isNew) {
  const entry = libraryEntry(entryId);
  if (!entry) return;
  currentLibraryId = entryId;
  isNewLibraryEntry = !!isNew;
  document.getElementById("modal-title").textContent = entry.label || "Nouveau bouton";
  document.getElementById("modal-label").value = entry.label || "";
  document.getElementById("modal-type").value = entry.type || "bouton";
  ensureSelectHasOption("modal-action-type", entry.action && entry.action.type);
  document.getElementById("modal-action-type").value = (entry.action && entry.action.type) || "none";
  document.getElementById("modal-action-target").value = entry.action_field || "";
  document.getElementById("modal-ha-entity").value = entry.ha_entity || "";
  document.getElementById("modal-show-light-color").checked = !!entry.show_light_color;
  selectedAppTarget = entry.action_field || null;
  modal.dataset.selectedIcon = entry.icon || "";
  document.getElementById("icon-search").value = "";
  renderIconPicker(entry.icon || "");
  updateModalFieldsVisibility();
  modal.classList.remove("hidden");
}

function closeModal() {
  modal.classList.add("hidden");
  currentLibraryId = null;
  isNewLibraryEntry = false;
}

document.getElementById("modal-type").addEventListener("change", updateModalFieldsVisibility);
document.getElementById("modal-action-type").addEventListener("change", updateLaunchPickerVisibility);
document.getElementById("icon-search").addEventListener("input", (e) => {
  renderIconPicker(modal.dataset.selectedIcon || "", e.target.value);
});

document.getElementById("modal-cancel").addEventListener("click", () => {
  if (isNewLibraryEntry && currentLibraryId !== null) {
    removeLibraryEntry(currentLibraryId);
    renderGrid();
  }
  closeModal();
});

document.getElementById("modal-delete").addEventListener("click", () => {
  if (currentLibraryId !== null) {
    removeLibraryEntry(currentLibraryId);
    renderGrid();
  }
  closeModal();
});

document.getElementById("modal-apply").addEventListener("click", () => {
  if (currentLibraryId === null) return;
  const entry = libraryEntry(currentLibraryId);
  if (!entry) return;
  entry.label = document.getElementById("modal-label").value.trim() || "Bouton";
  entry.type = document.getElementById("modal-type").value;
  entry.icon = modal.dataset.selectedIcon || "";
  entry.action = { type: document.getElementById("modal-action-type").value, target: null };
  entry.action_field = document.getElementById("modal-action-target").value;
  entry.ha_entity = document.getElementById("modal-ha-entity").value.trim();
  entry.show_light_color = document.getElementById("modal-show-light-color").checked;
  renderGrid();
  closeModal();
});

/* Mode simple (par defaut) vs avance (3 blocs horaire/antihoraire/appui
 * independants) : la config avancee reste possible ("Personnalise") mais
 * le cas courant - une seule entite/appli, horaire = augmente/antihoraire
 * = diminue - se regle en un seul picker au lieu de repeter la meme cible
 * deux fois avec des prefixes up:/down: a deviner. detectSimpleKind()
 * reconnait une config existante qui suit ce patron (compose par
 * composeSimpleEncoder ou migree depuis l'ancien mode avance) pour
 * pre-remplir le mode simple a la reouverture ; sinon ("Personnalise")
 * les 3 blocs avances restent la source de verite, inchanges.*/
const NONE_ACTION = { type: "none", target: "" };

function detectSimpleKind(enc) {
  const cw = enc.clockwise || NONE_ACTION;
  const acw = enc.anticlockwise || NONE_ACTION;
  const press = enc.press || NONE_ACTION;
  const isNone = (a) => (a.type || "none") === "none";
  const targetApp = (a, prefix) => (a.target || "").startsWith(prefix) ? a.target.slice(prefix.length) : null;

  if (isNone(cw) && isNone(acw) && isNone(press)) return { kind: "none" };

  if (cw.type === "ha_adjust" && acw.type === "ha_adjust" && isNone(press)) {
    const cwEntity = targetApp(cw, "up:");
    const acwEntity = targetApp(acw, "down:");
    if (cwEntity && cwEntity === acwEntity) return { kind: "ha_adjust", entityId: cwEntity };
  }

  if (cw.type === "app_volume" && acw.type === "app_volume") {
    const cwApp = targetApp(cw, "up:");
    const acwApp = targetApp(acw, "down:");
    const muteOk = isNone(press) || (press.type === "app_mute" && press.target === cwApp);
    if (cwApp && cwApp === acwApp && muteOk) return { kind: "app_volume", app: cwApp, mute: press.type === "app_mute" };
  }

  if (cw.type === "media" && cw.target === "vol_up" && acw.type === "media" && acw.target === "vol_down") {
    const muteOk = isNone(press) || (press.type === "media" && press.target === "mute");
    if (muteOk) return { kind: "media", mute: press.type === "media" };
  }

  return { kind: "custom" };
}

function composeSimpleEncoder(kind) {
  if (kind === "none") return { clockwise: { ...NONE_ACTION }, anticlockwise: { ...NONE_ACTION }, press: { ...NONE_ACTION } };
  const mute = document.getElementById("encoder-simple-mute").checked;
  if (kind === "ha_adjust") {
    const entityId = document.getElementById("encoder-simple-ha-search").dataset.entityId || "";
    if (!entityId) return { clockwise: { ...NONE_ACTION }, anticlockwise: { ...NONE_ACTION }, press: { ...NONE_ACTION } };
    return {
      clockwise: { type: "ha_adjust", target: `up:${entityId}` },
      anticlockwise: { type: "ha_adjust", target: `down:${entityId}` },
      press: { ...NONE_ACTION },
    };
  }
  if (kind === "app_volume") {
    const app = document.getElementById("encoder-simple-app").value;
    if (!app) return { clockwise: { ...NONE_ACTION }, anticlockwise: { ...NONE_ACTION }, press: { ...NONE_ACTION } };
    return {
      clockwise: { type: "app_volume", target: `up:${app}` },
      anticlockwise: { type: "app_volume", target: `down:${app}` },
      press: mute ? { type: "app_mute", target: app } : { ...NONE_ACTION },
    };
  }
  if (kind === "media") {
    return {
      clockwise: { type: "media", target: "vol_up" },
      anticlockwise: { type: "media", target: "vol_down" },
      press: mute ? { type: "media", target: "mute" } : { ...NONE_ACTION },
    };
  }
  return { clockwise: { ...NONE_ACTION }, anticlockwise: { ...NONE_ACTION }, press: { ...NONE_ACTION } };
}

function populateSimpleAppPicker() {
  const select = document.getElementById("encoder-simple-app");
  const current = select.value;
  select.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Choisir une application...";
  select.appendChild(placeholder);
  (audioSessions || []).forEach((session) => {
    const opt = document.createElement("option");
    opt.value = session.key;
    opt.textContent = session.name;
    select.appendChild(opt);
  });
  select.value = current;
}

function selectSimpleHaEntity(entity) {
  const search = document.getElementById("encoder-simple-ha-search");
  search.value = entity.name;
  search.dataset.entityId = entity.entity_id;
}

function applyEncoderSimpleVisibility() {
  const kind = document.getElementById("encoder-simple-kind").value;
  document.getElementById("encoder-simple-ha-fields").style.display = kind === "ha_adjust" ? "block" : "none";
  document.getElementById("encoder-simple-app").style.display = kind === "app_volume" ? "block" : "none";
  document.getElementById("encoder-simple-mute-row").style.display = (kind === "app_volume" || kind === "media") ? "block" : "none";
  document.getElementById("encoder-simple-hint").style.display = (kind === "none" || kind === "custom") ? "none" : "block";
  document.getElementById("encoder-advanced-block").style.display = kind === "custom" ? "block" : "none";

  if (kind === "ha_adjust") {
    loadHaEntitiesIfNeeded((err) => {
      document.getElementById("encoder-simple-ha-status").textContent = err || "";
      renderEntityList(
        "encoder-simple-ha-list", document.getElementById("encoder-simple-ha-search").value,
        selectSimpleHaEntity, HA_ADJUST_DOMAINS,
      );
    });
  } else if (kind === "app_volume") {
    loadAudioSessionsIfNeeded(() => populateSimpleAppPicker());
  }
}

document.getElementById("encoder-simple-kind").addEventListener("change", applyEncoderSimpleVisibility);
document.getElementById("encoder-simple-ha-search").addEventListener("input", (e) => {
  renderEntityList("encoder-simple-ha-list", e.target.value, selectSimpleHaEntity, HA_ADJUST_DOMAINS);
});

function openEncoderModal(index) {
  currentEncoderIndex = index;
  document.getElementById("encoder-modal-title").textContent = `Encodeur ${index + 1}`;
  const enc = encoders[index];
  DIRECTIONS.forEach((direction) => {
    const d = enc[direction] || { type: "none", target: "" };
    document.getElementById(`encoder-modal-${direction}-type`).value = d.type || "none";
    document.getElementById(`encoder-modal-${direction}-target`).value = d.target || "";
    updateEncoderAppPickerVisibility(direction);
    updateEncoderHaPickerVisibility(direction);
  });

  const detected = detectSimpleKind(enc);
  document.getElementById("encoder-simple-kind").value = detected.kind;
  document.getElementById("encoder-simple-mute").checked = !!detected.mute;
  applyEncoderSimpleVisibility();
  if (detected.kind === "ha_adjust") {
    loadHaEntitiesIfNeeded(() => {
      const entity = (haEntities || []).find((e) => e.entity_id === detected.entityId);
      const search = document.getElementById("encoder-simple-ha-search");
      search.value = entity ? entity.name : detected.entityId;
      search.dataset.entityId = detected.entityId;
    });
  } else if (detected.kind === "app_volume") {
    loadAudioSessionsIfNeeded(() => {
      populateSimpleAppPicker();
      document.getElementById("encoder-simple-app").value = detected.app;
    });
  }

  encoderModal.classList.remove("hidden");
}

function closeEncoderModal() {
  encoderModal.classList.add("hidden");
  currentEncoderIndex = null;
}

document.getElementById("encoder-modal-cancel").addEventListener("click", closeEncoderModal);
document.getElementById("encoder-modal-apply").addEventListener("click", () => {
  if (currentEncoderIndex === null) return;
  const kind = document.getElementById("encoder-simple-kind").value;
  let enc;
  if (kind !== "custom") {
    enc = composeSimpleEncoder(kind);
  } else {
    enc = {};
    DIRECTIONS.forEach((direction) => {
      enc[direction] = {
        type: document.getElementById(`encoder-modal-${direction}-type`).value,
        target: document.getElementById(`encoder-modal-${direction}-target`).value,
      };
    });
  }
  encoders[currentEncoderIndex] = enc;
  closeEncoderModal();
});

/* Picker "app_volume"/"app_mute" (encodeurs) : liste des applications
 * ayant une session audio active (voir app_volume.py::list_audio_sessions
 * et la route /audio-sessions), chargee une seule fois par session comme
 * audioDevices dans audio-devices.js. Le champ cible reste un input texte
 * libre ("up:chrome.exe" / "down:chrome.exe" pour app_volume, "chrome.exe"
 * tout court pour app_mute) - ce picker se contente d'y ecrire une valeur,
 * sans empecher de la modifier a la main ensuite. */
let audioSessions = null;

function loadAudioSessionsIfNeeded(callback) {
  if (audioSessions !== null) { callback(null); return; }
  fetch("/audio-sessions")
    .then((r) => r.json())
    .then((data) => {
      audioSessions = data.sessions || [];
      callback(data.error || null);
    })
    .catch(() => {
      audioSessions = [];
      callback("Impossible de contacter l'appli.");
    });
}

function populateEncoderAppPicker(direction) {
  const select = document.getElementById(`encoder-modal-${direction}-app`);
  const current = select.value;
  select.innerHTML = "";
  const placeholder = document.createElement("option");
  placeholder.value = "";
  placeholder.textContent = "Choisir une application...";
  select.appendChild(placeholder);
  (audioSessions || []).forEach((session) => {
    const opt = document.createElement("option");
    opt.value = session.key;
    opt.textContent = session.name;
    select.appendChild(opt);
  });
  select.value = current;
}

function updateEncoderAppPickerVisibility(direction) {
  const type = document.getElementById(`encoder-modal-${direction}-type`).value;
  const select = document.getElementById(`encoder-modal-${direction}-app`);
  const needsPicker = type === "app_volume" || type === "app_mute";
  select.style.display = needsPicker ? "block" : "none";
  if (!needsPicker) return;
  loadAudioSessionsIfNeeded(() => {
    populateEncoderAppPicker(direction);
    const target = document.getElementById(`encoder-modal-${direction}-target`).value;
    const app = type === "app_mute" ? target : (target.includes(":") ? target.split(":")[1] : "");
    if (app) select.value = app;
  });
}

function applyEncoderAppSelection(direction) {
  const app = document.getElementById(`encoder-modal-${direction}-app`).value;
  if (!app) return;
  const type = document.getElementById(`encoder-modal-${direction}-type`).value;
  const value = type === "app_mute" ? app : `${direction === "anticlockwise" ? "down" : "up"}:${app}`;
  document.getElementById(`encoder-modal-${direction}-target`).value = value;
}

DIRECTIONS.forEach((direction) => {
  document.getElementById(`encoder-modal-${direction}-type`).addEventListener("change", () => {
    updateEncoderAppPickerVisibility(direction);
    updateEncoderHaPickerVisibility(direction);
  });
  document.getElementById(`encoder-modal-${direction}-app`)
    .addEventListener("change", () => applyEncoderAppSelection(direction));
});

/* Popup de la carte meteo (widget dedie, voir makeWeatherTile()) - juste
 * une entite HA (domaine "weather" uniquement) et une visibilite, pas de
 * type/icone/action a choisir contrairement a un emplacement. */
const weatherModal = document.getElementById("weather-modal");

function openWeatherModal() {
  document.getElementById("weather-modal-visible").checked = !!weather.visible;
  document.getElementById("weather-modal-entity").value = weather.entity || "";
  document.getElementById("weather-modal-search").value = "";
  document.getElementById("weather-modal-status").textContent = "";
  loadHaEntitiesIfNeeded((err) => {
    document.getElementById("weather-modal-status").textContent = err || "";
    renderEntityList("weather-modal-list", "", (entity) => {
      document.getElementById("weather-modal-search").value = entity.name;
      document.getElementById("weather-modal-entity").value = entity.entity_id;
    }, "weather");
  });
  weatherModal.classList.remove("hidden");
}

function closeWeatherModal() {
  weatherModal.classList.add("hidden");
}

document.getElementById("weather-modal-search").addEventListener("input", (e) => {
  renderEntityList("weather-modal-list", e.target.value, (entity) => {
    document.getElementById("weather-modal-search").value = entity.name;
    document.getElementById("weather-modal-entity").value = entity.entity_id;
  }, "weather");
});

document.getElementById("weather-modal-cancel").addEventListener("click", closeWeatherModal);
document.getElementById("weather-modal-apply").addEventListener("click", () => {
  const wasVisible = !!weather.visible;
  weather.entity = document.getElementById("weather-modal-entity").value.trim();
  weather.visible = document.getElementById("weather-modal-visible").checked;
  if (weather.visible && !wasVisible) {
    const g = slotGrid(weather);
    if (hasCollision(-1, g)) {
      const free = findFreeCell(-1, g.colspan, g.rowspan);
      weather.grid = { col: free.col, row: free.row, colspan: g.colspan, rowspan: g.rowspan };
    }
  }
  renderGrid();
  closeWeatherModal();
});

document.getElementById("config-form").addEventListener("submit", () => {
  document.getElementById("profiles_json").value = JSON.stringify(profiles);
});
