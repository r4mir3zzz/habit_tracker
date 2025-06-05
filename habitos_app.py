import streamlit as st
import pandas as pd
import sqlite3
import datetime
import matplotlib.pyplot as plt

# --- BASE DE DATOS ---
def crear_tabla():
    with sqlite3.connect("habitos.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS registros (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT,
                usuario TEXT,
                habito TEXT,
                completado INTEGER
            )
        ''')

def crear_tabla_invitaciones():
    with sqlite3.connect("habitos.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS invitaciones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                emisor TEXT NOT NULL,
                receptor TEXT NOT NULL,
                estado TEXT CHECK (estado IN ('pendiente', 'aceptada')) NOT NULL
            )
        ''')

def crear_tabla_habitos():
    with sqlite3.connect("habitos.db") as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS habitos_personalizados (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                usuario TEXT NOT NULL,
                habito TEXT NOT NULL
            )
        ''')

def agregar_habito(usuario, habito):
    with sqlite3.connect("habitos.db") as conn:
        conn.execute("INSERT INTO habitos_personalizados (usuario, habito) VALUES (?, ?)", (usuario, habito))

def obtener_habitos(usuario):
    with sqlite3.connect("habitos.db") as conn:
        df = pd.read_sql_query("SELECT habito FROM habitos_personalizados WHERE usuario = ?", conn, params=(usuario,))
    return df['habito'].tolist()

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

crear_tabla()
crear_tabla_invitaciones()
crear_tabla_habitos()

# --- LOGIN SIMPLE ---
usuarios = {
    "luis": "1234",
    "suri": "1234"
}

st.title("📊 Seguimiento de Hábitos Compartido")

usuario_actual = st.sidebar.text_input("Usuario")
contrasena = st.sidebar.text_input("Contraseña", type="password")

if usuario_actual in usuarios and usuarios[usuario_actual] == contrasena:
    st.sidebar.success(f"Bienvenido/a {usuario_actual}")

    # --- GESTIÓN DE INVITACIONES ---
    st.sidebar.markdown("### 🤝 Invitaciones")
    otros_usuarios = [u for u in usuarios.keys() if u != usuario_actual]
    destinatario = st.sidebar.selectbox("Invitar a:", otros_usuarios)
    if st.sidebar.button("Enviar invitación"):
        with sqlite3.connect("habitos.db") as conn:
            ya_existe = conn.execute('''
                SELECT * FROM invitaciones
                WHERE (emisor = ? AND receptor = ?) OR (emisor = ? AND receptor = ?)
            ''', (usuario_actual, destinatario, destinatario, usuario_actual)).fetchone()

            if ya_existe:
                st.sidebar.warning("Ya hay una invitación entre ustedes.")
            else:
                conn.execute('''
                    INSERT INTO invitaciones (emisor, receptor, estado)
                    VALUES (?, ?, 'pendiente')
                ''', (usuario_actual, destinatario))
                st.sidebar.success("Invitación enviada.")

    with sqlite3.connect("habitos.db") as conn:
        pendientes = conn.execute('''
            SELECT emisor FROM invitaciones
            WHERE receptor = ? AND estado = 'pendiente'
        ''', (usuario_actual,)).fetchall()

    if pendientes:
        st.sidebar.markdown("**Invitaciones recibidas:**")
        for (emisor,) in pendientes:
            if st.sidebar.button(f"Aceptar de {emisor}"):
                with sqlite3.connect("habitos.db") as conn:
                    conn.execute('''
                        UPDATE invitaciones
                        SET estado = 'aceptada'
                        WHERE emisor = ? AND receptor = ?
                    ''', (emisor, usuario_actual))
                st.sidebar.success(f"Ahora puedes ver a {emisor}")
                st.rerun()

    # --- TABS PRINCIPALES ---
    tab1, tab2, tab3, tab4 = st.tabs(["📋 Registrar", "📈 Tu progreso", "👀 Ver otros", "⚙️ Mis hábitos"])

    # --- REGISTRO DE HÁBITOS ---
    with tab1:
        st.subheader("✅ Registrar hábito")
        fecha = st.date_input("Fecha", datetime.date.today())
        habitos_lista = obtener_habitos(usuario_actual)

        if habitos_lista:
            habito = st.selectbox("Selecciona un hábito", habitos_lista)
        else:
            st.info("Aún no has creado hábitos. Agrega uno desde la pestaña '⚙️ Mis hábitos'")
            habito = None

        completado = st.checkbox("¿Completado?")

        if st.button("Guardar"):
            if not habito:
                st.error("Selecciona un hábito primero")
            else:
                agregar_registro(str(fecha), usuario_actual, habito, int(completado))
                st.success("Registro guardado")

    # --- PROGRESO PERSONAL ---
    with tab2:
        st.subheader("📈 Tu progreso")
        df = obtener_registros(usuario_actual)
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
            st.write("📊 Porcentaje de cumplimiento")
            st.dataframe(porcentaje.rename("Cumplimiento (%)"))

            st.subheader("📅 Últimos registros")
            st.dataframe(df.sort_values("fecha", ascending=False).head(10))

            st.download_button("📥 Descargar tus registros", df.to_csv(index=False), file_name="mis_habitos.csv")
        else:
            st.info("Aún no has registrado hábitos.")

    # --- PROGRESO DE OTROS USUARIOS (solo con invitación aceptada) ---
    with tab3:
        st.subheader("👀 Ver progreso de otro usuario")
        with sqlite3.connect("habitos.db") as conn:
            invitados = conn.execute('''
                SELECT emisor FROM invitaciones
                WHERE receptor = ? AND estado = 'aceptada'
            ''', (usuario_actual,)).fetchall()

        usuarios_disponibles = [fila[0] for fila in invitados]

        if usuarios_disponibles:
            seleccionado = st.selectbox("Selecciona un usuario", usuarios_disponibles)
            df_otro = obtener_registros(seleccionado)

            if not df_otro.empty:
                resumen_otro = df_otro.groupby("habito")["completado"].sum()
                st.write(f"Resumen de hábitos de **{seleccionado}**")
                st.dataframe(resumen_otro)

                fig2, ax2 = plt.subplots()
                resumen_otro.plot(kind="bar", ax=ax2, color="orange")
                ax2.set_ylabel("Veces completado")
                ax2.set_title(f"Progreso de {seleccionado}")
                st.pyplot(fig2)

                st.subheader("📅 Últimos registros de esa persona")
                st.dataframe(df_otro.sort_values("fecha", ascending=False).head(10))
            else:
                st.info(f"{seleccionado} aún no ha registrado hábitos.")
        else:
            st.info("Nadie te ha enviado una invitación aún.")

    # --- GESTIÓN DE HÁBITOS PERSONALIZADOS ---
    with tab4:
        st.subheader("⚙️ Mis hábitos")
        habitos_actuales = obtener_habitos(usuario_actual)

        if habitos_actuales:
            habito_a_eliminar = st.selectbox("Selecciona un hábito para eliminar", habitos_actuales)
            if st.button("Eliminar hábito"):
                eliminar_habito(usuario_actual, habito_a_eliminar)
                st.success("Hábito eliminado")
                st.rerun()
        else:
            st.info("No tienes hábitos definidos todavía.")

        nuevo_habito = st.text_input("Agregar nuevo hábito")
        if st.button("Añadir nuevo hábito") and nuevo_habito.strip():
            agregar_habito(usuario_actual, nuevo_habito.strip())
            st.success("Hábito añadido")
            st.rerun()

else:
    st.warning("Credenciales incorrectas. Intenta de nuevo.")