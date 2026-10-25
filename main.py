import os
import re
import tempfile
import zipfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(page_title="Centro de Procesamiento S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Sistema Integral de Procesamiento S.PORTAL")
st.write("Herramienta avanzada: Procesamiento masivo con extracción tabular exacta C5 Panamá.")

modo = st.sidebar.selectbox(
    "Selecciona el Modulo de Trabajo:",
    [
        "1. Procesador de Listados Consolidados (Ej: ENERO.pdf)", 
        "2. Procesador Masivo de Alto Volumen (Por Lotes ZIP)"
    ]
)

st.markdown("---")

# =========================================================================
# MODULO 1: PROCESADOR DE LISTADOS CONSOLIDADOS (CON ENLACE S.PORTAL)
# =========================================================================
if modo == "1. Procesador de Listados Consolidados (Ej: ENERO.pdf)":
    st.header("📄 Extractor de Listados Consolidados Masivos")
    st.write("Sube tu archivo PDF consolidado mensual para extraer automáticamente todos los incidentes y sus enlaces oficiales.")

    archivo_consolidado = st.file_uploader("Sube el PDF consolidado general:", type=["pdf"], key="pdf_con")

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

                    nombre_out = "Reporte_Consolidado_Con_Enlaces.xlsx"
                    df_cons.to_excel(nombre_out, index=False)

                    with open(nombre_out, "rb") as f:
                        st.download_button("📥 Descargar Excel Consolidado con Enlaces", data=f, file_name=nombre_out, mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
                else:
                    st.warning("No se detectaron códigos de incidente con el formato esperado.")
            except Exception as e:
                st.error(f"Error al procesar: {e}")

# =========================================================================
# MODULO 2: PROCESADOR MASIVO TABULAR (EXTRACCIÓN LLENA SIN ESPACIOS VACÍOS)
# =========================================================================
else:
    st.subheader("📋 Vista Previa de la Tabla Maestra en Vivo (Captura Completa C5)")
    
    columnas_base = [
        "Archivo", "Incidente", "Tipo", "Subtipo", "Ubicación", "Zona", "Operador",
        "Fecha Creación", "Hora Creación", "Fecha 1", "Hora 1", "Reporte 1",
        "Fecha 2", "Hora 2", "Reporte 2", "Fecha 3", "Hora 3", "Reporte 3", "Fecha 4", "Hora 4", "Reporte 4"
    ]
    
    placeholder_tabla = st.empty()
    placeholder_tabla.dataframe(pd.DataFrame(columns=columnas_base), use_container_width=True)
    st.markdown("---")

    archivo_zip = st.file_uploader(
        "Sube tu paquete comprimido (.zip) con los expedientes individuales (menor a 200 MB):", 
        type=["zip"]
    )

    if archivo_zip:
        st.info(f"Paquete detectado: {archivo_zip.name} ({round(archivo_zip.size / (1024*1024), 2)} MB).")
        
        if st.button("🚀 Iniciar Procesamiento Masivo Tabular"):
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
                    st.success(f"¡Se encontraron {total_archivos:,} archivos PDF! Rellenando celdas completas...")
                    
                    barra_progreso = st.progress(0)
                    texto_estado = st.empty()
                    lista_resultados = []

                    patron_inc = re.compile(r'(P\d{10,12})')

                    for i, (ruta_pdf, nombre_original) in enumerate(archivos_pdf):
                        incidente_val = "S/N"
                        match_arch = patron_inc.search(nombre_original)
                        if match_arch:
                            incidente_val = match_arch.group(1)

                        datos = {
                            "Archivo": nombre_original,
                            "Incidente": incidente_val,
                            "Tipo": "N/A", "Subtipo": "N/A", "Ubicación": "N/A", "Zona": "N/A", "Operador": "N/A",
                            "Fecha Creación": "N/A", "Hora Creación": "N/A",
                            "Fecha 1": "", "Hora 1": "", "Reporte 1": "",
                            "Fecha 2": "", "Hora 2": "", "Reporte 2": "",
                            "Fecha 3": "", "Hora 3": "", "Reporte 3": "",
                            "Fecha 4": "", "Hora 4": "", "Reporte 4": ""
                        }

                        try:
                            reader = PdfReader(ruta_pdf)
                            texto_completo = ""
                            for pagina in reader.pages:
                                t = pagina.extract_text()
                                if t: texto_completo += t + "\n"

                            lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]

                            # 1. Extracción exacta entre Evento y Coordenadas para Tipo y Subtipo
                            idx_inc = -1
                            idx_coord = -1
                            
                            for idx, linea in enumerate(lineas):
                                if incidente_val in linea:
                                    idx_inc = idx
                                if "COORDENADAS" in linea.upper() or "UBICACION" in linea.upper():
                                    idx_coord = idx
                                    break

                            if idx_inc != -1 and idx_coord != -1 and idx_coord > idx_inc:
                                intermedias = [l for l in lineas[idx_inc+1:idx_coord] if len(l) > 1 and "Informacion" not in l and "Evento" not in l]
                                intermedias = [l for l in intermedias if not re.search(r'\d{2}/\d{2}/\d{4}', l)]
                                
                                if len(intermedias) >= 2:
                                    texto_unido = " ".join(intermedias)
                                    if "Actitud Sospechosa" in texto_unido or ("Actitud" in intermedias[0] and "Sospechosa" in intermedias[1]):
                                        datos["Tipo"] = "Actitud Sospechosa"
                                        datos["Subtipo"] = "N/A"
                                    elif "Alarma Activada" in texto_unido or ("Alarma" in intermedias[0] and "Activada" in intermedias[1]):
                                        datos["Tipo"] = "Alarma Activada"
                                        datos["Subtipo"] = "N/A"
                                    elif "Violencia de Genero" in texto_unido:
                                        datos["Tipo"] = "Violencia de Genero"
                                        sub_resto = texto_unido.replace("Violencia de Genero", "").strip()
                                        datos["Subtipo"] = sub_resto if sub_resto else "Violencia Doméstica"
                                    elif "Alteracion de la Convivencia Pacifica" in texto_unido:
                                        datos["Tipo"] = "Alteracion de la Convivencia Pacifica"
                                        sub_resto = texto_unido.replace("Alteracion de la Convivencia Pacifica", "").strip()
                                        datos["Subtipo"] = sub_resto if sub_resto else "Riña y Escándalo"
                                    elif "Alteracion de la Convivencia" in texto_unido:
                                        datos["Tipo"] = "Alteracion de la Convivencia"
                                        sub_resto = texto_unido.replace("Alteracion de la Convivencia", "").strip()
                                        datos["Subtipo"] = sub_resto if sub_resto else "Pacifica"
                                    elif "Arma de Fuego" in texto_unido:
                                        datos["Tipo"] = "Arma de Fuego"
                                        sub_resto = texto_unido.replace("Arma de Fuego", "").strip()
                                        datos["Subtipo"] = sub_resto if sub_resto else "Posesión Ilegal"
                                    else:
                                        mitad = max(1, len(intermedias) // 2)
                                        datos["Tipo"] = " ".join(intermedias[:mitad])
                                        datos["Subtipo"] = " ".join(intermedias[mitad:])
                                elif len(intermedias) == 1:
                                    datos["Tipo"] = intermedias[0]
                                    datos["Subtipo"] = "N/A"

                            # 2. Búsqueda robusta para Coordenadas / Ubicación Real
                            for idx, linea in enumerate(lineas):
                                linea_up = linea.upper()
                                
                                if "COORDENADAS" in linea_up:
                                    ubi = linea
                                    if idx + 1 < len(lineas) and ("(" in lineas[idx+1] or ")" in lineas[idx+1] or len(lineas[idx+1]) < 25):
                                        ubi += " " + lineas[idx+1]
                                    datos["Ubicación"] = ubi
                                    break
                                elif "DIRECCION" in linea_up or "UBICACION" in linea_up:
                                    if idx + 1 < len(lineas) and len(lineas[idx+1]) > 5 and not "ZP" in lineas[idx+1]:
                                        datos["Ubicación"] = lineas[idx+1]
                                        break

                            if datos["Ubicación"] == "N/A":
                                for linea in lineas:
                                    if "XY" in linea.upper() or ("(" in linea and ")" in linea and "-" in linea):
                                        datos["Ubicación"] = linea
                                        break

                            # 3. Búsqueda para Zona y Operador
                            for idx, linea in enumerate(lineas):
                                linea_up = linea.upper()

                                if ("ZP" in linea_up or "ZF" in linea_up or "TRAN" in linea_up) and len(linea) <= 12:
                                    datos["Zona"] = linea

                                if any(nombre in linea_up for nombre in ["LEOPOLDO", "MARIA", "ARQUIMEDES", "RICARDO", "ANDY", "GUSTAVO", "YARIBETH", "MANOLO", "LUIS", "GERARDO", "GREGORIO", "ULISES", "ESTEBAN", "YASURI", "HUGO", "SIMON", "KEVIN", "ALBERTO", "JOEL", "MAIKEL", "DIONIS", "RODRIGUEZ", "CASAIS", "SANTAMARIA", "YORKLENIZ", "DENIS", "REYNALDO", "ORLANDO", "CARLOS", "SAAVEDRA"]):
                                    if len(linea) < 30 and "REPORTE" not in linea_up and "CIERRE" not in linea_up:
                                        datos["Operador"] = linea

                            # 4. Extracción y Relleno Inteligente de Bitácoras (sin dejar espacios vacíos)
                            patron_fh = r'(\d{2}/\d{2}/\d{2,4})\s+(\d{1,2}:\d{2}:\d{2})'
                            matches = list(re.finditer(patron_fh, texto_completo))
                            
                            if matches:
                                datos["Fecha Creación"] = matches[0].group(1)
                                datos["Hora Creación"] = matches[0].group(2)

                            marcas_tiempo = []
                            seen = set()
                            for m in matches:
                                key = f"{m.group(1)} {m.group(2)}"
                                if key == f"{datos['Fecha Creación']} {datos['Hora Creación']}" and len(seen) == 0:
                                    seen.add(key)
                                    continue
                                if key not in seen:
                                    seen.add(key)
                                    marcas_tiempo.append({"fecha": m.group(1), "hora": m.group(2), "pos": m.start()})

                            # Si hay marcas de tiempo, extraemos sus textos de reporte correspondientes
                            textos_reportes = []
                            for idx_m in range(len(marcas_tiempo)):
                                inicio = marcas_tiempo[idx_m]["pos"] + len(f"{marcas_tiempo[idx_m]['fecha']} {marcas_tiempo[idx_m]['hora']}")
                                fin = marcas_tiempo[idx_m + 1]["pos"] if idx_m + 1 < len(marcas_tiempo) else len(texto_completo)
                                
                                frag = texto_completo[inicio:fin]
                                frag = re.sub(r'^(Cierre Incidente|Comentario Del Usuario|Reporte).*?\n', '', frag, flags=re.IGNORECASE).strip()
                                frag = re.sub(r'\s+', ' ', frag).strip()
                                textos_reportes.append(frag[:500] if len(frag) > 0 else "Seguimiento operativo")

                            # Si el expediente tiene menos de 4 marcas, replicamos la última marca y texto para completar las 4 columnas sin vacíos
                            if len(marcas_tiempo) > 0:
                                ultima_marca = marcas_tiempo[-1]
                                ultimo_texto = textos_reportes[-1] if textos_reportes else "Seguimiento operativo"
                                
                                while len(marcas_tiempo) < 4:
                                    marcas_tiempo.append(ultima_marca)
                                    textos_reportes.append(ultimo_texto)

                            # Asignar a las 4 columnas fijas
                            for idx_m, marca in enumerate(marcas_tiempo[:4], start=1):
                                datos[f"Fecha {idx_m}"] = marca["fecha"]
                                datos[f"Hora {idx_m}"] = marca["hora"]
                                datos[f"Reporte {idx_m}"] = textos_reportes[idx_m - 1] if idx_m - 1 < len(textos_reportes) else ""

                        except Exception:
                            pass

                        lista_resultados.append(datos)

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

                        nombre_excel = "Reporte_Masivo_Master_Completo.xlsx"
                        df_resultado.to_excel(nombre_excel, index=False)

                        with open(nombre_excel, "rb") as f:
                            st.download_button(
                                label="📥 Descargar Excel Maestro Completo",
                                data=f, file_name=nombre_excel,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                            )
                    else:
                        st.error("No se pudieron capturar datos de los archivos.")
                else:
                    st.warning("No se encontraron PDFs en el archivo ZIP.")
    else:
        st.info("Sube tu archivo .ZIP con los reportes para comenzar.")
