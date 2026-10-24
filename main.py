import os
import time
import pandas as pd
from playwright.sync_api import sync_playwright

def extraer_incidentes_s_portal():
    print("Iniciando el navegador automatizado...")
    
    with sync_playwright() as p:
        # Puedes cambiar a headless=False si quieres ver cómo el robot abre la página y hace el trabajo
        browser = p.chromium.launch(headless=False, slow_mo=100)
        page = browser.new_page()
        
        # 1. URL de acceso al S.Portal / Hexagon (Ajusta la URL exacta de tu entorno)
        url_portal = "https://c5-cad-app.c5.gob.pa/Tupa/PNPC5" # Reemplaza con la URL base si es distinta
        print(f"Navegando a: {url_portal}")
        page.goto(url_portal)
        
        # 2. LOGIN AUTOMÁTICO (Ingresa tus selectores según los campos de usuario y contraseña)
        # Nota: Deberás verificar los IDs o nombres de los campos de texto de login si cambian
        try:
            # Ejemplo genérico de campos de usuario y contraseña (ajustar selectores si es necesario)
            # page.fill('input[name="username"]', 'TU_USUARIO')
            # page.fill('input[name="password"]', 'TU_CLAVE')
            # page.click('button[type="submit"]')
            print("Por favor, inicia sesión manualmente en la ventana del navegador que se abrio...")
            print("Una vez que estés dentro de la lista de incidentes, presiona ENTER aquí en la consola.")
            input() # Pausa para que entres con tu usuario y clave de forma segura si hay captchas o tokens
        except Exception as e:
            print(f"Error en el login: {e}")
            
        print("Iniciando la lectura masiva de casos...")
        
        # Lista para almacenar los datos extraídos de cada caso
        datos_consolidado = []
        
        # Simulación del bucle que recorrerá la tabla de incidentes
        # Aquí el script leerá las filas de la tabla principal
        filas = page.locator("table tr") # Ajustar el selector de la tabla de incidentes
        total_filas = filas.count()
        print(f"Se detectaron {total_filas} filas en la vista actual.")
        
        for i in range(1, total_filas): # Empezamos en 1 para saltar los encabezados
            fila = filas.nth(i)
            
            # Extraer columnas básicas de la tabla principal
            try:
                nro_incidente = fila.locator("td").nth(0).inner_text()
                tipo = fila.locator("td").nth(1).inner_text()
                subtipo = fila.locator("td").nth(2).inner_text()
                ubicacion = fila.locator("td").nth(3).inner_text()
                zona = fila.locator("td").nth(4).inner_text()
                creacion = fila.locator("td").nth(5).inner_text()
                operador = fila.locator("td").nth(6).inner_text()
                
                # Opcional: Si necesitas hacer clic para entrar al detalle y extraer la bitácora completa:
                # fila.locator("a").click() # o hacer clic sobre el ID del incidente
                # page.wait_for_selector(".detalle-incidente")
                # extraer detalles de la bitácora...
                # page.go_back()
                
                caso_info = {
                    "Incidente": nro_incidente,
                    "Tipo": tipo,
                    "Subtipo": subtipo,
                    "Ubicación": ubicacion,
                    "Zona": zona,
                    "Creación": creacion,
                    "Operador": operador
                }
                
                datos_consolidado.append(caso_info)
                print(f"Procesado caso {i}/{total_filas}: {nro_incidente}")
                
            except Exception as e:
                print(f"No se pudo leer la fila {i}: {e}")
                continue

        # 3. EXPORTAR A EXCEL MASIVO
        if datos_consolidado:
            df = pd.DataFrame(datos_consolidado)
            nombre_archivo = "Estudio_Incidentes_Consolidado.xlsx"
            df.to_excel(nombre_archivo, index=False)
            print(f"\n¡Éxito! Se han exportado {len(datos_consolidado)} casos al archivo: {nombre_archivo}")
        else:
            print("No se recolectaron datos para exportar.")

        browser.close()

if __name__ == "__main__":
    extrayendo = False
    # Descomenta la siguiente línea cuando configures tus selectores exactos
    # extraer_incidentes_s_portal()
