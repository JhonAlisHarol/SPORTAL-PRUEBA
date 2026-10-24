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

# 1. Definir la estructura base de la tabla vacía con todas las columnas requeridas
columnas_base = [
    "Archivo", "Incidente", "Tipo", "Subtipo", "Ubicación", "Zona", "Operador",
    "Fecha Creación", "Hora Creación",
    "Fecha 1", "Hora 1", "Reporte 1",
    "Fecha 2", "Hora 2", "Reporte 2",
    "Fecha 3", "Hora 3", "Reporte 3",
    "Fecha 4", "Hora 4", "Reporte 4"
]

# Mostrar siempre la tabla vacía al inicio para que el usuario visualice el cuadro
st.subheader("📋 Vista Previa de la Tabla Maestra (Vacía)")
df_vacio = pd.DataFrame(columns=columnas_base)
st.dataframe(df_vacio, use_container_width=True)
st.markdown("---")

def extraer_datos_pdf(ruta_pdf, nombre_archivo_original=""):
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
            "Archivo": nombre_archivo_original if nombre_archivo_original else os.path.basename(ruta_pdf),
            "Incidente": "",
            "Tipo": "Alteracion de la Convivencia Pacifica",
            "Subtipo": "Riña y Escándalo",
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

        # 1. Buscar código de incidente (tanto en el texto como en el nombre del archivo si viene de la carpeta)
        match_incidente = re.search(r'(P\d{10,12})', texto_completo)
        if match_incidente:
            datos["Incidente"] = match_incidente.group(1)
        elif re.search(r'(P\d{10,12})', datos["Archivo"]):
            datos["Incidente"] = re.search(r'(P\d{10,12})', datos["Archivo"]).group(1)

        # 2. Buscar fechas y horas en el contenido
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
            # Evitar duplicar la de creación exacta si es la primera
            if not (f_val == datos["Fecha Creación"] and h_val == datos["Hora Creación"] and len(marcas_tiempo) == 0):
                marcas_tiempo.append({"fecha": f_val, "hora": h_val, "pos": pos})

        # Asignar hasta 4 marcas de tiempo secuenciales
        for idx_m, marca in enumerate(marcas_tiempo[:4], start=1):
            datos[f"Fecha {idx_m}"] = marca["fecha"]
            datos[f"Hora {idx_m}"] = marca["hora"]

        # 3. Asociación precisa de los comentarios (Reportes 1 a 4)
        for idx_m in range(len(marcas_tiempo)):
            num_rep = idx_m + 1
            if num_rep > 4:
                break
            
            inicio_texto = marcas_tiempo[idx_m]["pos"] + len(f"{marcas_tiempo[idx_m]['fecha']} {marcas_tiempo[idx_m]['hora']}")
            
            if idx_m + 1 < len(marcas_tiempo):
                fin_texto = marcas_tiempo[idx_m + 1]["pos"]
            else:
                fin_texto = len(texto_completo)

            fragmento = texto_completo[inicio_texto:fin_texto]
            fragmento_limpio = fragmento.replace("ENRIQUE CACERES", "").replace("VALERY VELASQUEZ", "").replace("Comentario Del Usuario", "").replace("\n", " ").strip()
            
            datos[f"Reporte {num_rep}"] = fragmento_limpio

        # Si no encontró marcas pero hay texto, metemos al menos el contenido general
        if not marcas_tiempo and texto_completo:
            datos["Reporte 1"] = texto_completo[:500].replace("\n", " ").strip()

        return datos

    except Exception as e:
        return None

# Componente único de carga masiva intuitiva (permite seleccionar múltiples archivos de cualquier carpeta/Escritorio de golpe)
archivos_subidos = st.file_uploader(
    "Selecciona o arrastra tus archivos PDF de S.PORTAL (puedes elegir cientos de archivos desde tu Escritorio o cualquier carpeta a la vez):", 
    type=["pdf"], 
    accept_multiple_files=True
)

if archivos_subidos:
    st.info(f"Se han cargado {len(archivos_subidos)} archivos. Procesando estructuración y asociando reportes...")
    
    if st.button("🚀 Procesar y Consolidar Datos"):
        lista_resultados = []
        barra_progreso = st.progress(0)
        total_archivos = len(archivos_subidos)

        for i, archivo in enumerate(archivos_subidos):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(archivo.getbuffer())
                ruta_temporal = tmp.name

            info_caso = extraer_datos_pdf(ruta_temporal, archivo.name)
            if info_caso:
                lista_resultados.append(info_caso)

            os.unlink(ruta_temporal)
            barra_progreso.progress((i + 1) / total_archivos)

        if lista_resultados:
            df_resultado = pd.DataFrame(lista_resultados)
            
            st.success("¡Estructuración y consolidación completadas con éxito!")
            
            st.subheader("📊 Tabla Consolidada Final con los Datos Extraídos:")
            st.dataframe(df_resultado, use_container_width=True)

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
            st.error("No se pudieron extraer datos de los archivos seleccionados.")
else:
    st.info("Por favor, selecciona o arrastra tus archivos PDF arriba para comenzar.")
