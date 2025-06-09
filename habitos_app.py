import streamlit as st
import pandas as pd
import sqlite3
import datetime
import matplotlib.pyplot as plt
import smtplib
import random
import string
from email.mime.text import MIMEText

# --- CONFIGURACIÓN EMAIL ---
EMAIL_SENDER = "lramireza616@gmail.com"
EMAIL_PASSWORD = "fwksyemwtpzvnkzn"
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

# --- BASE DE DATOS ---
def crear_tablas():
    with sqlite3.connect("habitos.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS usuarios (
                correo TEXT PRIMARY KEY,
                username TEXT UNIQUE,
                contrasena TEXT,
                verificado INTEGER DEFAULT 0,
                token TEXT
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                usuario TEXT,
                habito TEXT,
                completado INTEGER
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS habitos_personalizados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                habito TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invitaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emisor TEXT NOT NULL,
                receptor TEXT NOT NULL,
                estado TEXT CHECK (estado IN ('pendiente', 'aceptada')) NOT NULL
            )
        ''')

crear_tablas()

# --- FUNCIONES DE USUARIO ---
def registrar_usuario(correo, username, contrasena):
    token = generar_token()
    with sqlite3.connect("habitos.db") as conn:
        ya_existe = conn.execute("SELECT * FROM usuarios WHERE correo = ? OR username = ?", (correo, username)).fetchone()
        if ya_existe:
            return False, "El correo o el nombre de usuario ya están registrados."
        conn.execute("INSERT INTO usuarios (correo, username, contrasena, token) VALUES (?, ?, ?, ?)", (correo, username, contrasena, token))
        enviar_correo(correo, token)
        return True, "Te hemos enviado un código de verificación por correo."

def verificar_usuario(correo, token_ingresado):
    with sqlite3.connect("habitos.db") as conn:
        usuario = conn.execute("SELECT token FROM usuarios WHERE correo = ?", (correo,)).fetchone()
        if usuario and usuario[0] == token_ingresado:
            conn.execute("UPDATE usuarios SET verificado = 1 WHERE correo = ?", (correo,))
            return True
        return False

def login_valido(correo, contrasena):
    with sqlite3.connect("habitos.db") as conn:
        res = conn.execute("SELECT verificado FROM usuarios WHERE correo = ? AND contrasena = ?", (correo, contrasena)).fetchone()
        return res is not None and res[0] == 1

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
        with sqlite3.connect("habitos.db") as conn:
            username_actual = conn.execute("SELECT username FROM usuarios WHERE correo = ?", (correo,)).fetchone()[0]

        st.sidebar.success(f"Bienvenido/a {username_actual}")

        def obtener_habitos(usuario):
            with sqlite3.connect("habitos.db") as conn:
                df = pd.read_sql_query("SELECT habito FROM habitos_personalizados WHERE usuario = ?", conn, params=(usuario,))
            return df['habito'].tolist()

        def agregar_habito(usuario, habito):
            with sqlite3.connect("habitos.db") as conn:
                conn.execute("INSERT INTO habitos_personalizados (usuario, habito) VALUES (?, ?)", (usuario, habito))

        def eliminar_habito(usuario, habito):
            with sqlite3.connect("habitos.db") as conn:
                conn.execute("DELETE FROM habitos_personalizados WHERE usuario = ? AND habito = ?", (usuario, habito))

        def agregar_registro(fecha, usuario, habito, completado):
            with sqlite3.connect("habitos.db") as conn:
                conn.execute("INSERT INTO registros (fecha, usuario, habito, completado) VALUES (?, ?, ?, ?)",
                            (fecha, usuario, habito, completado))

        def obtener_registros(usuario):
            with sqlite3.connect("habitos.db") as conn:
                df = pd.read_sql_query("SELECT * FROM registros WHERE usuario = ?", conn, params=(usuario,))
            return df

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
                    agregar_registro(str(fecha), username_actual, habito, int(completado))
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
            with sqlite3.connect("habitos.db") as conn:
                invitados = conn.execute('''
                    SELECT emisor FROM invitaciones
                    WHERE receptor = ? AND estado = 'aceptada'
                ''', (username_actual,)).fetchall()

            disponibles = [u[0] for u in invitados]
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
                    eliminar_habito(username_actual, habito_a_eliminar)
                    st.success("Hábito eliminado")
                    st.rerun()

            nuevo_habito = st.text_input("Nuevo hábito")
            if st.button("Añadir") and nuevo_habito.strip():
                agregar_habito(username_actual, nuevo_habito.strip())
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
                    with sqlite3.connect("habitos.db") as conn:
                        existe = conn.execute("SELECT * FROM usuarios WHERE username = ?", (username_destino,)).fetchone()
                        ya_invitado = conn.execute('''
                            SELECT * FROM invitaciones
                            WHERE emisor = ? AND receptor = ?
                        ''', (username_actual, username_destino)).fetchone()

                        if not existe:
                            st.error("Ese usuario no existe.")
                        elif ya_invitado:
                            st.warning("Ya enviaste una invitación a ese usuario.")
                        else:
                            conn.execute('''
                                INSERT INTO invitaciones (emisor, receptor, estado)
                                VALUES (?, ?, 'pendiente')
                            ''', (username_actual, username_destino))
                            st.success("Invitación enviada.")

            st.markdown("### Invitaciones recibidas")
            with sqlite3.connect("habitos.db") as conn:
                recibidas = conn.execute('''
                    SELECT id, emisor FROM invitaciones
                    WHERE receptor = ? AND estado = 'pendiente'
                ''', (username_actual,)).fetchall()

            if recibidas:
                for inv_id, emisor in recibidas:
                    col1, col2, col3 = st.columns([2, 1, 1])
                    col1.write(f"Invitación de: {emisor}")
                    if col2.button("Aceptar", key=f"aceptar_{inv_id}"):
                        with sqlite3.connect("habitos.db") as conn:
                            conn.execute("UPDATE invitaciones SET estado = 'aceptada' WHERE id = ?", (inv_id,))
                        st.success(f"Has aceptado la invitación de {emisor}")
                        st.experimental_rerun()
                    if col3.button("Rechazar", key=f"rechazar_{inv_id}"):
                        with sqlite3.connect("habitos.db") as conn:
                            conn.execute("DELETE FROM invitaciones WHERE id = ?", (inv_id,))
                        st.warning(f"Has rechazado la invitación de {emisor}")
                        st.experimental_rerun()
            else:
                st.info("No tienes invitaciones pendientes.")
    else:
        st.warning("Credenciales incorrectas o usuario no verificado.")
