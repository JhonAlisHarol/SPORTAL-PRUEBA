import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright

def extraer_incidentes_s_portal():
    print("Iniciando el navegador automatizado...")
    
    with sync_playwright() as p:
        # Lanzamos el navegador en modo visible (headless=False) para que puedas ver el proceso
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()
        
        # 1. URL de acceso al S.Portal / Hexagon
        url_portal = "https://c5-cad-app.c5.gob.pa/Tupa/PNPC5"
        print(f"Navegando a: {url_portal}")
        page.goto(url_portal)
        
        # 2. INICIO DE SESIÓN
        print("\n" + "="*50)
        print("INSTRUCCIÓN:")
        print("Inicia sesión manualmente en la ventana del navegador que se abrió.")
        print("Navega hasta la sección de 'Detalles de Incidentes' donde se ve la lista y el rango de fechas.")
        print("Una vez que estés visualizando la tabla con los casos, presiona ENTER aquí en la consola...")
        print("="*50 + "\n")
        
        # Pausa para que entres de forma segura con tu usuario y contraseña
        input() 
            
        print("Iniciando la lectura masiva de casos desde la pantalla...")
        
        datos_consolidado = []
        
        try:
            # Localizamos las filas de la tabla de incidentes en la vista actual
            # (Ajusta el selector si la estructura HTML requiere mayor precisión)
            filas = page.locator("table tr")
            total_filas = filas.count()
            print(f"Se detectaron {total_filas} filas en la vista actual.")
            
            for i in range(1, total_filas): # Empezamos en 1 para omitir los encabezados de la tabla
                fila = filas.nth(i)
                
                try:
                    # Extracción de las columnas principales de la tabla
                    nro_incidente = fila.locator("td").nth(0).inner_text()
                    tipo = fila.locator("td").nth(1).inner_text()
                    subtipo = fila.locator("td").nth(2).inner_text()
                    ubicacion = fila.locator("td").nth(3).inner_text()
                    zona = fila.locator("td").nth(4).inner_text()
                    creacion = fila.locator("td").nth(5).inner_text()
                    operador = fila.locator("td").nth(6).inner_text()
                    
                    caso_info = {
                        "Incidente": nro_incidente.strip(),
                        "Tipo": tipo.strip(),
                        "Subtipo": subtipo.strip(),
                        "Ubicación": ubicacion.strip(),
                        "Zona": zona.strip(),
                        "Creación": creacion.strip(),
                        "Operador": operador.strip()
                    }
                    
                    datos_consolidado.append(caso_info)
                    print(f"Procesado caso [{i}/{total_filas}]: {nro_incidente}")
                    
                except Exception as e:
                    # Si alguna fila no cumple con la estructura exacta, la salta para continuar con las demás
                    continue

        except Exception as e:
            print(f"Ocurrió un error al leer la tabla de incidentes: {e}")

        # 3. EXPORTAR A EXCEL MASIVO
        if datos_consolidado:
            df = pd.DataFrame(datos_consolidado)
            nombre_archivo = "Estudio_Incidentes_S_Portal.xlsx"
            df.to_excel(nombre_archivo, index=False)
            print(f"\n¡Éxito total! Se han exportado {len(datos_consolidado)} casos al archivo: {nombre_archivo}")
        else:
            print("\nNo se recolectaron datos para exportar. Asegúrate de estar en la vista de la tabla antes de presionar ENTER.")

        browser.close()

if __name__ == "__main__":
    # Ejecución de la función principal
    extraer_incidentes_s_portal()
