import streamlit as st
import pandas as pd
import os

st.set_page_config(page_title="Alabanza IDR - Local", layout="wide")

DB_FILE = "database.csv"

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
            "Numero", "Cancion", "Notas_Piano", "Notas_Guitarra", 
            "Letra", "Video_Bateria", "Tono", "Estado", "Tipo", "Audio"
        ])
        df.to_csv(DB_FILE, index=False)

def get_data():
    init_db()
    df = pd.read_csv(DB_FILE)
    return df.sort_values("Numero")

def save_data(df):
    df.to_csv(DB_FILE, index=False)

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

column_config = {
    "Numero": st.column_config.NumberColumn("N°", format="%d"),
    "Cancion": st.column_config.TextColumn("Canción"),
    "Notas_Piano": st.column_config.LinkColumn("🎹 Piano", display_text="Link 🎹"),
    "Notas_Guitarra": st.column_config.LinkColumn("🎸 Guitarra", display_text="Link 🎸"),
    "Letra": st.column_config.LinkColumn("📄 Letra", display_text="Link 📄"),
    "Video_Bateria": st.column_config.LinkColumn("🥁 Batería", display_text="Link 🥁"),
    "Audio": st.column_config.LinkColumn("🎧 Audio", display_text="Link 🎧"),
    "Estado": st.column_config.SelectboxColumn("Estado", options=["OK", "APRENDIENDO"], required=True),
    "Tipo": st.column_config.SelectboxColumn("Tipo", options=["Lenta", "Movida"], required=True)
}

menu = st.sidebar.selectbox("Seleccionar Rol", ["Dirección", "Equipo", "Administrador"])
df = get_data()

if menu == "Dirección":
    st.title("🎤 Vista de Dirección")
    if not df.empty:
        df_dir = df[df['Estado'] == "OK"]
        if not df_dir.empty:
            st.dataframe(
                df_dir[["Numero", "Cancion", "Letra", "Audio", "Tipo"]], 
                column_config=column_config, 
                use_container_width=True, 
                hide_index=True
            )
        else:
            st.info("No hay canciones con estado 'OK'.")

elif menu == "Equipo":
    if authenticate("Equipo", "IDR19"):
        st.title("🎸 Listado del Equipo")
        search = st.text_input("Buscar por nombre o número")
        if not df.empty:
            display_df = df[
                df['Cancion'].str.contains(search, case=False, na=False) | 
                df['Numero'].astype(str).str.contains(search)
            ] if search else df
            st.dataframe(display_df, column_config=column_config, use_container_width=True, hide_index=True)

elif menu == "Administrador":
    if authenticate("Administrador", "adminIDR"):
        st.title("⚙️ Panel de Control (Local)")
        
        tab_add, tab_manage = st.tabs(["➕ Agregar Canción", "🔧 Gestionar Base de Datos"])
        
        with tab_add:
            with st.form("new_song", clear_on_submit=True):
                col1, col2 = st.columns(2)
                with col1:
                    nombre = st.text_input("Nombre de la Canción")
                    piano = st.text_input("Notas Piano (URL)")
                    guitarra = st.text_input("Notas Guitarra (URL)")
                    letra = st.text_input("Letra (URL)")
                with col2:
                    bateria = st.text_input("Video Bateria (URL)")
                    tono = st.text_input("Tono")
                    estado = st.selectbox("Estado", ["OK", "APRENDIENDO"])
                    tipo = st.selectbox("Tipo", ["Lenta", "Movida"])
                    audio = st.text_input("Audio (URL)")
                
                if st.form_submit_button("Guardar Localmente"):
                    if nombre:
                        next_id = int(df["Numero"].max() + 1) if not df.empty else 1
                        new_row = pd.DataFrame([{
                            "Numero": next_id, "Cancion": nombre, "Notas_Piano": piano,
                            "Notas_Guitarra": guitarra, "Letra": letra, "Video_Bateria": bateria,
                            "Tono": tono, "Estado": estado, "Tipo": tipo, "Audio": audio
                        }])
                        df = pd.concat([df, new_row], ignore_index=True)
                        save_data(df)
                        st.toast(f"✅ Canción #{next_id} guardada!", icon='🎉')
                        st.rerun()
                    else:
                        st.warning("El nombre es obligatorio.")

        with tab_manage:
            if not df.empty:
                st.subheader("Registros Actuales")
                st.dataframe(df, column_config=column_config, use_container_width=True, hide_index=True)
                
                st.divider()
                st.subheader("Eliminar Registro")
                id_del = st.number_input("Ingrese el Número (N°) a eliminar", min_value=1, step=1)
                if st.button("Eliminar Permanentemente", type="primary"):
                    df = df[df["Numero"] != id_del]
                    save_data(df)
                    st.toast(f"🗑️ Registro #{id_del} eliminado.", icon='⚠️')
                    st.rerun()

                st.divider()
                st.subheader("Modificar Estado")
                col_update1, col_update2 = st.columns([2, 1])
                
                with col_update1:
                    song_options = df.apply(lambda x: f"{x['Numero']} - {x['Cancion']}", axis=1).tolist()
                    selected_song = st.selectbox("Seleccione canción", options=song_options)
                    id_update = int(selected_song.split(" - ")[0])
                
                with col_update2:
                    current_status = df[df['Numero'] == id_update]['Estado'].values[0]
                    new_status = st.selectbox("Nuevo Estado", ["OK", "APRENDIENDO"], 
                                            index=0 if current_status == "OK" else 1)

                if st.button("Actualizar Estado"):
                    df.loc[df['Numero'] == id_update, 'Estado'] = new_status
                    save_data(df)
                    st.toast(f"✅ #{id_update} actualizado a {new_status}")
                    st.rerun()