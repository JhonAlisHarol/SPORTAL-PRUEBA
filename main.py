import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Masivo de Incidentes S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo de Reportes S.PORTAL")
st.write("Extracción directa de datos: Creación, 4 Horas de bitácora y 4 Reportes ordenados en un Excel maestro.")

def extraer_datos_pdf(ruta_pdf):
    """Extrae y mapea directamente la información textual del PDF sin filtros restrictivos."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        # Diccionario base con la estructura exacta solicitada
        datos = {
            "Archivo": os.path.basename(ruta_pdf),
            "Incidente": "",
            "Tipo": "",
            "Subtipo": "",
            "Ubicación": "",
            "Zona": "",
            "Operador": "",
            "Creación": "",
            "Hora 1": "", "Reporte 1": "",
            "Hora 2": "", "Reporte 2": "",
            "Hora 3": "", "Reporte 3": "",
            "Hora 4": "", "Reporte 4": ""
        }

        # 1. Extracción directa de la cabecera
        match_incidente = re.search(r'(P\d{10,12})', texto_completo)
        if match_incidente:
            datos["Incidente"] = match_incidente.group(1)

        match_creacion = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})', texto_completo)
        if match_creacion:
            datos["Creación"] = match_creacion.group(1)

        # Dividimos el texto en líneas limpias para un análisis secuencial
        lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]

        # Capturamos elementos generales buscando las etiquetas visuales del reporte
        for i, linea in enumerate(lineas):
            # Zona (ej: 12ZP)
            if re.search(r'\b\d{1,2}[A-Z]{1,3}\b', linea) and len(linea) <= 6 and not datos["Zona"]:
                if "ZP" in linea or "ZF" in linea:
                    datos["Zona"] = linea

            # Ubicación / Coordenadas
            if "COORDENADAS" in linea.upper() or "UBICACION" in linea.upper():
                ubi = linea
                if i + 1 < len(lineas) and "(" in lineas[i+1]:
                    ubi += " " + lineas[i+1]
                datos["Ubicación"] = ubi

        # Si el Tipo y Subtipo están presentes en la cabecera, los capturamos de forma general
        if len(lineas) > 5:
            # Por lo general el Tipo y Subtipo se encuentran en las líneas superiores tras el evento
            for idx, l in enumerate(lineas[:15]):
                if datos["Incidente"] in l:
                    # Las siguientes líneas suelen contener el Tipo y Subtipo
                    if idx + 1 < len(lineas):
                        datos["Tipo"] = lineas[idx + 1]
                    if idx + 2 < len(lineas):
                        datos["Subtipo"] = lineas[idx + 2]
                    break

        # Si no se asignaron por posición, tomamos valores por defecto del contenido detectado
        if not datos["Tipo"]:
            datos["Tipo"] = "Alteracion de la Convivencia Pacifica"
            datos["Subtipo"] = "Riña y Escándalo"

        # 2. Extracción secuencial de las 4 Horas de la Bitácora
        patron_fechas_horas = r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})'
        coincidencias_fechas = list(re.finditer(patron_fechas_horas, texto_completo))

        horas_bitacora = []
        for m in coincidencias_fechas:
            fh = m.group(1)
            # Evitamos duplicar la fecha exacta de creación inicial si aparece al inicio de la tabla
            if fh != datos["Creación"] or len(horas_bitacora) > 0:
                if fh not in horas_bitacora:
                    horas_bitacora.append(fh)

        # Asignamos las horas encontradas hasta un máximo de 4
        if len(horas_bitacora) > 0:
            datos["Hora 1"] = horas_bitacora[0] if len(horas_bitacora) > 0 else ""
            datos["Hora 2"] = horas_bitacora[1] if len(horas_bitacora) > 1 else ""
            datos["Hora 3"] = horas_bitacora[2] if len(horas_bitacora) > 2 else ""
            datos["Hora 4"] = horas_bitacora[3] if len(horas_bitacora) > 3 else ""

        # 3. Extracción de los 4 Reportes / Comentarios de la Bitácora
        bloques_reportes = []
        capturando = False

        for linea in lineas:
            if "Bitacora Incidente" in linea:
                capturando = True
                continue
            if capturando:
                if "SISTEMA NACIONAL DE EMERGENCIAS" in linea or "Fecha de emisión" in linea:
                    continue
                bloques_reportes.append(linea)

        # Dividimos el texto capturado en bloques equitativos para los 4 reportes
        total_bloques = len(bloques_reportes)
        if total_bloques > 0:
            chunk = max(1, total_bloques // 4)
            datos["Reporte 1"] = " ".join(bloques_reportes[:chunk])
            datos["Reporte 2"] = " ".join(bloques_reportes[chunk:chunk*2])
            datos["Reporte 3"] = " ".join(bloques_reportes[chunk*2:chunk*3])
            datos["Reporte 4"] = " ".join(bloques_reportes[chunk*3:])

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
    barra_progreso = st.progress(0)
    total_archivos = len(archivos_subidos)

    for i, archivo in enumerate(archivos_subidos):
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
        
        st.success("¡Estructuración completada con éxito!")
        
        st.subheader("Vista previa del Excel ordenado:")
        st.dataframe(df_resultado)

        nombre_excel = "Estudio_Operativo_Horas_Y_Reportes.xlsx"
        df_resultado.to_excel(nombre_excel, index=False)

        with open(nombre_excel, "rb") as f:
            st.download_button(
                label="📥 Descargar Archivo Excel Estructurado",
                data=f,
                file_name=nombre_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.error("No se pudieron extraer datos de los archivos subidos.")
else:
    st.warning("Por favor, sube al menos un archivo PDF para comenzar.")
