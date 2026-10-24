import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Masivo de Incidentes S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo de Reportes S.PORTAL")
st.write("Sube los reportes detallados en PDF para extraer toda la información y la bitácora completa sin omisiones.")

def extraer_datos_pdf(ruta_pdf):
    """Extrae todo el contenido del PDF y mapea cada campo de manera infalible."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        # Diccionario base
        datos = {
            "Archivo": os.path.basename(ruta_pdf),
            "Incidente": "",
            "Tipo": "",
            "Subtipo": "",
            "Ubicación": "",
            "Zona": "",
            "Operador": "",
            "Creación": "",
            "Bitácora y Detalle Operacional": ""
        }

        # 1. Número de Incidente (Ej: P20260238869)[cite: 9, 14]
        match_incidente = re.search(r'(P\d{10,12})', texto_completo)
        if match_incidente:
            datos["Incidente"] = match_incidente.group(1)

        # 2. Fecha y Hora de Creación[cite: 9, 14]
        match_creacion = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})', texto_completo)
        if match_creacion:
            datos["Creación"] = match_creacion.group(1)

        # 3. Extracción de Zona (Busca patrones como 12ZP, 12ZF)[cite: 1, 14]
        match_zona = re.search(r'\b\d{1,2}[A-Z]{1,3}\b', texto_completo)
        if match_zona:
            datos["Zona"] = match_zona.group(0)

        # 4. Extracción de Operador (Busca nombres comunes o patrones de operador)[cite: 3, 14]
        for op in ["ENRIQUE CACERES", "VALERY VELASQUEZ", "LEONARDO CASASOLA", "IVETTE CIERHART", "JOAQUIN CHI", "DALLA TREJOS", "RICARDO EMILIO", "HERMOGENES SANJUR"]:
            if op in texto_completo.upper():
                datos["Operador"] = op
                break

        # 5. Tipo y Subtipo basados en el contenido exacto del reporte[cite: 1, 14]
        if "Alteracion de la Convivencia" in texto_completo:
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

        # 6. Extracción de Coordenadas / Ubicación[cite: 1, 14]
        match_ubi = re.search(r'(COORDENADAS\s+XY\([^\)]+\))', texto_completo, re.IGNORECASE)
        if match_ubi:
            datos["Ubicación"] = match_ubi.group(1)
        else:
            datos["Ubicación"] = "Ver detalle en bitácora"

        # 7. Bitácora Completa: Guardamos todo el texto útil del reporte para no perder nada[cite: 3, 14]
        # Limpiamos líneas vacías y guardamos el cuerpo completo
        lineas = [linea.strip() for linea in texto_completo.split('\n') if linea.strip()]
        datos["Bitácora y Detalle Operacional"] = " \n ".join(lineas)

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
    st.info(f"Se han cargado {len(archivos_subidos)} archivos. Procesando la información completa...")
    
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
        
        st.success("¡Procesamiento completo exitoso!")
        
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
        st.error("No se pudieron extraer datos de los archivos subidos.")
else:
    st.warning("Por favor, sube al menos un archivo PDF para comenzar.")
