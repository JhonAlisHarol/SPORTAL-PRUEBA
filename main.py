import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import requests
from bs4 import BeautifulSoup
import streamlit as st

# Configuración de la página de Streamlit
st.set_page_config(page_title="Procesador Maestro Automático S.PORTAL", page_icon="⚙️", layout="wide")

st.title("⚙️ Procesador Masivo Automático con Detalles S.PORTAL")
st.write("Sube el PDF de listado general. El sistema recorrerá automáticamente cada caso en la red interna para extraer el 100% de los detalles, operador, horas y reportes de la bitácora.")

def extraer_detalles_incidente(incidente_id):
    """Accede por red interna al detalle de cada incidente y extrae toda la bitácora y operador."""
    url = f"http://c5-cad-app.c5.gob.pa/Tupa/PNPC5/Report/DetallesDelIncidente?Evento={incidente_id}"
    datos_caso = {
        "Incidente": incidente_id,
        "Operador": "N/A",
        "Fecha Creación": "",
        "Hora Creación": "",
        "Fecha 1": "", "Hora 1": "", "Reporte 1": "",
        "Fecha 2": "", "Hora 2": "", "Reporte 2": "",
        "Fecha 3": "", "Hora 3": "", "Reporte 3": "",
        "Fecha 4": "", "Hora 4": "", "Reporte 4": ""
    }
    try:
        response = requests.get(url, timeout=5)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            texto_pagina = soup.get_text()

            # 1. Fecha y Hora de Creación
            match_creacion = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})', texto_pagina)
            if match_creacion:
                datos_caso["Fecha Creación"] = match_creacion.group(1)
                datos_caso["Hora Creación"] = match_creacion.group(2)

            # 2. Operador
            posibles_nombres = [
                "ENRIQUE CACERES", "VALERY VELASQUEZ", "LEONARDO CASASOLA", "IVETTE GIERHART", 
                "JOAQUIN CHI", "DALILA TREJOS", "RICARDO EMILIO MAYORGA LORENZO", "HERMOGENES SANJUR", 
                "ANTONIO PATRICIO", "ARMANDO GONZALEZ", "ESTEBAN E. HERNANDEZ H.", "YARIBETH M. ESCUDERO H.",
                "MARIA ISABEL MADRID CASTILLO", "DORIAN GREAVES", "ANGELICA RODRIGUEZ", "ERICK ROSALES SANCHEZ JIRON",
                "LEOPOLDO SERRANO BROWN", "JERRY JORDAN", "PABLO GONZALEZ", "ANGEL JORDAN"
            ]
            for nom in posibles_nombres:
                if nom in texto_pagina.upper():
                    datos_caso["Operador"] = nom
                    break

            # 3. Marcas de tiempo adicionales y Reportes (1 a 4)
            patron_fh = r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})'
            matches = list(re.finditer(patron_fh, texto_pagina))
            
            marcas = []
            for m in matches:
                f_val = m.group(1)
                h_val = m.group(2)
                pos = m.start()
                if not (f_val == datos_caso["Fecha Creación"] and h_val == datos_caso["Hora Creación"] and len(marcas) == 0):
                    marcas.append({"fecha": f_val, "hora": h_val, "pos": pos})

            for idx_m, marca in enumerate(marcas[:4], start=1):
                datos_caso[f"Fecha {idx_m}"] = marca["fecha"]
                datos_caso[f"Hora {idx_m}"] = marca["hora"]

            for idx_m in range(len(marcas)):
                num_rep = idx_m + 1
                if num_rep > 4:
                    break
                inicio = marcas[idx_m]["pos"] + len(f"{marcas[idx_m]['fecha']} {marcas[idx_m]['hora']}")
                fin = marcas[idx_m + 1]["pos"] if idx_m + 1 < len(marcas) else len(texto_pagina)
                fragmento = texto_pagina[inicio:fin].replace("Comentario Del Usuario", "").replace("\n", " ").strip()
                datos_caso[f"Reporte {num_rep}"] = fragmento

    except Exception:
        pass  # Si un caso falla temporalmente, continúa con el siguiente
        
    return datos_caso

def procesar_pdf_listado(ruta_pdf):
    reader = PdfReader(ruta_pdf)
    texto_completo = ""
    for pagina in reader.pages:
        t = pagina.extract_text()
        if t:
            texto_completo += t + "\n"
    
    # Extraer todos los códigos únicos del PDF
    codigos = re.findall(r'(P\d{10,12})', texto_completo)
    return list(dict.fromkeys(codigos)) # Elimina duplicados manteniendo el orden

# Interfaz de Streamlit
archivos_subidos = st.file_uploader("Sube el PDF de listado general de S.PORTAL:", type=["pdf"])

if archivos_subidos:
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(archivos_subidos.getbuffer())
        ruta_temporal = tmp.name

    lista_codigos = procesar_pdf_listado(ruta_temporal)
    os.unlink(ruta_temporal)

    if lista_codigos:
        st.info(f"Se han detectado {len(lista_codigos)} códigos. Iniciando extracción automática de detalles en la red interna...")
        
        resultados = []
        barra = st.progress(0)
        total = len(lista_codigos)

        for i, codigo in enumerate(lista_codigos):
            info_caso = extraer_detalles_incidente(codigo)
            resultados.append(info_caso)
            barra.progress((i + 1) / total)

        df_resultado = pd.DataFrame(resultados)
        st.success("¡Extracción masiva completada con éxito!")
        
        st.subheader("Vista previa del Excel Consolidado con Detalles:")
        st.dataframe(df_resultado)

        nombre_excel = "Estudio_Operativo_Detallado_Completo.xlsx"
        df_resultado.to_excel(nombre_excel, index=False)

        with open(nombre_excel, "rb") as f:
            st.download_button(
                label="📥 Descargar Archivo Excel Consolidado Completo",
                data=f,
                file_name=nombre_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.error("No se encontraron códigos de incidente válidos en el PDF.")
else:
    st.warning("Sube el PDF de listado general de S.PORTAL para comenzar el proceso automático.")
