import streamlit as st
import google.generativeai as genai
from docx import Document
from docx.shared import Pt, RGBColor, Inches
from docx.enum.text import WD_PARAGRAPH_ALIGNMENT
import io
import time
import tempfile
import os
import re
from datetime import datetime

# --- 1. CONFIGURACIÓN VISUAL ---
st.set_page_config(
    page_title="LegalAudit AI",
    page_icon="⚖️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS (Incluye el Modo Oscuro para la barra lateral)
st.markdown("""
    <style>
    /* BARRA LATERAL OSCURA */
    section[data-testid="stSidebar"] {background-color: #101820;}
    section[data-testid="stSidebar"] h1, section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] label, section[data-testid="stSidebar"] .stMarkdown,
    section[data-testid="stSidebar"] p {color: #ffffff !important;}
    
    /* FONDO PRINCIPAL */
    .main {background-color: #f4f6f9;}
    h1 {color: #2c3e50; font-family: 'Helvetica', sans-serif;}
    
    /* BOTONES DORADOS */
    .stButton>button {
        width: 100%; border-radius: 8px; height: 3em; 
        background-color: #c5a059; color: white; font-weight: bold; border: none;
    }
    .stButton>button:hover {background-color: #b08d4b; color: white;}
    
    /* VISIBILIDAD DE ARCHIVOS EN BARRA LATERAL */
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] div,
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] small,
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] span {color: #ffffff !important;}
    [data-testid="stSidebar"] [data-testid="stFileUploaderFile"] svg {fill: #ffffff !important;}
    [data-testid="stSidebar"] button[kind="secondary"] {background-color: #ffffff !important; color: #000000 !important; border: none;}
    
    /* CAJA DE ÉXITO */
    .success-box {padding: 1rem; background-color: #d4edda; border-left: 6px solid #28a745; color: #155724; margin-bottom: 1rem;}
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN SEGURA ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ Error: No se detecta la API Key en los Secrets.")
    st.stop()

# --- 3. FUNCIONES DE LIMPIEZA Y WORD ---

def clean_technical_output(text):
    """
    Elimina los bloques de código Python que la IA a veces muestra.
    Busca patrones entre ``` y ``` y los borra.
    """
    # Eliminar bloques de código ```python ... ``` o ``` ... ```
    clean_text = re.sub(r'```.*?```', '', text, flags=re.DOTALL)
    # Eliminar líneas sueltas que parezcan código técnico
    return clean_text.strip()

def add_markdown_to_doc(doc, text):
    """Convierte Markdown limpio a Word"""
    lines = text.split('\n')
    table_buffer = []
    in_table = False

    for line in lines:
        stripped = line.strip()
        if not stripped: continue # Saltar líneas vacías extra

        # Detectar Tablas
        if stripped.startswith('|') and stripped.endswith('|'):
            if '---' in stripped: continue
            row_data = [c.strip() for c in stripped.split('|') if c.strip()]
            table_buffer.append(row_data)
            in_table = True
        else:
            # Dibujar tabla pendiente
            if in_table and table_buffer:
                if len(table_buffer) > 0:
                    rows = len(table_buffer)
                    cols = len(table_buffer[0])
                    t = doc.add_table(rows=rows, cols=cols)
                    t.style = 'Table Grid'
                    t.autofit = True
                    for r, row_data in enumerate(table_buffer):
                        for c, cell_text in enumerate(row_data):
                            if c < cols:
                                cell = t.cell(r, c)
                                p = cell.paragraphs[0]
                                p.text = cell_text
                                if r == 0: 
                                    for run in p.runs: run.bold = True
                table_buffer = []
                in_table = False

            # Formato de texto
            if stripped.startswith('## '):
                doc.add_heading(stripped.replace('#', '').strip(), level=1)
            elif stripped.startswith('### '):
                doc.add_heading(stripped.replace('#', '').strip(), level=2)
            elif stripped.startswith('- '):
                doc.add_paragraph(stripped[2:], style='List Bullet')
            elif stripped:
                p = doc.add_paragraph()
                # Negritas
                parts = re.split(r'(\*\*.*?\*\*)', stripped)
                for part in parts:
                    if part.startswith('**') and part.endswith('**'):
                        p.add_run(part[2:-2]).bold = True
                    else:
                        p.add_run(part)
    return doc

def create_professional_report(content_text):
    doc = Document()
    # Portada
    for _ in range(5): doc.add_paragraph()
    title = doc.add_heading('INFORME DE AUDITORÍA SOCIETARIA', 0)
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    subtitle = doc.add_paragraph('Análisis de Titularidad Real y Trayectoria')
    subtitle.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    doc.add_paragraph(f'Fecha: {datetime.now().strftime("%d/%m/%Y")}').alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    doc.add_page_break()
    
    # Contenido Limpio
    add_markdown_to_doc(doc, content_text)
    
    # Pie
    section = doc.sections[0]
    p = section.footer.paragraphs[0]
    p.text = "Documento generado por IA - Palomares Consultores"
    p.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    return doc

# --- 4. INTERFAZ ---
with st.sidebar:
    # LOGO (Si subiste 'logo.png' a GitHub se verá, si no usa un icono)
    try:
        st.image("logo.png", width=280)
    except:
        st.image("https://cdn-icons-png.flaticon.com/512/1998/1998342.png", width=100)
        
    st.markdown("### Panel de Control")
    uploaded_files = st.file_uploader("1. Sube Escrituras (PDF)", type=['pdf'], accept_multiple_files=True)
    st.markdown("---")
    analyze_btn = st.button("2. EJECUTAR ANÁLISIS ✨", type="primary")

# --- 5. LÓGICA ---
st.title("⚖️ Auditoría Legal Inteligente")

if not uploaded_files:
    st.info("👋 Sube los documentos en el menú de la izquierda para comenzar.")

if analyze_btn and uploaded_files:
    tab1, tab2 = st.tabs(["📄 Informe", "📥 Word"])
    
    with tab1:
        progress = st.progress(0, text="Iniciando...")
        try:
            gemini_files = []
            # A. Subida
            for i, f in enumerate(uploaded_files):
                progress.progress((i/len(uploaded_files))*0.5, text=f"Leyendo: {f.name}")
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(f.getvalue())
                    tmp_path = tmp.name
                g_file = genai.upload_file(path=tmp_path, display_name=f.name)
                gemini_files.append(g_file)
                os.remove(tmp_path)

            progress.progress(0.6, text="Procesando...")
            time.sleep(2)
            
            # B. PROMPT (Con instrucción de ocultar código)
            SYSTEM_PROMPT = """
            ROL: Abogado Mercantilista.
            OBJETIVO: Informe de Due Diligence.
            
            REGLAS ESTRICTAS DE SALIDA:
            1. **NO MUESTRES CÓDIGO:** Usa Python internamente para calcular, pero EN EL INFORME FINAL SOLO QUIERO EL TEXTO Y LAS TABLAS. Oculta los bloques de código, variables y pasos intermedios.
            2. **TABLAS:** Genera tablas Markdown limpias.
            3. **ESTILO:** Narrativo profesional.
            
            ESTRUCTURA:
            1. Resumen Ejecutivo.
            2. Cronología Detallada.
            3. Tabla de Titularidad Actual (Calculada exactamente).
            4. Incidencias.
            """

            # C. Generación
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=SYSTEM_PROMPT,
                tools='code_execution'
            )
            response = model.generate_content(["Genera el informe.", *gemini_files])
            
            # D. LIMPIEZA DE CÓDIGO (El filtro mágico)
            final_text = clean_technical_output(response.text)
            
            progress.empty()
            st.markdown('<div class="success-box">✅ Análisis completado.</div>', unsafe_allow_html=True)
            st.markdown(final_text)
            
            st.session_state['report_text'] = final_text

        except Exception as e:
            st.error(f"Error: {e}")

    with tab2:
        if 'report_text' in st.session_state:
            st.write("Descarga el documento final formateado.")
            doc = create_professional_report(st.session_state['report_text'])
            bio = io.BytesIO()
            doc.save(bio)
            st.download_button("📥 Descargar Word", data=bio.getvalue(), file_name="Auditoria.docx", mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document")

