/* Picker d'entites Home Assistant, recherchable - utilise a deux endroits
 * dans la popup d'emplacement : la source d'un widget barre/texte, et la
 * cible d'une action "home_assistant" (avec un choix de service courant
 * pour le domaine de l'entite selectionnee). Meme cache, chargee une
 * seule fois par session. Depend des elements/fonctions definies dans
 * dashboard.js (charge avant ce fichier). */

let haEntities = null;

function loadHaEntitiesIfNeeded(callback) {
  if (haEntities !== null) { callback(null); return; }
  fetch("/ha-entities")
    .then((r) => r.json())
    .then((data) => {
      haEntities = data.entities || [];
      callback(data.error || null);
    })
    .catch(() => {
      haEntities = [];
      callback("Impossible de contacter l'appli.");
    });
}

function renderEntityList(listId, query, onSelect, domainFilter) {
  const list = document.getElementById(listId);
  list.innerHTML = "";
  if (!haEntities) return;

  // domainFilter accepte un domaine unique (string) ou une liste de
  // domaines (array, voir le picker "ha_adjust" des encodeurs qui accepte
  // plusieurs domaines a la fois : light/media_player/fan/cover/climate).
  const pool = !domainFilter
    ? haEntities
    : Array.isArray(domainFilter)
      ? haEntities.filter((e) => domainFilter.includes(e.domain))
      : haEntities.filter((e) => e.domain === domainFilter);
  const q = query.trim().toLowerCase();
  const filtered = q
    ? pool.filter((e) => e.name.toLowerCase().includes(q) || e.entity_id.toLowerCase().includes(q)).slice(0, 50)
    : pool.slice(0, 50);

  if (!filtered.length) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = q ? "Aucune entite trouvee." : "Tapez pour rechercher parmi vos entites.";
    list.appendChild(empty);
    return;
  }

  filtered.forEach((entity) => {
    const row = document.createElement("div");
    row.className = "entity-row";

    const name = document.createElement("span");
    name.className = "entity-name";
    name.textContent = entity.name;
    row.appendChild(name);

    const meta = document.createElement("span");
    meta.className = "entity-meta";
    meta.textContent = `${entity.entity_id} - ${entity.state}`;
    row.appendChild(meta);

    row.addEventListener("click", () => onSelect(entity));
    list.appendChild(row);
  });
}

/* --- Source d'un widget barre/texte (modal-source-fields) --- */

function updateHaSourceVisibility() {
  const type = document.getElementById("modal-type").value;
  const isWidget = type === "barre" || type === "texte";
  if (isWidget) {
    loadHaEntitiesIfNeeded((err) => {
      document.getElementById("modal-ha-entity-status").textContent = err || "";
      renderEntityList("modal-ha-entity-list", document.getElementById("modal-ha-entity-search").value, (entity) => {
        document.getElementById("modal-ha-entity").value = entity.entity_id;
      });
    });
  }
}

document.getElementById("modal-ha-entity-search").addEventListener("input", (e) => {
  renderEntityList("modal-ha-entity-list", e.target.value, (entity) => {
    document.getElementById("modal-ha-entity").value = entity.entity_id;
  });
});

/* --- Cible d'une action "home_assistant" (modal-action-fields) --- */

function updateHaActionVisibility() {
  const isHa = document.getElementById("modal-action-type").value === "home_assistant";
  document.getElementById("modal-ha-action-fields").style.display = isHa ? "block" : "none";
  if (isHa) {
    loadHaEntitiesIfNeeded((err) => {
      document.getElementById("modal-ha-action-status").textContent = err || "";
      renderEntityList("modal-ha-action-list", document.getElementById("modal-ha-action-search").value, selectHaActionEntity);
    });
  }
  updateHaColorRowVisibility();
}

/* La case "afficher la couleur de l'ampoule" n'a de sens que pour une
 * cible du domaine "light" - determine a partir de modal-action-target
 * (deja tenu a jour que l'entite vienne du picker ou soit tapee a la main
 * au format compact "domaine.service:entite"), pas de select.dataset qui
 * n'est renseigne qu'apres une interaction avec le picker dans CETTE
 * ouverture de popup. */
function updateHaColorRowVisibility() {
  const target = document.getElementById("modal-action-target").value || "";
  const isLight = document.getElementById("modal-action-type").value === "home_assistant" && target.startsWith("light.");
  document.getElementById("modal-ha-color-row").style.display = isLight ? "block" : "none";
}

function selectHaActionEntity(entity) {
  document.getElementById("modal-ha-action-search").value = entity.name;
  fetch(`/ha-services/${encodeURIComponent(entity.domain)}`)
    .then((r) => r.json())
    .then((data) => {
      const select = document.getElementById("modal-ha-action-service");
      select.innerHTML = "";
      (data.services || []).forEach((service) => {
        const opt = document.createElement("option");
        opt.value = service;
        opt.textContent = service;
        select.appendChild(opt);
      });
      select.dataset.domain = entity.domain;
      select.dataset.entityId = entity.entity_id;
      composeHaActionTarget();
    });
}

function composeHaActionTarget() {
  const select = document.getElementById("modal-ha-action-service");
  const domain = select.dataset.domain;
  const entityId = select.dataset.entityId;
  if (!domain || !entityId || !select.value) return;
  document.getElementById("modal-action-target").value = `${domain}.${select.value}:${entityId}`;
  updateHaColorRowVisibility();
}

document.getElementById("modal-ha-action-search").addEventListener("input", (e) => {
  renderEntityList("modal-ha-action-list", e.target.value, selectHaActionEntity);
});
document.getElementById("modal-ha-action-service").addEventListener("change", composeHaActionTarget);
document.getElementById("modal-action-target").addEventListener("input", updateHaColorRowVisibility);
/* updateHaActionVisibility() est deja appelee sur le meme evenement via
 * updateLaunchPickerVisibility() dans dashboard.js - pas de listener
 * redondant ici. */

/* --- Cible d'un encodeur "home_assistant"/"ha_adjust" (encoder-modal) ---
 * Meme picker recherchable que modal-ha-action-fields ci-dessus, mais
 * repete pour chacune des 3 directions (clockwise/anticlockwise/press,
 * voir DIRECTIONS dans dashboard.js) - avant ce picker, il fallait taper
 * a la main le format compact "domaine.service:entite" (home_assistant)
 * ou "up:entite"/"down:entite" (ha_adjust), en devinant soi-meme lequel
 * des deux prefixes correspond a quel sens de rotation. Desormais le sens
 * (up = horaire/appui, down = antihoraire) est deduit de la direction
 * choisie, comme applyEncoderAppSelection() le fait deja pour
 * app_volume/app_mute (voir dashboard.js). */
const HA_ADJUST_DOMAINS = ["light", "media_player", "fan", "cover", "climate"];

function updateEncoderHaPickerVisibility(direction) {
  const type = document.getElementById(`encoder-modal-${direction}-type`).value;
  const isHa = type === "home_assistant";
  const isAdjust = type === "ha_adjust";
  document.getElementById(`encoder-modal-${direction}-ha-fields`).style.display = (isHa || isAdjust) ? "block" : "none";
  document.getElementById(`encoder-modal-${direction}-ha-service`).style.display = isHa ? "block" : "none";
  if (!isHa && !isAdjust) return;
  loadHaEntitiesIfNeeded((err) => {
    document.getElementById(`encoder-modal-${direction}-ha-status`).textContent = err || "";
    renderEntityList(
      `encoder-modal-${direction}-ha-list`,
      document.getElementById(`encoder-modal-${direction}-ha-search`).value,
      (entity) => selectEncoderHaEntity(direction, entity),
      isAdjust ? HA_ADJUST_DOMAINS : null,
    );
  });
}

function selectEncoderHaEntity(direction, entity) {
  document.getElementById(`encoder-modal-${direction}-ha-search`).value = entity.name;
  const type = document.getElementById(`encoder-modal-${direction}-type`).value;
  if (type === "ha_adjust") {
    const sign = direction === "anticlockwise" ? "down" : "up";
    document.getElementById(`encoder-modal-${direction}-target`).value = `${sign}:${entity.entity_id}`;
    return;
  }
  fetch(`/ha-services/${encodeURIComponent(entity.domain)}`)
    .then((r) => r.json())
    .then((data) => {
      const select = document.getElementById(`encoder-modal-${direction}-ha-service`);
      select.innerHTML = "";
      (data.services || []).forEach((service) => {
        const opt = document.createElement("option");
        opt.value = service;
        opt.textContent = service;
        select.appendChild(opt);
      });
      select.dataset.domain = entity.domain;
      select.dataset.entityId = entity.entity_id;
      composeEncoderHaTarget(direction);
    });
}

function composeEncoderHaTarget(direction) {
  const select = document.getElementById(`encoder-modal-${direction}-ha-service`);
  const domain = select.dataset.domain;
  const entityId = select.dataset.entityId;
  if (!domain || !entityId || !select.value) return;
  document.getElementById(`encoder-modal-${direction}-target`).value = `${domain}.${select.value}:${entityId}`;
}

DIRECTIONS.forEach((direction) => {
  document.getElementById(`encoder-modal-${direction}-ha-search`).addEventListener("input", (e) => {
    renderEntityList(
      `encoder-modal-${direction}-ha-list`, e.target.value, (entity) => selectEncoderHaEntity(direction, entity),
      document.getElementById(`encoder-modal-${direction}-type`).value === "ha_adjust" ? HA_ADJUST_DOMAINS : null,
    );
  });
  document.getElementById(`encoder-modal-${direction}-ha-service`)
    .addEventListener("change", () => composeEncoderHaTarget(direction));
});
