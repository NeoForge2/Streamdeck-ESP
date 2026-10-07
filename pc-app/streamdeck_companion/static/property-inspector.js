/* Progressive V2 Property Inspector for the historical dashboard.
 * The action schema comes from /api/v2/action-catalog. Existing specialised
 * pickers (apps, HA, audio) remain in place and keep writing to the same
 * target control id, so this enhancement stays backward compatible. */

(() => {
  const API_URL = "/api/v2/action-catalog";
  const MEDIA_COMMANDS = ["play_pause", "next", "previous", "vol_up", "vol_down", "mute"];
  let catalog = null;

  function actionById(actionId) {
    if (!catalog) return null;
    return (catalog.actions || []).find((action) => action.id === actionId) || null;
  }

  function populateActionSelect(select, choices) {
    if (!select) return;
    const current = select.value;
    select.innerHTML = "";
    (choices || []).forEach((choice) => {
      const option = document.createElement("option");
      option.value = choice.id;
      option.textContent = choice.label;
      select.appendChild(option);
    });
    if (current && ![...select.options].some((option) => option.value === current)) {
      const legacy = document.createElement("option");
      legacy.value = current;
      legacy.textContent = `${current} (ancien reglage)`;
      select.insertBefore(legacy, select.firstChild);
    }
    if (current) select.value = current;
  }

  function buildControl(field, id, currentValue) {
    let control;
    if (field.type === "select") {
      control = document.createElement("select");
      (field.options || []).forEach((value) => {
        const option = document.createElement("option");
        option.value = value;
        option.textContent = value;
        control.appendChild(option);
      });
    } else {
      control = document.createElement("input");
      if (field.type === "number") control.type = "number";
      else if (field.type === "boolean") control.type = "checkbox";
      else control.type = "text";
    }
    control.id = id;
    control.dataset.v2Inspector = "1";
    control.setAttribute("aria-label", field.label || field.key || "Parametre");
    if (field.required) control.required = true;
    if (field.type === "boolean") {
      control.checked = currentValue === true || currentValue === "true" || currentValue === "1";
    } else {
      control.value = currentValue ?? field.default ?? "";
    }
    return control;
  }

  async function dynamicOptions(source) {
    if (source === "media_commands") {
      return MEDIA_COMMANDS.map((value) => ({ value, label: value }));
    }
    if (source === "audio_outputs") {
      const response = await fetch("/audio-devices");
      const data = await response.json();
      return (data.devices || []).map((item) => ({ value: item.id, label: item.name || item.id }));
    }
    if (source === "audio_apps") {
      const response = await fetch("/audio-sessions");
      const data = await response.json();
      return (data.sessions || []).map((item) => ({ value: item.key, label: item.name || item.key }));
    }
    return [];
  }

  async function renderTarget(selectId, targetId) {
    const typeSelect = document.getElementById(selectId);
    const oldControl = document.getElementById(targetId);
    if (!typeSelect || !oldControl) return;

    const currentValue = oldControl.type === "checkbox" ? oldControl.checked : oldControl.value;
    const action = actionById(typeSelect.value);
    const field = action && action.fields && action.fields.length ? action.fields[0] : null;

    if (!field) {
      const fallback = document.createElement("input");
      fallback.type = "text";
      fallback.id = targetId;
      fallback.value = currentValue || "";
      fallback.placeholder = "Parametre de l'action";
      oldControl.replaceWith(fallback);
      return;
    }

    const control = buildControl(field, targetId, currentValue);
    if (field.options_source && control.tagName === "SELECT") {
      try {
        const options = await dynamicOptions(field.options_source);
        const selected = String(currentValue ?? field.default ?? "");
        control.innerHTML = "";
        options.forEach((item) => {
          const option = document.createElement("option");
          option.value = item.value;
          option.textContent = item.label;
          control.appendChild(option);
        });
        if (selected && ![...control.options].some((option) => option.value === selected)) {
          const legacy = document.createElement("option");
          legacy.value = selected;
          legacy.textContent = `${selected} (actuel)`;
          control.insertBefore(legacy, control.firstChild);
        }
        control.value = selected;
      } catch (_error) {
        // Keep the select usable even when a dynamic source is unavailable.
      }
    }

    const previousLabel = oldControl.previousElementSibling;
    if (previousLabel && previousLabel.tagName === "LABEL" && previousLabel.dataset.v2InspectorLabel === "1") {
      previousLabel.textContent = field.label || field.key;
    } else {
      const label = document.createElement("label");
      label.dataset.v2InspectorLabel = "1";
      label.textContent = field.label || field.key;
      oldControl.parentNode.insertBefore(label, oldControl);
    }
    oldControl.replaceWith(control);
  }

  function bindInspector(typeSelectId, targetId) {
    const select = document.getElementById(typeSelectId);
    if (!select) return;
    select.addEventListener("change", () => {
      renderTarget(typeSelectId, targetId);
    });
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

    populateActionSelect(document.getElementById("modal-action-type"), catalog.choices && catalog.choices.button);
    bindInspector("modal-action-type", "modal-action-target");
    await renderTarget("modal-action-type", "modal-action-target");

    ["clockwise", "anticlockwise", "press"].forEach((direction) => {
      const selectId = `encoder-modal-${direction}-type`;
      const targetId = `encoder-modal-${direction}-target`;
      populateActionSelect(document.getElementById(selectId), catalog.choices && catalog.choices.encoder);
      bindInspector(selectId, targetId);
      renderTarget(selectId, targetId);
    });
  }

  document.addEventListener("DOMContentLoaded", bootstrap);
})();
