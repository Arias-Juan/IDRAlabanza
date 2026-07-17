import streamlit as st
import pandas as pd
import os

from datetime import datetime, timedelta
from html import escape

st.set_page_config(page_title="Alabanza IDR - Local", layout="wide")

DB_FILE = "database.csv"
SETLIST_FILE = "setlist.csv"

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: white; color: black; }
    [data-testid="stHeader"] { background: rgba(255,255,255,0); }
    [data-testid="stSidebar"] { background-color: #f0f2f6; }

    .tabla-wrap { overflow-x: auto; }

    .tabla-canciones {
        width: 100%;
        border-collapse: collapse;
    }

    .tabla-canciones th {
        text-align: left;
        padding: 10px 8px;
        border-bottom: 2px solid #d0d5dd;
        font-size: 0.85rem;
        white-space: nowrap;
    }

    /* height:1px hace que el 100% del <a> resuelva contra el alto real
       de la fila, para que el link llene la celda aunque el nombre de
       la canción ocupe dos renglones. */
    .tabla-canciones td {
        padding: 0;
        height: 1px;
        border-bottom: 1px solid #eaecf0;
    }

    .tabla-canciones td.texto {
        padding: 6px 8px;
        white-space: nowrap;
    }

    .tabla-canciones td.vacio {
        padding: 6px 8px;
        color: #9aa0a6;
        text-align: center;
    }

    /* El <a> ocupa toda la celda: se puede tocar en cualquier punto. */
    .tabla-canciones a.celda-link {
        display: flex;
        align-items: center;
        justify-content: center;
        box-sizing: border-box;
        height: calc(100% - 6px);
        min-height: 38px;
        min-width: 40px;
        margin: 3px;
        padding: 4px 8px;
        border-radius: 8px;
        background-color: #e8f0fe;
        color: #1a4fcc;
        font-size: 1.15rem;
        text-decoration: none;
        white-space: nowrap;
    }

    .tabla-canciones th.col-link { text-align: center; }

    .tabla-canciones a.celda-link:active { background-color: #c9dcff; }
    </style>
    """, unsafe_allow_html=True)

def init_db():
    if not os.path.exists(DB_FILE):
        df = pd.DataFrame(columns=[
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
        ])

        df.to_csv(DB_FILE, index=False)

def init_setlist():
    if not os.path.exists(SETLIST_FILE):
        df = pd.DataFrame(columns=[
            "Orden",
            "Numero",
            "Fecha_Creacion"
        ])

        df.to_csv(SETLIST_FILE, index=False)

def get_data():
    init_db()

    try:
        df = pd.read_csv(DB_FILE)

        expected_columns = [
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
        ]

        for col in expected_columns:
            if col not in df.columns:
                df[col] = ""

        return df.sort_values("Numero")

    except Exception:
        return pd.DataFrame(columns=[
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
        ])

def save_data(df):
    df.to_csv(DB_FILE, index=False)

def get_setlist():
    init_setlist()

    try:
        df = pd.read_csv(SETLIST_FILE)

        if df.empty:
            return df

        df["Fecha_Creacion"] = pd.to_datetime(df["Fecha_Creacion"])

        limite = datetime.now() - timedelta(days=7)

        df = df[df["Fecha_Creacion"] >= limite]

        df = df.sort_values("Orden")

        return df

    except Exception:
        return pd.DataFrame(columns=[
            "Orden",
            "Numero",
            "Fecha_Creacion"
        ])

def save_setlist(df):
    df.to_csv(SETLIST_FILE, index=False)

def authenticate(role_name, correct_password):
    auth_key = f"auth_{role_name}"

    if auth_key not in st.session_state:
        st.session_state[auth_key] = False

    if not st.session_state[auth_key]:
        st.sidebar.subheader(f"Acceso {role_name}")

        pw = st.sidebar.text_input(
            "Password",
            type="password",
            key=f"pw_{role_name}"
        )

        if st.sidebar.button(f"Entrar como {role_name}"):
            if pw == correct_password:
                st.session_state[auth_key] = True
                st.rerun()
            else:
                st.sidebar.error("Contraseña incorrecta")

        return False

    return True

column_config = {
    "Numero": st.column_config.NumberColumn("N°", format="%d"),
    "Cancion": st.column_config.TextColumn("Canción"),
    "Notas_Piano": st.column_config.LinkColumn(
        "🎹 Piano",
        display_text="Link 🎹"
    ),
    "Notas_Guitarra": st.column_config.LinkColumn(
        "🎸 Guitarra",
        display_text="Link 🎸"
    ),
    "Letra": st.column_config.LinkColumn(
        "📄 Letra",
        display_text="Link 📄"
    ),
    "Video_Bateria": st.column_config.LinkColumn(
        "🥁 Batería",
        display_text="Link 🥁"
    ),
    "Audio": st.column_config.LinkColumn(
        "🎧 Audio",
        display_text="Link 🎧"
    ),
    "Estado": st.column_config.SelectboxColumn(
        "Estado",
        options=["OK", "APRENDIENDO"],
        required=True
    ),
    "Tipo": st.column_config.SelectboxColumn(
        "Tipo",
        options=["Lenta", "Movida"],
        required=True
    )
}

# emoji -> se muestra en el encabezado y en el chip; el texto va como
# tooltip para no ensanchar la columna en pantallas angostas.
LINK_COLUMNS = {
    "Notas_Piano": ("🎹", "Notas de piano"),
    "Notas_Guitarra": ("🎸", "Notas de guitarra"),
    "Letra": ("📄", "Letra"),
    "Video_Bateria": ("🥁", "Video de batería"),
    "Audio": ("🎧", "Audio")
}

TEXT_HEADERS = {
    "Numero": "N°",
    "Cancion": "Canción"
}

def listado_desde_setlist(df, setlist):
    """Arma el listado en orden, salteando canciones borradas de la base.

    Devuelve (listado_df, faltantes). Los números repetidos se conservan.
    """
    numeros = setlist["Numero"].tolist()
    disponibles = set(df["Numero"])

    presentes = [n for n in numeros if n in disponibles]
    faltantes = [n for n in numeros if n not in disponibles]

    listado_df = (
        df[df["Numero"].isin(presentes)]
        .set_index("Numero")
        .loc[presentes]
        .reset_index()
    )

    return listado_df, faltantes

def avisar_faltantes(faltantes):
    if faltantes:
        numeros = ", ".join(f"N° {n}" for n in dict.fromkeys(faltantes))

        st.warning(
            f"{numeros}: ya no está(n) en la base y no se muestra(n)."
        )

def texto_para_compartir(listado_df):
    lineas = ["🎵 Listado", ""]

    for idx, row in enumerate(listado_df.itertuples(), start=1):
        tono = (
            ""
            if pd.isna(row.Tono) or not str(row.Tono).strip()
            else f" ({str(row.Tono).strip()})"
        )

        lineas.append(f"{idx}. {row.Cancion}{tono}")

    return "\n".join(lineas)

def render_song_table(data, columns):
    parts = [
        '<div class="tabla-wrap">',
        '<table class="tabla-canciones"><thead><tr>'
    ]

    for col in columns:
        if col in LINK_COLUMNS:
            emoji, titulo = LINK_COLUMNS[col]

            parts.append(
                f'<th class="col-link" title="{escape(titulo, quote=True)}">'
                f"{emoji}</th>"
            )

        else:
            parts.append(
                f"<th>{escape(TEXT_HEADERS.get(col, col))}</th>"
            )

    parts.append("</tr></thead><tbody>")

    for _, row in data.iterrows():
        parts.append("<tr>")

        for col in columns:
            value = row.get(col)

            if col in LINK_COLUMNS:
                emoji, titulo = LINK_COLUMNS[col]

                url = (
                    ""
                    if pd.isna(value)
                    else str(value).strip()
                )

                if url.startswith(("http://", "https://")):
                    parts.append(
                        f'<td><a class="celda-link" target="_blank" '
                        f'rel="noopener" title="{escape(titulo, quote=True)}" '
                        f'href="{escape(url, quote=True)}">'
                        f"{emoji}</a></td>"
                    )

                else:
                    parts.append('<td class="vacio">—</td>')

            else:
                if pd.isna(value):
                    text = ""

                elif col == "Numero":
                    text = str(int(value))

                else:
                    text = str(value)

                parts.append(
                    f'<td class="texto">{escape(text)}</td>'
                )

        parts.append("</tr>")

    parts.append("</tbody></table></div>")

    st.markdown("".join(parts), unsafe_allow_html=True)

menu = st.sidebar.selectbox(
    "Seleccionar Rol",
    ["Dirección", "Equipo", "Administrador"]
)

df = get_data()
setlist = get_setlist()

if menu == "Dirección":
    st.title("🎤 Vista de Dirección")

    if not df.empty:
        df_dir = df[df["Estado"] == "OK"]

        if not df_dir.empty:
            render_song_table(
                df_dir,
                [
                    "Numero",
                    "Cancion",
                    "Letra",
                    "Audio",
                    "Tipo"
                ]
            )

        else:
            st.info("No hay canciones con estado 'OK'.")

elif menu == "Equipo":
    st.title("🎸 Listado del Equipo")

    if not setlist.empty:
        listado_df, faltantes = listado_desde_setlist(df, setlist)

        st.subheader("🎵 Listado Actual")

        avisar_faltantes(faltantes)

        render_song_table(
            listado_df,
            [
                "Numero",
                "Cancion",
                "Tono",
                "Letra",
                "Notas_Piano",
                "Notas_Guitarra",
                "Video_Bateria",
                "Audio",
                "Tipo"
            ]
        )

        expiracion = (
            setlist["Fecha_Creacion"].max() +
            timedelta(days=7)
        )

        st.caption(
            f"Expira: {expiracion.strftime('%d/%m/%Y %H:%M')}"
        )

        st.divider()

    search = st.text_input("Buscar por nombre o número")

    if not df.empty:
        if search:
            display_df = df[
                df["Cancion"].str.contains(
                    search,
                    case=False,
                    na=False
                ) |
                df["Numero"].astype(str).str.contains(
                    search,
                    na=False
                )
            ]

        else:
            display_df = df

        st.subheader("📚 Todas las Canciones")

        render_song_table(
            display_df,
            [
                "Numero",
                "Cancion",
                "Tono",
                "Letra",
                "Notas_Piano",
                "Notas_Guitarra",
                "Video_Bateria",
                "Audio",
                "Estado",
                "Tipo"
            ]
        )

elif menu == "Administrador":
    if authenticate("Administrador", "adminIDR"):
        st.title("⚙️ Panel de Control (Local)")

        tab_add, tab_manage, tab_setlist = st.tabs([
            "➕ Agregar Canción",
            "🔧 Gestionar Base de Datos",
            "🎵 Listado"
        ])

        with tab_add:
            with st.form("new_song", clear_on_submit=True):
                col1, col2 = st.columns(2)

                with col1:
                    nombre = st.text_input(
                        "Nombre de la Canción"
                    )

                    piano = st.text_input(
                        "Notas Piano (URL)"
                    )

                    guitarra = st.text_input(
                        "Notas Guitarra (URL)"
                    )

                    letra = st.text_input(
                        "Letra (URL)"
                    )

                with col2:
                    bateria = st.text_input(
                        "Video Bateria (URL)"
                    )

                    tono = st.text_input("Tono")

                    estado = st.selectbox(
                        "Estado",
                        ["OK", "APRENDIENDO"]
                    )

                    tipo = st.selectbox(
                        "Tipo",
                        ["Lenta", "Movida"]
                    )

                    audio = st.text_input(
                        "Audio (URL)"
                    )

                if st.form_submit_button(
                    "Guardar Localmente"
                ):
                    if nombre:
                        next_id = (
                            int(df["Numero"].max() + 1)
                            if not df.empty
                            else 1
                        )

                        new_row = {
                            "Numero": next_id,
                            "Cancion": nombre,
                            "Notas_Piano": piano,
                            "Notas_Guitarra": guitarra,
                            "Letra": letra,
                            "Video_Bateria": bateria,
                            "Tono": tono,
                            "Estado": estado,
                            "Tipo": tipo,
                            "Audio": audio
                        }

                        df_to_save = pd.concat(
                            [
                                df,
                                pd.DataFrame([new_row])
                            ],
                            ignore_index=True
                        )

                        try:
                            save_data(df_to_save)

                            st.toast(
                                f"✅ Canción #{next_id} guardada con éxito!",
                                icon="🎉"
                            )

                            st.rerun()

                        except Exception as e:
                            st.error(
                                f"Error al guardar: {e}"
                            )

                    else:
                        st.warning(
                            "El nombre es obligatorio."
                        )

        with tab_manage:
            if not df.empty:
                st.subheader("Registros Actuales")

                st.dataframe(
                    df,
                    column_config=column_config,
                    use_container_width=True,
                    hide_index=True
                )

                st.divider()

                st.subheader("Eliminar Registro")

                id_del = st.number_input(
                    "Ingrese el Número (N°) de canción a eliminar",
                    min_value=1,
                    step=1
                )

                if st.button(
                    "Eliminar Permanentemente",
                    type="primary"
                ):
                    try:
                        df_updated = df[
                            df["Numero"] != id_del
                        ]

                        save_data(df_updated)

                        st.toast(
                            f"🗑️ Registro #{id_del} eliminado.",
                            icon="⚠️"
                        )

                        st.rerun()

                    except Exception as e:
                        st.error(
                            f"Error al eliminar: {e}"
                        )

                st.divider()

                st.subheader("Modificar Estado")

                col_update1, col_update2 = st.columns(
                    [2, 1]
                )

                with col_update1:
                    song_options = df.apply(
                        lambda x:
                        f"{x['Numero']} - {x['Cancion']}",
                        axis=1
                    ).tolist()

                    selected_song = st.selectbox(
                        "Seleccione la canción a actualizar",
                        options=song_options
                    )

                    id_update = int(
                        selected_song.split(" - ")[0]
                    )

                with col_update2:
                    current_status = df[
                        df["Numero"] == id_update
                    ]["Estado"].values[0]

                    new_status = st.selectbox(
                        "Nuevo Estado",
                        options=[
                            "OK",
                            "APRENDIENDO"
                        ],
                        index=0
                        if current_status == "OK"
                        else 1
                    )

                if st.button(
                    "Actualizar Estado",
                    use_container_width=True
                ):
                    try:
                        df.loc[
                            df["Numero"] == id_update,
                            "Estado"
                        ] = new_status

                        save_data(df)

                        st.toast(
                            f"✅ Canción #{id_update} actualizada a {new_status}",
                            icon="🔄"
                        )

                        st.rerun()

                    except Exception as e:
                        st.error(
                            f"Error al actualizar: {e}"
                        )

        with tab_setlist:
            st.subheader("🎵 Crear Listado Temporal")

            songs = df.apply(
                lambda x:
                f"{x['Numero']} - {x['Cancion']}",
                axis=1
            ).tolist()

            if "setlist_builder" not in st.session_state:
                st.session_state["setlist_builder"] = []

            # El reset del selectbox va en un callback: Streamlit no deja
            # cambiar el valor de un widget ya instanciado en la misma
            # ejecución.
            def agregar_cancion():
                seleccion = st.session_state.get("song_pick")

                if seleccion:
                    st.session_state["setlist_builder"].append(
                        seleccion
                    )

                    st.session_state["song_pick"] = None

            col_pick, col_add = st.columns([4, 1])

            with col_pick:
                st.selectbox(
                    "Canción a agregar",
                    options=songs,
                    index=None,
                    placeholder="Escribí para buscar…",
                    key="song_pick"
                )

            with col_add:
                st.write("")

                st.button(
                    "➕ Agregar",
                    use_container_width=True,
                    on_click=agregar_cancion
                )

            selected_songs = st.session_state["setlist_builder"]

            if selected_songs:
                st.info(
                    "El orden de esta lista será el orden del listado. "
                    "Una misma canción puede repetirse."
                )

                for idx, song in enumerate(selected_songs):
                    (
                        col_song,
                        col_up,
                        col_down,
                        col_del
                    ) = st.columns([6, 1, 1, 1])

                    col_song.markdown(
                        f"**{idx + 1}.** {song}"
                    )

                    if col_up.button(
                        "⬆️",
                        key=f"up_{idx}",
                        disabled=idx == 0,
                        use_container_width=True
                    ):
                        selected_songs[idx - 1], selected_songs[idx] = (
                            selected_songs[idx],
                            selected_songs[idx - 1]
                        )

                        st.rerun()

                    if col_down.button(
                        "⬇️",
                        key=f"down_{idx}",
                        disabled=idx == len(selected_songs) - 1,
                        use_container_width=True
                    ):
                        selected_songs[idx + 1], selected_songs[idx] = (
                            selected_songs[idx],
                            selected_songs[idx + 1]
                        )

                        st.rerun()

                    if col_del.button(
                        "🗑️",
                        key=f"del_{idx}",
                        use_container_width=True
                    ):
                        selected_songs.pop(idx)

                        st.rerun()

            col_save, col_clear = st.columns(2)

            with col_save:
                if st.button(
                    "💾 Publicar Listado",
                    use_container_width=True,
                    disabled=not selected_songs
                ):
                    rows = []

                    for idx, song in enumerate(
                        selected_songs,
                        start=1
                    ):
                        numero = int(
                            song.split(" - ")[0]
                        )

                        rows.append({
                            "Orden": idx,
                            "Numero": numero,
                            "Fecha_Creacion": datetime.now()
                        })

                    setlist_df = pd.DataFrame(rows)

                    save_setlist(setlist_df)

                    st.session_state["setlist_builder"] = []

                    st.toast(
                        "✅ Listado publicado por 7 días",
                        icon="🎵"
                    )

                    st.rerun()

            with col_clear:
                if st.button(
                    "🗑️ Limpiar Listado",
                    use_container_width=True
                ):
                    empty_df = pd.DataFrame(columns=[
                        "Orden",
                        "Numero",
                        "Fecha_Creacion"
                    ])

                    save_setlist(empty_df)

                    st.session_state["setlist_builder"] = []

                    st.toast(
                        "🗑️ Listado eliminado",
                        icon="⚠️"
                    )

                    st.rerun()

            if not setlist.empty:
                st.divider()

                st.subheader("📋 Listado Actual")

                current_df, faltantes = listado_desde_setlist(
                    df,
                    setlist
                )

                avisar_faltantes(faltantes)

                current_df.insert(
                    0,
                    "Orden",
                    range(1, len(current_df) + 1)
                )

                st.dataframe(
                    current_df[[
                        "Orden",
                        "Numero",
                        "Cancion",
                        "Tipo",
                        "Estado"
                    ]],
                    use_container_width=True,
                    hide_index=True
                )

                expiracion = (
                    setlist["Fecha_Creacion"].max() +
                    timedelta(days=7)
                )

                st.caption(
                    f"⏳ Expira el: {expiracion.strftime('%d/%m/%Y %H:%M')}"
                )

                st.divider()

                st.subheader("💬 Para compartir")

                st.code(
                    texto_para_compartir(current_df),
                    language=None
                )