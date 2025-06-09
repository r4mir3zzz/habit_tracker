import random
import string
import streamlit as st
import smtplib
from email.mime.text import MIMEText
import pandas as pd
from config import supabase, EMAIL_SENDER, EMAIL_PASSWORD, SMTP_SERVER, SMTP_PORT

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

def actualizar_registro(fecha, usuario, habito, completado):
    try:
        supabase.table('registros').update({
            'completado': completado
        }).eq('usuario', usuario).eq('habito', habito).eq('fecha', str(fecha)).execute()
        return True
    except Exception as e:
        st.error(f"Error al actualizar registro: {str(e)}")
        return False