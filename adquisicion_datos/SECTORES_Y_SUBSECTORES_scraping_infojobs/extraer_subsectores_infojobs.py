import os
import csv
from bs4 import BeautifulSoup

carpeta = "subsectores_html"
salida_csv = "subsectores.csv"

# Abrimos el CSV para escribir resultados
with open(salida_csv, "w", encoding="utf-8", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sector", "subsector", "url_subsector"])  # encabezados

    # Iterar sobre todos los archivos HTML en la carpeta
    for archivo in os.listdir(carpeta):
        if not archivo.endswith(".html"):
            continue  # ignorar archivos que no sean HTML

        ruta = os.path.join(carpeta, archivo)
        print(f"Procesando: {archivo}")

        # Leer el contenido HTML
        with open(ruta, "r", encoding="utf-8") as f_html:
            html = f_html.read()

        # Crear el objeto BeautifulSoup
        soup = BeautifulSoup(html, "html.parser")

        # Buscar el div con la clase deseada
        div_objetivo = soup.find("div", class_="center-inline-list-desk")
        if not div_objetivo:
            print(f"No se encontró el div en {archivo}")
            continue

        # Buscar los enlaces dentro del div
        subsectores = div_objetivo.find_all("a", class_="app_ij_Track")

        # Extraer nombre y URL y escribirlos en el CSV
        for subsector in subsectores:
            name = subsector.text.strip()
            url_subsector = subsector.get("href", "")
            writer.writerow([archivo.replace(".html",""), name, url_subsector])