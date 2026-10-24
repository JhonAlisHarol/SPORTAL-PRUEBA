import os
import re
import tempfile
import zipfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Centro de Procesamiento S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Sistema Integral de Procesamiento S.PORTAL")
st.write("Herramienta avanzada: Procesamiento de listados consolidados en PDF y captura masiva mediante archivo ZIP.")

modo = st.sidebar.selectbox(
    "Selecciona el Modulo de Trabajo:",
    [
        "1. Procesador de Listados Consolidados (Ej: ENERO.pdf)", 
        "2. Procesador Masivo de ZIP de PDFs (Expedientes)"
    ]
)

st.markdown("---")

# =========================================================================
# MODULO 1: PROCESADOR DE LISTADOS CONSOLIDADOS
# =========================================================================
if modo == "1. Procesador de Listados Consolidados (Ej: ENERO.pdf)":
    st.header("📄 Extractor de Listados Consolidados Masivos")
    st.write("Sube tu archivo PDF consolidado mensual para extraer automáticamente todos los incidentes.")

    archivo_consolidado = st.file_uploader("Sube el PDF consolidado general:", type=["pdf"], key="pdf_con")

    if archivo_consolidado:
        st.info(f"Archivo cargado: {archivo_consolidado.name}. Listo para procesar.")

        if st.button("🚀 Extraer Datos del Listado Consolidado"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(archivo_consolidado.getbuffer())
                ruta_tmp = tmp.name

            try:
                reader = PdfReader(ruta_tmp)
                total_paginas = len(reader.pages)
                lista_registros = []
                barra = st.progress(0)
                patron_fila = re.compile(r'(P\d{10,12})')

                for idx, pagina in enumerate(reader.pages):
                    texto_pag = pagina.extract_text()
                    if not texto_pag:
                        continue
                    
                    lineas = [l.strip() for l in texto_pag.split('\n') if l.strip()]
                    i = 0
                    while i < len(lineas):
                        match_inc = patron_fila.search(lineas[i])
                        if match_inc:
                            inc_id = match_inc.group(1)
                            tipo_val = lineas[i+1] if i+1 < len(lineas) else "N/A"
                            sub_val = lineas[i+2] if i+2 < len(lineas) else "N/A"
                            
                            ubi_val, zona_val, crea_val, op_val = "N/A", "N/A", "N/A", "N/A"
                            
                            for k in range(i, min(i + 10, len(lineas))):
                                if "COORDENADAS" in lineas[k].upper():
                                    ubi_val = lineas[k]
                                    if k+1 < len(lineas) and ")" in lineas[k+1]:
                                        ubi_val += " " + lineas[k+1]
                                if re.search(r'\b\d{1,2}[A-Z]{1,3}\b', lineas[k]) and len(lineas[k]) <= 6 and ("ZP" in lineas[k].upper() or "ZF" in lineas[k].upper()):
                                    zona_val = lineas[k]
                                if re.search(r'\d{2}/\d{2}/\d{4}', lineas[k]):
                                    crea_val = lineas[k]
                                    if k+1 < len(lineas) and re.search(r'\d{1,2}:\d{2}', lineas[k+1]):
                                        crea_val += " " + lineas[k+1]

                            lista_registros.append({
                                "Incidente": inc_id, "Tipo": tipo_val, "Subtipo": sub_val,
                                "Ubicación": ubi_val, "Zona": zona_val, "Creación": crea_val, "Operador": op_val
                            })
                        i += 1
                    barra.progress((idx + 1) / total_paginas)

                os.unlink(ruta_tmp)

                if lista_registros:
                    df_cons = pd.DataFrame(lista_registros).drop_duplicates(subset=["Incidente"])
                    st.success(f"¡Extracción completada! Se encontraron {len(df_cons)} registros únicos.")
                    st.dataframe(df_cons, use_container_width=True)

                    nombre_out = "Reporte_Consolidado_Mes.xlsx"
                    df_cons.to_excel(nombre_out, index=False)

                    with open(nombre_out, "rb") as f:
                        st.download_button("📥 Descargar Excel Consolidado", data=f, file_name=nombre_out, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.warning("No se detectaron códigos de incidente con el formato esperado.")
            except Exception as e:
                st.error(f"Error al procesar: {e}")

# =========================================================================
# MODULO 2: PROCESADOR MASIVO MEDIANTE ARCHIVO ZIP (EVITA SELECCIONAR CIENTOS)
# =========================================================================
else:
    st.subheader("📋 Vista Previa de la Tabla Maestra (Vacía)")
    
    columnas_base = [
        "Archivo", "Incidente", "Tipo", "Subtipo", "Ubicación", "Zona", "Operador",
        "Fecha Creación", "Hora Creación", "Fecha 1", "Hora 1", "Reporte 1",
        "Fecha 2", "Hora 2", "Reporte 2", "Fecha 3", "Hora 3", "Reporte 3", "Fecha 4", "Hora 4", "Reporte 4"
    ]
    st.dataframe(pd.DataFrame(columns=columnas_base), use_container_width=True)
    st.markdown("---")

    def extraer_datos_pdf_rapido(ruta_pdf, nombre_archivo_original=""):
        try:
            reader = PdfReader(ruta_pdf)
            texto_completo = "".join([p.extract_text() + "\n" for p in reader.pages if p.extract_text()])

            datos = {
                "Archivo": nombre_archivo_original or os.path.basename(ruta_pdf),
                "Incidente": "", "Tipo": "", "Subtipo": "", "Ubicación": "N/A", "Zona": "N/A", "Operador": "N/A",
                "Fecha Creación": "", "Hora Creación": "",
                "Fecha 1": "", "Hora 1": "", "Reporte 1": "",
                "Fecha 2": "", "Hora 2": "", "Reporte 2": "",
                "Fecha 3": "", "Hora 3": "", "Reporte 3": "",
                "Fecha 4": "", "Hora 4": "", "Reporte 4": ""
            }

            match_inc = re.search(r'(P\d{10,12})', texto_completo)
            if match_inc:
                datos["Incidente"] = match_inc.group(1)
            elif re.search(r'(P\d{10,12})', datos["Archivo"]):
                datos["Incidente"] = re.search(r'(P\d{10,12})', datos["Archivo"]).group(1)

            lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
            ops = ["ENRIQUE CACERES", "VALERY VELASQUEZ", "LEONARDO CASASOLA", "IVETTE GIERHART", "JOAQUIN CHI", "DALILA TREJOS", "HERMOGENES SANJUR", "ANTONIO PATRICIO", "RICARDO EMILIO"]

            for linea in lineas:
                linea_up = linea.upper()
                for op in ops:
                    if op in linea_up:
                        datos["Operador"] = op
                        break
                if (re.search(r'\b\d{0,2}[A-Z]{1,3}\b', linea) and len(linea) <= 6) and ("ZP" in linea_up or "ZF" in linea_up or "ZONA" in linea_up):
                    if datos["Zona"] == "N/A":
                        datos["Zona"] = linea

            if datos["Incidente"]:
                for idx, l in enumerate(lineas):
                    if datos["Incidente"] in l:
                        if idx + 1 < len(lineas): datos["Tipo"] = lineas[idx + 1]
                        if idx + 2 < len(lineas): datos["Subtipo"] = lineas[idx + 2]
                        break

            match_coords = re.search(r'(COORDENADAS\s+XY\s*\([^)]+\))', texto_completo, re.IGNORECASE)
            if match_coords:
                datos["Ubicación"] = match_coords.group(1).replace("\n", " ")

            patron_fh = r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})'
            matches = list(re.finditer(patron_fh, texto_completo))
            if matches:
                datos["Fecha Creación"] = matches[0].group(1)
                datos["Hora Creación"] = matches[0].group(2)

            marcas_tiempo = [{"fecha": m.group(1), "hora": m.group(2), "pos": m.start()} for m in matches if not (m.group(1) == datos["Fecha Creación"] and m.group(2) == datos["Hora Creación"] and len(matches) == 1)]
            
            for idx_m, marca in enumerate(marcas_tiempo[:4], start=1):
                datos[f"Fecha {idx_m}"] = marca["fecha"]
                datos[f"Hora {idx_m}"] = marca["hora"]

            for idx_m in range(len(marcas_tiempo)):
                if idx_m + 1 > 4: break
                inicio = marcas_tiempo[idx_m]["pos"] + len(f"{marcas_tiempo[idx_m]['fecha']} {marcas_tiempo[idx_m]['hora']}")
                fin = marcas_tiempo[idx_m + 1]["pos"] if idx_m + 1 < len(marcas_tiempo) else len(texto_completo)
                frag = texto_completo[inicio:fin].replace("Comentario Del Usuario", "").replace("\n", " ").strip()
                if datos["Operador"] != "N/A": frag = frag.replace(datos["Operador"], "").strip()
                datos[f"Reporte {idx_m + 1}"] = frag

            return datos
        except:
            return None

    # Selector mediante archivo ZIP masivo
    archivo_zip = st.file_uploader(
        "Sube tu archivo .ZIP que contenga la carpeta con todos los PDFs (¡Sube miles de golpe de una sola vez!):", 
        type=["zip"]
    )

    if archivo_zip:
        st.info("Archivo ZIP cargado correctamente en memoria.")
        
        if st.button("🚀 Procesar ZIP Masivo y Generar Excel"):
            lista_resultados = []
            
            with tempfile.TemporaryDirectory() as temp_dir:
                # Descomprimir el ZIP de forma interna
                with zipfile.ZipFile(archivo_zip, 'r') as zip_ref:
                    zip_ref.extractall(temp_dir)
                
                # Buscar todos los archivos PDF dentro de la estructura descomprimida
                archivos_pdf = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            archivos_pdf.append(os.path.join(root, file))
                
                total_archivos = len(archivos_pdf)
                if total_archivos > 0:
                    barra_progreso = st.progress(0)
                    
                    for i, ruta_pdf in enumerate(archivos_pdf):
                        nombre_original = os.path.basename(ruta_pdf)
                        info_caso = extraer_datos_pdf_rapido(ruta_pdf, nombre_original)
                        if info_caso:
                            lista_resultados.append(info_caso)
                        barra_progreso.progress((i + 1) / total_archivos)

                    if lista_resultados:
                        df_resultado = pd.DataFrame(lista_resultados)
                        st.success(f"¡Procesamiento masivo finalizado! Se leyeron {len(df_resultado)} PDFs con éxito.")
                        st.dataframe(df_resultado, use_container_width=True)

                        nombre_excel = "Reporte_Captura_Master_SPortal.xlsx"
                        df_resultado.to_excel(nombre_excel, index=False)

                        with open(nombre_excel, "rb") as f:
                            st.download_button(
                                label="📥 Descargar Excel Consolidado de Captura",
                                data=f, file_name=nombre_excel,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.error("No se pudieron extraer datos de los PDFs dentro del ZIP.")
                else:
                    st.warning("El archivo ZIP no contiene ningún documento PDF en su interior.")
    else:
        st.info("Por favor, sube tu archivo .ZIP con los reportes para iniciar la captura masiva.")
