/* V2 Action Library progressive enhancement.
 * Built entirely from /api/v2/action-catalog so actions, categories and the
 * Property Inspector share one source of truth. */

(() => {
  const API_URL = "/api/v2/action-catalog";
  let catalog = null;

  function applyAction(actionId) {
    const select = document.getElementById("modal-action-type");
    if (!select) return;
    if (![...select.options].some((option) => option.value === actionId)) return;
    select.value = actionId;
    select.dispatchEvent(new Event("change", { bubbles: true }));
  }

  function matches(action, query, category) {
    if (category && action.category !== category) return false;
    const needle = query.trim().toLowerCase();
    if (!needle) return true;
    return `${action.id} ${action.name} ${action.description || ""} ${action.category}`.toLowerCase().includes(needle);
  }

  function renderList(root, search, categorySelect) {
    const list = root.querySelector("[data-action-library-list]");
    if (!list || !catalog) return;
    list.innerHTML = "";
    const actions = (catalog.actions || []).filter((action) => matches(action, search.value, categorySelect.value));
    if (!actions.length) {
      const empty = document.createElement("p");
      empty.className = "hint";
      empty.textContent = "Aucune action trouvee.";
      list.appendChild(empty);
      return;
    }

    actions.forEach((action) => {
      const card = document.createElement("button");
      card.type = "button";
      card.className = "secondary";
      card.draggable = true;
      card.dataset.actionLibraryId = action.id;
      card.style.display = "block";
      card.style.width = "100%";
      card.style.margin = "6px 0";
      card.style.textAlign = "left";
      card.textContent = `${action.name} — ${action.category}`;
      card.title = action.description || action.name;
      card.addEventListener("click", () => applyAction(action.id));
      card.addEventListener("dragstart", (event) => {
        event.dataTransfer.setData("application/x-streamdeck-action", action.id);
        event.dataTransfer.effectAllowed = "copy";
      });
      list.appendChild(card);
    });
  }

  function buildLibrary() {
    const modal = document.querySelector("#slot-modal .modal");
    const buttons = modal && modal.querySelector(".modal-buttons");
    if (!modal || !buttons || modal.querySelector("[data-action-library]")) return;

    const root = document.createElement("section");
    root.dataset.actionLibrary = "1";
    root.style.marginTop = "18px";

    const title = document.createElement("h3");
    title.textContent = "Bibliotheque d'actions";
    root.appendChild(title);

    const hint = document.createElement("p");
    hint.className = "hint";
    hint.textContent = "Cliquez une action ou glissez-la dans la zone ci-dessous pour l'appliquer au bouton.";
    root.appendChild(hint);

    const search = document.createElement("input");
    search.type = "search";
    search.placeholder = "Rechercher une action...";
    search.dataset.actionLibrarySearch = "1";
    root.appendChild(search);

    const category = document.createElement("select");
    category.dataset.actionLibraryCategory = "1";
    const all = document.createElement("option");
    all.value = "";
    all.textContent = "Toutes les categories";
    category.appendChild(all);
    (catalog.categories || []).forEach((value) => {
      const option = document.createElement("option");
      option.value = value;
      option.textContent = value;
      category.appendChild(option);
    });
    root.appendChild(category);

    const list = document.createElement("div");
    list.dataset.actionLibraryList = "1";
    list.style.maxHeight = "220px";
    list.style.overflow = "auto";
    root.appendChild(list);

    const dropZone = document.createElement("div");
    dropZone.dataset.actionLibraryDrop = "1";
    dropZone.className = "hint";
    dropZone.style.border = "1px dashed currentColor";
    dropZone.style.padding = "12px";
    dropZone.style.marginTop = "8px";
    dropZone.textContent = "Deposez une action ici";
    dropZone.addEventListener("dragover", (event) => {
      event.preventDefault();
      event.dataTransfer.dropEffect = "copy";
    });
    dropZone.addEventListener("drop", (event) => {
      event.preventDefault();
      const actionId = event.dataTransfer.getData("application/x-streamdeck-action");
      if (actionId) applyAction(actionId);
    });
    root.appendChild(dropZone);

    search.addEventListener("input", () => renderList(root, search, category));
    category.addEventListener("change", () => renderList(root, search, category));
    modal.insertBefore(root, buttons);
    renderList(root, search, category);
  }

  async function bootstrap() {
    if (!document.getElementById("modal-action-type")) return;
    try {
      const response = await fetch(API_URL);
      if (!response.ok) return;
      catalog = await response.json();
    } catch (_error) {
      return;
    }
    buildLibrary();
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
})();
