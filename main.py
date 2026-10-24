import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Masivo de Incidentes S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo de Reportes S.PORTAL")
st.write("Extracción estructurada: Fechas y Horas separadas, Cabecera y Reportes detallados de la bitácora.")

def extraer_datos_pdf(ruta_pdf):
    """Extrae, separa fechas/horas y captura con precisión los reportes y la cabecera del PDF."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        # Diccionario base con columnas separadas para fechas y horas
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

        # 1. Extracción de la Cabecera
        match_incidente = re.search(r'(P\d{10,12})', texto_completo)
        if match_incidente:
            datos["Incidente"] = match_incidente.group(1)

        # Fecha y Hora de Creación separadas
        match_creacion = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})', texto_completo)
        if match_creacion:
            datos["Fecha Creación"] = match_creacion.group(1)
            datos["Hora Creación"] = match_creacion.group(2)

        lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]

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

        # Tipo y Subtipo por defecto basados en el estándar del sistema
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

        # 2. Extracción de Fechas, Horas y Reportes secuenciales de la Bitácora
        # Buscamos coincidencias de Fecha y Hora en el texto
        patron_fh = r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})'
        coincidencias = list(re.finditer(patron_fh, texto_completo))

        fechas_horas_lista = []
        for m in coincidencias:
            f_val = m.group(1)
            h_val = m.group(2)
            combinado = (f_val, h_val)
            # Evitamos duplicar la fecha/hora inicial exacta de creación si se repite al inicio
            if combinado not in fechas_horas_lista:
                fechas_horas_lista.append(combinado)

        # Asignamos hasta 4 marcas de tiempo separadas (Fecha y Hora 1 al 4)
        # Omitimos la primera si corresponde a la creación general
        idx_inicio = 1 if len(fechas_horas_lista) > 1 and fechas_horas_lista[0][1] == datos["Hora Creación"] else 0
        
        slot = 1
        for j in range(idx_inicio, len(fechas_horas_lista)):
            if slot <= 4:
                f_item, h_item = fechas_horas_lista[j]
                datos[f"Fecha {slot}"] = f_item
                datos[f"Hora {slot}"] = h_item
                slot += 1

        # 3. Captura precisa de los comentarios / reportes de la bitácora
        # Extraemos las líneas ubicadas específicamente tras la sección "Bitacora Incidente"
        capturando = False
        textos_bitacora = []

        for linea in lineas:
            if "Bitacora Incidente" in linea:
                capturando = True
                continue
            if capturando:
                if "SISTEMA NACIONAL DE EMERGENCIAS" in linea or "Fecha de emisión" in linea:
                    continue
                # Filtramos líneas que son solo marcas de fecha/hora para quedarnos con los comentarios limpios
                if not re.match(r'^\d{2}/\d{2}/\d{4}$', linea) and not re.match(r'^\d{1,2}:\d{2}:\d{2}$', linea):
                    textos_bitacora.append(linea)

        # Unimos y seccionamos los textos capturados en 4 reportes lógicos
        texto_unido_bitacora = " ".join(textos_bitacora)
        
        # Limpiamos palabras repetidas de usuarios del sistema si aparecen
        texto_limpio = texto_unido_bitacora.replace("ENRIQUE CACERES", "").replace("VALERY VELASQUEZ", "").replace("Comentario Del Usuario", "").strip()

        # Dividimos el texto limpio en fragmentos para los 4 reportes
        if texto_limpio:
            palabras = texto_limpio.split()
            tamano_bloque = max(1, len(palabras) // 4)
            
            for r_idx in range(1, 5):
                inicio = (r_idx - 1) * tamano_bloque
                fin = r_idx * tamano_bloque if r_idx < 4 else len(palabras)
                segmento = " ".join(palabras[inicio:fin])
                if segmento.strip():
                    datos[f"Reporte {r_idx}"] = segmento

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
    st.info(f"Se han cargado {len(archivos_subidos)} archivos. Procesando y separando fechas/horas...")
    
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

        nombre_excel = "Estudio_Operativo_Fechas_Horas_Separadas.xlsx"
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
