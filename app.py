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

# CSS Personalizado para que se vea moderno
st.markdown("""
    <style>
    .main {background-color: #f9f9f9;}
    h1 {color: #2c3e50; font-family: 'Helvetica', sans-serif;}
    h2 {color: #34495e;}
    .stButton>button {
        width: 100%; 
        border-radius: 8px; 
        height: 3em; 
        background-color: #2c3e50; 
        color: white; 
        font-weight: bold;
    }
    .stButton>button:hover {
        background-color: #34495e;
        border-color: #34495e;
        color: white;
    }
    .success-box {
        padding: 1rem;
        background-color: #d4edda;
        border-left: 6px solid #28a745;
        color: #155724;
        margin-bottom: 1rem;
    }
    </style>
    """, unsafe_allow_html=True)

# --- 2. CONEXIÓN SEGURA ---
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    genai.configure(api_key=api_key)
except:
    st.error("⚠️ Error Crítico: No se detecta la API Key en los Secrets.")
    st.stop()

# --- 3. MOTOR DE WORD PROFESIONAL ---
def add_markdown_to_doc(doc, text):
    """Convierte Markdown a elementos nativos de Word"""
    lines = text.split('\n')
    table_buffer = []
    in_table = False

    for line in lines:
        stripped = line.strip()

        # Detección de Tablas
        if stripped.startswith('|') and stripped.endswith('|'):
            if '---' in stripped: continue
            row_data = [c.strip() for c in stripped.split('|') if c.strip()]
            table_buffer.append(row_data)
            in_table = True
        else:
            # Dibujar tabla si se acabó
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
                                # Poner negrita en la cabecera
                                p = cell.paragraphs[0]
                                run = p.add_run(cell_text)
                                if r == 0: run.bold = True
                
                table_buffer = []
                in_table = False

            # Títulos
            if stripped.startswith('## '):
                doc.add_heading(stripped.replace('#', '').strip(), level=1)
            elif stripped.startswith('### '):
                doc.add_heading(stripped.replace('#', '').strip(), level=2)
            # Listas
            elif stripped.startswith('- '):
                doc.add_paragraph(stripped[2:], style='List Bullet')
            # Párrafos normales
            elif stripped:
                p = doc.add_paragraph()
                # Procesar negritas simples **texto**
                parts = re.split(r'(\*\*.*?\*\*)', stripped)
                for part in parts:
                    if part.startswith('**') and part.endswith('**'):
                        p.add_run(part[2:-2]).bold = True
                    else:
                        p.add_run(part)

    return doc

def create_professional_report(content_text):
    """Crea un Word con portada y formato"""
    doc = Document()
    
    # --- PORTADA ---
    for _ in range(5): doc.add_paragraph() # Espacio
    title = doc.add_heading('INFORME DE AUDITORÍA SOCIETARIA', 0)
    title.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    subtitle = doc.add_paragraph('Análisis de Titularidad Real y Trayectoria')
    subtitle.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    date_p = doc.add_paragraph(f'Fecha de emisión: {datetime.now().strftime("%d/%m/%Y")}')
    date_p.alignment = WD_PARAGRAPH_ALIGNMENT.CENTER
    
    doc.add_page_break() # Salto de página
    
    # --- CONTENIDO ---
    add_markdown_to_doc(doc, content_text)
    
    # --- PIE DE PÁGINA ---
    section = doc.sections[0]
    footer = section.footer
    p = footer.paragraphs[0]
    p.text = "Informe generado automáticamente por LegalAudit AI"
    p.alignment = WD_PARAGRAPH_ALIGNMENT.RIGHT
    
    return doc

# --- 4. INTERFAZ: BARRA LATERAL ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1998/1998342.png", width=80)
    st.title("Panel de Control")
    st.markdown("---")
    
    uploaded_files = st.file_uploader(
        "1. Sube las Escrituras (PDF)", 
        type=['pdf'], 
        accept_multiple_files=True,
        help="Sube constitución, ampliaciones, compraventas, etc."
    )
    
    st.markdown("---")
    analyze_btn = st.button("2. EJECUTAR ANÁLISIS ✨", type="primary")
    
    st.info("💡 **Consejo:** Sube todos los documentos de una misma empresa juntos para que la IA pueda trazar la historia completa.")

# --- 5. INTERFAZ: ÁREA CENTRAL ---
st.title("⚖️ Auditoría Legal Inteligente")
st.markdown("##### Generador de informes de titularidad real y Cap Tables")

if not uploaded_files:
    st.markdown("""
    <div style="padding: 20px; background-color: #e8f4f8; border-radius: 10px;">
        <h4>👋 Bienvenido</h4>
        <p>Esta herramienta utiliza <b>Gemini 2.5 Flash</b> para leer escrituras notariales complejas.</p>
        <p><b>Cómo funciona:</b></p>
        <ol>
            <li>Sube los PDFs en el menú de la izquierda.</li>
            <li>La IA ordenará cronológicamente los hechos.</li>
            <li>Se calculará matemáticamente el reparto de capital.</li>
            <li>Podrás descargar un Word profesional.</li>
        </ol>
    </div>
    """, unsafe_allow_html=True)

# --- 6. LÓGICA DE ANÁLISIS ---
if analyze_btn and uploaded_files:
    
    # Pestañas para organizar la salida
    tab1, tab2 = st.tabs(["📄 Informe Visual", "📥 Descarga Word"])
    
    with tab1:
        progress_bar = st.progress(0, text="Iniciando motor de IA...")
        
        try:
            # A. Subida a Google
            gemini_files = []
            for i, uploaded_file in enumerate(uploaded_files):
                progress_bar.progress((i / len(uploaded_files)) * 0.5, text=f"Leyendo: {uploaded_file.name}...")
                
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                    tmp.write(uploaded_file.getvalue())
                    tmp_path = tmp.name
                
                g_file = genai.upload_file(path=tmp_path, display_name=uploaded_file.name)
                gemini_files.append(g_file)
                os.remove(tmp_path)

            # B. Espera activa
            progress_bar.progress(0.6, text="Procesando documentos en la nube...")
            time.sleep(2) # Pequeña pausa para asegurar sincronización
            
            # C. El Prompt Maestro (MEJORADO)
            SYSTEM_PROMPT = """
            ROL: Abogado Mercantilista Senior y Auditor.
            OBJETIVO: Analizar la documentación societaria y generar un informe de Due Diligence.

            METODOLOGÍA OBLIGATORIA:
            1. **CODE EXECUTION:** Usa Python para calcular el Cap Table. Prohibido calcular de memoria.
            2. **CRONOLOGÍA:** Ordena los hechos por la fecha de la escritura, NO por el nombre del archivo.
            3. **MONEDA:** Convierte todo a EUROS para la tabla final, pero cita las PESETAS originales en la narrativa.

            ESTRUCTURA DEL INFORME (Usa Markdown):
            
            ## 1. Resumen Ejecutivo
            Breve párrafo (3 líneas) con el estado actual de la empresa: Capital actual, Órgano de administración vigente y sede social.

            ## 2. Cronología de Actos Jurídicos
            (Narra historia paso a paso. Sé preciso con las fechas y Notarios).
            - **[FECHA] - Constitución/Ampliación/Venta:** Detalle de la operación.

            ## 3. Cuadro de Titularidad Real (Cap Table)
            (Genera una tabla Markdown exacta calculada vía Python):
            | Socio | DNI/NIF | Nº Participaciones | % Capital | Valor Nominal Total (€) |

            ## 4. Observaciones / Incidencias
            Indica si hay saltos en la numeración de participaciones o datos ilegibles.
            """

            # D. Ejecución del Modelo
            progress_bar.progress(0.8, text="Redactando informe legal...")
            
            model = genai.GenerativeModel(
                model_name="gemini-2.5-flash",
                system_instruction=SYSTEM_PROMPT,
                tools='code_execution'
            )
            
            response = model.generate_content(["Genera el informe de auditoría completo.", *gemini_files])
            
            progress_bar.progress(1.0, text="¡Finalizado!")
            time.sleep(0.5)
            progress_bar.empty()

            # E. Mostrar Resultados
            st.markdown('<div class="success-box">✅ Análisis completado con éxito. Revisa los datos abajo.</div>', unsafe_allow_html=True)
            st.markdown(response.text)
            
            # Guardamos el texto en la sesión para que no se borre al cambiar de pestaña
            st.session_state['report_text'] = response.text

        except Exception as e:
            st.error(f"Ocurrió un error: {e}")

    with tab2:
        if 'report_text' in st.session_state:
            st.markdown("### Descargar Entregable")
            st.write("El informe está listo. Haz clic abajo para obtener el documento Word formateado con portada.")
            
            # Generar Word
            doc = create_professional_report(st.session_state['report_text'])
            bio = io.BytesIO()
            doc.save(bio)
            
            st.download_button(
                label="📥 Descargar Informe Profesional (.docx)",
                data=bio.getvalue(),
                file_name=f"Auditoria_Legal_{datetime.now().strftime('%Y%m%d')}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
        else:
            st.info("👈 Ejecuta el análisis en la pestaña anterior para generar el documento.")
