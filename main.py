import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Masivo de Incidentes S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo y Captura S.PORTAL (Alta Velocidad)")
st.write("Estructuración avanzada optimizada: Carga masiva de PDFs locales para descarga directa en Excel maestro.")

# 1. Definir la estructura base de la tabla vacía con todas las columnas requeridas (visible siempre)
columnas_base = [
    "Archivo", "Incidente", "Tipo", "Subtipo", "Ubicación", "Zona", "Operador",
    "Fecha Creación", "Hora Creación",
    "Fecha 1", "Hora 1", "Reporte 1",
    "Fecha 2", "Hora 2", "Reporte 2",
    "Fecha 3", "Hora 3", "Reporte 3",
    "Fecha 4", "Hora 4", "Reporte 4"
]

st.subheader("📋 Vista Previa de la Tabla Maestra (Vacía)")
df_vacio = pd.DataFrame(columns=columnas_base)
st.dataframe(df_vacio, use_container_width=True)
st.markdown("---")

def extraer_datos_pdf_rapido(ruta_pdf, nombre_archivo_original=""):
    """Extracción optimizada extrayendo dinámicamente Tipo, Subtipo y Ubicación oficial para el Excel."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        datos = {
            "Archivo": nombre_archivo_original if nombre_archivo_original else os.path.basename(ruta_pdf),
            "Incidente": "",
            "Tipo": "",
            "Subtipo": "",
            "Ubicación": "N/A",
            "Zona": "N/A",
            "Operador": "N/A",
            "Fecha Creación": "",
            "Hora Creación": "",
            "Fecha 1": "", "Hora 1": "", "Reporte 1": "",
            "Fecha 2": "", "Hora 2": "", "Reporte 2": "",
            "Fecha 3": "", "Hora 3": "", "Reporte 3": "",
            "Fecha 4": "", "Hora 4": "", "Reporte 4": ""
        }

        # Extracción de Incidente
        match_incidente = re.search(r'(P\d{10,12})', texto_completo)
        if match_incidente:
            datos["Incidente"] = match_incidente.group(1)
        elif re.search(r'(P\d{10,12})', datos["Archivo"]):
            datos["Incidente"] = re.search(r'(P\d{10,12})', datos["Archivo"]).group(1)

        lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]

        # Lista de operadores frecuentes del C5
        operadores_conocidos = [
            "ENRIQUE CACERES", "VALERY VELASQUEZ", "LEONARDO CASASOLA", 
            "IVETTE GIERHART", "JOAQUIN CHI", "DALILA TREJOS", 
            "HERMOGENES SANJUR", "ANTONIO PATRICIO", "RICARDO EMILIO"
        ]

        # Detección de Zona y Operador
        for i, linea in enumerate(lineas):
            linea_up = linea.upper()
            
            for op in operadores_conocidos:
                if op in linea_up:
                    datos["Operador"] = op
                    break
            
            if (re.search(r'\b\d{0,2}[A-Z]{1,3}\b', linea) and len(linea) <= 6) and ("ZP" in linea_up or "ZF" in linea_up or "ZONA" in linea_up):
                if datos["Zona"] == "N/A":
                    datos["Zona"] = linea

        # Extracción dinámica y precisa de Tipo y Subtipo buscando las etiquetas oficiales en el PDF
        for i, linea in enumerate(lineas):
            linea_up = linea.upper()
            
            if "TIPO" in linea_up and i + 1 < len(lineas) and datos["Tipo"] == "":
                candidato_tipo = lineas[i + 1]
                if candidato_tipo not in ["Subtipo", "Ubicacion", "Zona", "Operador"]:
                    datos["Tipo"] = candidato_tipo

            if "SUBTIPO" in linea_up and i + 1 < len(lineas) and datos["Subtipo"] == "":
                candidato_sub = lineas[i + 1]
                if candidato_sub not in ["Ubicacion", "Zona", "Operador", "Creacion"]:
                    datos["Subtipo"] = candidato_sub

        # Respaldo por posición si las etiquetas directas varían
        if datos["Tipo"] == "" and len(lineas) > 5:
            for idx, l in enumerate(lineas[:15]):
                if datos["Incidente"] in l:
                    if idx + 1 < len(lineas):
                        datos["Tipo"] = lineas[idx + 1]
                    if idx + 2 < len(lineas):
                        datos["Subtipo"] = lineas[idx + 2]
                    break

        # Capturar la ubicación exacta tipo COORDENADAS XY (...) tal como viene en el PDF
        match_coords = re.search(r'(COORDENADAS\s+XY\s*\([^)]+\))', texto_completo, re.IGNORECASE)
        if match_coords:
            datos["Ubicación"] = match_coords.group(1).replace("\n", " ")
        else:
            for i, linea in enumerate(lineas):
                if "COORDENADAS" in linea.upper():
                    ubi_txt = linea
                    if i + 1 < len(lineas) and ")" in lineas[i+1]:
                        ubi_txt += " " + lineas[i+1]
                    datos["Ubicación"] = ubi_txt
                    break

        # Extracción de Fechas, Horas y Reportes de la bitácora
        patron_fh = r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})'
        matches = list(re.finditer(patron_fh, texto_completo))

        if matches:
            datos["Fecha Creación"] = matches[0].group(1)
            datos["Hora Creación"] = matches[0].group(2)

        marcas_tiempo = []
        for m in matches:
            f_val = m.group(1)
            h_val = m.group(2)
            pos = m.start()
            if not (f_val == datos["Fecha Creación"] and h_val == datos["Hora Creación"] and len(marcas_tiempo) == 0):
                marcas_tiempo.append({"fecha": f_val, "hora": h_val, "pos": pos})

        for idx_m, marca in enumerate(marcas_tiempo[:4], start=1):
            datos[f"Fecha {idx_m}"] = marca["fecha"]
            datos[f"Hora {idx_m}"] = marca["hora"]

        for idx_m in range(len(marcas_tiempo)):
            num_rep = idx_m + 1
            if num_rep > 4:
                break
            inicio_texto = marcas_tiempo[idx_m]["pos"] + len(f"{marcas_tiempo[idx_m]['fecha']} {marcas_tiempo[idx_m]['hora']}")
            fin_texto = marcas_tiempo[idx_m + 1]["pos"] if idx_m + 1 < len(marcas_tiempo) else len(texto_completo)
            fragmento = texto_completo[inicio_texto:fin_texto]
            
            fragmento_limpio = fragmento.replace("Comentario Del Usuario", "").replace("\n", " ").strip()
            if datos["Operador"] != "N/A":
                fragmento_limpio = fragmento_limpio.replace(datos["Operador"], "").strip()
            
            datos[f"Reporte {num_rep}"] = fragmento_limpio

        if not marcas_tiempo and texto_completo:
            datos["Reporte 1"] = texto_completo[:500].replace("\n", " ").strip()

        # Respaldo para Operador si aparece en el texto general
        if datos["Operador"] == "N/A":
            for op in operadores_conocidos:
                if op in texto_completo.upper():
                    datos["Operador"] = op
                    break

        return datos
    except Exception as e:
        return None

# Componente de carga masiva de alta velocidad
archivos_subidos = st.file_uploader(
    "Selecciona o arrastra tu lote masivo de PDFs desde la computadora (Soporta miles de archivos de golpe):", 
    type=["pdf"], 
    accept_multiple_files=True
)

if archivos_subidos:
    cantidad_subida = len(archivos_subidos)
    st.info(f"Se han cargado {cantidad_subida} archivos en memoria. Listo para captura de alta velocidad.")
    
    if st.button("🚀 Ejecutar Captura Masiva y Generar Excel"):
        lista_resultados = []
        barra_progreso = st.progress(0)
        total_archivos = len(archivos_subidos)

        for i, archivo in enumerate(archivos_subidos):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(archivo.getbuffer())
                ruta_temporal = tmp.name

            info_caso = extraer_datos_pdf_rapido(ruta_temporal, archivo.name)
            if info_caso:
                lista_resultados.append(info_caso)

            os.unlink(ruta_temporal)
            barra_progreso.progress((i + 1) / total_archivos)

        if lista_resultados:
            df_resultado = pd.DataFrame(lista_resultados)
            
            st.success("¡Captura masiva finalizada con éxito!")
            
            st.subheader("📊 Tabla Consolidada de Captura:")
            st.dataframe(df_resultado, use_container_width=True)

            nombre_excel = "Reporte_Captura_Master_SPortal.xlsx"
            df_resultado.to_excel(nombre_excel, index=False)

            with open(nombre_excel, "rb") as f:
                st.download_button(
                    label="📥 Descargar Excel Consolidado de Captura",
                    data=f,
                    file_name=nombre_excel,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )
        else:
            st.error("No se pudieron extraer datos de los archivos seleccionados.")
else:
    st.info("Por favor, selecciona o arrastra tu lote de PDFs para iniciar la captura.")
