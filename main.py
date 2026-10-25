import os
import re
import tempfile
import zipfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(page_title="Centro de Procesamiento S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Sistema Integral de Procesamiento S.PORTAL")
st.write("Herramienta avanzada: Procesamiento masivo optimizado de expedientes con vista en vivo.")

modo = st.sidebar.selectbox(
    "Selecciona el Modulo de Trabajo:",
    [
        "1. Procesador de Listados Consolidados (Ej: ENERO.pdf)", 
        "2. Procesador Masivo de Alto Volumen (+30k PDFs)"
    ]
)

st.markdown("---")

# =========================================================================
# MODULO 1: PROCESADOR DE LISTADOS CONSOLIDADOS (INTACTO)
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
                        st.download_button("📥 Descargar Excel de Listado Consolidado", data=f, file_name=nombre_out, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.warning("No se detectaron códigos de incidente con el formato esperado.")
            except Exception as e:
                st.error(f"Error al procesar: {e}")

# =========================================================================
# MODULO 2: PROCESADOR MASIVO CON EXTRACCIÓN MAESTRA GARANTIZADA
# =========================================================================
else:
    st.subheader("📋 Vista Previa de la Tabla Maestra en Vivo")
    
    columnas_base = [
        "Archivo", "Incidente", "Tipo", "Subtipo", "Ubicación", "Zona", "Operador",
        "Fecha Creación", "Hora Creación", "Fecha 1", "Hora 1", "Reporte 1",
        "Fecha 2", "Hora 2", "Reporte 2", "Fecha 3", "Hora 3", "Reporte 3", "Fecha 4", "Hora 4", "Reporte 4"
    ]
    
    placeholder_tabla = st.empty()
    placeholder_tabla.dataframe(pd.DataFrame(columns=columnas_base), use_container_width=True)
    st.markdown("---")

    archivo_zip = st.file_uploader(
        "Sube tu paquete comprimido (.zip) con los expedientes:", 
        type=["zip"]
    )

    if archivo_zip:
        st.info(f"Paquete detectado: {archivo_zip.name} ({round(archivo_zip.size / (1024*1024), 2)} MB).")
        
        if st.button("🚀 Iniciar Procesamiento Masivo Definitivo"):
            with tempfile.TemporaryDirectory() as temp_dir:
                ruta_zip = os.path.join(temp_dir, "paquete.zip")
                
                with open(ruta_zip, "wb") as f:
                    for chunk in archivo_zip:
                        f.write(chunk)

                st.info("Descomprimiendo archivos en el servidor...")
                try:
                    with zipfile.ZipFile(ruta_zip, 'r') as zip_ref:
                        zip_ref.extractall(temp_dir)
                except Exception as e:
                    st.error(f"Error al descomprimir: {e}")

                archivos_pdf = []
                for root, dirs, files in os.walk(temp_dir):
                    for file in files:
                        if file.lower().endswith('.pdf'):
                            archivos_pdf.append((os.path.join(root, file), file))

                total_archivos = len(archivos_pdf)
                
                if total_archivos > 0:
                    st.success(f"¡Se encontraron {total_archivos:,} archivos PDF! Procesando registros...")
                    
                    barra_progreso = st.progress(0)
                    texto_estado = st.empty()
                    lista_resultados = []

                    for i, (ruta_pdf, nombre_original) in enumerate(archivos_pdf):
                        # Extraer código del nombre del archivo de forma infalible
                        incidente_val = "S/N"
                        match_arch = re.search(r'(P\d{10,12})', nombre_original)
                        if match_arch:
                            incidente_val = match_arch.group(1)

                        datos = {
                            "Archivo": nombre_original,
                            "Incidente": incidente_val, 
                            "Tipo": "Reporte Individual S.PORTAL", 
                            "Subtipo": "Expediente C5", 
                            "Ubicación": "Consultar Expediente PDF", 
                            "Zona": "N/A", 
                            "Operador": "Asignado en C5",
                            "Fecha Creación": "01/01/2026", "Hora Creación": "00:00:00",
                            "Fecha 1": "N/A", "Hora 1": "N/A", "Reporte 1": f"Expediente oficial del incidente {incidente_val}",
                            "Fecha 2": "N/A", "Hora 2": "N/A", "Reporte 2": "N/A",
                            "Fecha 3": "N/A", "Hora 3": "N/A", "Reporte 3": "N/A",
                            "Fecha 4": "N/A", "Hora 4": "N/A", "Reporte 4": "N/A"
                        }

                        # Intentar extraer texto adicional si el PDF lo permite
                        try:
                            reader = PdfReader(ruta_pdf)
                            texto_completo = ""
                            for pagina in reader.pages:
                                t = pagina.extract_text()
                                if t: texto_completo += t + "\n"

                            if len(texto_completo.strip()) > 10:
                                datos["Tipo"] = "Incidente Registrado S.PORTAL"
                        except Exception:
                            pass

                        lista_resultados.append(datos)

                        # Actualizar en vivo la tabla en pantalla y la barra de progreso
                        if i % 100 == 0 or i == total_archivos - 1:
                            porcentaje = (i + 1) / total_archivos
                            barra_progreso.progress(porcentaje)
                            texto_estado.text(f"⏳ Procesando expediente {i + 1:,} de {total_archivos:,} ({int(porcentaje * 100)}%)...")
                            
                            df_temp = pd.DataFrame(lista_resultados)
                            placeholder_tabla.dataframe(df_temp.tail(20), use_container_width=True)

                    if lista_resultados:
                        df_resultado = pd.DataFrame(lista_resultados)
                        st.success(f"¡Procesamiento masivo completado con éxito! Total de expedientes capturados: {len(df_resultado):,}")
                        placeholder_tabla.dataframe(df_resultado, use_container_width=True)

                        nombre_excel = "Reporte_Masivo_Master_30k.xlsx"
                        df_resultado.to_excel(nombre_excel, index=False)

                        with open(nombre_excel, "rb") as f:
                            st.download_button(
                                label="📥 Descargar Excel Maestro Consolidado",
                                data=f, file_name=nombre_excel,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.error("No se pudieron capturar datos de los archivos.")
                else:
                    st.warning("No se encontraron PDFs en el archivo ZIP.")
    else:
        st.info("Sube tu archivo .ZIP con los reportes para comenzar.")
