import streamlit as st
import pandas as pd
import datetime
import matplotlib.pyplot as plt
import smtplib
import random
import string
from email.mime.text import MIMEText
import os
from supabase import create_client, Client
from dotenv import load_dotenv  # Añade esta línea

# Cargar variables de entorno al inicio del script
load_dotenv()  # Añade esta línea

# --- CONFIGURACIÓN SUPABASE ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Verifica que las variables se cargaron correctamente
if not SUPABASE_URL or not SUPABASE_KEY:
    st.error("Error: No se pudieron cargar las credenciales de Supabase. Verifica tu archivo .env")
    st.stop()

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# --- CONFIGURACIÓN EMAIL ---
EMAIL_SENDER = os.getenv("EMAIL_SENDER")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587

# --- FUNCIONES AUXILIARES ---
def enviar_correo(destinatario, token):
    msg = MIMEText(f"Tu código de verificación es: {token}")
    msg['Subject'] = "Verifica tu cuenta"
    msg['From'] = EMAIL_SENDER
    msg['To'] = destinatario

    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(EMAIL_SENDER, EMAIL_PASSWORD)
        server.send_message(msg)

def generar_token():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

# --- FUNCIONES DE USUARIO ---
def registrar_usuario(correo, username, contrasena):
    token = generar_token()
    try:
        # Verificar si el usuario ya existe
        res = supabase.table('usuarios').select('*').or_(f'correo.eq.{correo},username.eq.{username}').execute()
        if len(res.data) > 0:
            return False, "El correo o el nombre de usuario ya están registrados."
        
        # Insertar nuevo usuario
        supabase.table('usuarios').insert({
            'correo': correo,
            'username': username,
            'contrasena': contrasena,
            'token': token,
            'verificado': False
        }).execute()
        
        enviar_correo(correo, token)
        return True, "Te hemos enviado un código de verificación por correo."
    except Exception as e:
        return False, f"Error al registrar: {str(e)}"

def verificar_usuario(correo, token_ingresado):
    try:
        res = supabase.table('usuarios').select('token').eq('correo', correo).execute()
        if res.data and res.data[0]['token'] == token_ingresado:
            supabase.table('usuarios').update({'verificado': True}).eq('correo', correo).execute()
            return True
        return False
    except Exception as e:
        st.error(f"Error al verificar: {str(e)}")
        return False

def login_valido(correo, contrasena):
    try:
        res = supabase.table('usuarios').select('verificado').eq('correo', correo).eq('contrasena', contrasena).execute()
        return res.data and res.data[0]['verificado']
    except Exception as e:
        st.error(f"Error en login: {str(e)}")
        return False

# --- FUNCIONES DE HÁBITOS ---
def obtener_habitos(usuario):
    try:
        res = supabase.table('habitos_personalizados').select('habito').eq('usuario', usuario).execute()
        return [h['habito'] for h in res.data]
    except Exception as e:
        st.error(f"Error al obtener hábitos: {str(e)}")
        return []

def agregar_habito(usuario, habito):
    try:
        supabase.table('habitos_personalizados').insert({
            'usuario': usuario,
            'habito': habito
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error al agregar hábito: {str(e)}")
        return False

def eliminar_habito(usuario, habito):
    try:
        supabase.table('habitos_personalizados').delete().eq('usuario', usuario).eq('habito', habito).execute()
        return True
    except Exception as e:
        st.error(f"Error al eliminar hábito: {str(e)}")
        return False

def agregar_registro(fecha, usuario, habito, completado):
    try:
        supabase.table('registros').insert({
            'fecha': str(fecha),
            'usuario': usuario,
            'habito': habito,
            'completado': completado
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error al agregar registro: {str(e)}")
        return False

def obtener_registros(usuario):
    try:
        res = supabase.table('registros').select('*').eq('usuario', usuario).execute()
        return pd.DataFrame(res.data)
    except Exception as e:
        st.error(f"Error al obtener registros: {str(e)}")
        return pd.DataFrame()

# --- FUNCIONES DE INVITACIONES ---
def obtener_invitaciones_aceptadas(receptor):
    try:
        res = supabase.table('invitaciones').select('emisor').eq('receptor', receptor).eq('estado', 'aceptada').execute()
        return [i['emisor'] for i in res.data]
    except Exception as e:
        st.error(f"Error al obtener invitaciones: {str(e)}")
        return []

def obtener_invitaciones_pendientes(receptor):
    try:
        res = supabase.table('invitaciones').select('id,emisor').eq('receptor', receptor).eq('estado', 'pendiente').execute()
        return res.data
    except Exception as e:
        st.error(f"Error al obtener invitaciones pendientes: {str(e)}")
        return []

def enviar_invitacion(emisor, receptor):
    try:
        # Verificar si el receptor existe
        res = supabase.table('usuarios').select('username').eq('username', receptor).execute()
        if not res.data:
            return False, "Ese usuario no existe."
        
        # Verificar si ya existe una invitación
        res = supabase.table('invitaciones').select('*').eq('emisor', emisor).eq('receptor', receptor).execute()
        if res.data:
            return False, "Ya enviaste una invitación a ese usuario."
        
        # Crear nueva invitación
        supabase.table('invitaciones').insert({
            'emisor': emisor,
            'receptor': receptor,
            'estado': 'pendiente'
        }).execute()
        return True, "Invitación enviada."
    except Exception as e:
        return False, f"Error al enviar invitación: {str(e)}"

def actualizar_invitacion(inv_id, estado):
    try:
        supabase.table('invitaciones').update({'estado': estado}).eq('id', inv_id).execute()
        return True
    except Exception as e:
        st.error(f"Error al actualizar invitación: {str(e)}")
        return False

def eliminar_invitacion(inv_id):
    try:
        supabase.table('invitaciones').delete().eq('id', inv_id).execute()
        return True
    except Exception as e:
        st.error(f"Error al eliminar invitación: {str(e)}")
        return False

# --- APP STREAMLIT ---
st.title("📊 Seguimiento de Hábitos Compartido")

modo = st.sidebar.radio("Selecciona una opción:", ["Iniciar sesión", "Crear cuenta"])

if modo == "Crear cuenta":
    st.subheader("📝 Crear nueva cuenta")
    correo = st.text_input("Correo")
    username = st.text_input("Nombre de usuario (debe ser único)")
    contrasena = st.text_input("Contraseña", type="password")
    if st.button("Registrarme"):
        ok, msg = registrar_usuario(correo, username, contrasena)
        if ok:
            st.success(msg) 
        else:
            st.error(msg)

    token_input = st.text_input("Ingresa el código enviado por correo para verificar tu cuenta")
    if st.button("Verificar cuenta"):
        if verificar_usuario(correo, token_input):
            st.success("Cuenta verificada. Ahora puedes iniciar sesión.")
        else:
            st.error("Código incorrecto.")

elif modo == "Iniciar sesión":
    correo = st.sidebar.text_input("Correo")
    contrasena = st.sidebar.text_input("Contraseña", type="password")

    if login_valido(correo, contrasena):
        try:
            res = supabase.table('usuarios').select('username').eq('correo', correo).execute()
            username_actual = res.data[0]['username']
        except Exception as e:
            st.error(f"Error al obtener usuario: {str(e)}")
            st.stop()

        st.sidebar.success(f"Bienvenido/a {username_actual}")

        tab1, tab2, tab3, tab4, tab5 = st.tabs(["📋 Registrar", "📈 Tu progreso", "👀 Ver otros", "⚙️ Mis hábitos", "📤 Compartir progreso"])

        with tab1:
            st.subheader("✅ Registrar hábito")
            fecha = st.date_input("Fecha", datetime.date.today())
            habitos_lista = obtener_habitos(username_actual)

            if habitos_lista:
                habito = st.selectbox("Selecciona un hábito", habitos_lista)
            else:
                st.info("Aún no has creado hábitos.")
                habito = None

            completado = st.checkbox("¿Completado?")

            if st.button("Guardar"):
                if not habito:
                    st.error("Selecciona un hábito primero")
                else:
                    if agregar_registro(fecha, username_actual, habito, int(completado)):
                        st.success("Registro guardado")

        with tab2:
            st.subheader("📈 Tu progreso")
            df = obtener_registros(username_actual)
            if not df.empty:
                resumen = df.groupby("habito")["completado"].sum()
                st.dataframe(resumen)

                fig, ax = plt.subplots()
                resumen.plot(kind="bar", ax=ax)
                ax.set_ylabel("Veces completado")
                ax.set_title("Progreso por hábito")
                st.pyplot(fig)

                total = df.groupby("habito").size()
                cumplidos = df.groupby("habito")["completado"].sum()
                porcentaje = (cumplidos / total * 100).round(1)
                st.dataframe(porcentaje.rename("Cumplimiento (%)"))
            else:
                st.info("No hay registros aún.")

        with tab3:
            st.subheader("👀 Ver progreso de otro usuario")
            disponibles = obtener_invitaciones_aceptadas(username_actual)
            if disponibles:
                seleccionado = st.selectbox("Selecciona un usuario", disponibles)
                df_otro = obtener_registros(seleccionado)
                if not df_otro.empty:
                    resumen_otro = df_otro.groupby("habito")["completado"].sum()
                    st.dataframe(resumen_otro)
                else:
                    st.info("Sin registros aún.")
            else:
                st.info("Nadie te ha invitado aún.")

        with tab4:
            st.subheader("⚙️ Mis hábitos")
            habitos_actuales = obtener_habitos(username_actual)

            if habitos_actuales:
                habito_a_eliminar = st.selectbox("Eliminar hábito", habitos_actuales)
                if st.button("Eliminar"):
                    if eliminar_habito(username_actual, habito_a_eliminar):
                        st.success("Hábito eliminado")
                        st.rerun()

            nuevo_habito = st.text_input("Nuevo hábito")
            if st.button("Añadir") and nuevo_habito.strip():
                if agregar_habito(username_actual, nuevo_habito.strip()):
                    st.success("Añadido")
                    st.rerun()

        with tab5:
            st.subheader("📤 Compartir tu progreso con otros")

            st.markdown("### Invitar a otro usuario")
            username_destino = st.text_input("Nombre de usuario del usuario a invitar")
            if st.button("Enviar invitación"):
                if username_destino == username_actual:
                    st.error("No puedes invitarte a ti mismo.")
                else:
                    ok, msg = enviar_invitacion(username_actual, username_destino)
                    if ok:
                        st.success(msg)
                    else:
                        st.error(msg)

            st.markdown("### Invitaciones recibidas")
            recibidas = obtener_invitaciones_pendientes(username_actual)

            if recibidas:
                for inv in recibidas:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    col1.write(f"Invitación de: {inv['emisor']}")
                    if col2.button("Aceptar", key=f"aceptar_{inv['id']}"):
                        if actualizar_invitacion(inv['id'], 'aceptada'):
                            st.success(f"Has aceptado la invitación de {inv['emisor']}")
                            st.rerun()
                    if col3.button("Rechazar", key=f"rechazar_{inv['id']}"):
                        if eliminar_invitacion(inv['id']):
                            st.warning(f"Has rechazado la invitación de {inv['emisor']}")
                            st.rerun()
            else:
                st.info("No tienes invitaciones pendientes.")
    else:
        st.warning("Credenciales incorrectas o usuario no verificado.")