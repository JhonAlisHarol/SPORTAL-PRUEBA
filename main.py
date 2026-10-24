import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Masivo de Incidentes S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo de Reportes S.PORTAL")
st.write("Extracción de datos: Fechas y Horas separadas + Captura directa de los Reportes de la Bitácora.")

def extraer_datos_pdf(ruta_pdf):
    """Extrae datos de cabecera, separa fechas/horas y captura con precisión los 4 reportes de la bitácora."""
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
            "Fecha Creación": "",
            "Hora Creación": "",
            "Fecha 1": "", "Hora 1": "", "Reporte 1": "",
            "Fecha 2": "", "Hora 2": "", "Reporte 2": "",
            "Fecha 3": "", "Hora 3": "", "Reporte 3": "",
            "Fecha 4": "", "Hora 4": "", "Reporte 4": ""
        }

        # 1. Cabecera general
        match_incidente = re.search(r'(P\d{10,12})', texto_completo)
        if match_incidente:
            datos["Incidente"] = match_incidente.group(1)

        match_creacion = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})', texto_completo)
        if match_creacion:
            datos["Fecha Creación"] = match_creacion.group(1)
            datos["Hora Creación"] = match_creacion.group(2)

        lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]

        for i, linea in enumerate(lineas):
            if re.search(r'\b\d{1,2}[A-Z]{1,3}\b', linea) and len(linea) <= 6 and not datos["Zona"]:
                if "ZP" in linea or "ZF" in linea:
                    datos["Zona"] = linea

            if "COORDENADAS" in linea.upper() or "UBICACION" in linea.upper():
                ubi = linea
                if i + 1 < len(lineas) and "(" in lineas[i+1]:
                    ubi += " " + lineas[i+1]
                datos["Ubicación"] = ubi

        if len(lineas) > 5:
            for idx, l in enumerate(lineas[:15]):
                if datos["Incidente"] in l:
                    if idx + 1 < len(lineas):
                        datos["Tipo"] = lineas[idx + 1]
                    if idx + 2 < len(lineas):
                        datos["Subtipo"] = lineas[idx + 2]
                    break

        if not datos["Tipo"]:
            datos["Tipo"] = "Alteracion de la Convivencia Pacifica"
            datos["Subtipo"] = "Riña y Escándalo"

        # 2. Extracción de Fechas y Horas (1 a 4)
        patron_fh = r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})'
        coincidencias = list(re.finditer(patron_fh, texto_completo))

        fechas_horas_lista = []
        for m in coincidencias:
            f_val = m.group(1)
            h_val = m.group(2)
            combinado = (f_val, h_val)
            if combinado not in fechas_horas_lista:
                fechas_horas_lista.append(combinado)

        idx_inicio = 1 if len(fechas_horas_lista) > 1 and fechas_horas_lista[0][1] == datos["Hora Creación"] else 0
        
        slot = 1
        for j in range(idx_inicio, len(fechas_horas_lista)):
            if slot <= 4:
                f_item, h_item = fechas_horas_lista[j]
                datos[f"Fecha {slot}"] = f_item
                datos[f"Hora {slot}"] = h_item
                slot += 1

        # 3. Captura directa y robusta de los Reportes de la Bitácora
        # Buscamos todo el texto que se encuentra desde "Bitacora Incidente" en adelante
        texto_lower = texto_completo.lower()
        pos_bitacora = texto_lower.find("bitacora incidente")
        
        if pos_bitacora != -1:
            texto_bitacora_crudo = texto_completo[pos_bitacora:]
            # Limpiamos textos innecesarios del pie de página si los hay
            texto_bitacora_crudo = texto_bitacora_crudo.replace("SISTEMA NACIONAL DE EMERGENCIAS", "").replace("Fecha de emisión:", "")
            
            # Dividimos el bloque en párrafos o líneas de comentarios útiles
            lineas_bitacora = [l.strip() for l in texto_bitacora_crudo.split('\n') if len(l.strip()) > 10]
            
            # Asignamos de forma directa los textos encontrados a los 4 reportes
            for idx_rep in range(1, 5):
                if idx_rep - 1 < len(lineas_bitacora):
                    datos[f"Reporte {idx_rep}"] = lineas_bitacora[idx_rep - 1]
        else:
            # Fallback por si la etiqueta varía
            datos["Reporte 1"] = "Ver detalle en el reporte original PDF"

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
    st.info(f"Se han cargado {len(archivos_subidos)} archivos. Procesando horas y reportes...")
    
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
        
        script_summary = "Vista previa del Excel con Horas y Reportes:"
        st.subheader(script_summary)
        st.dataframe(df_resultado)

        nombre_excel = "Estudio_Operativo_Final.xlsx"
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
