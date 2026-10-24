import os
import re
import tempfile
import pandas as pd
from pypdf import PdfReader
import streamlit as st

st.set_page_config(page_title="Procesador Masivo S.PORTAL", page_icon="📊", layout="wide")

st.title("📊 Procesador Masivo y Consolidador S.PORTAL")
st.write("Sube tu PDF masivo de listado general para extraer todos los casos al instante y obtener tus archivos listos para descargar.")

def procesar_pdf_masivo(ruta_pdf):
    """Procesa el PDF de listado general de S.PORTAL y extrae de forma limpia todos los incidentes."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            t = pagina.extract_text()
            if t:
                texto_completo += t + "\n"

        lineas = [l.strip() for l in texto_completo.split('\n') if l.strip()]
        casos_extraidos = []
        
        i = 0
        while i < len(lineas):
            linea = lineas[i]
            
            match_inc = re.search(r'(P\d{10,12})', linea)
            if match_inc:
                incidente_id = match_inc.group(1)
                
                tipo = "N/A"
                subtipo = "N/A"
                zona = "N/A"
                fecha_creacion = ""
                hora_creacion = ""
                operador = "N/A"
                
                contexto_bloque = " ".join(lineas[i:i+8])
                
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
                    subtipo = "Riña y Escándalo" if "Riña" in contexto_bloque else "Alteración del Orden Publico"
                elif "Tránsito" in contexto_bloque or "Colisión" in contexto_bloque:
                    tipo = "Tránsito"
                    subtipo = "Colisión" if "Colisión" in contexto_bloque else "Infracción"
                elif "Arma de Fuego" in contexto_bloque:
                    tipo = "Arma de Fuego"
                    subtipo = "Posesión Ilegal / Detonaciones"
                elif "Violencia de Genero" in contexto_bloque or "Violencia Doméstica" in contexto_bloque:
                    tipo = "Violencia de Genero"
                    subtipo = "Violencia Doméstica"
                elif "Actitud Sospechosa" in contexto_bloque:
                    tipo = "Actitud Sospechosa"
                    subtipo = "N/A"
                elif "Hurto" in contexto_bloque:
                    tipo = "Hurto"
                    subtipo = "A Propiedad / Con Destreza"
                elif "Pánico" in contexto_bloque:
                    tipo = "Pánico"
                    subtipo = "N/A"
                else:
                    tipo = "Incidente General S.PORTAL"
                    subtipo = "N/A"

                casos_extraidos.append({
                    "Incidente": incidente_id,
                    "Tipo": tipo,
                    "Subtipo": subtipo,
                    "Zona": zona,
                    "Fecha Creación": fecha_creacion,
                    "Hora Creación": hora_creacion,
                    "Operador": operador
                })
            i += 1

        return casos_extraidos

    except Exception as e:
        return []

# Interfaz de carga
archivo_pdf = st.file_uploader("Sube el PDF de listado general de S.PORTAL:", type=["pdf"])

if archivo_pdf:
    bytes_pdf = archivo_pdf.getvalue()

    with st.spinner("Procesando masivamente el documento..."):
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
            tmp.write(bytes_pdf)
            ruta_temporal = tmp.name

        resultados = procesar_pdf_masivo(ruta_temporal)
        os.unlink(ruta_temporal)

    if resultados:
        df_final = pd.DataFrame(resultados)
        st.success(f"¡Procesamiento masivo exitoso! Se han consolidado {len(df_final)} casos en total.")
        
        st.subheader("Vista previa de la Matriz Maestra:")
        st.dataframe(df_final)

        # Contenedor de descargas directas
        st.markdown("---")
        st.subheader("📥 Opciones de Descarga")
        
        col1, col2 = st.columns(2)

        with col1:
            nombre_excel = "Matriz_Operativa_S_PORTAL.xlsx"
            df_final.to_excel(nombre_excel, index=False)
            with open(nombre_excel, "rb") as f:
                st.download_button(
                    label="📊 Descargar Excel Consolidado Maestro",
                    data=f,
                    file_name=nombre_excel,
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

        with col2:
            st.download_button(
                label="📄 Descargar PDF Original Resguardado",
                data=bytes_pdf,
                file_name="Reporte_Original_S_Portal.pdf",
                mime="application/pdf",
                use_container_width=True
            )

    else:
        st.error("No se pudieron extraer datos válidos del PDF.")
else:
    st.info("Por favor, sube tu archivo PDF de listado general de S.PORTAL para comenzar.")
