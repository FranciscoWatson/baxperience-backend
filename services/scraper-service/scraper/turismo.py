import requests
from bs4 import BeautifulSoup
import json
import re

def scrap_turismo():
    url = "https://turismo.buenosaires.gob.ar/es/que-hacer-en-la-ciudad"
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64; rv:140.0) Gecko/20100101 Firefox/140.0"
    }
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        content = response.content.decode('utf-8')
        print("[scraper] HTML descargado desde la web.")
    except Exception as e:
        print(f"[scraper] Error al acceder a la página: {e}")
        return

    soup = BeautifulSoup(content, 'lxml')

    # Buscar el JSON embebido en el JavaScript
    actividades = []
    
    # El archivo HTML está codificado con spans, necesitamos extraer el texto plano
    # Buscar el patrón const json = ` seguido del contenido JSON
    json_pattern = r'const json = `(.*?)`'
    json_match = re.search(json_pattern, content, re.DOTALL)
    
    if json_match:
        json_content = json_match.group(1)
        
        # El contenido puede estar dentro de spans HTML, necesitamos limpiarlo
        # Primero remover los spans y extraer solo el texto
        clean_json = re.sub(r'</span></span><span[^>]*><span[^>]*>', '', json_content)
        clean_json = re.sub(r'<[^>]+>', '', clean_json)
        clean_json = clean_json.strip()
        
        if clean_json:
            try:
                data = json.loads(clean_json)
                if isinstance(data, list):
                    actividades = data
                print(f"[scraper] JSON encontrado con {len(actividades)} actividades")
            except json.JSONDecodeError as e:
                print(f"[scraper] Error al parsear JSON: {e}")
                print(f"[scraper] Primeros 200 caracteres del JSON: {clean_json[:200]}")
    
    if not actividades:
        print("[scraper] No se pudo extraer el JSON, intentando método alternativo...")
        # Buscar directamente en el texto usando BeautifulSoup
        soup_text = soup.get_text()
        json_match_alt = re.search(r'\[{"orden":[^}]+}.*?\]', soup_text, re.DOTALL)
        if json_match_alt:
            try:
                data = json.loads(json_match_alt.group(0))
                if isinstance(data, list):
                    actividades = data
                print(f"[scraper] JSON alternativo encontrado con {len(actividades)} actividades")
            except json.JSONDecodeError as e:
                print(f"[scraper] Error al parsear JSON alternativo: {e}")

    # Si no se encontraron actividades en el JSON, buscar en el HTML estático (fallback)
    if not actividades:
        print("[scraper] No se encontraron actividades en el JSON, buscando en HTML estático...")
        cards = soup.find_all("div", class_="views-row")
        print(f"[scraper] Se encontraron {len(cards)} actividades en HTML estático")
        
        for idx, card in enumerate(cards, start=1):
            title_div = card.find("div", class_="views-field-title")
            if title_div:
                link = title_div.find("a")
                if link:
                    title = link.text.strip()
                    href = link['href']
                    print(f"{idx}. {title} → https://turismo.buenosaires.gob.ar{href}")
        return

    # Procesar las actividades del JSON
    print(f"[scraper] Se encontraron {len(actividades)} actividades")
    
    for idx, actividad in enumerate(actividades, start=1):
        titulo = actividad.get('nombre_actividad', 'Sin título')
        categoria = actividad.get('categoria_actividad_filtro', '')
        tematica = actividad.get('tematica_actividad_filtro', '')
        precio = actividad.get('precio_actividad_filtro', '')
        url_boton = actividad.get('url_boton', '')
        descripcion = actividad.get('descripcion', '')
        
        # Construir información adicional
        info_adicional = []
        if categoria:
            info_adicional.append(f"Categoría: {categoria}")
        if tematica:
            info_adicional.append(f"Temática: {tematica}")
        if precio:
            info_adicional.append(f"Precio: {precio}")
        
        info_str = " | ".join(info_adicional) if info_adicional else ""
        
        print(f"{idx}. {titulo}")
        if info_str:
            print(f"   {info_str}")
        if descripcion:
            # Limpiar la descripción de HTML tags
            desc_clean = re.sub(r'<[^>]+>', '', descripcion).strip()
            if desc_clean:
                print(f"   Descripción: {desc_clean[:100]}{'...' if len(desc_clean) > 100 else ''}")
        if url_boton:
            print(f"   URL: {url_boton}")
        print()
