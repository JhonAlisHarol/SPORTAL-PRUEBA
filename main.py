import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Masivo de Incidentes S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo de Reportes S.PORTAL")
st.write("Extracción estructurada por columnas: Creación, Horas (1 a 4) y Reportes (1 a 4) ordenados en Excel.")

def extraer_datos_pdf(ruta_pdf):
    """Extrae y separa cronológicamente las horas y los comentarios de la bitácora del PDF."""
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

        # 1. Datos Generales de la Cabecera[cite: 16]
        match_incidente = re.search(r'(P\d{10,12})', texto_completo)
        if match_incidente:
            datos["Incidente"] = match_incidente.group(1)

        match_creacion = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})', texto_completo)
        if match_creacion:
            datos["Creación"] = match_creacion.group(1)

        match_zona = re.search(r'\b\d{1,2}[A-Z]{1,3}\b', texto_completo)
        if match_zona:
            datos["Zona"] = match_zona.group(0)

        for op in ["ENRIQUE CACERES", "VALERY VELASQUEZ", "LEONARDO CASASOLA", "IVETTE CIERHART", "JOAQUIN CHI", "DALLA TREJOS", "RICARDO EMILIO", "HERMOGENES SANJUR"]:
            if op in texto_completo.upper():
                datos["Operador"] = op
                break

        if "Alteracion de la Convivencia" in texto_completo:[cite: 16]
            datos["Tipo"] = "Alteracion de la Convivencia Pacífica"
            datos["Subtipo"] = "Riña y Escándalo"
        elif "Arma de Fuego" in texto_completo:
            datos["Tipo"] = "Arma de Fuego"
            datos["Subtipo"] = "Posesión Ilegal / Detonaciones"
        elif "Violencia de Genero" in texto_completo or "Violencia Doméstica" in texto_completo:
            datos["Tipo"] = "Violencia de Género"
            datos["Subtipo"] = "Violencia Doméstica"
        elif "Robo" in texto_completo:
            datos["Tipo"] = "Robo"
            datos["Subtipo"] = "Robo Simple"
        else:
            datos["Tipo"] = "Incidente General S.PORTAL"
            datos["Subtipo"] = "N/A"

        match_ubi = re.search(r'(COORDENADAS\s+XY\([^\)]+\))', texto_completo, re.IGNORECASE)
        if match_ubi:[cite: 16]
            datos["Ubicación"] = match_ubi.group(1)
        else:
            datos["Ubicación"] = "N/A"

        # 2. Extracción secuencial de las horas y comentarios de la bitácora[cite: 16, 17]
        # Buscamos todas las fechas/horas con formato dd/mm/yyyy hh:mm:ss dentro del texto
        patron_fechas_horas = r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})'
        coincidencias_fechas = list(re.finditer(patron_fechas_horas, texto_completo))

        # Omitimos la primera coincidencia si es la fecha de cabecera/creación y nos enfocamos en la bitácora
        horas_bitacora = []
        for m in coincidencias_fechas:
            fh = m.group(1)
            # Evitamos duplicar la fecha exacta de creación inicial si aparece al inicio de la tabla
            if fh != datos["Creación"] or len(horas_bitacora) > 0:
                if fh not in horas_bitacora:
                    horas_bitacora.append(fh)

        # Asignamos hasta 4 horas de bitácora secuencialmente
        if len(horas_bitacora) > 0:
            datos["Hora 1"] = horas_bitacora[0] if len(horas_bitacora) > 0 else ""
            datos["Hora 2"] = horas_bitacora[1] if len(horas_bitacora) > 1 else ""
            datos["Hora 3"] = horas_bitacora[2] if len(horas_bitacora) > 2 else ""
            datos["Hora 4"] = horas_bitacora[3] if len(horas_bitacora) > 3 else ""

        # Extracción y separación de los bloques de comentarios (Reportes 1 al 4)
        # Limpiamos el texto para seccionarlo por bloques lógicos
        lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
        
        # Recopilamos fragmentos de texto ubicados después de la sección de bitácora
        bloques_reportes = []
        texto_acumulado = ""
        capturando = False

        for linea in lineas:
            if "Bitacora Incidente" in linea:
                capturando = True
                continue
            if capturando:
                if "SISTEMA NACIONAL DE EMERGENCIAS" in linea or "Fecha de emisión" in linea:
                    continue
                bloques_reportes.append(linea)

        texto_unido = " ".join(bloques_reportes)

        # Dividimos de forma inteligente el texto de los comentarios en 4 partes proporcionales correspondientes a los reportes
        # O buscamos frases clave características del reporte que nos compartiste
        if "el alertante inidca" in texto_unido.lower():
            partes = texto_unido.split("Comentario Del Usuario")
            for idx, parte in enumerate(partes[1:], start=1):
                if idx <= 4:
                    # Limpiamos textos repetitivos de cabeceras de usuario
                    texto_limpio = parte.replace("ENRIQUE CACERES", "").replace("VALERY VELASQUEZ", "").strip()
                    datos[f"Reporte {idx}"] = texto_limpio
        else:
            # Fallback general si la estructura varía ligeramente
            if len(bloques_reportes) > 0:
                datos["Reporte 1"] = " ".join(bloques_reportes[:int(len(bloques_reportes)/4) or 1])
                datos["Reporte 2"] = " ".join(bloques_reportes[int(len(bloques_reportes)/4):int(len(bloques_reportes)/2) or 2])
                datos["Reporte 3"] = " ".join(bloques_reportes[int(len(bloques_reportes)/2):int(len(bloques_reportes)*3/4) or 3])
                datos["Reporte 4"] = " ".join(bloques_reportes[int(len(bloques_reportes)*3/4):])

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
    st.info(f"Se han cargado {len(archivos_subidos)} archivos. Organizando horas y reportes...")
    
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
        
        st.success("¡Estructuración de datos completada con éxito!")
        
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
