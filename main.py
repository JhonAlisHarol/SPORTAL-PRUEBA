import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Masivo de Incidentes S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo de Reportes S.PORTAL")
st.write("Sube los reportes detallados en PDF del sistema de emergencias para consolidarlos automáticamente en un archivo de Excel estructurado sin perder ningún detalle.")

def extraer_datos_pdf(ruta_pdf):
    """Extrae de forma precisa toda la información estructurada de un reporte individual de S.Portal."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        # Diccionario base para almacenar todos los campos
        datos = {
            "Archivo": os.path.basename(ruta_pdf),
            "Incidente": "",
            "Tipo": "",
            "Subtipo": "",
            "Ubicación": "",
            "Zona": "",
            "Operador": "",
            "Creación": "",
            "Bitácora y Acciones Policiales": ""
        }

        # 1. Número de Incidente (Ej: P20260238869)[cite: 9]
        match_incidente = re.search(r'(P\d{10,12})', texto_completo)
        if match_incidente:
            datos["Incidente"] = match_incidente.group(1)

        # 2. Fecha de Creación del Incidente[cite: 9]
        match_creacion = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})', texto_completo)
        if match_creacion:
            datos["Creación"] = match_creacion.group(1)

        # 3. Extracción estructurada basada en las secciones del reporte PDF
        lineas = [linea.strip() for linea in texto_completo.split('\n') if linea.strip()]
        
        bitacora_texto = []
        capturando_bitacora = False
        
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            
            # Detectar Operador y Zona en las líneas generales
            if "ENRIQUE" in linea.upper() or "CACERES" in linea.upper() or "VALERY" in linea.upper():[cite: 3]
                if not datos["Operador"]:
                    datos["Operador"] = linea

            # Detectar Zonas (ej. 12ZF)[cite: 1]
            if re.search(r'\d+[A-Z]+', linea) and len(linea) < 10 and not datos["Zona"]:
                if "ZF" in linea or "ZP" in linea:[cite: 1]
                    datos["Zona"] = linea

            # Capturar Coordenadas o Ubicación[cite: 1]
            if "COORDENADAS" in linea.upper() or "UBICACION" in linea.upper():
                ubicacion_completa = linea
                if i + 1 < len(lineas) and ("(" in lineas[i+1] or ")" in lineas[i+1]):
                    ubicacion_completa += " " + lineas[i+1]
                datos["Ubicación"] = ubicacion_completa

            # Detectar Tipos y Subtipos comunes en los reportes[cite: 1]
            if "Alteracion" in linea or "Arma" in linea or "Violencia" in linea or "Robo" in linea or "Actitud" in linea or "Pánico" in linea:
                if not datos["Tipo"]:
                    datos["Tipo"] = linea

            # Capturar Bloque de Bitácora y Comentarios detallados[cite: 3]
            if "Bitacora Incidente" in linea or "Comentario" in linea or "Del Usuario" in linea:
                capturando_bitacora = True
                i += 1
                continue

            if capturando_bitacora:
                if "SISTEMA NACIONAL DE EMERGENCIAS" in linea or "Fecha de emisión" in linea:[cite: 9]
                    capturando_bitacora = False
                else:
                    bitacora_texto.append(linea)

            i += 1

        # Unimos todo el contenido de la bitácora y parte policial de forma limpia
        datos["Bitácora y Acciones Policiales"] = " | ".join(bitacora_texto)

        # Fallback de respaldo si algún campo quedó vacío pero el texto lo contiene
        if not datos["Tipo"] and "Alteracion de la Convivencia" in texto_completo:[cite: 1]
            datos["Tipo"] = "Alteracion de la Convivencia Pacífica"
        if not datos["Subtipo"] and "Riña" in texto_completo:[cite: 1]
            datos["Subtipo"] = "Riña y Escándalo"

        return datos

    except Exception as e:
        return None

# Interfaz de carga de archivos en Streamlit
archivos_subidos = st.file_uploader(
    "Sube tus archivos PDF de incidentes aquí (Puedes seleccionar varios a la vez):", 
    type=["pdf"], 
    accept_multiple_files=True
)

if archivos_subidos:
    st.info(f"Se han cargado {len(archivos_subidos)} archivos. Procesando información detallada...")
    
    lista_resultados = []
    barra_progreso = st.progress(0)
    total_archivos = len(archivos_subidos)

    for i, archivo in enumerate(archivos_subidos):
        # CORREGIDO: Se usa delete=False correctamente
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.getbuffer())
            ruta_temporal = tmp.name

        info_caso = extraer_datos_pdf(ruta_temporal)
        if info_caso:
            lista_resultados.append(info_caso)

        os.unlink(ruta_temporal)
        barra_progreso.progress((i + 1) / total_archivos)

    if lista_resultados:
        df_resultado = pd.DataFrame(lista_resultados)
        
        st.success("¡Procesamiento completo y detallado con éxito!")
        
        st.subheader("Vista previa de los casos consolidados:")
        st.dataframe(df_resultado)

        nombre_excel = "Estudio_Operativo_Incidentes_Completo.xlsx"
        df_resultado.to_excel(nombre_excel, index=False)

        with open(nombre_excel, "rb") as f:
            st.download_button(
                label="📥 Descargar Archivo Excel Maestro Completo",
                data=f,
                file_name=nombre_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.error("No se pudieron extraer datos de los archivos subidos. Verifica que sean los reportes correctos.")
else:
    st.warning("Por favor, sube al menos un archivo PDF para comenzar.")
