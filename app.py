import streamlit as st
import google.generativeai as genai
from docx import Document
import io
import time
import tempfile
import os

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Gestor de Escrituras", page_icon="⚖️", layout="wide")

# --- GESTIÓN DE LA CLAVE DE SEGURIDAD (NUBE) ---
try:
    # Intenta coger la clave de los secretos de la nube
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
    # --- CÓDIGO TEMPORAL DE DIAGNÓSTICO ---
st.subheader("⚠️ LISTA DE MODELOS DISPONIBLES:")
try:
    for m in genai.list_models():
        if 'generateContent' in m.supported_generation_methods:
            st.code(m.name)
except Exception as e:
    st.error(f"Error listando modelos: {e}")
# ---------------------------------------
except:
    st.error("⚠️ No se ha detectado la API Key. Configúrala en los 'Secrets' de Streamlit.")
    st.stop()

# --- ESTILOS VISUALES ---
st.markdown("""
    <style>
    .main {background-color: #f8f9fa;}
    h1 {color: #1f2937;}
    </style>
    """, unsafe_allow_html=True)

st.title("⚖️ Auditoría Legal con IA")
st.markdown("**Sube las escrituras (PDF) para obtener el informe narrativo y el cuadro de socios.**")

# --- FUNCIONES ---
def wait_for_files_active(files):
    progress_text = "Analizando documentos en los servidores de Google..."
    my_bar = st.progress(0, text=progress_text)
    for i, file in enumerate(files):
        file_check = genai.get_file(file.name)
        while file_check.state.name == "PROCESSING":
            time.sleep(2)
            file_check = genai.get_file(file.name)
        my_bar.progress((i + 1) / len(files), text=f"Procesado: {file.display_name}")
    my_bar.empty()

def clean_markdown_for_word(text):
    return text.replace('**', '').replace('##', '').replace('###', '')

# --- SUBIDA DE ARCHIVOS ---
uploaded_files = st.file_uploader("Arrastra aquí los PDFs", type=['pdf'], accept_multiple_files=True)

# --- EL CEREBRO (Tu Prompt Maestro) ---
SYSTEM_INSTRUCTION = """
Eres un experto Jurista y Auditor Mercantil. Tu tarea es analizar escrituras y redactar un informe NARRATIVO formal.

INSTRUCCIONES DE ESTILO:
1. TONO NARRATIVO: Redacta la historia de la empresa cronológicamente (Constitución -> Ampliaciones -> Cambios).
2. MONEDA: Si hay pesetas, pon su equivalencia en euros entre paréntesis.
3. TABLA FINAL: Genera al final una tabla Markdown con: | SOCIOS | PARTICIPACIONES | CAPITAL (€) | % |.

REGLA DE ORO:
Usa CODE EXECUTION (Python) para calcular los totales. No sumes de memoria.
"""

# --- EJECUCIÓN ---
if st.button("Generar Informe 🚀", type="primary"):
    if not uploaded_files:
        st.warning("Primero sube los archivos.")
    else:
        try:
            gemini_files = []
            with st.spinner('Subiendo a la nube segura...'):
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
                        tmp_file.write(uploaded_file.getvalue())
                        tmp_path = tmp_file.name
                    g_file = genai.upload_file(path=tmp_path, display_name=uploaded_file.name)
                    gemini_files.append(g_file)
                    os.remove(tmp_path)

            with st.spinner('La IA está redactando el informe...'):
                wait_for_files_active(gemini_files)
                model = genai.GenerativeModel(
                    model_name="gemini-1.5-pro-latest", 
                    system_instruction=SYSTEM_INSTRUCTION,
                    tools='code_execution'
                )
                response = model.generate_content(["Analiza los documentos y genera el informe.", *gemini_files])
                
            st.success("¡Informe completado!")

            col1, col2 = st.columns([0.7, 0.3])
            with col1:
                st.markdown(response.text)
            with col2:
                doc = Document()
                doc.add_heading('Informe de Auditoría', 0)
                clean_text = clean_markdown_for_word(response.text)
                for paragraph in clean_text.split('\n'):
                    if paragraph.strip():
                        doc.add_paragraph(paragraph)
                bio = io.BytesIO()
                doc.save(bio)
                st.download_button("📥 Descargar WORD", data=bio.getvalue(), file_name="Informe_Legal.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

        except Exception as e:

            st.error(f"Error: {e}")



