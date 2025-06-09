import streamlit as st
import pandas as pd
import datetime
import plotly.graph_objects as go
from config import supabase
from functions import *

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
            st.subheader("✅ Registrar hábitos del día")

            fecha = st.date_input("Fecha", datetime.date.today())
            habitos_lista = obtener_habitos(username_actual)

            if not habitos_lista:
                st.info("Aún no has creado hábitos.")
            else:
                # Obtener registros existentes de ese día
                registros = obtener_registros(username_actual)
                registros_fecha = registros[registros["fecha"] == pd.to_datetime(fecha)]

                st.write("Marca los hábitos completados para esta fecha:")

                # Mostrar tabla de hábitos con checkbox
                completados = {}
                for habito in habitos_lista:
                    ya_existe = registros_fecha[registros_fecha["habito"] == habito]

                    if not ya_existe.empty:
                        # Ya registrado -> usar su valor actual
                        valor = bool(ya_existe["completado"].values[0])
                    else:
                        # No registrado aún -> por defecto False
                        valor = False

                    completados[habito] = st.checkbox(habito, value=valor)

                if st.button("Guardar cambios"):
                    guardados = []
                    for habito, estado in completados.items():
                        ya_existe = registros_fecha[registros_fecha["habito"] == habito]

                        if not ya_existe.empty:
                            # Ya existe → actualizar si cambió
                            registro_id = ya_existe["id"].values[0] if "id" in ya_existe.columns else None
                            if int(estado) != ya_existe["completado"].values[0]:
                                actualizar_registro(fecha, username_actual, habito, int(estado))
                                guardados.append(habito)
                        else:
                            # No existe → insertar nuevo
                            agregar_registro(fecha, username_actual, habito, int(estado))
                            guardados.append(habito)

                    if guardados:
                        st.success(f"Actualizado: {', '.join(guardados)}")
                    else:
                        st.info("No hubo cambios por guardar.")

        with tab2:
            st.subheader("📈 Tu progreso")

            df = obtener_registros(username_actual)

            if not df.empty:
                # Asegurarte de que la fecha no tenga hora
                df["fecha"] = pd.to_datetime(df["fecha"]).dt.date

                # Tomar el último estado por fecha + hábito (evita duplicados)
                df = df.sort_values("fecha")  # En caso haya varios registros, toma el último
                df = df.drop_duplicates(subset=["fecha", "habito"], keep="last")

                total_habitos = df["habito"].nunique()

                # Ahora calcula cuántos se marcaron como completados por día
                completados_diarios = df[df["completado"] == 1].groupby("fecha").size()

                # Progreso diario como porcentaje
                progreso_diario = completados_diarios / total_habitos * 100
                progreso_diario = progreso_diario.reindex(sorted(df["fecha"].unique()), fill_value=0)

                st.dataframe(progreso_diario.rename("Cumplimiento diario (%)"))

                # Crear gráfico usando fechas como strings para ocultar la hora
                fig = go.Figure()
                fig.add_trace(go.Scatter(
                    x=progreso_diario.index.astype(str),
                    y=progreso_diario.values,
                    mode="lines+markers",
                    line=dict(color="mediumseagreen"),
                    name="Cumplimiento (%)"
                ))

                fig.update_layout(
                    title="Progreso Diario de Hábitos",
                    xaxis_title="Fecha",
                    yaxis_title="Cumplimiento (%)",
                    yaxis=dict(range=[0, 100]),
                    template="plotly_white",
                    hovermode="x unified"
                )

                st.plotly_chart(fig, use_container_width=True)

            else:
                st.info("No hay registros aún.")

        with tab3:
            st.subheader("👀 Ver progreso de otro usuario")
            disponibles = obtener_invitaciones_aceptadas(username_actual)

            if disponibles:
                seleccionado = st.selectbox("Selecciona un usuario", disponibles)
                df_otro = obtener_registros(seleccionado)

                if not df_otro.empty:
                    df_otro["fecha"] = pd.to_datetime(df_otro["fecha"]).dt.date

                    # 🔧 Corregimos duplicados por fecha y hábito (conservar el último estado registrado)
                    df_otro = df_otro.sort_values("fecha")
                    df_otro = df_otro.drop_duplicates(subset=["fecha", "habito"], keep="last")

                    total_habitos_otro = df_otro["habito"].nunique()

                    completados_diarios_otro = df_otro[df_otro["completado"] == 1].groupby("fecha").size()
                    progreso_diario_otro = completados_diarios_otro / total_habitos_otro * 100
                    progreso_diario_otro = progreso_diario_otro.reindex(sorted(df_otro["fecha"].unique()), fill_value=0)

                    st.dataframe(progreso_diario_otro.rename("Cumplimiento diario (%)"))

                    fig_otro = go.Figure()
                    fig_otro.add_trace(go.Scatter(
                        x=progreso_diario_otro.index.astype(str),
                        y=progreso_diario_otro.values,
                        mode="lines+markers",
                        line=dict(color="dodgerblue"),
                        name=f"Progreso de {seleccionado}"
                    ))

                    fig_otro.update_layout(
                        title=f"Progreso Diario de {seleccionado}",
                        xaxis_title="Fecha",
                        yaxis_title="Cumplimiento (%)",
                        yaxis=dict(range=[0, 100]),
                        template="plotly_white",
                        hovermode="x unified"
                    )

                    st.plotly_chart(fig_otro, use_container_width=True)

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