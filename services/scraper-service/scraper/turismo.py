import requests
from bs4 import BeautifulSoup
import json
import re
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlparse

def mapear_categoria_unificada(categoria_original):
    """
    Mapea categorías originales del scraper a categorías unificadas
    compatibles con el sistema de POIs.
    """
    mapeo = {
        'Visita guiada': 'Lugares Históricos',
        'Experiencias': 'Entretenimiento',
        'Paseo': 'Entretenimiento',
        'Teatro': 'Entretenimiento',
        'Música': 'Entretenimiento',
        'Danza': 'Entretenimiento',
        'Arte': 'Arte y Cultura',
        'Exposición': 'Arte y Cultura',
        'Museo': 'Arte y Cultura',
        'Cine': 'Entretenimiento',
        'Gastronomía': 'Gastronomía',
        'Feria': 'Entretenimiento',
        'Festival': 'Entretenimiento',
        'Deporte': 'Entretenimiento',
        'Infantil': 'Entretenimiento',
        'Familiar': 'Entretenimiento'
    }
    
    # Buscar mapeo exacto o parcial
    categoria_unificada = mapeo.get(categoria_original)
    if categoria_unificada:
        return categoria_unificada
    
    # Buscar coincidencias parciales (case insensitive)
    categoria_lower = categoria_original.lower()
    for original, unificada in mapeo.items():
        if original.lower() in categoria_lower or categoria_lower in original.lower():
            return unificada
    
    # Si no hay mapeo, categorizar por defecto
    return 'Entretenimiento'

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

    # Procesar las actividades del JSON para el data processor
    print(f"[scraper] Se encontraron {len(actividades)} actividades")
    
    eventos_procesados = []
    
    for idx, actividad in enumerate(actividades, start=1):
        evento = procesar_evento(actividad)
        eventos_procesados.append(evento)
        
        # Solo mostrar progreso cada 25 eventos para evitar overflow de consola
        if idx % 25 == 0 or idx <= 5 or idx == len(actividades):
            print(f"[{idx}/{len(actividades)}] {evento['nombre']} - {evento['barrio']}")
    
    # Estructurar datos para el data processor
    print(f"\n[scraper] Datos procesados para el data processor:")
    print(f"- Total de eventos: {len(eventos_procesados)}")
    print(f"- Eventos con coordenadas: {sum(1 for e in eventos_procesados if e['coordenadas_extraidas'])}")
    print(f"- Organizadores únicos: {len(set(e['organizador'] for e in eventos_procesados if e['organizador']))}")
    print(f"- Barrios únicos: {len(set(e['barrio'] for e in eventos_procesados if e['barrio']))}")
    
    return eventos_procesados


def formatear_para_data_processor(eventos_procesados):
    """
    Formatea los datos en JSON listo para el data processor - sin necesidad de parseo adicional
    """
    eventos_para_db = {
        "metadata": {
            "total_eventos": len(eventos_procesados),
            "fecha_scraping": datetime.now().isoformat(),
            "fuente": "https://turismo.buenosaires.gob.ar/es/que-hacer-en-la-ciudad",
            "version_scraper": "2.0",
            "campos_disponibles": [
                "nombre", "descripcion", "categoria_evento", "tematica", 
                "direccion_evento", "ubicacion_especifica", "latitud", "longitud", "barrio",
                "dias_semana", "hora_inicio", "hora_fin", "horarios_texto",
                "url_evento", "organizador", "categoria_precio", "tipos_compania",
                "tags_descuento", "foto_url"
            ]
        },
        "eventos": []
    }
    
    for evento in eventos_procesados:
        # Estructura ajustada al nuevo esquema de BD (solo campos existentes)
        evento_limpio = {
            # CAMPOS PRINCIPALES DE LA TABLA EVENTOS
            "nombre": evento['nombre'] or "",
            "descripcion": evento['descripcion'] or "",
            "categoria_evento": evento['categoria_evento'] or "",
            "tematica": evento['tematica'] or "",
            
            # UBICACIÓN - Solo campos que existen en la tabla
            "direccion_evento": evento['direccion_evento'] or "",
            "ubicacion_especifica": evento['ubicacion_especifica'] or "",
            "latitud": evento['latitud'],  # puede ser None
            "longitud": evento['longitud'],  # puede ser None
            "barrio": evento['barrio'] or "",
            
            # FECHAS Y HORARIOS - Solo campos que existen
            "dias_semana": evento['dias_semana'] or "",  # formato: LMXJVSD
            "hora_inicio": evento['hora_inicio'],  # formato: HH:MM:SS o None
            "hora_fin": evento['hora_fin'],  # formato: HH:MM:SS o None
            
            # CONTACTO Y URLs - Solo campos que existen en la tabla
            "url_evento": evento['url_evento'] or "",
            
            # METADATA SCRAPING
            "fecha_scraping": evento['fecha_scraping'],
            "url_fuente": "https://turismo.buenosaires.gob.ar/es/que-hacer-en-la-ciudad",
            
            # CAMPOS ADICIONALES DEL SCRAPER (no van a la BD, son para análisis)
            "organizador": evento['organizador'] or "",  # EXTRA: no existe en tabla eventos
            "categoria_precio": evento['categoria_precio'] or "",  # EXTRA: para análisis
            "tipos_compania": evento['tipos_compania'] or "",  # EXTRA: para análisis
            "tags_descuento": evento['tags_descuento'] or "",  # EXTRA: para análisis
            "foto_url": evento['foto_url'] or "",  # EXTRA: para análisis
            "horarios_texto": evento['horarios_texto'] or ""  # EXTRA: texto original sin parsear
        }
        
        eventos_para_db["eventos"].append(evento_limpio)
    
    return eventos_para_db


def extraer_datos_para_bd_eventos(evento_completo):
    """
    Extrae solo los campos que van directamente a la tabla eventos de la BD
    Elimina campos extra que no existen en el esquema
    """
    return {
        # CAMPOS QUE EXISTEN EN LA TABLA EVENTOS
        "nombre": evento_completo.get('nombre', ''),
        "descripcion": evento_completo.get('descripcion', ''),
        "categoria_evento": evento_completo.get('categoria_evento', ''),
        "tematica": evento_completo.get('tematica', ''),
        
        # Ubicación
        "direccion_evento": evento_completo.get('direccion_evento', ''),
        "ubicacion_especifica": evento_completo.get('ubicacion_especifica', ''),
        "latitud": evento_completo.get('latitud'),
        "longitud": evento_completo.get('longitud'),
        "barrio": evento_completo.get('barrio', ''),
        
        # Fechas y horarios
        "dias_semana": evento_completo.get('dias_semana', ''),
        "hora_inicio": evento_completo.get('hora_inicio'),
        "hora_fin": evento_completo.get('hora_fin'),
        
        # URLs de contacto
        "url_evento": evento_completo.get('url_evento', ''),
        
        # Metadata
        "fecha_scraping": evento_completo.get('fecha_scraping'),
        "url_fuente": evento_completo.get('url_fuente', '')
    }


def obtener_eventos_para_data_processor():
    """
    Función directa para el data processor - Retorna eventos sin generar archivos
    """
    print("[data-processor-api] Obteniendo eventos desde scraper...")
    
    eventos_raw = scrap_turismo()
    if eventos_raw:
        datos_estructurados = formatear_para_data_processor(eventos_raw)
        print(f"[data-processor-api] {len(datos_estructurados['eventos'])} eventos obtenidos")
        return datos_estructurados
    else:
        print("[data-processor-api]  No se pudieron obtener eventos")
        return None


def procesar_evento(actividad):
    """
    Procesa una actividad del JSON y extrae todos los campos necesarios para el data processor
    """
    evento = {}
    
    # INFORMACIÓN BÁSICA
    evento['nombre'] = actividad.get('nombre_actividad', 'Sin título')
    evento['descripcion'] = limpiar_html(actividad.get('descripcion', ''))
    
    # MAPEO DE CATEGORÍAS UNIFICADAS - Compatible con POIs
    categoria_original = actividad.get('categoria_actividad_filtro', '')
    evento['categoria_evento'] = mapear_categoria_unificada(categoria_original)
    evento['tematica'] = actividad.get('tematica_actividad_filtro', '')
    
    # UBICACIÓN
    evento['direccion_evento'] = actividad.get('calle_altura', '')
    evento['barrio'] = actividad.get('barrio', '')
    evento['latitud'] = None
    evento['longitud'] = None
    evento['coordenadas_extraidas'] = False
    
    # Extraer coordenadas de la URL de Google Maps
    coordenadas_url = actividad.get('coordenadas', '')
    if coordenadas_url:
        lat, lng = extraer_coordenadas(coordenadas_url)
        if lat and lng:
            evento['latitud'] = lat
            evento['longitud'] = lng
            evento['coordenadas_extraidas'] = True
    
    # FECHAS Y HORARIOS
    evento['dias_semana'] = procesar_dias_filtro(actividad.get('dias_filtro', ''))
    evento['horarios_texto'] = actividad.get('dias_horarios', '')
    evento['hora_inicio'], evento['hora_fin'] = extraer_horarios(evento['horarios_texto'])
    
    # PRECIOS Y CATEGORÍAS
    evento['categoria_precio'] = actividad.get('precio_filtro', '')  # Descuento, Gratuito, etc.
    evento['tags_descuento'] = actividad.get('tags', '')
    
    # ORGANIZADOR Y COMPAÑÍA
    evento['organizador'] = actividad.get('proveedor', '')
    evento['tipos_compania'] = actividad.get('tipo_compania_filtro', '')  # solo, en pareja, etc.
    
    # URLS Y CONTACTO
    evento['url_evento'] = actividad.get('url_boton', '')
    evento['foto_url'] = actividad.get('foto', '')
    
    # METADATA
    evento['orden_original'] = actividad.get('orden', '')
    evento['fecha_scraping'] = datetime.now().isoformat()
    
    # UBICACIÓN ESPECÍFICA (extraer de descripción si es necesario)
    evento['ubicacion_especifica'] = extraer_ubicacion_especifica(evento['descripcion'])
    
    return evento


def limpiar_html(texto):
    """Limpia tags HTML y entidades del texto"""
    if not texto:
        return ''
    # Limpiar HTML tags
    texto_limpio = re.sub(r'<[^>]+>', '', texto)
    # Limpiar entidades HTML comunes
    texto_limpio = texto_limpio.replace('&#34;', '"').replace('&amp;', '&')
    return texto_limpio.strip()


def extraer_coordenadas(coordenadas_url):
    """
    Extrae latitud y longitud de una URL de Google Maps
    Ejemplo: 'https://www.google.com/maps?q=-34.5626255,-58.4709615'
    """
    try:
        if '?q=' in coordenadas_url:
            # Extraer la parte después de ?q=
            coords_part = coordenadas_url.split('?q=')[1]
            # Separar latitud y longitud
            if ',' in coords_part:
                lat_str, lng_str = coords_part.split(',', 1)
                lat = float(lat_str.strip())
                lng = float(lng_str.strip())
                return lat, lng
    except (ValueError, IndexError):
        pass
    return None, None


def procesar_dias_filtro(dias_filtro):
    """
    Convierte el formato 'jueves,viernes,sabado,domingo' a formato estándar
    """
    if not dias_filtro:
        return ''
    
    # Mapeo de días en español a formato estándar
    mapeo_dias = {
        'lunes': 'L',
        'martes': 'M',
        'miercoles': 'X',
        'jueves': 'J',
        'viernes': 'V',
        'sabado': 'S',
        'domingo': 'D'
    }
    
    dias_lista = [dia.strip().lower() for dia in dias_filtro.split(',')]
    dias_codigo = []
    
    for dia in dias_lista:
        if dia in mapeo_dias:
            dias_codigo.append(mapeo_dias[dia])
    
    return ''.join(dias_codigo)


def extraer_horarios(horarios_texto):
    """
    Extrae hora de inicio y fin del texto de horarios
    Ejemplo: 'Jueves a domingos, de 14 a 19 h.'
    """
    if not horarios_texto:
        return None, None
    
    # Buscar patrones de horario como "de 14 a 19" o "14 a 17"
    patron_horario = r'de\s+(\d{1,2})\s+a\s+(\d{1,2})'
    match = re.search(patron_horario, horarios_texto)
    
    if match:
        hora_inicio = f"{match.group(1)}:00:00"
        hora_fin = f"{match.group(2)}:00:00"
        return hora_inicio, hora_fin
    
    return None, None


def extraer_ubicacion_especifica(descripcion):
    """
    Intenta extraer información de ubicación específica de la descripción
    """
    if not descripcion:
        return ''
    
    # Buscar patrones como "Sala X", "Auditorio", "Patio", etc.
    patrones_ubicacion = [
        r'(Sala\s+[^\s,\.]+)',
        r'(Auditorio[^\s,\.]*)',
        r'(Patio\s+[^\s,\.]+)',
        r'(Anexo\s+[^\s,\.]+)'
    ]
    
    for patron in patrones_ubicacion:
        match = re.search(patron, descripcion, re.IGNORECASE)
        if match:
            return match.group(1)
    
    return ''
