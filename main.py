import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Masivo de Incidentes S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo de Reportes S.PORTAL")
st.write("Estructuración avanzada: Separación exacta de Fechas, Horas y asociación directa de cada Comentario en su respectivo Reporte (1 al 4).")

def extraer_datos_pdf(ruta_pdf):
    """Extrae cabecera, separa fechas/horas y asocia cada comentario de la bitácora a su respectivo reporte."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        # Diccionario base con la estructura exacta
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

        # 2. Extracción de todas las ocurrencias de Fecha y Hora en el texto
        patron_fh = r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})'
        matches = list(re.finditer(patron_fh, texto_completo))

        # Almacenamos las marcas de tiempo encontradas con sus posiciones de caracteres
        marcas_tiempo = []
        for m in matches:
            f_val = m.group(1)
            h_val = m.group(2)
            pos = m.start()
            # Evitamos duplicar la primera si es exactamente la fecha/hora de creación inicial
            if not (f_val == datos["Fecha Creación"] and h_val == datos["Hora Creación"] and len(marcas_tiempo) == 0):
                marcas_tiempo.append({"fecha": f_val, "hora": h_val, "pos": pos})

        # Asignamos hasta 4 marcas de tiempo secuenciales (Fecha y Hora 1 a 4)
        for idx_m, marca in enumerate(marcas_tiempo[:4], start=1):
            datos[f"Fecha {idx_m}"] = marca["fecha"]
            datos[f"Hora {idx_m}"] = marca["hora"]

        # 3. Asociación precisa de los comentarios (Reportes 1 a 4) basados en las posiciones del texto
        for idx_m in range(len(marcas_tiempo)):
            num_rep = idx_m + 1
            if num_rep > 4:
                break
            
            inicio_texto = marcas_tiempo[idx_m]["pos"] + len(f"{marcas_tiempo[idx_m]['fecha']} {marcas_tiempo[idx_m]['hora']}")
            
            # El fin del comentario es donde empieza la siguiente marca de tiempo, o el final del documento
            if idx_m + 1 < len(marcas_tiempo):
                fin_texto = marcas_tiempo[idx_m + 1]["pos"]
            else:
                fin_texto = len(texto_completo)

            # Extraemos el fragmento de texto entre esta marca y la siguiente
            fragmento = texto_completo[inicio_texto:fin_texto]
            
            # Limpiamos etiquetas de usuarios repetidas y saltos de línea excesivos
            fragmento_limpio = fragmento.replace("ENRIQUE CACERES", "").replace("VALERY VELASQUEZ", "").replace("Comentario Del Usuario", "").replace("\n", " ").strip()
            
            # Guardamos el comentario en su respectivo reporte
            datos[f"Reporte {num_rep}"] = fragmento_limpio

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
    st.info(f"Se han cargado {len(archivos_subidos)} archivos. Procesando horas y asociando reportes...")
    
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
        
        st.subheader("Vista previa del Excel con Fechas, Horas y Reportes Asociados:")
        st.dataframe(df_resultado)

        nombre_excel = "Estudio_Operativo_Final_Preciso.xlsx"
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
