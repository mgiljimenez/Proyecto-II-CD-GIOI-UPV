import csv
from bs4 import BeautifulSoup

# Abrir archivo HTML local
with open("sectores.html", "r", encoding="utf-8") as f:
    html = f.read()

# Crear el objeto BeautifulSoup
soup = BeautifulSoup(html, "html.parser")

# Buscar el div con todas esas clases
div_objetivo = soup.find("div", class_="home-search-results-items app_mobileCollapsableSectorItems")
if not div_objetivo:
    raise ValueError("No se encontró el div con clase 'home-search-results-items app_mobileCollapsableSectorItems'")

# Buscar todos los enlaces de sectores
sectores = div_objetivo.find_all("a", class_="app_ij_Track")

# Crear y guardar CSV
with open("sectores.csv", "w", encoding="utf-8", newline="") as f_csv:
    writer = csv.writer(f_csv)
    writer.writerow(["sector", "url_sector"])  # encabezados
    for sector in sectores:
        name = sector.text.strip()
        url_sector = sector.get("href", "")
        writer.writerow([name, url_sector])

print("Archivo CSV generado: sectores.csv")
