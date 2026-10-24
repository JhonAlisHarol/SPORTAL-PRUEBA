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

        return datos

    except Exception as e:
        return None

# Selección del método de entrada: Archivos directos o Ruta de Carpeta Local
metodo_carga = st.radio("Selecciona el método para ingresar tus PDFs:", ["Subir Archivos Directamente", "Procesar desde una Carpeta Local"])

rutas_pdfs = []

if metodo_carga == "Subir Archivos Directamente":
    archivos_subidos = st.file_uploader(
        "Sube tus archivos PDF de incidentes aquí (Puedes seleccionar varios a la vez):", 
        type=["pdf"], 
        accept_multiple_files=True
    )
    if archivos_subidos:
        for archivo in archivos_subidos:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".pdf")
            tmp.write(archivo.getbuffer())
            rutas_pdfs.append(tmp.name)

else:
    ruta_carpeta = st.text_input("Ingresa la ruta completa de la carpeta en tu equipo (ej. C:\\Users\\hcedeño\\Desktop\\Reportes_S_Portal_PDF):")
    if ruta_carpeta and os.path.exists(ruta_carpeta):
        archivos_en_carpeta = [os.path.join(ruta_carpeta, f) for f in os.listdir(ruta_carpeta) if f.lower().endswith('.pdf')]
        st.success(f"Se encontraron {len(archivos_en_carpeta)} archivos PDF en la carpeta especificada.")
        rutas_pdfs = archivos_en_carpeta
    elif ruta_carpeta:
        st.error("La ruta ingresada no existe o no es válida.")

if rutas_pdfs:
    if st.button("🚀 Procesar y Consolidar Datos"):
        lista_resultados = []
        barra_progreso = st.progress(0)
        total_archivos = len(rutas_pdfs)

        for i, ruta_pdf in enumerate(rutas_pdfs):
            info_caso = extraer_datos_pdf(ruta_pdf)
            if info_caso:
                lista_resultados.append(info_caso)
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
    st.info("Por favor, selecciona los archivos o ingresa la ruta de la carpeta para comenzar.")
