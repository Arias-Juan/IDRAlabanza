"use strict";

// ---------------------------------------------------------------- config

// emoji -> se muestra en el encabezado y en el chip; el texto va como
// tooltip para no ensanchar la columna en pantallas angostas.
const LINK_COLUMNS = {
    Notas_Piano: ["🎹", "Notas de piano"],
    Notas_Guitarra: ["🎸", "Notas de guitarra"],
    Letra: ["📄", "Letra"],
    Video_Bateria: ["🥁", "Video de batería"],
    Audio: ["🎧", "Audio"]
};

const TEXT_HEADERS = {
    Numero: "N°",
    Cancion: "Canción"
};

const COLS_DIRECCION = ["Numero", "Cancion", "Letra", "Audio", "Tipo"];

const COLS_EQUIPO = [
    "Numero",
    "Cancion",
    "Tono",
    "Letra",
    "Notas_Piano",
    "Notas_Guitarra",
    "Video_Bateria",
    "Audio",
    "Tipo"
];

const COLS_TODAS = [...COLS_EQUIPO, "Estado"];

const COLS_ADMIN = [
    "Numero",
    "Cancion",
    "Notas_Piano",
    "Notas_Guitarra",
    "Letra",
    "Video_Bateria",
    "Tono",
    "Estado",
    "Tipo",
    "Audio"
];

const state = {
    songs: [],
    setlist: null,
    textoCatalogo: "",
    builder: [],
    apiKey: localStorage.getItem("idra_api_key") || "",
    autenticado: false,
    ttlDias: 7,

    // Mientras BigQuery responde se muestran puntitos en lugar del mensaje
    // de "no hay canciones"; a los 5 segundos gana el mensaje.
    cargado: false,
    esperaVencida: false
};

const ESPERA_MAX_MS = 5000;

const $ = (id) => document.getElementById(id);

// ------------------------------------------------------------- utilidades

function escapeHtml(value) {
    return String(value)
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#39;");
}

/** true mientras convenga mostrar los puntitos en vez del vacío. */
function esperando() {
    return !state.cargado && !state.esperaVencida;
}

function bloqueVacio(mensaje) {
    if (esperando()) {
        return (
            '<div class="cargando" role="status" aria-label="Cargando">' +
            "<span></span><span></span><span></span></div>"
        );
    }

    return mensaje ? `<p class="info">${escapeHtml(mensaje)}</p>` : "";
}

function toast(mensaje, esError = false) {
    const el = document.createElement("div");

    el.className = esError ? "toast error" : "toast";
    el.textContent = mensaje;

    $("toasts").appendChild(el);

    setTimeout(() => el.remove(), 4000);
}

async function api(path, options = {}) {
    const headers = { ...(options.headers || {}) };

    if (options.body) {
        headers["Content-Type"] = "application/json";
    }

    if (options.auth) {
        headers["X-API-Key"] = state.apiKey;
    }

    const res = await fetch(path, { ...options, headers });

    if (!res.ok) {
        let detail = `Error ${res.status}`;

        try {
            const data = await res.json();

            if (typeof data.detail === "string") {
                detail = data.detail;
            } else if (Array.isArray(data.detail)) {
                detail = data.detail
                    .map((d) => `${d.loc?.join(".")}: ${d.msg}`)
                    .join(" | ");
            }
        } catch {
            /* respuesta sin cuerpo JSON */
        }

        // El backend habla de "API key"; en la interfaz es la contraseña.
        if (res.status === 401) {
            detail = "Contraseña incorrecta.";
        }

        const error = new Error(detail);

        error.status = res.status;

        throw error;
    }

    return res.status === 204 ? null : res.json();
}

// ----------------------------------------------------------- render tabla

function renderSongTable(container, data, columns, vacio = "") {
    if (!data.length) {
        container.innerHTML = bloqueVacio(vacio);

        return;
    }

    const parts = [
        '<div class="tabla-wrap">',
        '<table class="tabla-canciones"><thead><tr>'
    ];

    for (const col of columns) {
        if (LINK_COLUMNS[col]) {
            const [emoji, titulo] = LINK_COLUMNS[col];

            parts.push(
                `<th class="col-link" title="${escapeHtml(titulo)}">` +
                `${emoji}</th>`
            );
        } else {
            parts.push(`<th>${escapeHtml(TEXT_HEADERS[col] || col)}</th>`);
        }
    }

    parts.push("</tr></thead><tbody>");

    for (const row of data) {
        parts.push("<tr>");

        for (const col of columns) {
            const value = row[col];

            if (LINK_COLUMNS[col]) {
                const [emoji, titulo] = LINK_COLUMNS[col];
                const url = value == null ? "" : String(value).trim();

                if (url.startsWith("http://") || url.startsWith("https://")) {
                    parts.push(
                        '<td><a class="celda-link" target="_blank" ' +
                        `rel="noopener" title="${escapeHtml(titulo)}" ` +
                        `href="${escapeHtml(url)}">${emoji}</a></td>`
                    );
                } else {
                    parts.push('<td class="vacio">—</td>');
                }
            } else {
                const text = value == null ? "" : String(value);

                parts.push(`<td class="texto">${escapeHtml(text)}</td>`);
            }
        }

        parts.push("</tr>");
    }

    parts.push("</tbody></table></div>");

    container.innerHTML = parts.join("");
}

function avisarFaltantes(container, faltantes) {
    if (!faltantes || !faltantes.length) {
        container.innerHTML = "";

        return;
    }

    const numeros = faltantes.map((n) => `N° ${n}`).join(", ");

    container.innerHTML =
        `<p class="warning">${escapeHtml(numeros)}: ya no está(n) en la ` +
        "base y no se muestra(n).</p>";
}

// ------------------------------------------------------------- datos

async function cargarCanciones() {
    state.songs = await api("/api/songs");
}

async function cargarSetlist() {
    state.setlist = await api("/api/setlist");
}

async function cargarCatalogo() {
    const data = await api("/api/songs/texto-compartir");

    state.textoCatalogo = data.texto;
}

async function refrescar() {
    try {
        await Promise.all([
            cargarCanciones(),
            cargarSetlist(),
            cargarCatalogo()
        ]);

        state.cargado = true;

        renderVistaActual();
    } catch (err) {
        // Aunque falle, se deja de esperar: mejor el mensaje que puntitos
        // eternos.
        state.cargado = true;

        renderVistaActual();

        toast(err.message, true);
    }
}

// ------------------------------------------------------------- vistas

function renderDireccion() {
    const ok = state.songs.filter((s) => s.Estado === "OK");

    renderSongTable(
        $("tabla-direccion"),
        ok,
        COLS_DIRECCION,
        "No hay canciones con estado 'OK'."
    );
}

function renderEquipo() {
    const setlist = state.setlist;
    const tieneListado = setlist && setlist.canciones.length > 0;

    $("bloque-listado").classList.toggle("oculto", !tieneListado);

    if (tieneListado) {
        avisarFaltantes($("aviso-faltantes"), setlist.faltantes);

        renderSongTable($("tabla-listado"), setlist.canciones, COLS_EQUIPO);

        $("publicado").textContent =
            `⏳ Publicado: ${formatearFecha(setlist.publicado)}`;
    }

    const busqueda = $("buscador").value.trim().toLowerCase();

    const filtradas = busqueda
        ? state.songs.filter(
              (s) =>
                  (s.Cancion || "").toLowerCase().includes(busqueda) ||
                  String(s.Numero).includes(busqueda)
          )
        : state.songs;

    renderSongTable(
        $("tabla-equipo"),
        filtradas,
        COLS_TODAS,
        "No se encontraron canciones."
    );
}

function formatearFecha(iso) {
    if (!iso) {
        return "—";
    }

    const fecha = new Date(iso);

    return fecha.toLocaleString("es-AR", {
        dateStyle: "short",
        timeStyle: "short"
    });
}

function renderCompartir() {
    const setlist = state.setlist;
    const tiene = setlist && setlist.canciones.length > 0;

    $("sin-listado").classList.toggle("oculto", tiene || esperando());
    $("espera-listado").innerHTML = tiene ? "" : bloqueVacio("");
    $("bloque-compartir-listado").classList.toggle("oculto", !tiene);

    if (tiene) {
        $("texto-compartir").textContent = setlist.texto_compartir;
    }

    const hayCatalogo = Boolean(state.textoCatalogo);

    $("espera-catalogo").innerHTML = hayCatalogo ? "" : bloqueVacio("");
    $("bloque-catalogo").classList.toggle("oculto", !hayCatalogo);

    if (hayCatalogo) {
        $("texto-catalogo").textContent = state.textoCatalogo;
    }
}

function renderAdmin() {
    $("admin-bloqueado").classList.toggle("oculto", state.autenticado);
    $("admin-panel").classList.toggle("oculto", !state.autenticado);

    if (!state.autenticado) {
        return;
    }

    renderSongTable($("tabla-admin"), state.songs, COLS_ADMIN);

    // Selector de canción a actualizar: conserva la selección si sigue.
    const select = $("upd-cancion");
    const previo = select.value;

    select.innerHTML = state.songs
        .map(
            (s) =>
                `<option value="${s.Numero}">` +
                `${escapeHtml(`${s.Numero} - ${s.Cancion}`)}</option>`
        )
        .join("");

    if (previo && state.songs.some((s) => String(s.Numero) === previo)) {
        select.value = previo;
    }

    sincronizarEstadoActual();

    $("songs-datalist").innerHTML = state.songs
        .map(
            (s) =>
                `<option value="${escapeHtml(`${s.Numero} - ${s.Cancion}`)}">`
        )
        .join("");

    renderBuilder();
    renderListadoAdmin();
}

function sincronizarEstadoActual() {
    const numero = Number($("upd-cancion").value);
    const song = state.songs.find((s) => s.Numero === numero);

    if (song) {
        $("upd-estado").value = song.Estado;
    }
}

function renderBuilder() {
    const cont = $("builder");

    $("info-orden").classList.toggle("oculto", !state.builder.length);
    $("btn-publicar").disabled = !state.builder.length;

    cont.innerHTML = "";

    state.builder.forEach((song, idx) => {
        const fila = document.createElement("div");

        fila.className = "builder-fila";

        const label = document.createElement("div");

        label.innerHTML =
            `<strong>${idx + 1}.</strong> ` +
            escapeHtml(`${song.Numero} - ${song.Cancion}`);

        const btnUp = crearBoton("⬆️", idx === 0, () => {
            [state.builder[idx - 1], state.builder[idx]] = [
                state.builder[idx],
                state.builder[idx - 1]
            ];

            renderBuilder();
        });

        const btnDown = crearBoton(
            "⬇️",
            idx === state.builder.length - 1,
            () => {
                [state.builder[idx + 1], state.builder[idx]] = [
                    state.builder[idx],
                    state.builder[idx + 1]
                ];

                renderBuilder();
            }
        );

        const btnDel = crearBoton("🗑️", false, () => {
            state.builder.splice(idx, 1);

            renderBuilder();
        });

        fila.append(label, btnUp, btnDown, btnDel);

        cont.appendChild(fila);
    });
}

function crearBoton(texto, deshabilitado, onClick) {
    const btn = document.createElement("button");

    btn.className = "btn icono";
    btn.textContent = texto;
    btn.disabled = deshabilitado;
    btn.type = "button";
    btn.addEventListener("click", onClick);

    return btn;
}

function renderListadoAdmin() {
    const setlist = state.setlist;
    const tiene = setlist && setlist.canciones.length > 0;

    $("bloque-listado-admin").classList.toggle("oculto", !tiene);

    if (!tiene) {
        return;
    }

    avisarFaltantes($("aviso-faltantes-admin"), setlist.faltantes);

    const conOrden = setlist.canciones.map((song, idx) => ({
        ...song,
        Orden: idx + 1
    }));

    renderSongTable($("tabla-listado-admin"), conOrden, [
        "Orden",
        "Numero",
        "Cancion",
        "Tipo",
        "Estado"
    ]);
}

function rolActual() {
    return $("rol").value;
}

function renderVistaActual() {
    const rol = rolActual();

    $("vista-direccion").classList.toggle("oculto", rol !== "direccion");
    $("vista-equipo").classList.toggle("oculto", rol !== "equipo");
    $("vista-compartir").classList.toggle("oculto", rol !== "compartir");
    $("vista-admin").classList.toggle("oculto", rol !== "admin");
    $("sidebar-admin").classList.toggle("oculto", rol !== "admin");

    if (rol === "direccion") {
        renderDireccion();
    } else if (rol === "equipo") {
        renderEquipo();
    } else if (rol === "compartir") {
        renderCompartir();
    } else {
        renderAdmin();
    }
}

// ------------------------------------------------------------- auth

async function login(silencioso = false) {
    if (!state.apiKey) {
        return false;
    }

    try {
        await api("/api/auth/check", { method: "POST", auth: true });

        state.autenticado = true;

        localStorage.setItem("idra_api_key", state.apiKey);

        $("login-error").classList.add("oculto");
        $("btn-login").classList.add("oculto");
        $("btn-logout").classList.remove("oculto");
        $("api-key").value = "";

        renderVistaActual();

        return true;
    } catch (err) {
        state.autenticado = false;

        if (!silencioso) {
            $("login-error").textContent = err.message;
            $("login-error").classList.remove("oculto");
        } else {
            // Key guardada que ya no sirve: se descarta sin molestar.
            localStorage.removeItem("idra_api_key");
            state.apiKey = "";
        }

        return false;
    }
}

function logout() {
    state.apiKey = "";
    state.autenticado = false;

    localStorage.removeItem("idra_api_key");

    $("btn-login").classList.remove("oculto");
    $("btn-logout").classList.add("oculto");

    renderVistaActual();
}

// ------------------------------------------------------------- acciones

async function guardarCancion(event) {
    event.preventDefault();

    const nombre = $("f-cancion").value.trim();

    if (!nombre) {
        toast("El nombre es obligatorio.", true);

        return;
    }

    const payload = {
        Cancion: nombre,
        Notas_Piano: $("f-piano").value.trim(),
        Notas_Guitarra: $("f-guitarra").value.trim(),
        Letra: $("f-letra").value.trim(),
        Video_Bateria: $("f-bateria").value.trim(),
        Tono: $("f-tono").value.trim(),
        Estado: $("f-estado").value,
        Tipo: $("f-tipo").value,
        Audio: $("f-audio").value.trim()
    };

    try {
        const creadas = await api("/api/songs", {
            method: "POST",
            auth: true,
            body: JSON.stringify(payload)
        });

        $("form-cancion").reset();

        toast(`✅ Canción #${creadas[0].Numero} guardada con éxito!`);

        await refrescar();
    } catch (err) {
        toast(`Error al insertar: ${err.message}`, true);
    }
}

async function eliminarCancion() {
    const numero = Number($("del-numero").value);

    if (!numero) {
        return;
    }

    if (!confirm(`¿Eliminar permanentemente la canción N° ${numero}?`)) {
        return;
    }

    try {
        await api(`/api/songs/${numero}`, { method: "DELETE", auth: true });

        toast(`🗑️ Registro #${numero} eliminado.`);

        await refrescar();
    } catch (err) {
        toast(`Error al eliminar: ${err.message}`, true);
    }
}

async function actualizarEstado() {
    const numero = Number($("upd-cancion").value);
    const estado = $("upd-estado").value;

    if (!numero) {
        return;
    }

    try {
        await api(`/api/songs/${numero}`, {
            method: "PATCH",
            auth: true,
            body: JSON.stringify({ Estado: estado })
        });

        toast(`✅ Canción #${numero} actualizada a ${estado}`);

        await refrescar();
    } catch (err) {
        toast(`Error al actualizar: ${err.message}`, true);
    }
}

function agregarAlBuilder() {
    const valor = $("song-pick").value.trim();

    if (!valor) {
        return;
    }

    const numero = Number(valor.split(" - ")[0]);
    const song = state.songs.find((s) => s.Numero === numero);

    if (!song) {
        toast("Elegí una canción de la lista.", true);

        return;
    }

    state.builder.push(song);

    $("song-pick").value = "";

    renderBuilder();
}

async function publicarListado() {
    try {
        await api("/api/setlist", {
            method: "PUT",
            auth: true,
            body: JSON.stringify({
                numeros: state.builder.map((s) => s.Numero)
            })
        });

        state.builder = [];

        toast(`✅ Listado publicado por ${state.ttlDias} días`);

        await refrescar();
    } catch (err) {
        toast(`Error al publicar listado: ${err.message}`, true);
    }
}

async function limpiarListado() {
    if (!confirm("¿Eliminar el listado publicado?")) {
        return;
    }

    try {
        await api("/api/setlist", { method: "DELETE", auth: true });

        state.builder = [];

        toast("🗑️ Listado eliminado");

        await refrescar();
    } catch (err) {
        toast(`Error al limpiar listado: ${err.message}`, true);
    }
}

async function copiarTexto(idOrigen) {
    const texto = $(idOrigen).textContent;

    try {
        await navigator.clipboard.writeText(texto);

        toast("📋 Copiado al portapapeles");
    } catch {
        toast("No se pudo copiar automáticamente.", true);
    }
}

// ------------------------------------------------------------- init

function initEventos() {
    $("rol").addEventListener("change", () => {
        // En móvil el panel tapa el contenido: al elegir un rol se cierra.
        $("sidebar").classList.remove("abierto");

        renderVistaActual();
    });

    $("buscador").addEventListener("input", renderEquipo);

    $("menu-toggle").addEventListener("click", () =>
        $("sidebar").classList.toggle("abierto")
    );

    $("btn-login").addEventListener("click", () => {
        state.apiKey = $("api-key").value.trim();

        login();
    });

    $("api-key").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            state.apiKey = $("api-key").value.trim();

            login();
        }
    });

    $("btn-logout").addEventListener("click", logout);

    for (const tab of document.querySelectorAll(".tab")) {
        tab.addEventListener("click", () => {
            document
                .querySelectorAll(".tab")
                .forEach((t) => t.classList.remove("activo"));

            tab.classList.add("activo");

            for (const panel of document.querySelectorAll(".panel")) {
                panel.classList.add("oculto");
            }

            $(`tab-${tab.dataset.tab}`).classList.remove("oculto");
        });
    }

    $("form-cancion").addEventListener("submit", guardarCancion);
    $("btn-eliminar").addEventListener("click", eliminarCancion);
    $("btn-actualizar").addEventListener("click", actualizarEstado);
    $("upd-cancion").addEventListener("change", sincronizarEstadoActual);
    $("btn-agregar").addEventListener("click", agregarAlBuilder);
    $("btn-publicar").addEventListener("click", publicarListado);
    $("btn-limpiar").addEventListener("click", limpiarListado);
    $("btn-copiar").addEventListener("click", () =>
        copiarTexto("texto-compartir")
    );

    $("btn-copiar-catalogo").addEventListener("click", () =>
        copiarTexto("texto-catalogo")
    );

    $("song-pick").addEventListener("keydown", (e) => {
        if (e.key === "Enter") {
            e.preventDefault();

            agregarAlBuilder();
        }
    });
}

async function init() {
    initEventos();

    // Puntitos desde el primer frame, sin esperar a la primera respuesta.
    renderVistaActual();

    setTimeout(() => {
        if (!state.cargado) {
            state.esperaVencida = true;

            renderVistaActual();
        }
    }, ESPERA_MAX_MS);

    try {
        const config = await api("/api/config");

        state.ttlDias = config.setlist_ttl_days;
    } catch {
        /* si falla, queda el default */
    }

    if (state.apiKey) {
        await login(true);
    }

    await refrescar();
}

init();
