import streamlit as st
import pandas as pd
from google.cloud import bigquery
from google.oauth2 import service_account # Agrega este import

# Reemplaza la línea client = bigquery.Client() por esto:
if "gcp_service_account" in st.secrets:
    # Usar credenciales de Streamlit Cloud Secrets
    creds_info = st.secrets["gcp_service_account"]
    credentials = service_account.Credentials.from_service_account_info(creds_info)
    client = bigquery.Client(credentials=credentials, project=creds_info["project_id"])
else:
    # Fallback para desarrollo local (ADC)
    client = bigquery.Client()

st.set_page_config(page_title="Alabanza IDR", layout="wide")

client = bigquery.Client()
TABLE_ID = "asistente-personal-unico.alabanza.canciones"

def get_data():
    try:
        query = f"SELECT * FROM `{TABLE_ID}` ORDER BY Numero"
        return client.query(query).to_dataframe()
    except Exception:
        return pd.DataFrame(columns=[
            "Numero", "Cancion", "Notas_Piano", "Notas_Guitarra", 
            "Letra", "Video_Bateria", "Tono", "Estado", "Tipo", "Audio"
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
    if authenticate("Equipo", "Alabanza"):
        st.title("🎸 Listado del Equipo")
        search = st.text_input("Buscar por nombre o número")
        if not df.empty:
            display_df = df[df['Cancion'].str.contains(search, case=False) | df['Numero'].astype(str).str.contains(search)] if search else df
            st.dataframe(display_df, column_config=column_config, use_container_width=True, hide_index=True)

elif menu == "Administrador":
    if authenticate("Administrador", "IDR2026"):
        st.title("⚙️ Panel de Control")
        
        tab_add, tab_manage = st.tabs(["➕ Agregar Canción", "🔧 Gestionar Base de Datos"])
        
        with tab_add:
            with st.form("new_song"):
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
                
                if st.form_submit_button("Guardar en BigQuery"):
                    if nombre:
                        next_id = int(df["Numero"].max() + 1) if not df.empty else 1
                        new_row = {
                            "Numero": next_id, "Cancion": nombre, "Notas_Piano": piano,
                            "Notas_Guitarra": guitarra, "Letra": letra, "Video_Bateria": bateria,
                            "Tono": tono, "Estado": estado, "Tipo": tipo, "Audio": audio
                        }
                        
                        # Creamos un DF de una sola fila para el load job
                        df_to_load = pd.DataFrame([new_row])
                        
                        # Configuración del Job para que haga Append
                        job_config = bigquery.LoadJobConfig(
                            write_disposition="WRITE_APPEND",
                        )
                        
                        try:
                            job = client.load_table_from_dataframe(
                                df_to_load, TABLE_ID, job_config=job_config
                            )
                            job.result()  # Espera a que termine el job
                            st.success(f"Canción #{next_id} guardada correctamente")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al insertar: {e}")
                    else:
                        st.warning("El nombre es obligatorio.")

        with tab_manage:
            if not df.empty:
                st.subheader("Registros Actuales")
                st.dataframe(df, column_config=column_config, use_container_width=True, hide_index=True)
                
                st.divider()
                st.subheader("Eliminar Registro")
                id_del = st.number_input("Ingrese el Número (N°) de canción a eliminar", min_value=1, step=1)
                if st.button("Eliminar Permanentemente", type="primary"):
                    del_query = f"DELETE FROM `{TABLE_ID}` WHERE Numero = {id_del}"
                    client.query(del_query).result()
                    st.warning(f"Registro #{id_del} eliminado.")
                    st.rerun()