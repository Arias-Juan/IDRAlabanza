import streamlit as st
import pandas as pd
import os

from datetime import datetime, timedelta

st.set_page_config(page_title="Alabanza IDR - Local", layout="wide")

DB_FILE = "database.csv"
SETLIST_FILE = "setlist.csv"

st.markdown("""
    <style>
    [data-testid="stAppViewContainer"] { background-color: white; color: black; }
    [data-testid="stHeader"] { background: rgba(255,255,255,0); }
    [data-testid="stSidebar"] { background-color: #f0f2f6; }
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

        limite = datetime.now() - timedelta(hours=72)

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
            st.dataframe(
                df_dir[[
                    "Numero",
                    "Cancion",
                    "Letra",
                    "Audio",
                    "Tipo"
                ]],
                column_config=column_config,
                use_container_width=True,
                hide_index=True
            )

        else:
            st.info("No hay canciones con estado 'OK'.")

elif menu == "Equipo":
    st.title("🎸 Listado del Equipo")

    if not setlist.empty:
        numeros = setlist["Numero"].tolist()

        listado_df = (
            df[df["Numero"].isin(numeros)]
            .set_index("Numero")
            .loc[numeros]
            .reset_index()
        )

        st.subheader("🎵 Listado Actual")

        st.dataframe(
            listado_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True
        )

        expiracion = (
            setlist["Fecha_Creacion"].max() +
            timedelta(hours=72)
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

        st.dataframe(
            display_df,
            column_config=column_config,
            use_container_width=True,
            hide_index=True
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

            selected_songs = st.multiselect(
                "Seleccionar canciones en orden",
                songs
            )

            if selected_songs:
                st.info(
                    "El orden de selección será el orden del listado."
                )

                preview_rows = []

                for idx, song in enumerate(
                    selected_songs,
                    start=1
                ):
                    preview_rows.append({
                        "Orden": idx,
                        "Canción": song
                    })

                st.dataframe(
                    pd.DataFrame(preview_rows),
                    use_container_width=True,
                    hide_index=True
                )

            col_save, col_clear = st.columns(2)

            with col_save:
                if st.button(
                    "💾 Publicar Listado",
                    use_container_width=True
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

                    st.toast(
                        "✅ Listado publicado por 72 horas",
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

                    st.toast(
                        "🗑️ Listado eliminado",
                        icon="⚠️"
                    )

                    st.rerun()

            if not setlist.empty:
                st.divider()

                st.subheader("📋 Listado Actual")

                numeros = setlist["Numero"].tolist()

                current_df = (
                    df[df["Numero"].isin(numeros)]
                    .set_index("Numero")
                    .loc[numeros]
                    .reset_index()
                )

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
                    timedelta(hours=72)
                )

                st.caption(
                    f"⏳ Expira el: {expiracion.strftime('%d/%m/%Y %H:%M')}"
                )