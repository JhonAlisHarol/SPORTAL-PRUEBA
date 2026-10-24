import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Masivo de Listados S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo de Reportes S.PORTAL")
st.write("Sube el PDF de listado general (con cientos de casos) para extraer y consolidar automáticamente todos los incidentes en un Excel estructurado.")

def procesar_pdf_listado(ruta_pdf):
    """Procesa un PDF masivo de listado general y extrae fila por fila todos los incidentes."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        # Dividir todo el texto en líneas limpias
        lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]

        casos_extraidos = []
        
        # Recorremos el texto buscando patrones de números de incidente (Ej: P20260238869)
        # y capturando la información circundante en el listado tabular
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            
            # Detectar código de incidente
            match_inc = re.search(r'(P\d{10,12})', linea)
            if match_inc:
            if match_inc:
                incidente_id = match_inc.group(1)
                
                # Valores por defecto para la fila
                tipo = "N/A"
                subtipo = "N/A"
                zona = "N/A"
                fecha_creacion = ""
                hora_creacion = ""
                operador = "N/A"
                
                # Buscamos en las líneas siguientes inmediatas los datos de la fila del reporte tabular
                contexto_bloque = " ".join(lineas[i:i+10])
                
                # Extraer Fecha y Hora de Creación (dd/mm/yyyy hh:mm:ss o similar)
                match_fh = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})', contexto_bloque)
                if match_fh:
                    fecha_creacion = match_fh.group(1)
                    hora_creacion = match_fh.group(2)
                
                # Extraer Zona (Patrones como 12ZP, 8ZP, TRAN, etc.)
                match_zn = re.search(r'\b(\d{1,2}[A-Z]{1,3}|TRAN)\b', contexto_bloque)
                if match_zn:
                    zona = match_zn.group(1)

                # Extraer Operador por nombres frecuentes en el sistema
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

                # Capturar Tipo y Subtipo basado en palabras clave comunes del S.PORTAL
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

                # Guardamos el caso estructurado
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

# Interfaz de carga de archivos en Streamlit
archivos_subidos = st.file_uploader(
    "Sube el PDF de listado general de S.PORTAL (ej. el reporte consolidado de 21 páginas):", 
    type=["pdf"], 
    accept_multiple_files=False
)

if archivos_subidos:
    st.info("Procesando el listado general y extrayendo todos los incidentes...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(archivos_subidos.getbuffer())
        ruta_temporal = tmp.name

    lista_resultados = procesar_pdf_listado(ruta_temporal)
    os.unlink(ruta_temporal)

    if lista_resultados:
        df_resultado = pd.DataFrame(lista_resultados)
        
        st.success(f"¡Procesamiento masivo exitoso! Se han extraído {len(df_resultado)} casos del PDF.")
        
        st.subheader("Vista previa de los casos consolidados:")
        st.dataframe(df_resultado)

        nombre_excel = "Estudio_Operativo_Listado_Maestro.xlsx"
        df_resultado.to_excel(nombre_excel, index=False)

        with open(nombre_excel, "rb") as f:
            st.download_button(
                label="📥 Descargar Archivo Excel Maestro Consolidado",
                data=f,
                file_name=nombre_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.error("No se pudieron extraer incidentes del PDF. Asegúrate de subir el reporte de listado general correcto.")
else:
    st.warning("Por favor, sube el PDF de listado general de S.PORTAL para comenzar.")
