import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(page_title="Centro de Procesamiento S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Sistema Integral de Procesamiento S.PORTAL")
st.write("Herramienta avanzada: Procesamiento masivo por selección múltiple de archivos PDF.")

modo = st.sidebar.selectbox(
    "Selecciona el Modulo de Trabajo:",
    [
        "1. Procesador de Listados Consolidados (Cualquier Mes)", 
        "2. Procesador Masivo por Selección Múltiple de PDFs"
    ]
)

st.markdown("---")

# =========================================================================
# MODULO 1: PROCESADOR DE LISTADOS CONSOLIDADOS (MULTIMES)
# =========================================================================
if modo == "1. Procesador de Listados Consolidados (Cualquier Mes)":
    st.header("📄 Extractor de Listados Consolidados Mensuales")
    st.write("Sube el archivo PDF consolidado del mes para extraer automáticamente todos los incidentes y sus enlaces.")

    archivo_consolidado = st.file_uploader("Sube el PDF consolidado mensual:", type=["pdf"], key="pdf_con")

    if archivo_consolidado:
        st.info(f"Archivo cargado: {archivo_consolidado.name}. Listo para procesar.")

        if st.button("🚀 Extraer Datos y Enlaces del Listado Consolidado"):
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

                            enlace_portal = f"http://c5-cad-app.c5.gob.pa/Tupa/PNPC5/Report/DetallesDelIncidente?Evento={inc_id}"

                            lista_registros.append({
                                "Incidente": inc_id, 
                                "Tipo": tipo_val, 
                                "Subtipo": sub_val,
                                "Ubicación": ubi_val, 
                                "Zona": zona_val, 
                                "Creación": crea_val, 
                                "Operador": op_val,
                                "Enlace S.PORTAL": enlace_portal
                            })
                        i += 1
                    barra.progress((idx + 1) / total_paginas)

                os.unlink(ruta_tmp)

                if lista_registros:
                    df_cons = pd.DataFrame(lista_registros).drop_duplicates(subset=["Incidente"])
                    st.success(f"¡Extracción completada! Se encontraron {len(df_cons)} registros únicos con sus enlaces.")
                    st.dataframe(df_cons, use_container_width=True)

                    nombre_out = "Reporte_Consolidado_Mes_Con_Enlaces.xlsx"
                    df_cons.to_excel(nombre_out, index=False)

                    with open(nombre_out, "rb") as f:
                        st.download_button("📥 Descargar Excel Consolidado con Enlaces", data=f, file_name=nombre_out, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.warning("No se detectaron códigos de incidente con el formato esperado.")
            except Exception as e:
                st.error(f"Error al procesar: {e}")

# =========================================================================
# MODULO 2: PROCESADOR MASIVO POR SELECCIÓN MÚLTIPLE DE ARCHIVOS PDF
# =========================================================================
else:
    st.subheader("📋 Vista Previa de la Tabla Maestra en Vivo (Extracción Masiva C5)")
    st.write("Selecciona y sube tus archivos PDF individuales directamente desde tu equipo para procesarlos en lote.")

    columnas_base = [
        "Archivo", "Incidente", "Tipo", "Subtipo", "Ubicación", "Zona", "Operador",
        "Fecha Creación", "Hora Creación", "Fecha 1", "Hora 1", "Reporte 1",
        "Fecha 2", "Hora 2", "Reporte 2", "Fecha 3", "Hora 3", "Reporte 3", "Fecha 4", "Hora 4", "Reporte 4", "Enlace S.PORTAL"
    ]
    
    placeholder_tabla = st.empty()
    placeholder_tabla.dataframe(pd.DataFrame(columns=columnas_base), use_container_width=True)
    st.markdown("---")

    archivos_subidos = st.file_uploader(
        "Selecciona los expedientes PDF (puedes elegir varios a la vez):", 
        type=["pdf"], 
        accept_multiple_files=True
    )

    if archivos_subidos:
        st.info(f"Se han cargado {len(archivos_subidos):,} archivos PDF listos para procesar.")
        
        if st.button("🚀 Iniciar Extracción Masiva por Lotes"):
            barra_progreso = st.progress(0)
            texto_estado = st.empty()
            lista_resultados = []

            total_archivos = len(archivos_subidos)
            patron_inc = re.compile(r'(P\d{10,12})')

            for i, archivo_pdf in enumerate(archivos_subidos):
                nombre_original = archivo_pdf.name
                incidente_val = "S/N"
                match_arch = patron_inc.search(nombre_original)
                if match_arch:
                    incidente_val = match_arch.group(1)

                enlace_portal = f"http://c5-cad-app.c5.gob.pa/Tupa/PNPC5/Report/DetallesDelIncidente?Evento={incidente_val}"

                datos = {
                    "Archivo": nombre_original,
                    "Incidente": incidente_val,
                    "Tipo": "N/A", "Subtipo": "N/A", "Ubicación": "N/A", "Zona": "N/A", "Operador": "N/A",
                    "Fecha Creación": "N/A", "Hora Creación": "N/A",
                    "Fecha 1": "N/A", "Hora 1": "N/A", "Reporte 1": "N/A",
                    "Fecha 2": "N/A", "Hora 2": "N/A", "Reporte 2": "N/A",
                    "Fecha 3": "N/A", "Hora 3": "N/A", "Reporte 3": "N/A",
                    "Fecha 4": "N/A", "Hora 4": "N/A", "Reporte 4": "N/A",
                    "Enlace S.PORTAL": enlace_portal
                }

                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                        tmp.write(archivo_pdf.getbuffer())
                        ruta_tmp = tmp.name

                    reader = PdfReader(ruta_tmp)
                    texto_completo = ""
                    for pagina in reader.pages:
                        t = pagina.extract_text()
                        if t: texto_completo += t + "\n"

                    os.unlink(ruta_tmp)

                    lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]

                    for idx, linea in enumerate(lineas):
                        if incidente_val in linea:
                            if idx + 1 < len(lineas): datos["Tipo"] = lineas[idx + 1]
                            if idx + 2 < len(lineas): datos["Subtipo"] = lineas[idx + 2]
                            if idx + 3 < len(lineas): datos["Ubicación"] = lineas[idx + 3]
                            if idx + 4 < len(lineas): datos["Zona"] = lineas[idx + 4]
                            if idx + 5 < len(lineas): datos["Operador"] = lineas[idx + 5]

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
                        datos[f"Reporte {idx_m + 1}"] = frag[:400]

                except Exception:
                    pass

                lista_resultados.append(datos)

                if i % 50 == 0 or i == total_archivos - 1:
                    porcentaje = (i + 1) / total_archivos
                    barra_progreso.progress(porcentaje)
                    texto_estado.text(f"⏳ Procesando expediente {i + 1:,} de {total_archivos:,} ({int(porcentaje * 100)}%)...")
                    
                    df_temp = pd.DataFrame(lista_resultados)
                    placeholder_tabla.dataframe(df_temp.tail(20), use_container_width=True)

            if lista_resultados:
                df_resultado = pd.DataFrame(lista_resultados)
                st.success(f"¡Procesamiento masivo completado con éxito! Total de expedientes capturados: {len(df_resultado):,}")
                placeholder_tabla.dataframe(df_resultado, use_container_width=True)

                nombre_excel = "Reporte_Masivo_Master_Definitivo.xlsx"
                df_resultado.to_excel(nombre_excel, index=False)

                with open(nombre_excel, "rb") as f:
                    st.download_button(
                        label="📥 Descargar Excel Maestro Definitivo",
                        data=f, file_name=nombre_excel,
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
            else:
                st.error("No se pudieron capturar datos de los archivos.")
    else:
        st.info("Selecciona tus archivos PDF usando el botón de arriba para comenzar.")
