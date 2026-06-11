function getRow(id) {
    return document.querySelector(`tr[data-id="${id}"]`);
}

function getRowData(id) {
    const row = getRow(id);

    return {
        title: row.querySelector('[name="title"]').value,
        artist: row.querySelector('[name="artist"]').value,
        album_artist: row.querySelector('[name="album_artist"]').value || row.querySelector('[name="artist"]').value,
        album: row.querySelector('[name="album"]').value,
        year: row.querySelector('[name="year"]').value,
        genre: row.querySelector('[name="genre"]').value,
        track_number: row.querySelector('[name="track_number"]').value,
        disc_number: row.querySelector('[name="disc_number"]').value || "1",
        comments: row.querySelector('[name="comments"]').value || "",
        lyrics: row.querySelector('[name="lyrics"]').value || ""
    };
}

async function postForm(url, data) {
    const body = new URLSearchParams();

    Object.keys(data).forEach((key) => {
        body.append(key, data[key] || "");
    });

    const response = await fetch(url, {
        method: "POST",
        body
    });

    return response.json();
}

async function saveRow(id) {
    const data = getRowData(id);
    const result = await postForm(`/api/rows/${id}/update`, data);

    if (!result.ok) {
        alert(result.error || "No se pudo guardar la fila");
        return;
    }

    markRowSaved(id);
}

async function autoMetadata(id) {
    await saveRow(id);

    const response = await fetch(`/api/rows/${id}/auto-metadata`, {
        method: "POST"
    });

    const result = await response.json();

    if (!result.ok) {
        alert(result.error || "No se pudieron buscar los datos");
        return;
    }

    fillRow(id, result.item);
}

async function saveLibrary(id) {
    await saveRow(id);

    const response = await fetch(`/api/rows/${id}/save-library`, {
        method: "POST"
    });

    const result = await response.json();

    if (!result.ok) {
        alert(result.error || "No se pudo guardar en biblioteca");
        return;
    }

    refreshHistory();
}

async function sendJellyfin(id) {
    const response = await fetch(`/api/rows/${id}/send-jellyfin`, {
        method: "POST"
    });

    const result = await response.json();

    if (!result.ok) {
        alert("No se pudo refrescar Jellyfin. Revisa JELLYFIN_URL y JELLYFIN_API_KEY.");
        return;
    }

    refreshHistory();
}

function fillRow(id, item) {
    const row = getRow(id);

    row.querySelector('[name="title"]').value = item.title || "";
    row.querySelector('[name="artist"]').value = item.artist || "";
    row.querySelector('[name="album"]').value = item.album || "";
    row.querySelector('[name="year"]').value = item.year || "";
    row.querySelector('[name="genre"]').value = item.genre || "";
    row.querySelector('[name="track_number"]').value = item.track_number || "";
    row.querySelector('[name="album_artist"]').value = item.album_artist || "";
    row.querySelector('[name="disc_number"]').value = item.disc_number || "1";
    row.querySelector('[name="comments"]').value = item.comments || "";
    row.querySelector('[name="lyrics"]').value = item.lyrics || "";
}

function markRowSaved(id) {
    const row = getRow(id);
    row.classList.add("saved-flash");

    setTimeout(() => {
        row.classList.remove("saved-flash");
    }, 700);
}

function toggleAllRows(source) {
    document.querySelectorAll(".row-check").forEach((checkbox) => {
        checkbox.checked = source.checked;
    });
}

async function bulkSendJellyfin() {
    const ids = Array.from(document.querySelectorAll(".row-check:checked"))
        .map((checkbox) => Number(checkbox.value));

    if (!ids.length) {
        alert("Selecciona al menos un registro.");
        return;
    }

    const response = await fetch("/api/bulk/send-jellyfin", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ ids })
    });

    const result = await response.json();

    if (!result.ok) {
        alert("No se pudo refrescar Jellyfin. Revisa la configuración.");
        return;
    }

    refreshHistory();
}

async function refreshHistory() {
    window.location.reload();
}

setInterval(() => {
    fetch("/api/history")
        .then((response) => response.json())
        .then((items) => {
            const hasActive = items.some((item) => {
                return ["queued", "getting_info", "downloading", "tagging"].includes(item.status);
            });

            if (hasActive) {
                window.location.reload();
            }
        })
        .catch(() => {});
}, 6000);