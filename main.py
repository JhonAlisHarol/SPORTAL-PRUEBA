import os
import re
import pandas as pd
from pypdf import PdfReader

def extraer_datos_pdf(ruta_pdf):
    """Extrae la información estructurada de un reporte individual de S.Portal."""
    try:
        reader = PdfReader(ruta_pdf)
        texto_completo = ""
        for pagina in reader.pages:
            texto_extraido = pagina.extract_text()
            if texto_extraido:
                texto_completo += texto_extraido + "\n"

        # Diccionario para almacenar los campos extraídos
        datos = {
            "Archivo": os.path.basename(ruta_pdf),
            "Incidente": "",
            "Tipo": "",
            "Subtipo": "",
            "Ubicación": "",
            "Zona": "",
            "Operador": "",
            "Creación": "",
            "Bitácora y Acciones Policiales": ""
        }

        # Extracción mediante expresiones regulares basadas en el formato del reporte
        # 1. Número de Incidente (Ej: P20260238869)
        match_incidente = re.search(r'(P\d{10,12})', texto_completo)
        if match_incidente:
            datos["Incidente"] = match_incidente.group(1)

        # 2. Fecha de Creación (Ej: 23/10/2026 0:01:03)
        match_creacion = re.search(r'(\d{2}/\d{2}/\d{4}\s+\d{1,2}:\d{2}:\d{2})', texto_completo)
        if match_creacion:
            datos["Creación"] = match_creacion.group(1)

        # 3. Extracción de bloques de bitácora y comentarios
        # Buscamos las líneas de comentarios y parte policial para unificarlas en el análisis
        lineas = texto_completo.split('\n')
        bitacora_acumulada = []
        
        capturando = False
        for linea in lineas:
            if "Bitacora Incidente" in linea or "Comentario" in linea:
                capturando = True
                continue
            if capturando and linea.strip():
                bitacora_acumulada.append(linea.strip())

        datos["Bitácora y Acciones Policiales"] = " | ".join(bitacora_acumulada)

        return datos

    except Exception as e:
        print(f"Error procesando {ruta_pdf}: {e}")
        return None

def procesar_carpeta_incidentes(carpeta_entrada="reportes_pdf", archivo_salida="Excel_Maestro_Incidentes.xlsx"):
    """Recorre una carpeta con múltiples PDFs de incidentes y genera un Excel consolidado."""
    if not os.path.exists(carpeta_entrada):
        os.makedirs(carpeta_entrada)
        print(f"Se ha creado la carpeta '{carpeta_entrada}'. Coloca allí los PDFs exportados de los casos.")
        return

    archivos = [f for f in os.listdir(carpeta_entrada) if f.lower().endswith('.pdf')]
    
    if not archivos:
        print(f"No se encontraron archivos PDF en la carpeta '{carpeta_entrada}'. ¡Añade algunos para comenzar!")
        return

    print(f"Se encontraron {len(archivos)} reportes PDF para procesar...")
    lista_resultados = []

    for archivo in archivos:
        ruta_completa = os.path.join(carpeta_entrada, archivo)
        info_caso = extraer_datos_pdf(ruta_completa)
        if info_caso:
            lista_resultados.append(info_caso)

    if lista_resultados:
        df = pd.DataFrame(lista_resultados)
        df.to_excel(archivo_salida, index=False)
        print(f"\n¡Proceso exitoso! Se han consolidado {len(lista_resultados)} casos en el archivo: '{archivo_salida}'")
    else:
        print("No se pudieron extraer datos de los archivos analizados.")

if __name__ == "__main__":
    # Carpeta donde colocarás los PDFs descargados del sistema institucional
    CARPETA_PDFS = "reportes_pdf"
    ARCHIVO_EXCEL = "Estudio_Operativo_Incidentes.xlsx"
    
    procesar_carpeta_incidentes(CARPETA_PDFS, ARCHIVO_EXCEL)
