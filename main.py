import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Centro de Procesamiento S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Sistema Integral de Procesamiento S.PORTAL")
st.write("Herramienta avanzada: Procesamiento de listados consolidados en PDF y captura masiva de expedientes individuales.")

# Menú de navegación lateral o superior para separar ambas funciones sin alterar la segunda
modo = st.sidebar.selectbox(
    "Selecciona el Modulo de Trabajo:",
    [
        "1. Procesador de Listados Consolidados (Ej: ENERO.pdf)", 
        "2. Procesador Masivo de PDFs Individuales (Expedientes)"
    ]
)

st.markdown("---")

# =========================================================================
# MODULO 1: PROCESADOR DE LISTADOS CONSOLIDADOS (NUEVO)
# =========================================================================
if modo == "1. Procesador de Listados Consolidados (Ej: ENERO.pdf)":
    st.header("📄 Extractor de Listados Consolidados Masivos")
    st.write("Sube tu archivo PDF consolidado mensual (ej. ENERO.pdf) para extraer automáticamente todos los incidentes en formato tabular.")

    archivo_consolidado = st.file_uploader("Sube el PDF consolidado general:", type=["pdf"], key="pdf_con")

    if archivo_consolidado:
        st.info(f"Archivo cargado: {archivo_consolidado.name}. Listo para procesar las páginas.")

        if st.button("🚀 Extraer Datos del Listado Consolidado"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(archivo_consolidado.getbuffer())
                ruta_tmp = tmp.name

            try:
                reader = PdfReader(ruta_tmp)
                total_paginas = len(reader.pages)
                
                lista_registros = []
                barra = st.progress(0)
                
                # Expresión regular para capturar filas de incidentes tabulares en los reportes consolidados
                # Estructura típica: Incidente (P2026...), Tipo, Subtipo, Operador, Ubicación, Fecha/Hora, Zona
                patron_fila = re.compile(r'(P\d{10,12})')

                for idx, pagina in enumerate(reader.pages):
                    texto_pag = pagina.extract_text()
                    if not texto_pag:
                        continue
                    
                    lineas = [l.strip() for l in texto_pag.split('\n') if l.strip()]
                    
                    # Analizador de líneas para listados tabulares
                    i = 0
                    while i < len(lineas):
                        match_inc = patron_fila.search(lineas[i])
                        if match_inc:
                            inc_id = match_inc.group(1)
                            # Intentar extraer elementos cercanos de la tabla consolidada
                            tipo_val = lineas[i+1] if i+1 < len(lineas) else "N/A"
                            sub_val = lineas[i+2] if i+2 < len(lineas) else "N/A"
                            
                            # Buscar coordenadas en las líneas siguientes
                            ubi_val = "N/A"
                            zona_val = "N/A"
                            crea_val = "N/A"
                            op_val = "N/A"
                            
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
                                "Incidente": inc_id,
                                "Tipo": tipo_val,
                                "Subtipo": sub_val,
                                "Ubicación": ubi_val,
                                "Zona": zona_val,
                                "Creación": crea_val,
                                "Operador": op_val
                            })
                        i += 1

                    barra.progress((idx + 1) / total_paginas)

                os.unlink(ruta_tmp)

                if lista_registros:
                    df_cons = pd.DataFrame(lista_registros)
                    # Eliminar duplicados si los hubiera por salto de página
                    df_cons = df_cons.drop_duplicates(subset=["Incidente"])
                    
                    st.success(f"¡Extracción completada! Se encontraron {len(df_cons)} registros únicos.")
                    st.dataframe(df_cons, use_container_width=True)

                    nombre_out = "Reporte_Consolidado_Mes.xlsx"
                    df_cons.to_excel(nombre_out, index=False)

                    with open(nombre_out, "rb") as f:
                        st.download_button(
                            label="📥 Descargar Excel de Listado Consolidado",
                            data=f,
                            file_name=nombre_out,
                            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                        )
                else:
                    st.warning("No se detectaron códigos de incidente con el formato esperado en este PDF.")

            except Exception as e:
                st.error(f"Ocurrió un error al procesar el archivo: {e}")

# =========================================================================
# MODULO 2: PROCESADOR MASIVO DE PDFS INDIVIDUALES (TU SEGUNDA PARTE INTACTA)
# =========================================================================
else:
    st.subheader("📋 Vista Previa de la Tabla Maestra (Vacía)")
    
    columnas_base = [
        "Archivo", "Incidente", "Tipo", "Subtipo", "Ubicación", "Zona", "Operador",
        "Fecha Creación", "Hora Creación",
        "Fecha 1", "Hora 1", "Reporte 1",
        "Fecha 2", "Hora 2", "Reporte 2",
        "Fecha 3", "Hora 3", "Reporte 3",
        "Fecha 4", "Hora 4", "Reporte 4"
    ]

    df_vacio = pd.DataFrame(columns=columnas_base)
    st.dataframe(df_vacio, use_container_width=True)
    st.markdown("---")

    def extraer_datos_pdf_rapido(ruta_pdf, nombre_archivo_original=""):
        """Extracción optimizada con captura directa y dinámica de Tipo y Subtipo desde la cabecera."""
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

            match_incidente = re.search(r'(P\d{10,12})', texto_completo)
            if match_incidente:
                datos["Incidente"] = match_incidente.group(1)
            elif re.search(r'(P\d{10,12})', datos["Archivo"]):
                datos["Incidente"] = re.search(r'(P\d{10,12})', datos["Archivo"]).group(1)

            lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]

            operadores_conocidos = [
                "ENRIQUE CACERES", "VALERY VELASQUEZ", "LEONARDO CASASOLA", 
                "IVETTE GIERHART", "JOAQUIN CHI", "DALILA TREJOS", 
                "HERMOGENES SANJUR", "ANTONIO PATRICIO", "RICARDO EMILIO"
            ]

            for i, linea in enumerate(lineas):
                linea_up = linea.upper()
                
                for op in operadores_conocidos:
                    if op in linea_up:
                        datos["Operador"] = op
                        break
                
                if (re.search(r'\b\d{0,2}[A-Z]{1,3}\b', linea) and len(linea) <= 6) and ("ZP" in linea_up or "ZF" in linea_up or "ZONA" in linea_up):
                    if datos["Zona"] == "N/A":
                        datos["Zona"] = linea

            if datos["Incidente"]:
                for idx, l in enumerate(lineas):
                    if datos["Incidente"] in l:
                        if idx + 1 < len(lineas):
                            datos["Tipo"] = lineas[idx + 1]
                        if idx + 2 < len(lineas):
                            datos["Subtipo"] = lineas[idx + 2]
                        break

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

            if datos["Operador"] == "N/A":
                for op in operadores_conocidos:
                    if op in texto_completo.upper():
                        datos["Operador"] = op
                        break

            return datos
        except Exception as e:
            return None

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
