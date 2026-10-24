import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador de Incidentes S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo de Reportes S.PORTAL")
st.write("Sube los reportes detallados en PDF del sistema de emergencias para consolidarlos automáticamente en un archivo de Excel estructurado.")

def extraer_datos_pdf(ruta_pdf):
    """Extrae la información estructurada de un reporte individual de S.Portal."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        # Diccionario base para los campos extraídos
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

        # 2. Fecha de Creación (Ej: 23/10/2026 0:01:03)[cite: 9]
        match_creacion = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})', texto_completo)
        if match_creacion:
            datos["Creación"] = match_creacion.group(1)

        # 3. Extracción y limpieza de la bitácora de comentarios y acciones[cite: 9]
        lineas = texto_completo.split('\n')
        bitacora_acumulada = []
        capturando = False
        
        for linea in lineas:
            if "Bitacora Incidente" in linea or "Comentario" in linea:
                capturando = True
                continue
            if capturando and linea.strip():
                bitacora_acumulada.append(linea.strip())

        datos["Bitácora y Acciones Policiales"] = " | ".join(bitacora_acumulada)

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
    st.info(f"Se han cargado {len(archivos_subidos)} archivos. Procesando información...")
    
    lista_resultados = []
    
    # Barra de progreso visual
    barra_progreso = st.progress(0)
    total_archivos = len(archivos_subidos)

    for i, archivo in enumerate(archivos_subidos):
        # Guardamos temporalmente cada archivo subido para que PyPDF pueda leerlo
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(archivo.getbuffer())
            ruta_temporal = tmp.name

        # Extraemos los datos
        info_caso = extraer_datos_pdf(ruta_temporal)
        if info_caso:
            lista_resultados.append(info_caso)

        # Limpiamos el archivo temporal
        os.unlink(ruta_temporal)
        
        # Actualizamos la barra de progreso
        barra_progreso.progress((i + 1) / total_archivos)

    if lista_resultados:
        df_resultado = pd.DataFrame(lista_resultados)
        
        st.success("¡Procesamiento completado con éxito!")
        
        # Mostrar una vista previa de los datos procesados en la pantalla
        st.subheader("Vista previa de los casos consolidados:")
        st.dataframe(df_resultado)

        # Preparar archivo Excel para descarga
        nombre_excel = "Estudio_Operativo_Incidentes.xlsx"
        df_resultado.to_excel(nombre_excel, index=False)

        with open(nombre_excel, "rb") as f:
            st.download_button(
                label="📥 Descargar Archivo Excel Maestro",
                data=f,
                file_name=nombre_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.error("No se pudieron extraer datos de los archivos subidos. Verifica que sean los reportes correctos.")
else:
    st.warning("Por favor, sube al menos un archivo PDF para comenzar.")
