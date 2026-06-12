function getAudioFormat() {
    const selector = document.getElementById("audio_format");
    return selector ? selector.value : "mp3";
}

function getInputRows() {
    return Array.from(document.querySelectorAll(".input-url-row"));
}

function getRow(id) {
    return document.querySelector(`tr[data-id="${id}"]`);
}

function setInputRowFetching(row, fetching) {
    row.dataset.fetching = fetching ? "1" : "0";

    row.querySelectorAll("button, input[type='checkbox']").forEach((element) => {
        element.disabled = fetching;
    });

    const textarea = row.querySelector(".input-url");
    if (textarea) {
        textarea.readOnly = fetching;
    }

    const status = row.querySelector(".input-row-status");
    if (status) {
        status.textContent = fetching ? "Obteniendo nombre..." : "";
    }
}

function setInputRowNotFound(row) {
    row.dataset.fetching = "0";
    row.dataset.notFound = "1";

    row.querySelectorAll("button, input[type='checkbox']").forEach((element) => {
        element.disabled = false;
    });

    const textarea = row.querySelector(".input-url");
    if (textarea) {
        textarea.readOnly = false;
    }

    const titleInput = row.querySelector(".original-title-input");
    if (titleInput) {
        titleInput.readOnly = false;
        titleInput.value = "No encontrado";
    }

    const uploaderInput = row.querySelector(".uploader-input");
    if (uploaderInput) {
        uploaderInput.readOnly = false;
    }

    const status = row.querySelector(".input-row-status");
    if (status) {
        status.textContent = "No encontrado. Puedes editar manualmente.";
    }
}

function createInputRow(url = "", checked = true) {
    const tbody = document.getElementById("input-url-body");

    if (!tbody) {
        return null;
    }

    const tr = document.createElement("tr");
    tr.className = "input-url-row";
    tr.dataset.fetching = "0";

    tr.innerHTML = `
        <td>
            <input type="checkbox" class="input-row-check" ${checked ? "checked" : ""} title="Seleccionar esta URL">
        </td>

        <td>
            <textarea
                class="form-control input-url"
                rows="1"
                placeholder="https://www.youtube.com/watch?v=..."
                onpaste="handleUrlPaste(event, this)"
                onblur="autoFetchNameForInputRow(this)"
                oninput="markInputRowDirty(this)"
                title="Pega una URL de YouTube. Si pegas varias líneas, se crearán varias filas."
            ></textarea>
            <div class="input-row-status"></div>
        </td>

        <td>
            <input class="cell-input original-title-input" readonly title="Nombre original del vídeo">
        </td>

        <td>
            <input class="cell-input uploader-input" readonly title="Canal o uploader">
        </td>

        <td class="actions-cell input-actions-cell">
            <button type="button" class="btn-mini action-fetch-name" onclick="fetchNameForInputRow(this)" title="Obtener nombre original">
                Obtener nombres
            </button>

            <button type="button" class="btn-mini accent action-queue" onclick="queueSingleInputRow(this)" title="Añadir esta URL a la cola">
                Añadir a cola
            </button>

            <button type="button" class="btn-mini action-view" onclick="openInputVideo(this)" title="Abrir vídeo original">
                Ver vídeo
            </button>

            <button type="button" class="btn-mini danger action-remove" onclick="removeInputRow(this)" title="Eliminar esta fila">
                Eliminar
            </button>
        </td>
    `;

    tbody.appendChild(tr);

    const textarea = tr.querySelector(".input-url");
    textarea.value = url;

    if (url) {
        setTimeout(() => {
            autoFetchNameForInputRow(textarea);
        }, 100);
    }

    return tr;
}

function addUrlRow() {
    const row = createInputRow("", true);

    if (row) {
        const input = row.querySelector(".input-url");
        if (input) {
            input.focus();
        }
    }
}

function removeInputRow(button) {
    const row = button.closest("tr");
    const tbody = document.getElementById("input-url-body");

    if (!row || !tbody || row.dataset.fetching === "1") {
        return;
    }

    if (tbody.children.length === 1) {
        row.querySelector(".input-url").value = "";
        row.querySelector(".original-title-input").value = "";
        row.querySelector(".original-title-input").readOnly = true;
        row.querySelector(".uploader-input").value = "";
        row.querySelector(".uploader-input").readOnly = true;
        row.querySelector(".input-row-status").textContent = "";
        row.querySelector(".input-row-check").checked = true;
        row.dataset.notFound = "0";
        return;
    }

    row.remove();
}

function toggleInputRows(source) {
    document.querySelectorAll(".input-row-check").forEach((checkbox) => {
        if (!checkbox.disabled) {
            checkbox.checked = source.checked;
        }
    });
}

function toggleHistoryRows(source) {
    document.querySelectorAll(".row-check").forEach((checkbox) => {
        checkbox.checked = source.checked;
    });
}

function markInputRowDirty(textarea) {
    const row = textarea.closest("tr");

    if (!row) {
        return;
    }

    row.dataset.notFound = "0";

    const titleInput = row.querySelector(".original-title-input");
    const uploaderInput = row.querySelector(".uploader-input");
    const status = row.querySelector(".input-row-status");

    titleInput.value = "";
    titleInput.readOnly = true;
    uploaderInput.value = "";
    uploaderInput.readOnly = true;
    status.textContent = "";
}

function normalizePastedUrls(text) {
    return text
        .split(/\r?\n/)
        .map((value) => value.trim())
        .filter((value) => value.length > 0);
}

function handleUrlPaste(event, textarea) {
    const pastedText = (event.clipboardData || window.clipboardData).getData("text");

    if (!pastedText) {
        return;
    }

    const urls = normalizePastedUrls(pastedText);

    if (urls.length <= 1) {
        setTimeout(() => {
            autoFetchNameForInputRow(textarea);
        }, 150);
        return;
    }

    event.preventDefault();
    textarea.value = urls[0];

    const row = textarea.closest("tr");
    if (row) {
        row.querySelector(".input-row-check").checked = true;
    }

    for (let index = 1; index < urls.length; index++) {
        createInputRow(urls[index], true);
    }

    setTimeout(() => {
        fetchNamesForInputRows();
    }, 200);
}

function getInputRowData(row) {
    const titleValue = row.querySelector(".original-title-input").value.trim();

    return {
        url: row.querySelector(".input-url").value.trim(),
        original_title: titleValue === "No encontrado" ? "" : titleValue,
        uploader: row.querySelector(".uploader-input").value.trim()
    };
}

function getSelectedInputRows() {
    return getInputRows().filter((row) => {
        const checkbox = row.querySelector(".input-row-check");
        const url = row.querySelector(".input-url").value.trim();
        return checkbox.checked && url.length > 0 && row.dataset.fetching !== "1";
    });
}

function getAllInputRowsWithUrl() {
    return getInputRows().filter((row) => {
        const url = row.querySelector(".input-url").value.trim();
        return url.length > 0 && row.dataset.fetching !== "1";
    });
}

async function fetchVideoInfoForUrls(urls, timeoutMs = 5000) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);

    try {
        const response = await fetch("/api/video-info", {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({ urls }),
            signal: controller.signal
        });

        return await response.json();
    } finally {
        clearTimeout(timer);
    }
}

async function autoFetchNameForInputRow(textarea) {
    const row = textarea.closest("tr");

    if (!row) {
        return;
    }

    const url = row.querySelector(".input-url").value.trim();
    const currentTitle = row.querySelector(".original-title-input").value.trim();

    if (!url || currentTitle || row.dataset.fetching === "1") {
        return;
    }

    await fetchNameForInputRow(row.querySelector(".action-fetch-name"));
}

async function fetchNameForInputRow(buttonOrRow) {
    const row = buttonOrRow.closest ? buttonOrRow.closest("tr") : buttonOrRow;

    if (!row || row.dataset.fetching === "1") {
        return;
    }

    const url = row.querySelector(".input-url").value.trim();

    if (!url) {
        alert("Introduce una URL primero.");
        return;
    }

    setInputRowFetching(row, true);
    row.querySelector(".original-title-input").value = "Buscando...";
    row.querySelector(".uploader-input").value = "";

    try {
        const result = await fetchVideoInfoForUrls([url], 5000);

        if (!result.ok || !result.results || !result.results.length || !result.results[0].ok) {
            setInputRowNotFound(row);
            return;
        }

        const item = result.results[0];
        const titleInput = row.querySelector(".original-title-input");
        const uploaderInput = row.querySelector(".uploader-input");

        titleInput.value = item.original_title || "No encontrado";
        uploaderInput.value = item.uploader || "";
        row.querySelector(".input-row-status").textContent = "";

        row.querySelectorAll("button, input[type='checkbox']").forEach((element) => {
            element.disabled = false;
        });

        row.querySelector(".input-url").readOnly = false;
        row.dataset.fetching = "0";
    } catch (error) {
        setInputRowNotFound(row);
    }
}

async function fetchNamesForInputRows() {
    const rows = getSelectedInputRows();

    if (!rows.length) {
        alert("Selecciona al menos una URL.");
        return;
    }

    for (const row of rows) {
        await fetchNameForInputRow(row.querySelector(".action-fetch-name"));
    }
}

async function queueRows(rows) {
    const validRows = rows
        .map((row) => getInputRowData(row))
        .filter((row) => row.url.length > 0);

    if (!validRows.length) {
        alert("No hay URLs válidas o todavía se están obteniendo nombres.");
        return;
    }

    const response = await fetch("/api/queue", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            rows: validRows,
            audio_format: getAudioFormat()
        })
    });

    const result = await response.json();

    if (!result.ok) {
        alert(result.error || "No se pudo añadir a la cola.");
        return;
    }

    refreshHistory();
}

async function queueSingleInputRow(button) {
    const row = button.closest("tr");

    if (row.dataset.fetching !== "1") {
        await queueRows([row]);
    }
}

async function queueSelectedInputRows() {
    await queueRows(getSelectedInputRows());
}

async function queueAllInputRows() {
    await queueRows(getAllInputRowsWithUrl());
}

function openInputVideo(button) {
    const url = button.closest("tr").querySelector(".input-url").value.trim();

    if (!url) {
        alert("Introduce una URL primero.");
        return;
    }

    window.open(url, "_blank", "noopener,noreferrer");
}

function openVideoUrl(url) {
    if (url) {
        window.open(url, "_blank", "noopener,noreferrer");
    }
}

function getHistoryRowData(id) {
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
    const result = await postForm(`/api/rows/${id}/update`, getHistoryRowData(id));

    if (!result.ok) {
        alert(result.error || "No se pudo guardar la fila.");
        return false;
    }

    markRowSaved(id);
    return true;
}

async function autoMetadata(id) {
    if (!(await saveRow(id))) {
        return;
    }

    const response = await fetch(`/api/rows/${id}/auto-metadata`, {
        method: "POST"
    });

    const result = await response.json();

    if (!result.ok) {
        alert(result.error || "No se pudieron buscar los datos.");
        return;
    }

    fillHistoryRow(id, result.item);
}

async function downloadRow(id) {
    if (!(await saveRow(id))) {
        return;
    }

    const response = await fetch(`/api/rows/${id}/download`, {
        method: "POST"
    });

    const result = await response.json();

    if (!result.ok) {
        alert(result.error || "No se pudo enviar a descarga.");
        return;
    }

    refreshHistory();
}

function selectedHistoryIds() {
    return Array.from(document.querySelectorAll(".row-check:checked"))
        .map((checkbox) => Number(checkbox.value));
}

async function saveSelectedRows() {
    const ids = selectedHistoryIds();

    if (!ids.length) {
        alert("Selecciona al menos un registro.");
        return;
    }

    for (const id of ids) {
        await saveRow(id);
    }
}

async function autoMetadataSelectedRows() {
    const ids = selectedHistoryIds();

    if (!ids.length) {
        alert("Selecciona al menos un registro.");
        return;
    }

    for (const id of ids) {
        await autoMetadata(id);
    }
}

async function downloadSelectedRows() {
    const ids = selectedHistoryIds();

    if (!ids.length) {
        alert("Selecciona al menos un registro.");
        return;
    }

    const response = await fetch("/api/rows/download-selected", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ ids })
    });

    const result = await response.json();

    if (!result.ok) {
        alert(result.error || "No se pudieron enviar a descarga.");
        return;
    }

    refreshHistory();
}

async function sendJellyfin(id) {
    if (!(await saveRow(id))) {
        return;
    }

    const response = await fetch(`/api/jellyfin/send/${id}`, {
        method: "POST"
    });

    const result = await response.json();

    if (!result.ok) {
        alert(result.error || "No se pudo enviar a Jellyfin. Revisa ajustes y rutas.");
        return;
    }

    refreshHistory();
}

async function sendSelectedToJellyfin() {
    const selectedCheckboxes = Array.from(document.querySelectorAll(".row-check:checked"));

    if (!selectedCheckboxes.length) {
        alert("Selecciona al menos un registro.");
        return;
    }

    const sendableIds = [];
    const skippedIds = [];

    selectedCheckboxes.forEach((checkbox) => {
        const id = Number(checkbox.value);
        const row = getRow(id);
        const sendButton = row ? row.querySelector('button[onclick^="sendJellyfin"]') : null;

        if (sendButton && sendButton.disabled) {
            skippedIds.push(id);
        } else {
            sendableIds.push(id);
        }
    });

    if (!sendableIds.length) {
        alert("Ninguno de los registros seleccionados está descargado todavía. No se puede enviar a Jellyfin.");
        return;
    }

    for (const id of sendableIds) {
        await saveRow(id);
    }

    const response = await fetch("/api/jellyfin/send-selected", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({ ids: sendableIds })
    });

    const result = await response.json();

    if (!result.ok) {
        alert(result.error || "No se pudo enviar a Jellyfin. Revisa ajustes y rutas.");
        return;
    }

    let sentCount = 0;
    let failedCount = 0;

    if (Array.isArray(result.results)) {
        sentCount = result.results.filter((item) => item.ok).length;
        failedCount = result.results.filter((item) => !item.ok).length;
    } else {
        sentCount = sendableIds.length;
    }

    const summary = [
        `${sentCount} registro(s) enviados a Jellyfin.`,
        skippedIds.length ? `${skippedIds.length} omitido(s) porque aún no estaban descargados.` : "",
        failedCount ? `${failedCount} fallido(s). Revisa el histórico para ver errores.` : ""
    ].filter(Boolean).join("");
    
    alert(summary);
    refreshHistory();
}

async function deleteSelectedRows() {
    const ids = selectedHistoryIds();

    if (!ids.length) {
        alert("Selecciona al menos un registro.");
        return;
    }

    if (!confirm(`¿Eliminar ${ids.length} registros seleccionados?`)) {
        return;
    }

    for (const id of ids) {
        await deleteRow(id, false, true);
    }

    refreshHistory();
}

async function deleteRow(id, force = false, silent = false) {
    let url = `/api/rows/${id}`;

    if (force) {
        url += "?force=true";
    }

    const response = await fetch(url, {
        method: "DELETE"
    });

    const result = await response.json();

    if (response.status === 409 && result.requires_confirmation) {
        const confirmed = silent
            ? true
            : confirm(result.message || "Aún no se ha pasado a Jellyfin. ¿Seguro que quieres eliminarlo de incoming?");

        if (!confirmed) {
            return;
        }

        return deleteRow(id, true, silent);
    }

    if (!result.ok) {
        if (!silent) {
            alert(result.error || "No se pudo eliminar el registro.");
        }
        return;
    }

    const row = getRow(id);
    if (row) {
        row.remove();
    }
}

function fillHistoryRow(id, item) {
    const row = getRow(id);

    if (!row) {
        return;
    }

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

    if (!row) {
        return;
    }

    row.classList.add("saved-flash");

    setTimeout(() => {
        row.classList.remove("saved-flash");
    }, 700);
}

function refreshHistory() {
    window.location.reload();
}

/* --------------------------------------------------------------------------
   Histórico usuario / vista principal
-------------------------------------------------------------------------- */

function toggleHistoryTools() {
    const element = document.getElementById("history-tools");

    if (!element) {
        return;
    }

    element.style.display = element.style.display === "none" ? "block" : "none";
}

const HISTORY_COLUMNS = [
    "select",
    "status",
    "original",
    "title",
    "artist",
    "album",
    "year",
    "track",
    "genre",
    "format",
    "jellyfin",
    "actions"
];

function initColumnToggles() {
    const box = document.getElementById("history-column-toggles");

    if (!box) {
        return;
    }

    const saved = JSON.parse(localStorage.getItem("dwsongs_visible_columns") || "{}");
    box.innerHTML = "";

    HISTORY_COLUMNS.forEach((column) => {
        const visible = saved[column] !== false;
        const label = document.createElement("label");
        label.className = "column-toggle-item";
        label.innerHTML = `<input type="checkbox" ${visible ? "checked" : ""} data-column-toggle="${column}"> ${column}`;
        box.appendChild(label);
    });

    box.querySelectorAll("input[data-column-toggle]").forEach((input) => {
        input.addEventListener("change", applyColumnVisibility);
    });

    applyColumnVisibility();
}

function applyColumnVisibility() {
    const saved = {};

    document.querySelectorAll("input[data-column-toggle]").forEach((input) => {
        saved[input.dataset.columnToggle] = input.checked;
    });

    localStorage.setItem("dwsongs_visible_columns", JSON.stringify(saved));

    HISTORY_COLUMNS.forEach((column) => {
        const visible = saved[column] !== false;
        document.querySelectorAll(`#history-table [data-column="${column}"]`).forEach((cell) => {
            cell.style.display = visible ? "" : "none";
        });
    });
}

function applyHistoryFilters() {
    const filters = {};

    document.querySelectorAll(".history-filter").forEach((input) => {
        if (input.value.trim()) {
            filters[input.dataset.filterColumn] = input.value.trim().toLowerCase();
        }
    });

    document.querySelectorAll("#history-table tbody tr[data-id]").forEach((row) => {
        let show = true;

        Object.keys(filters).forEach((column) => {
            const cell = row.querySelector(`[data-column="${column}"]`);
            const value = ((cell && (cell.dataset.filterValue || cell.textContent)) || "").toLowerCase();

            if (!value.includes(filters[column])) {
                show = false;
            }
        });

        row.style.display = show ? "" : "none";
    });
}

function clearHistoryFilters() {
    document.querySelectorAll(".history-filter").forEach((input) => {
        input.value = "";
    });

    applyHistoryFilters();
}

/* --------------------------------------------------------------------------
   Histórico admin /admin/downloads
-------------------------------------------------------------------------- */

function toggleAdminHistoryTools() {
    const element = document.getElementById("admin-history-tools");

    if (!element) {
        return;
    }

    element.style.display = element.style.display === "none" ? "block" : "none";
}

const ADMIN_HISTORY_COLUMNS = [
    "id",
    "user",
    "status",
    "url",
    "original",
    "uploader",
    "title",
    "artist",
    "album",
    "year",
    "track",
    "genre",
    "format",
    "incoming",
    "final",
    "incoming_size",
    "final_size",
    "created",
    "queued",
    "info",
    "download_started",
    "downloaded",
    "metadata",
    "moved",
    "jellyfin",
    "deleted",
    "actions"
];

function initAdminHistoryColumnToggles() {
    const box = document.getElementById("admin-history-column-toggles");

    if (!box) {
        return;
    }

    const saved = JSON.parse(localStorage.getItem("dwsongs_admin_visible_columns") || "{}");
    box.innerHTML = "";

    ADMIN_HISTORY_COLUMNS.forEach((column) => {
        const visible = saved[column] !== false;
        const label = document.createElement("label");
        label.className = "column-toggle-item";
        label.innerHTML = `<input type="checkbox" ${visible ? "checked" : ""} data-admin-column-toggle="${column}"> ${column}`;
        box.appendChild(label);
    });

    box.querySelectorAll("input[data-admin-column-toggle]").forEach((input) => {
        input.addEventListener("change", applyAdminHistoryColumnVisibility);
    });

    applyAdminHistoryColumnVisibility();
}

function applyAdminHistoryColumnVisibility() {
    const saved = {};

    document.querySelectorAll("input[data-admin-column-toggle]").forEach((input) => {
        saved[input.dataset.adminColumnToggle] = input.checked;
    });

    localStorage.setItem("dwsongs_admin_visible_columns", JSON.stringify(saved));

    ADMIN_HISTORY_COLUMNS.forEach((column) => {
        const visible = saved[column] !== false;
        document.querySelectorAll(`#admin-history-table [data-column="${column}"]`).forEach((cell) => {
            cell.style.display = visible ? "" : "none";
        });
    });
}

function applyAdminHistoryFilters() {
    const filters = {};

    document.querySelectorAll(".admin-history-filter").forEach((input) => {
        if (input.value.trim()) {
            filters[input.dataset.filterColumn] = input.value.trim().toLowerCase();
        }
    });

    document.querySelectorAll("#admin-history-table tbody tr[data-admin-download-id]").forEach((row) => {
        let show = true;

        Object.keys(filters).forEach((column) => {
            const cell = row.querySelector(`[data-column="${column}"]`);
            const value = ((cell && (cell.dataset.filterValue || cell.textContent)) || "").toLowerCase();

            if (!value.includes(filters[column])) {
                show = false;
            }
        });

        row.style.display = show ? "" : "none";

        const detailsRow = document.getElementById(`admin-actions-${row.dataset.adminDownloadId}`);
        if (detailsRow && !show) {
            detailsRow.style.display = "none";
        }
    });
}

function clearAdminHistoryFilters() {
    document.querySelectorAll(".admin-history-filter").forEach((input) => {
        input.value = "";
    });

    applyAdminHistoryFilters();
}

function toggleAdminActions(downloadId) {
    const row = document.getElementById(`admin-actions-${downloadId}`);

    if (!row) {
        return;
    }

    row.style.display = row.style.display === "none" ? "table-row" : "none";
}

document.addEventListener("DOMContentLoaded", () => {
    const firstUrlInput = document.querySelector(".input-url");

    if (firstUrlInput) {
        firstUrlInput.focus();
    }

    initColumnToggles();
    initAdminHistoryColumnToggles();

    document.querySelectorAll(".history-filter").forEach((input) => {
        input.addEventListener("input", applyHistoryFilters);
    });

    document.querySelectorAll(".admin-history-filter").forEach((input) => {
        input.addEventListener("input", applyAdminHistoryFilters);
    });
});

setInterval(() => {
    if (window.location.pathname !== "/") {
        return;
    }

    fetch("/api/history")
        .then((response) => response.json())
        .then((items) => {
            if (!Array.isArray(items)) {
                return;
            }

            const hasActive = items.some((item) => {
                return [
                    "pending",
                    "getting_info",
                    "queued",
                    "downloading",
                    "saving_library"
                ].includes(item.status);
            });

            if (hasActive) {
                window.location.reload();
            }
        })
        .catch(() => {});
}, 6000);
