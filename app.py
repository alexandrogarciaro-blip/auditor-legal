import streamlit as st
import google.generativeai as genai
from docx import Document
import io
import time
import tempfile
import os

# --- CONFIGURACIÓN DE LA PÁGINA ---
st.set_page_config(page_title="Auditor Legal IA", page_icon="⚖️", layout="wide")

# --- ESTILOS CSS ---
st.markdown("""
    <style>
    .stButton>button {width: 100%; border-radius: 5px; height: 3em; background-color: #FF4B4B; color: white;}
    </style>
    """, unsafe_allow_html=True)

# --- CONEXIÓN SEGURA (SECRETS) ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ Error: No se encuentra la API Key en los Secrets de Streamlit.")
    st.stop()

# --- TÍTULO ---
st.title("⚖️ Auditoría de Escrituras (PALOMARES CONSULTORES)")
st.markdown("---")
st.info("ℹ️ Sube todas las escrituras (PDF). La IA ordenará los hechos y calculará el reparto de socios.")

# --- FUNCIONES AUXILIARES ---
def wait_for_files_active(files):
    """Espera a que Google procese los archivos"""
    my_bar = st.progress(0, text="Procesando documentos en la nube...")
    for i, file in enumerate(files):
        file_check = genai.get_file(file.name)
        while file_check.state.name == "PROCESSING":
            time.sleep(1)
            file_check = genai.get_file(file.name)
        if file_check.state.name != "ACTIVE":
            st.error(f"Error procesando {file.display_name}")
            return False
        my_bar.progress((i + 1) / len(files), text=f"Listo: {file.display_name}")
    my_bar.empty()
    return True

def clean_markdown(text):
    """Limpia el texto para el Word"""
    return text.replace('**', '').replace('##', '').replace('###', '')

# --- INTERFAZ DE CARGA ---
uploaded_files = st.file_uploader("📂 Arrastra los PDFs aquí", type=['pdf'], accept_multiple_files=True)

# --- CEREBRO JURÍDICO (PROMPT) ---
SYSTEM_PROMPT = """
ROL: Eres un Auditor Mercantil Senior y Jurista Experto.
OBJETIVO: Analizar escrituras de una sociedad para generar un informe de TITULARIDAD REAL y TRAYECTORIA.

REGLAS OBLIGATORIAS:
1. USO DE PYTHON: Tienes PROHIBIDO hacer cálculos mentales. Usa siempre 'code_execution' para sumar/restar participaciones y calcular porcentajes.
2. ORDEN: Cronológico estricto basado en la fecha de otorgamiento dentro del texto.
3. ESTILO: Narrativo formal (no esquemático). Redacta la historia de la empresa.
4. MONEDA: Si hay Pesetas, indica su valor y la conversión a Euros entre paréntesis.

ESTRUCTURA DEL INFORME:
- Título: Informe de Auditoría Societaria.
- Capítulo 1: Constitución (Datos fundacionales).
- Capítulo 2: Evolución Histórica (Narra cada escritura: Ampliaciones, Ceses, Cambios domicilio...).
- Capítulo 3 (VITAL): TABLA DE TITULARIDAD ACTUAL.
  Debes generar una tabla final con: | SOCIO | Nº PARTICIPACIONES | VALOR NOMINAL (€) | % CAPITAL SOCIAL |

Si detectas errores en la cadena de titularidad (ej. alguien vende lo que no tiene), avisa en una sección de "INCIDENCIAS".
"""

# --- BOTÓN DE EJECUCIÓN ---
if st.button("🔍 INICIAR AUDITORÍA", type="primary"):
    if not uploaded_files:
        st.warning("⚠️ Por favor, sube al menos un documento.")
    else:
        try:
            # 1. Subida a Google
            gemini_files = []
            with st.spinner('Subiendo archivos a la IA...'):
                for uploaded_file in uploaded_files:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(uploaded_file.getvalue())
                        tmp_path = tmp.name
                    
                    g_file = genai.upload_file(path=tmp_path, display_name=uploaded_file.name)
                    gemini_files.append(g_file)
                    os.remove(tmp_path) # Borrar temporal local

            # 2. Procesamiento
            if wait_for_files_active(gemini_files):
                with st.spinner('🧠 Gemini 3 está leyendo, razonando y calculando... (Esto puede tardar unos segundos)'):
                    
                    # CONFIGURACIÓN DEL MODELO GEMINI 3
                    model = genai.GenerativeModel(
                        model_name="gemini-2.5-flash", ######################################################################################## VERSION DE GEMINI
                        system_instruction=SYSTEM_PROMPT,
                        tools='code_execution'
                    )
                    
                    # Llamada a la IA
                    response = model.generate_content(
                        ["Analiza los documentos adjuntos y genera el informe completo.", *gemini_files]
                    )

                # 3. Mostrar Resultados
                st.success("¡Análisis Completado!")
                
                col1, col2 = st.columns([0.6, 0.4])
                
                with col1:
                    st.markdown("### 📄 Vista Previa")
                    st.markdown(response.text)
                
                with col2:
                    st.markdown("### 📥 Descarga")
                    # Generar Word
                    doc = Document()
                    doc.add_heading('Informe de Auditoría Legal', 0)
                    
                    # Añadir texto limpio
                    clean_text = clean_markdown(response.text)
                    for line in clean_text.split('\n'):
                        if line.strip():
                            doc.add_paragraph(line)
                            
                    bio = io.BytesIO()
                    doc.save(bio)
                    
                    st.download_button(
                        label="Descargar Informe (.docx)",
                        data=bio.getvalue(),
                        file_name="Auditoria_Legal.docx",
                        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                    )

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")




