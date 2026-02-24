import streamlit as st
import pandas as pd

st.set_page_config(page_title="Alabanza IDR", layout="wide")

if 'db' not in st.session_state:
    st.session_state.db = pd.DataFrame(columns=[
        "Numero", "Canción", "Notas Piano", "Notas Guitarra", 
        "Letra", "Video Bateria", "Tono", "Estado", "Tipo", "Audio"
    ])

def authenticate(role_name, correct_password):
    auth_key = f"auth_{role_name}"
    if auth_key not in st.session_state:
        st.session_state[auth_key] = False
    
    if not st.session_state[auth_key]:
        st.sidebar.subheader(f"Acceso {role_name}")
        pw = st.sidebar.text_input(f"Password", type="password", key=f"pw_{role_name}")
        if st.sidebar.button(f"Entrar como {role_name}"):
            if pw == correct_password:
                st.session_state[auth_key] = True
                st.rerun()
            else:
                st.sidebar.error("Contraseña incorrecta")
        return False
    return True

# Configuración de columnas para visualización con enlaces y colores
column_config = {
    "Notas Piano": st.column_config.LinkColumn("🎹 Piano", display_text="Link 🎹"),
    "Notas Guitarra": st.column_config.LinkColumn("🎸 Guitarra", display_text="Link 🎸"),
    "Letra": st.column_config.LinkColumn("📄 Letra", display_text="Link 📄"),
    "Video Bateria": st.column_config.LinkColumn("🥁 Batería", display_text="Link 🥁"),
    "Audio": st.column_config.LinkColumn("🎧 Audio", display_text="Link 🎧"),
    "Estado": st.column_config.SelectboxColumn(
        "Estado",
        options=["OK", "APRENDIENDO"],
        required=True,
    ),
    "Tipo": st.column_config.SelectboxColumn(
        "Tipo",
        options=["Lenta", "Movida"],
        required=True,
    )
}

menu = st.sidebar.selectbox("Seleccionar Rol", ["Dirección", "Equipo", "Administrador", "Respaldo"])

if menu == "Dirección":
    st.title("🎤 Vista de Dirección")
    df = st.session_state.db
    if not df.empty:
        df_dir = df[df['Estado'] == "OK"]
        if not df_dir.empty:
            # En table() no se pueden poner colores complejos, usamos dataframe configurado
            st.dataframe(
                df_dir[["Numero", "Canción", "Letra", "Audio", "Tipo"]],
                column_config=column_config,
                use_container_width=True,
                hide_index=True
            )
        else:
            st.info("No hay canciones con estado 'OK' actualmente.")
    else:
        st.info("La base de datos está vacía.")

elif menu == "Equipo":
    if authenticate("Equipo", "IDR2026"):
        st.title("🎸 Listado del Equipo")
        search = st.text_input("Buscar por nombre o número")
        df = st.session_state.db
        if not df.empty:
            if search:
                df = df[df['Canción'].str.contains(search, case=False) | df['Numero'].astype(str).str.contains(search)]
            
            st.dataframe(
                df,
                column_config=column_config,
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.warning("Aún no hay canciones cargadas.")

elif menu == "Administrador":
    if authenticate("Administrador", "IDR19"):
        st.title("⚙️ Panel de Control")
        
        with st.expander("➕ Cargar Nueva Canción", expanded=True):
            with st.form("new_song"):
                col1, col2 = st.columns(2)
                with col1:
                    nombre = st.text_input("Nombre de la Canción")
                    piano = st.text_input("Notas Piano (Link)")
                    guitarra = st.text_input("Notas Guitarra (Link)")
                    letra = st.text_input("Letra (Link)")
                with col2:
                    bateria = st.text_input("Video Bateria (Link)")
                    tono = st.text_input("Tono")
                    estado = st.selectbox("Estado", ["OK", "APRENDIENDO"])
                    tipo = st.selectbox("Tipo", ["Lenta", "Movida"])
                    audio = st.text_input("Audio (Link)")
                
                if st.form_submit_button("Guardar Canción"):
                    if nombre:
                        next_id = st.session_state.db["Numero"].max() + 1 if not st.session_state.db.empty else 1
                        new_row = {
                            "Numero": int(next_id), "Canción": nombre, "Notas Piano": piano,
                            "Notas Guitarra": guitarra, "Letra": letra, "Video Bateria": bateria,
                            "Tono": tono, "Estado": estado, "Tipo": tipo, "Audio": audio
                        }
                        st.session_state.db = pd.concat([st.session_state.db, pd.DataFrame([new_row])], ignore_index=True)
                        st.success(f"Canción #{next_id} guardada con éxito")
                        st.rerun()

        if not st.session_state.db.empty:
            st.subheader("Registros Actuales")
            edited_df = st.data_editor(
                st.session_state.db, 
                column_config=column_config,
                num_rows="dynamic", 
                use_container_width=True, 
                key="editor",
                hide_index=True
            )
            if st.button("Guardar Cambios de la Tabla"):
                st.session_state.db = edited_df
                st.success("Cambios guardados en la sesión.")

elif menu == "Respaldo":
    if authenticate("Administrador", "IDR19"):
        st.title("⚙️ Backup")
        
        # Botón para descargar lo que hay en memoria
        csv = st.session_state.db.to_csv(index=False).encode('utf-8')
        st.download_button(
            "📥 Descargar Respaldo (CSV)",
            csv,
            "alabanza_backup.csv",
            "text/csv"
        )
        
        # Botón para cargar un archivo guardado anteriormente
        uploaded_file = st.file_uploader("📤 Cargar Respaldo (CSV)")
        if uploaded_file is not None:
            st.session_state.db = pd.read_csv(uploaded_file)
            st.success("Base de datos restaurada.")
            st.rerun()
