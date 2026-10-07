/* Picker de peripheriques de sortie audio (popup d'emplacement, action
 * "audio_output" - ex: basculer casque/enceintes). Chargee une seule fois
 * par session, meme pattern que ha-entities.js. Le champ compact en
 * dessous stocke l'identifiant opaque du peripherique (pas destine a etre
 * tape a la main, contrairement aux autres types d'action). Depend des
 * elements/fonctions definies dans dashboard.js (charge avant ce
 * fichier). */

let audioDevices = null;

function loadAudioDevicesIfNeeded(callback) {
  if (audioDevices !== null) { callback(null); return; }
  fetch("/audio-devices")
    .then((r) => r.json())
    .then((data) => {
      audioDevices = data.devices || [];
      callback(data.error || null);
    })
    .catch(() => {
      audioDevices = [];
      callback("Impossible de contacter l'appli.");
    });
}

function renderAudioDeviceList(query) {
  const list = document.getElementById("modal-audio-list");
  list.innerHTML = "";
  if (!audioDevices) return;

  const q = query.trim().toLowerCase();
  const filtered = q
    ? audioDevices.filter((d) => d.name.toLowerCase().includes(q))
    : audioDevices;

  if (!filtered.length) {
    const empty = document.createElement("p");
    empty.className = "hint";
    empty.textContent = q ? "Aucun peripherique trouve." : "Aucun peripherique audio actif detecte.";
    list.appendChild(empty);
    return;
  }

  filtered.forEach((device) => {
    const row = document.createElement("div");
    row.className = "entity-row";

    const name = document.createElement("span");
    name.className = "entity-name";
    name.textContent = device.name;
    row.appendChild(name);

    row.addEventListener("click", () => selectAudioDevice(device));
    list.appendChild(row);
  });
}

function selectAudioDevice(device) {
  document.getElementById("modal-audio-search").value = device.name;
  document.getElementById("modal-action-target").value = device.id;
}

function updateAudioPickerVisibility() {
  const isAudio = document.getElementById("modal-action-type").value === "audio_output";
  document.getElementById("modal-audio-fields").style.display = isAudio ? "block" : "none";
  if (isAudio) {
    loadAudioDevicesIfNeeded((err) => {
      document.getElementById("modal-audio-status").textContent = err || "";
      renderAudioDeviceList(document.getElementById("modal-audio-search").value);
    });
  }
}

document.getElementById("modal-audio-search").addEventListener("input", (e) => {
  renderAudioDeviceList(e.target.value);
});
