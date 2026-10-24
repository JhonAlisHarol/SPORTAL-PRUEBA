import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(page_title="Generador de Enlaces Masivos S.PORTAL", page_icon="🔗", layout="wide")

st.title("🔗 Generador de Enlaces Directos S.PORTAL")
st.write("Sube el PDF de listado general para estructurar todos los casos y habilitar sus enlaces directos al sistema.")

def procesar_pdf_con_enlaces(ruta_pdf):
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
        casos_extraidos = []
        
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            match_inc = re.search(r'(P\d{10,12})', linea)
            if match_inc:
                incidente_id = match_inc.group(1)
                
                tipo = "N/A"
                zona = "N/A"
                fecha_creacion = ""
                hora_creacion = ""
                operador = "N/A"
                
                contexto_bloque = " ".join(lineas[i:i+10])
                
                match_fh = re.search(r'(\d{2}/\d{2}/\d{4})\s+(\d{1,2}:\d{2}:\d{2})', contexto_bloque)
                if match_fh:
                    fecha_creacion = match_fh.group(1)
                    hora_creacion = match_fh.group(2)
                
                match_zn = re.search(r'\b(\d{1,2}[A-Z]{1,3}|TRAN)\b', contexto_bloque)
                if match_zn:
                    zona = match_zn.group(1)

                posibles_nombres = [
                    "ENRIQUE CACERES", "VALERY VELASQUEZ", "LEONARDO CASASOLA", "IVETTE GIERHART", 
                    "JOAQUIN CHI", "DALILA TREJOS", "RICARDO EMILIO MAYORGA LORENZO", "HERMOGENES SANJUR", 
                    "ANTONIO PATRICIO", "ARMANDO GONZALEZ", "ESTEBAN E. HERNANDEZ H.", "YARIBETH M. ESCUDERO H.",
                    "MARIA ISABEL MADRID CASTILLO", "DORIAN GREAVES", "ANGELICA RODRIGUEZ", "ERICK ROSALES SANCHEZ JIRON",
                    "LEOPOLDO SERRANO BROWN", "JERRY JORDAN", "PABLO GONZALEZ", "ANGEL JORDAN"
                ]
                for nom in posibles_nombres:
                    if nom in contexto_bloque.upper():
                        operador = nom
                        break

                if "Alteracion de la Convivencia" in contexto_bloque or "Riña" in contexto_bloque:
                    tipo = "Alteracion de la Convivencia Pacifica"
                elif "Tránsito" in contexto_bloque or "Colisión" in contexto_bloque:
                    tipo = "Tránsito"
                elif "Arma de Fuego" in contexto_bloque:
                    tipo = "Arma de Fuego"
                elif "Violencia de Genero" in contexto_bloque or "Violencia Doméstica" in contexto_bloque:
                    tipo = "Violencia de Genero"
                elif "Actitud Sospechosa" in contexto_bloque:
                    tipo = "Actitud Sospechosa"
                else:
                    tipo = "Incidente General S.PORTAL"

                # Construir el enlace directo oficial de la intranet
                url_detalle = f"http://c5-cad-app.c5.gob.pa/Tupa/PNPC5/Report/DetallesDelIncidente?Evento={incidente_id}"

                casos_extraidos.append({
                    "Incidente": incidente_id,
                    "Tipo": tipo,
                    "Zona": zona,
                    "Fecha Creación": fecha_creacion,
                    "Hora Creación": hora_creacion,
                    "Operador": operador,
                    "Enlace S.PORTAL": url_detalle
                })
            i += 1

        return casos_extraidos

    except Exception as e:
        return []

archivos_subidos = st.file_uploader("Sube el PDF de listado general de S.PORTAL:", type=["pdf"])

if archivos_subidos:
    st.info("Procesando el listado y generando enlaces directos...")
    
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        tmp.write(archivos_subidos.getbuffer())
        ruta_temporal = tmp.name

    lista_resultados = procesar_pdf_con_enlaces(ruta_temporal)
    os.unlink(ruta_temporal)

    if lista_resultados:
        df_resultado = pd.DataFrame(lista_resultados)
        
        st.success(f"¡Procesamiento exitoso! Se han estructurado {len(df_resultado)} casos con sus enlaces.")
        st.dataframe(df_resultado)

        nombre_excel = "Matriz_Incidentes_Con_Enlaces.xlsx"
        df_resultado.to_excel(nombre_excel, index=False)

        with open(nombre_excel, "rb") as f:
            st.download_button(
                label="📥 Descargar Excel con Enlaces Directos",
                data=f,
                file_name=nombre_excel,
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
    else:
        st.error("No se pudieron extraer datos del PDF.")
else:
    st.warning("Sube el PDF de listado general para comenzar.")
