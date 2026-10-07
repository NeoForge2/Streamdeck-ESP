/* Profils (onglets de l'accueil) : chaque profil a sa propre grille de 36
 * emplacements physiques + 3 encodeurs. L'ecran bascule automatiquement sur le
 * profil dont le declencheur correspond a l'application au premier plan
 * sur le PC (profile_watcher.py), ou manuellement via "Forcer ce profil"/
 * "Automatique". Depend des variables/elements/fonctions definis dans
 * dashboard.js (charge avant ce fichier) : profiles, slots, encoders,
 * activeEditIndex, renderGrid(), renderEncoderMock(). */

function switchProfileTab(index) {
  activeEditIndex = index;
  slots = profiles[index].slots;
  library = profiles[index].library;
  encoders = profiles[index].encoders;
  weather = profiles[index].weather;
  renderProfileTabs();
  renderGrid();
  renderEncoderMock();
}

function renderProfileTabs() {
  const tabs = document.getElementById("profile-tabs");
  tabs.innerHTML = "";

  profiles.forEach((profile, index) => {
    const tab = document.createElement("div");
    tab.className = "profile-tab" + (index === activeEditIndex ? " editing" : "");

    if (profile.name === liveActiveProfileName) {
      const dot = document.createElement("span");
      dot.className = "live-dot";
      dot.title = "Actif sur l'ecran en ce moment";
      tab.appendChild(dot);
    }

    const label = document.createElement("span");
    label.textContent = profile.name;
    tab.appendChild(label);

    const editIcon = document.createElement("span");
    editIcon.className = "edit-icon";
    editIcon.textContent = "\uE3C9"; /* "edit" (Material Icons) */
    editIcon.title = "Modifier le nom/declencheur";
    editIcon.addEventListener("click", (e) => { e.stopPropagation(); openProfileModal(index); });
    tab.appendChild(editIcon);

    tab.addEventListener("click", () => switchProfileTab(index));
    tabs.appendChild(tab);
  });

  const addTab = document.createElement("div");
  addTab.className = "profile-tab add-tab";
  addTab.textContent = "+ Nouveau profil";
  addTab.addEventListener("click", () => openProfileModal(null));
  tabs.appendChild(addTab);

  updateProfileStatusUI();
}

function updateProfileStatusUI() {
  const text = document.getElementById("profile-status-text");
  if (manualOverride) {
    text.textContent = `Profil force manuellement : ${liveActiveProfileName || "?"}`;
  } else if (liveActiveProfileName) {
    text.textContent = `Bascule automatique - actif en ce moment : ${liveActiveProfileName}`;
  } else {
    text.textContent = "Bascule automatique indisponible (Windows uniquement) - basculez manuellement avec \"Forcer ce profil\".";
  }
  document.getElementById("profile-auto-btn").style.display = manualOverride ? "inline-block" : "none";
}

function pollProfileStatus() {
  fetch("/profiles/status")
    .then((r) => r.json())
    .then((data) => {
      liveActiveProfileName = data.active_profile_name || liveActiveProfileName;
      manualOverride = !!data.manual_override;
      renderProfileTabs();
    })
    .catch(() => {});
}

document.getElementById("profile-force-btn").addEventListener("click", () => {
  const name = profiles[activeEditIndex].name;
  fetch("/profiles/force", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: "name=" + encodeURIComponent(name),
  })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) { alert("Impossible de forcer ce profil : " + data.error); return; }
      liveActiveProfileName = data.active_profile_name;
      manualOverride = true;
      renderProfileTabs();
    })
    .catch(() => alert("Impossible de contacter l'appli."));
});

document.getElementById("profile-auto-btn").addEventListener("click", () => {
  fetch("/profiles/auto", { method: "POST" })
    .then(() => { manualOverride = false; renderProfileTabs(); })
    .catch(() => {});
});

function makeDefaultSlots() {
  /* Emplacements PHYSIQUES (position/taille uniquement, voir
   * profiles.py::default_slot) - un nouveau profil demarre avec un ecran
   * vide (aucune entree de bibliotheque assignee), a l'utilisateur de
   * glisser des boutons dessus depuis la bibliotheque (vide elle aussi,
   * voir makeDefaultLibrary). Meme formule que profiles.py::default_grid
   * pour la position par defaut (range dans l'ordre de lecture, non
   * utilisee tant que library_id est null). */
  const slots = [];
  for (let i = 0; i < GRID_COLS * GRID_ROWS; i++) {
    slots.push({ library_id: null, grid: { col: i % GRID_COLS, row: Math.floor(i / GRID_COLS), colspan: 1, rowspan: 1 } });
  }
  return slots;
}

function makeDefaultLibrary() {
  return [];
}

function makeDefaultEncoders() {
  const empty = () => ({ type: "none", target: "" });
  return [0, 1, 2].map(() => ({ clockwise: empty(), anticlockwise: empty(), press: empty() }));
}

function makeDefaultWeather() {
  return { visible: false, entity: "", grid: { col: 0, row: 0, colspan: 2, rowspan: 2 } };
}

function openProfileModal(index) {
  editingProfileIndex = index;
  const isNew = index === null;
  document.getElementById("profile-modal-title").textContent = isNew ? "Nouveau profil" : "Modifier le profil";
  document.getElementById("profile-modal-name").value = isNew ? "" : profiles[index].name;
  document.getElementById("profile-modal-trigger").value = isNew ? "" : ((profiles[index].trigger && profiles[index].trigger.process) || "");
  document.getElementById("profile-modal-delete").style.display = (isNew || profiles.length <= 1) ? "none" : "inline-block";
  loadOpenWindows();
  profileModal.classList.remove("hidden");
}

function closeProfileModal() {
  profileModal.classList.add("hidden");
  editingProfileIndex = null;
}

document.getElementById("profile-modal-cancel").addEventListener("click", closeProfileModal);

/* Liste des applications ouvertes (Alt+Tab) plutot qu'un bouton "Detecter
 * l'appli active" - celui-ci detectait toujours le navigateur, puisqu'il
 * faut y cliquer pour declencher la detection. Rechargee a chaque
 * ouverture de la popup pour rester a jour. */
function loadOpenWindows() {
  const select = document.getElementById("profile-modal-open-windows");
  const status = document.getElementById("profile-modal-open-windows-status");
  select.innerHTML = '<option value="">— Chargement des applications ouvertes... —</option>';
  fetch("/open-windows")
    .then((r) => r.json())
    .then((data) => {
      const windows = data.windows || [];
      select.innerHTML = '<option value="">— Choisir une application ouverte —</option>';
      windows.forEach((w) => {
        const opt = document.createElement("option");
        opt.value = w.process;
        opt.textContent = `${w.title} (${w.process})`;
        select.appendChild(opt);
      });
      status.textContent = windows.length
        ? ""
        : "Aucune application detectee - fonctionnalite Windows uniquement, ou tapez le nom du processus a la main ci-dessous.";
    })
    .catch(() => {
      select.innerHTML = '<option value="">— Indisponible —</option>';
      status.textContent = "Impossible de charger la liste - tapez le nom du processus a la main ci-dessous.";
    });
}

document.getElementById("profile-modal-open-windows").addEventListener("change", (e) => {
  if (!e.target.value) return;
  document.getElementById("profile-modal-trigger").value = e.target.value;
  const nameField = document.getElementById("profile-modal-name");
  if (!nameField.value.trim()) {
    nameField.value = e.target.selectedOptions[0].textContent.replace(/\s*\([^)]*\)$/, "");
  }
});

document.getElementById("profile-modal-save").addEventListener("click", () => {
  const name = document.getElementById("profile-modal-name").value.trim() || "Profil";
  const triggerProcess = document.getElementById("profile-modal-trigger").value.trim();
  const trigger = triggerProcess ? { process: triggerProcess } : null;
  if (editingProfileIndex === null) {
    profiles.push({
      name, trigger, slots: makeDefaultSlots(), library: makeDefaultLibrary(),
      encoders: makeDefaultEncoders(), weather: makeDefaultWeather(),
    });
    closeProfileModal();
    switchProfileTab(profiles.length - 1);
  } else {
    profiles[editingProfileIndex].name = name;
    profiles[editingProfileIndex].trigger = trigger;
    closeProfileModal();
    renderProfileTabs();
  }
});

document.getElementById("profile-modal-delete").addEventListener("click", () => {
  if (editingProfileIndex === null || profiles.length <= 1) return;
  if (!confirm(`Supprimer le profil "${profiles[editingProfileIndex].name}" ?`)) return;
  profiles.splice(editingProfileIndex, 1);
  closeProfileModal();
  switchProfileTab(Math.min(activeEditIndex, profiles.length - 1));
});

renderProfileTabs();
renderGrid();
renderEncoderMock();
setInterval(pollProfileStatus, 3000);
