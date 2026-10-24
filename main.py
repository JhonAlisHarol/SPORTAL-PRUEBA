import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página
st.set_page_config(page_title="Procesador Masivo de Listados S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo y Automático de Listados S.PORTAL")
st.write("Sube tu PDF masivo de listado general. El sistema extraerá y estructurará todos los casos de golpe en un archivo Excel maestro.")

def procesar_pdf_masivo(ruta_pdf):
    """Procesa el PDF de listado general de S.PORTAL y extrae de forma limpia todos los incidentes."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            t = pagina.extract_text()
            if t:
                texto_completo += t + "\n"

        # Limpiar y separar por líneas
        lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
        casos_extraidos = []
        
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            
            # Buscar el código del incidente (Ej: P20260238869)
            match_inc = re.search(r'(P\d{10,12})', linea)
            if match_inc:
                incidente_id = match_inc.group(1)
                
                tipo = "N/A"
                subtipo = "N/A"
                zona = "N/A"
                fecha_creacion = ""
                hora_creacion = ""
                operador = "N/A"
                
                # Tomar un bloque de contexto alrededor de la línea actual
                contexto_bloque = " ".join(lineas[i:i+8])
                
                # Extraer Fecha y Hora de Creación
                match_fh = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})', contexto_bloque)
                if match_fh:
                    fecha_creacion = match_fh.group(1)
                    hora_creacion = match_fh.group(2)
                
                # Extraer Zona (Patrones como 12ZP, 8ZP, TRAN, etc.)
                match_zn = re.search(r'\b(\d{1,2}[A-Z]{1,3}|TRAN)\b', contexto_bloque)
                if match_zn:
                    zona = match_zn.group(1)

                # Extraer Operador por nombres frecuentes del C5
                posibles_nombres = [
                    "ENRIQUE CACERES", "VALERY VELASQUEZ", "LEONARDO CASASOLA", "IVETTE GIERHART", 
                    "JOAQUIN CHI", "DALILA TREJOS", "RICARDO EMILIO MAYORGA LORENZO", "HERMOGENES SANJUR", 
                    "ANTONIO PATRICIO", "ARMANDO GONZALEZ", "ESTEBAN E. HERNANDEZ H.", "YARIBETH M. ESCUDERO H.",
                    "MARIA ISABEL MADRID CASTILLO", "DORIAN GREAVES", "ANGELICA RODRIGUEZ", "ERICK ROSALES SANCHEZ JIRON",
                    "LEOPOLDO SERRANO BROWN", "JERRY JORDAN", "PABLO GONZALEZ", "ANGEL JORDAN"
                ]
                for nom in posibles_nombres:
                    if nom in contexto_bloque.upper():
                        operador = nom
                        break

                # Capturar Tipo y Subtipo analizando el texto del bloque
                if "Alteracion de la Convivencia" in contexto_bloque or "Riña" in contexto_bloque:
                    tipo = "Alteracion de la Convivencia Pacifica"
                    subtipo = "Riña y Escándalo" if "Riña" in contexto_bloque else "Alteración del Orden Publico"
                elif "Tránsito" in contexto_bloque or "Colisión" in contexto_bloque:
                    tipo = "Tránsito"
                    subtipo = "Colisión" if "Colisión" in contexto_bloque else "Infracción"
                elif "Arma de Fuego" in contexto_bloque:
                    tipo = "Arma de Fuego"
                    subtipo = "Posesión Ilegal / Detonaciones"
                elif "Violencia de Genero" in contexto_bloque or "Violencia Doméstica" in contexto_bloque:
                    tipo = "Violencia de Genero"
                    subtipo = "Violencia Doméstica"
                elif "Actitud Sospechosa" in contexto_bloque:
                    tipo = "Actitud Sospechosa"
                    subtipo = "N/A"
                elif "Hurto" in contexto_bloque:
                    tipo = "Hurto"
                    subtipo = "A Propiedad / Con Destreza"
                elif "Pánico" in contexto_bloque:
                    tipo = "Pánico"
                    subtipo = "N/A"
                else:
                    tipo = "Incidente General S.PORTAL"
                    subtipo = "N/A"

                # Guardar el registro estructurado
                casos_extraidos.append({
                    "Incidente": incidente_id,
                    "Tipo": tipo,
                    "Subtipo": subtipo,
                    "Zona": zona,
                    "Fecha Creación": fecha_creacion,
                    "Hora Creación": hora_creacion,
                    "Operador": operador
                })
            i += 1

        return casos_extraidos

    except Exception as e:
        return []

# Interfaz de carga en Streamlit
archivo_pdf = st.file_uploader("Sube el PDF de listado general de S.PORTAL:", type=["pdf"])

if archivo_pdf:
    with st.spinner("Procesando masivamente el documento..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo_pdf.getbuffer())
            ruta_temporal = tmp.name

        resultados = procesar_pdf_masivo(ruta_temporal)
        os.unlink(ruta_temporal)

    if resultados:
        df_final = pd.DataFrame(resultados)
        st.success(f"¡Procesamiento masivo exitoso! Se han consolidado {len(df_final)} casos en total.")
        
        st.subheader("Vista previa de la Matriz Maestra:")
        st.dataframe(df_final)

        nombre_excel = "Matriz_Operativa_S_PORTAL.xlsx"
        df_final.to_excel(nombre_excel, index=False)

        with open(nombre_excel, "rb") as f:
            st.download_button(
                label="📥 Descargar Archivo Excel Consolidado Maestro",
                data=f,
                file_name=nombre_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.error("No se pudieron extraer datos válidos del PDF. Verifica que sea el reporte de listado general correcto.")
else:
    st.info("Por favor, sube tu archivo PDF de listado general de S.PORTAL para comenzar.")
