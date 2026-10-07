/* Bibliotheque d'applications du picker "launch" (popup d'emplacement) :
 * applications actuellement ouvertes sur le PC (meme source que le
 * declencheur de profil - profile_watcher.py::list_open_windows, en tete
 * de liste car c'est le plus rapide a reconnaitre) + detectees (menu
 * Demarrer, via app_library.py) + personnalisees ajoutees via la tuile
 * "+ Ajouter", persistees cote serveur (custom_apps.py). Chargee une seule
 * fois par session, la tuile "+ Ajouter" met a jour le cache local ensuite
 * sans recharger. Depend des variables/elements definis dans dashboard.js
 * (charge avant ce fichier). */

let appLibrary = null;
let selectedAppTarget = null;

function loadAppLibraryIfNeeded() {
  if (appLibrary !== null) { renderAppGrid(); return; }
  const status = document.getElementById("modal-app-status");
  status.textContent = "Chargement de la bibliotheque d'applications...";
  Promise.all([
    fetch("/installed-apps").then((r) => r.json()),
    fetch("/open-windows").then((r) => r.json()),
  ])
    .then(([installed, openWindows]) => {
      appLibrary = {
        detected: installed.apps || [],
        custom: installed.custom || [],
        open: (openWindows.windows || []).map((w) => ({ name: w.title, target: w.target })),
      };
      status.textContent = installed.detect_error
        ? "Detection automatique indisponible sur ce systeme - ajoutez vos applications avec \"+ Ajouter\"."
        : "";
      renderAppGrid();
    })
    .catch(() => {
      appLibrary = { detected: [], custom: [], open: [] };
      status.textContent = "Impossible de charger la bibliotheque d'applications.";
      renderAppGrid();
    });
}

function renderAppGrid() {
  const grid = document.getElementById("modal-app-grid");
  grid.innerHTML = "";
  if (!appLibrary) return;

  const query = document.getElementById("modal-app-search").value.trim().toLowerCase();
  const seenTargets = new Set();
  const all = [
    ...appLibrary.custom.map((a) => ({ ...a, custom: true })),
    ...appLibrary.open.map((a) => ({ ...a, open: true })),
    ...appLibrary.detected,
  ].filter((a) => {
    if (seenTargets.has(a.target)) return false;
    seenTargets.add(a.target);
    return a.name.toLowerCase().includes(query);
  });

  all.forEach((app) => grid.appendChild(makeAppTile(app)));

  const addTile = document.createElement("div");
  addTile.className = "app-tile add-tile";
  addTile.title = "Ajouter une application a la bibliotheque";
  addTile.innerHTML = '<div class="app-icon">+</div><div class="app-name">Ajouter...</div>';
  addTile.addEventListener("click", addCustomApp);
  grid.appendChild(addTile);
}

function makeAppTile(app) {
  const tile = document.createElement("div");
  tile.className = "app-tile" + (app.target === selectedAppTarget ? " selected" : "");
  tile.title = app.open ? `${app.name} (ouverte actuellement)` : app.name;

  const icon = document.createElement("div");
  icon.className = "app-icon";
  icon.textContent = "\uE5C3"; /* "apps" (Material Icons) - glyphe generique */
  if (app.open) {
    const dot = document.createElement("span");
    dot.className = "live-dot";
    icon.appendChild(dot);
  }
  tile.appendChild(icon);

  const name = document.createElement("div");
  name.className = "app-name";
  name.textContent = app.name;
  tile.appendChild(name);

  tile.addEventListener("click", () => selectApp(app));

  if (app.custom) {
    const remove = document.createElement("div");
    remove.className = "app-remove";
    remove.textContent = "Retirer";
    remove.addEventListener("click", (e) => { e.stopPropagation(); removeCustomApp(app.target); });
    tile.appendChild(remove);
  }

  return tile;
}

function selectApp(app) {
  selectedAppTarget = app.target;
  document.getElementById("modal-action-target").value = app.target;
  const labelField = document.getElementById("modal-label");
  if (!labelField.value.trim() || /^Slot \d+$/.test(labelField.value.trim())) {
    labelField.value = app.name;
  }
  renderAppGrid();
}

function addCustomApp() {
  fetch("/custom-apps", { method: "POST" })
    .then((r) => r.json())
    .then((data) => {
      if (data.error) {
        alert("Impossible d'ouvrir le selecteur de fichier : " + data.error);
        return;
      }
      if (!data.target) return;
      appLibrary.custom = data.apps || appLibrary.custom;
      selectApp({ name: data.name, target: data.target });
    })
    .catch(() => alert("Impossible de contacter l'appli pour ouvrir le selecteur de fichier."));
}

function removeCustomApp(target) {
  fetch("/custom-apps/remove", {
    method: "POST",
    headers: { "Content-Type": "application/x-www-form-urlencoded" },
    body: "target=" + encodeURIComponent(target),
  })
    .then((r) => r.json())
    .then((data) => {
      appLibrary.custom = data.apps || [];
      renderAppGrid();
    })
    .catch(() => {});
}

document.getElementById("modal-app-search").addEventListener("input", renderAppGrid);
