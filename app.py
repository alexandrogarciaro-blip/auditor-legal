import streamlit as st
import google.generativeai as genai

st.set_page_config(page_title="Diagnóstico de Modelos")

# 1. Configurar Clave
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("Falta la API Key en los Secrets.")
    st.stop()

st.title("🕵️ Buscando modelos disponibles...")

# 2. Listar modelos compatibles
try:
    st.write("Estos son los NOMBRES EXACTOS que acepta tu cuenta:")
    found = False
    for m in genai.list_models():
        # Filtramos solo los que sirven para generar texto (chat)
        if 'generateContent' in m.supported_generation_methods:
            st.code(f'model_name="{m.name.replace("models/", "")}",')
            found = True
    
    if not found:
        st.warning("No se han encontrado modelos. Verifica tu API Key.")

except Exception as e:
    st.error(f"Error de conexión: {e}")
