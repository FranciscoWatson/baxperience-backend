"""
BAXperience - Procesador de CSVs a Base de Datos Operacional
============================================================

Este script procesa todos los CSVs filtrados y los inserta en la base de datos operacional.
Cada CSV tiene un formato diferente, por lo que se necesita una función específica para cada uno.

Arquitectura:
1. Procesar CSVs → BD Operacional (completa)
2. ETL: BD Operacional → BD Data Processor (optimizada para clustering)

Autor: BAXperience Team
"""

import pandas as pd
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import sys
from datetime import datetime
import hashlib
import logging
import requests
import time
from typing import Dict, List, Optional, Tuple
import time
from geopy.geocoders import Nominatim
try:
    from geopy.extra.rate_limiter import RateLimiter
except ImportError:
    # Fallback para versiones más nuevas de geopy
    from geopy import RateLimiter
import requests

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_processor.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DatabaseConfig:
    """Configuración de conexiones a bases de datos"""
    
    # BD Operacional (principal)
    OPERATIONAL_DB = {
        'host': os.getenv('OPERATIONAL_DB_HOST', 'localhost'),
        'port': os.getenv('OPERATIONAL_DB_PORT', '5432'),
        'database': os.getenv('OPERATIONAL_DB_NAME', 'OPERATIONAL_DB'),
        'user': os.getenv('OPERATIONAL_DB_USER', 'postgres'),
        'password': os.getenv('OPERATIONAL_DB_PASSWORD', 'admin')
    }
    
    # BD Data Processor (para clustering)
    PROCESSOR_DB = {
        'host': os.getenv('PROCESSOR_DB_HOST', 'localhost'),
        'port': os.getenv('PROCESSOR_DB_PORT', '5432'),
        'database': os.getenv('PROCESSOR_DB_NAME', 'PROCESSOR_DB'),
        'user': os.getenv('PROCESSOR_DB_USER', 'postgres'),
        'password': os.getenv('PROCESSOR_DB_PASSWORD', 'admin')
    }

class BarrioGeocoder:
    """
    Servicio para obtener barrios de Buenos Aires basándose en coordenadas
    Usa APIs públicas para geocodificación inversa
    """
    
    def __init__(self):
        self.cache = {}  # Cache para evitar consultas repetidas
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BAXperience/1.0 (Tourism Recommendation System)'
        })
        self.rate_limit_delay = 0.1  # 100ms entre requests
        self.last_request_time = 0
        
    def _rate_limit(self):
        """Aplicar rate limiting"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit_delay:
            time.sleep(self.rate_limit_delay - time_since_last)
        self.last_request_time = time.time()
    
    def get_barrio_by_coordinates(self, lat: float, lng: float) -> Optional[str]:
        """
        Obtener barrio basándose en coordenadas usando API de geocodificación
        """
        if lat is None or lng is None:
            return None
            
        # Crear clave para cache
        cache_key = f"{lat:.6f},{lng:.6f}"
        if cache_key in self.cache:
            return self.cache[cache_key]
        
        # Rate limiting
        self._rate_limit()
        
        try:
            # Intentar con API de Buenos Aires Data (más específica)
            barrio = self._get_barrio_from_ba_data(lat, lng)
            
            if not barrio:
                # Fallback a Nominatim (OpenStreetMap)
                barrio = self._get_barrio_from_nominatim(lat, lng)
            
            # Limpiar resultado
            barrio_clean = self._clean_barrio_name(barrio) if barrio else None
            
            # Guardar en cache
            self.cache[cache_key] = barrio_clean
            
            if barrio_clean:
                logger.debug(f"Barrio encontrado para {lat},{lng}: {barrio_clean}")
            
            return barrio_clean
            
        except Exception as e:
            logger.warning(f"Error obteniendo barrio para {lat},{lng}: {e}")
            return None
    
    def _get_barrio_from_ba_data(self, lat: float, lng: float) -> Optional[str]:
        """
        Obtener barrio usando la API de Buenos Aires Data
        """
        try:
            # API de Buenos Aires para obtener información por coordenadas
            url = "https://servicios.usig.buenosaires.gob.ar/normalizar"
            params = {
                'lat': lat,
                'lng': lng,
                'format': 'json'
            }
            
            response = self.session.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extraer barrio del resultado
                if isinstance(data, dict):
                    # Buscar en diferentes campos posibles
                    barrio = (data.get('barrio') or 
                             data.get('neighbourhood') or
                             data.get('localidad') or
                             data.get('partido'))
                    
                    if barrio and isinstance(barrio, str):
                        return barrio.strip()
                        
        except Exception as e:
            logger.debug(f"Error con API BA Data: {e}")
            
        return None
    
    def _get_barrio_from_nominatim(self, lat: float, lng: float) -> Optional[str]:
        """
        Obtener barrio usando Nominatim (OpenStreetMap) como fallback
        """
        try:
            url = "https://nominatim.openstreetmap.org/reverse"
            params = {
                'lat': lat,
                'lon': lng,
                'format': 'json',
                'addressdetails': 1,
                'accept-language': 'es'
            }
            
            response = self.session.get(url, params=params, timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'address' in data:
                    address = data['address']
                    
                    # Buscar barrio en diferentes campos
                    barrio = (address.get('neighbourhood') or
                             address.get('suburb') or
                             address.get('quarter') or
                             address.get('city_district') or
                             address.get('district'))
                    
                    if barrio and isinstance(barrio, str):
                        return barrio.strip()
                        
        except Exception as e:
            logger.debug(f"Error con Nominatim: {e}")
            
        return None
    
    def _clean_barrio_name(self, barrio: str) -> str:
        """
        Limpiar y normalizar nombre de barrio
        """
        if not barrio:
            return None
            
        # Convertir a título y limpiar
        barrio_clean = barrio.strip().title()
        
        # Mapeos específicos para Buenos Aires
        barrio_mappings = {
            'Microcentro': 'San Nicolas',
            'Centro': 'San Nicolas',
            'Casco Histórico': 'San Telmo',
            'Puerto Madero Este': 'Puerto Madero',
            'Puerto Madero Oeste': 'Puerto Madero',
            'Barrio Norte': 'Recoleta',
            'Las Cañitas': 'Palermo',
            'Palermo Soho': 'Palermo',
            'Palermo Hollywood': 'Palermo',
            'Villa Crespo': 'Villa Crespo',
            'Once': 'Balvanera'
        }
        
        return barrio_mappings.get(barrio_clean, barrio_clean)
    
    def get_stats(self) -> Dict:
        """Obtener estadísticas del geocoder"""
        return {
            'cache_size': len(self.cache),
            'cached_barrios': list(set(v for v in self.cache.values() if v))
        }

class GeocodingService:
    """Servicio de geocoding reverso para obtener barrios desde coordenadas"""
    
    def __init__(self):
        # Configurar Nominatim con rate limiting
        self.geolocator = Nominatim(
            user_agent="BAXperience-geocoding/1.0", 
            timeout=10
        )
        # Rate limiter: máximo 1 request por segundo para ser respetuoso con la API
        self.reverse_geocode = RateLimiter(
            self.geolocator.reverse, 
            min_delay_seconds=1.2
        )
        self.cache = {}  # Cache para evitar requests repetidos
        
    def get_barrio_from_coordinates(self, lat: float, lng: float) -> Optional[str]:
        """
        Obtener el barrio desde coordenadas usando geocoding reverso
        
        Args:
            lat: Latitud
            lng: Longitud
            
        Returns:
            Nombre del barrio o None si no se encuentra
        """
        if not lat or not lng or lat == 0 or lng == 0:
            return None
            
        # Crear key para cache
        cache_key = f"{lat:.6f},{lng:.6f}"
        
        # Verificar cache primero
        if cache_key in self.cache:
            return self.cache[cache_key]
            
        try:
            # Hacer geocoding reverso
            location = self.reverse_geocode((lat, lng), language='es')
            
            if location:
                address = location.raw.get('address', {})
                
                # Buscar barrio en diferentes campos posibles
                barrio = None
                
                # Prioridad de campos para Buenos Aires
                for field in ['suburb', 'neighbourhood', 'quarter', 'village', 'town', 'district']:
                    if field in address:
                        barrio = address[field]
                        break
                
                # Si no encontramos barrio, usar city_district
                if not barrio and 'city_district' in address:
                    barrio = address['city_district']
                    
                # Limpiar el nombre del barrio
                if barrio:
                    barrio = self._clean_barrio_name(barrio)
                    
                # Guardar en cache
                self.cache[cache_key] = barrio
                
                if barrio:
                    logger.debug(f"Geocoding: ({lat}, {lng}) -> {barrio}")
                else:
                    logger.debug(f"Geocoding: ({lat}, {lng}) -> No barrio encontrado")
                    
                return barrio
                
        except Exception as e:
            logger.warning(f"Error en geocoding para ({lat}, {lng}): {e}")
            # Guardar None en cache para evitar reintentos
            self.cache[cache_key] = None
            
        return None
    
    def _clean_barrio_name(self, barrio: str) -> str:
        """Limpiar y normalizar nombres de barrios"""
        if not barrio:
            return None
            
        # Convertir a título (primera letra mayúscula)
        barrio = barrio.strip().title()
        
        # Mapeo de nombres comunes para Buenos Aires
        barrio_mapping = {
            'San Nicolás': 'San Nicolas',
            'Micro Centro': 'San Nicolas',
            'Microcentro': 'San Nicolas',
            'Centro': 'San Nicolas',
            'La Boca': 'Boca',
            'Puerto Madero': 'Puerto Madero',
            'San Telmo': 'San Telmo',
            'Recoleta': 'Recoleta',
            'Palermo': 'Palermo',
            'Belgrano': 'Belgrano',
            'Villa Crespo': 'Villa Crespo',
            'Caballito': 'Caballito',
            'Balvanera': 'Balvanera',
            'Barracas': 'Barracas',
            'Constitución': 'Constitucion',
            'Retiro': 'Retiro',
            'Monserrat': 'Monserrat'
        }
        
        return barrio_mapping.get(barrio, barrio)
    
    def get_cache_stats(self) -> dict:
        """Obtener estadísticas del cache"""
        return {
            'total_entries': len(self.cache),
            'successful_geocoding': sum(1 for v in self.cache.values() if v is not None),
            'failed_geocoding': sum(1 for v in self.cache.values() if v is None)
        }

class CSVProcessor:
    """Procesador principal de CSVs"""
    
    def __init__(self):
        self.operational_conn = None
        self.processor_conn = None
        # Obtener ruta absoluta del directorio actual
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Subir dos niveles (services/data-processor-service) y entrar a csv-filtrados
        self.csv_base_path = os.path.join(current_dir, "csv-filtrados")
        self.categoria_ids = {}
        self.subcategoria_ids = {}
        
        # Inicializar geocoder mejorado
        self.geocoder = BarrioGeocoder()
        logger.info("Geocoder mejorado inicializado")
        
    def connect_databases(self):
        """Conectar a ambas bases de datos"""
        try:
            # Conexión a BD Operacional
            self.operational_conn = psycopg2.connect(**DatabaseConfig.OPERATIONAL_DB)
            self.operational_conn.autocommit = False
            logger.info("Conectado a BD Operacional")
            
            # Conexión a BD Data Processor (opcional por ahora)
            try:
                self.processor_conn = psycopg2.connect(**DatabaseConfig.PROCESSOR_DB)
                self.processor_conn.autocommit = False
                logger.info("Conectado a BD Data Processor")
            except Exception as e:
                logger.warning(f"No se pudo conectar a BD Data Processor: {e}")
                self.processor_conn = None
                
        except Exception as e:
            logger.error(f"Error conectando a bases de datos: {e}")
            raise
            
    def disconnect_databases(self):
        """Cerrar conexiones"""
        if self.operational_conn:
            self.operational_conn.close()
            logger.info("Desconectado de BD Operacional")
        if self.processor_conn:
            self.processor_conn.close()
            logger.info("Desconectado de BD Data Processor")
            
    def load_categoria_mappings(self):
        """Cargar IDs de categorías y subcategorías para mapeo"""
        cursor = self.operational_conn.cursor(cursor_factory=RealDictCursor)
        
        # Cargar categorías
        cursor.execute("SELECT id, nombre FROM categorias")
        for row in cursor.fetchall():
            self.categoria_ids[row['nombre'].lower()] = row['id']
            
        # Cargar subcategorías
        cursor.execute("SELECT id, nombre, categoria_id FROM subcategorias")
        for row in cursor.fetchall():
            key = f"{row['categoria_id']}_{row['nombre'].lower()}"
            self.subcategoria_ids[key] = row['id']
            
        cursor.close()
        logger.info(f"Cargadas {len(self.categoria_ids)} categorías y {len(self.subcategoria_ids)} subcategorías")
        
    def get_categoria_id(self, categoria_name: str) -> int:
        """Obtener ID de categoría por nombre"""
        categoria_key = categoria_name.lower()
        return self.categoria_ids.get(categoria_key)
        
    def get_subcategoria_id(self, categoria_id: int, subcategoria_name: str) -> Optional[int]:
        """Obtener ID de subcategoría por nombre y categoría"""
        subcategoria_key = f"{categoria_id}_{subcategoria_name.lower()}"
        return self.subcategoria_ids.get(subcategoria_key)
        
    def clean_coordinate(self, coord_str: str) -> Optional[float]:
        """Limpiar y convertir coordenadas"""
        if pd.isna(coord_str) or coord_str == '':
            return None
        try:
            # Reemplazar comas por puntos para decimales
            coord_clean = str(coord_str).replace(',', '.')
            return float(coord_clean)
        except (ValueError, TypeError):
            return None
            
    def clean_phone(self, phone_str: str) -> Optional[str]:
        """Limpiar números de teléfono"""
        if pd.isna(phone_str) or phone_str == '':
            return None
        # Remover espacios y caracteres especiales innecesarios
        phone_clean = str(phone_str).replace(' ', '').replace('-', '')
        return phone_clean if phone_clean else None
        
    def clean_text(self, text: str) -> Optional[str]:
        """Limpiar texto general"""
        if pd.isna(text) or text == '' or str(text).lower() == 'nan':
            return None
        return str(text).strip()
        
    def extract_comuna_number(self, comuna_str: str) -> Optional[str]:
        """Extraer número de comuna del texto"""
        if pd.isna(comuna_str) or comuna_str == '':
            return None
        
        # Convertir a string y buscar números
        comuna_text = str(comuna_str).upper()
        
        # Si contiene "COMUNA" seguido de número
        import re
        match = re.search(r'COMUNA\s*(\d+)', comuna_text)
        if match:
            return match.group(1)
        
        # Si es solo un número
        if comuna_text.isdigit():
            return comuna_text
            
        return None

    def insert_poi(self, poi_data: Dict) -> int:
        """Insertar POI en base de datos operacional con geocoding automático de barrios"""
        cursor = self.operational_conn.cursor()
        
        # GEOCODING AUTOMÁTICO: Si no tiene barrio pero tiene coordenadas, calcularlo
        if (not poi_data.get('barrio') or poi_data.get('barrio') in ['Sin especificar', '', None]) and \
           poi_data.get('latitud') and poi_data.get('longitud'):
            
            try:
                lat = float(poi_data['latitud'])
                lng = float(poi_data['longitud'])
                
                logger.debug(f"Calculando barrio para POI '{poi_data.get('nombre', 'Unknown')}' en ({lat}, {lng})")
                
                # Obtener barrio mediante geocoding mejorado
                barrio_calculado = self.geocoder.get_barrio_by_coordinates(lat, lng)
                
                if barrio_calculado:
                    poi_data['barrio'] = barrio_calculado
                    logger.info(f"[OK] Barrio calculado: '{poi_data['nombre']}' -> {barrio_calculado}")
                else:
                    logger.debug(f"[WARN] No se pudo calcular barrio para '{poi_data.get('nombre', 'Unknown')}'")
                    poi_data['barrio'] = 'Sin especificar'
            except (ValueError, TypeError) as e:
                logger.warning(f"Error convirtiendo coordenadas para geocoding: {e}")
        
        insert_query = """
        INSERT INTO pois (
            nombre, descripcion, categoria_id, subcategoria_id,
            latitud, longitud, direccion,
            calle, altura, piso, codigo_postal, barrio, comuna,
            telefono, codigo_area, email, web,
            tipo_cocina, tipo_ambiente, horario,
            material, autor, denominacion_simboliza,
            fuente_original, id_fuente_original
        ) VALUES (
            %(nombre)s, %(descripcion)s, %(categoria_id)s, %(subcategoria_id)s,
            %(latitud)s, %(longitud)s, %(direccion)s,
            %(calle)s, %(altura)s, %(piso)s, %(codigo_postal)s, %(barrio)s, %(comuna)s,
            %(telefono)s, %(codigo_area)s, %(email)s, %(web)s,
            %(tipo_cocina)s, %(tipo_ambiente)s, %(horario)s,
            %(material)s, %(autor)s, %(denominacion_simboliza)s,
            %(fuente_original)s, %(id_fuente_original)s
        ) RETURNING id
        """
        
        cursor.execute(insert_query, poi_data)
        poi_id = cursor.fetchone()[0]
        cursor.close()
        return poi_id

    def process_museos_csv(self) -> int:
        """Procesar CSV de museos"""
        logger.info("Procesando museos...")
        
        csv_path = os.path.join(self.csv_base_path, "museos-filtrado.csv")
        print(f"Intentando leer archivo: {csv_path}")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No se encuentra el archivo: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        categoria_id = self.get_categoria_id('museos')
        subcategoria_id = self.get_subcategoria_id(categoria_id, 'museos especializados')  # Default
        
        count = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                # Determinar subcategoría basada en el nombre del museo
                nombre = self.clean_text(row.get('nombre', ''))
                if not nombre:
                    continue
                    
                # Lógica simple para determinar subcategoría
                subcategoria_actual = subcategoria_id
                nombre_lower = nombre.lower()
                if any(word in nombre_lower for word in ['arte', 'malba', 'pintura']):
                    subcategoria_actual = self.get_subcategoria_id(categoria_id, 'museos de arte')
                elif any(word in nombre_lower for word in ['historia', 'histórico', 'patricios']):
                    subcategoria_actual = self.get_subcategoria_id(categoria_id, 'museos de historia')
                elif any(word in nombre_lower for word in ['ciencia', 'matemática', 'mineralogía']):
                    subcategoria_actual = self.get_subcategoria_id(categoria_id, 'museos de ciencia')
                
                poi_data = {
                    'nombre': nombre,
                    'descripcion': self.clean_text(row.get('Observaciones')),
                    'categoria_id': categoria_id,
                    'subcategoria_id': subcategoria_actual or subcategoria_id,
                    'latitud': self.clean_coordinate(row.get('Latitud')),
                    'longitud': self.clean_coordinate(row.get('Longitud')),
                    'direccion': self.clean_text(row.get('direccion')),
                    'calle': None,
                    'altura': None,
                    'piso': self.clean_text(row.get('piso')),
                    'codigo_postal': self.clean_text(row.get('CP')),
                    'barrio': None,
                    'comuna': None,
                    'telefono': self.clean_phone(row.get('telefono')),
                    'codigo_area': self.clean_text(row.get('cod_area')),
                    'email': self.clean_text(row.get('Mail')),
                    'web': self.clean_text(row.get('Web')),
                    'tipo_cocina': None,
                    'tipo_ambiente': None,
                    'horario': None,
                    'material': None,
                    'autor': None,
                    'denominacion_simboliza': None,
                    'fuente_original': 'csv_museos',
                    'id_fuente_original': self.clean_text(row.get('Cod_Loc'))
                }
                
                # Validar datos mínimos requeridos
                if poi_data['latitud'] is None or poi_data['longitud'] is None:
                    logger.warning(f"Museo sin coordenadas: {nombre}")
                    continue
                    
                poi_id = self.insert_poi(poi_data)
                count += 1
                
                if count % 10 == 0:
                    logger.info(f"Procesados {count} museos...")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error procesando museo {row.get('nombre', 'sin nombre')}: {e}")
                
        self.operational_conn.commit()
        logger.info(f"Museos procesados: {count} exitosos, {errors} errores")
        return count

    def process_gastronomia_csv(self) -> int:
        """Procesar CSV de gastronomía"""
        logger.info("Procesando gastronomía...")
        
        csv_path = os.path.join(self.csv_base_path, "oferta-gastronomica.csv")
        print(f"Intentando leer archivo: {csv_path}")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No se encuentra el archivo: {csv_path}")
        df = pd.read_csv(csv_path, encoding='latin1', sep=';')
        
        categoria_id = self.get_categoria_id('gastronomía')
        
        count = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                nombre = self.clean_text(row.get('nombre', ''))
                if not nombre:
                    continue
                    
                # Mapear categoría del CSV a subcategoría
                categoria_csv = self.clean_text(row.get('categoria', ''))
                subcategoria_id = None
                
                if categoria_csv:
                    categoria_lower = categoria_csv.lower()
                    if 'restaurante' in categoria_lower:
                        subcategoria_id = self.get_subcategoria_id(categoria_id, 'restaurante')
                    elif 'cafe' in categoria_lower or 'café' in categoria_lower:
                        subcategoria_id = self.get_subcategoria_id(categoria_id, 'café')
                    elif 'bar' in categoria_lower:
                        subcategoria_id = self.get_subcategoria_id(categoria_id, 'bar')
                    elif 'parrilla' in categoria_lower:
                        subcategoria_id = self.get_subcategoria_id(categoria_id, 'parrilla')
                    elif 'vineria' in categoria_lower:
                        subcategoria_id = self.get_subcategoria_id(categoria_id, 'vinería')
                
                # Si no encontramos subcategoría específica, usar default
                if not subcategoria_id:
                    subcategoria_id = self.get_subcategoria_id(categoria_id, 'restaurante')
                
                poi_data = {
                    'nombre': nombre,
                    'descripcion': None,
                    'categoria_id': categoria_id,
                    'subcategoria_id': subcategoria_id,
                    'latitud': self.clean_coordinate(row.get('lat')),
                    'longitud': self.clean_coordinate(row.get('long')),
                    'direccion': self.clean_text(row.get('direccion_completa')),
                    'calle': self.clean_text(row.get('calle_nombre')),
                    'altura': self.clean_text(row.get('calle_altura')),
                    'piso': None,
                    'codigo_postal': self.clean_text(row.get('codigo_postal')),
                    'barrio': self.clean_text(row.get('barrio')),
                    'comuna': self.clean_text(row.get('comuna')),
                    'telefono': self.clean_phone(row.get('telefono')),
                    'codigo_area': None,
                    'email': self.clean_text(row.get('mail')),
                    'web': None,
                    'tipo_cocina': self.clean_text(row.get('cocina')),
                    'tipo_ambiente': self.clean_text(row.get('ambientacion')),
                    'horario': self.clean_text(row.get('horario')),
                    'material': None,
                    'autor': None,
                    'denominacion_simboliza': None,
                    'fuente_original': 'csv_gastronomia',
                    'id_fuente_original': self.clean_text(row.get('id'))
                }
                
                # Validar datos mínimos requeridos
                if poi_data['latitud'] is None or poi_data['longitud'] is None:
                    logger.warning(f"Restaurante sin coordenadas: {nombre}")
                    continue
                    
                poi_id = self.insert_poi(poi_data)
                count += 1
                
                if count % 50 == 0:
                    logger.info(f"Procesados {count} establecimientos gastronómicos...")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error procesando establecimiento {row.get('nombre', 'sin nombre')}: {e}")
                
        self.operational_conn.commit()
        logger.info(f"Gastronomía procesada: {count} exitosos, {errors} errores")
        return count

    def process_monumentos_csv(self) -> int:
        """Procesar CSV de monumentos"""
        logger.info("Procesando monumentos...")
        
        csv_path = os.path.join(self.csv_base_path, "monumentos-caba.csv")
        print(f"Intentando leer archivo: {csv_path}")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No se encuentra el archivo: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8', sep=';')
        
        categoria_id = self.get_categoria_id('monumentos')
        subcategoria_id = self.get_subcategoria_id(categoria_id, 'monumento histórico')
        
        count = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                nombre = self.clean_text(row.get('DENOMINACION_SIMBOLIZA', ''))
                if not nombre:
                    continue
                
                poi_data = {
                    'nombre': nombre,
                    'descripcion': self.clean_text(row.get('OBSERVACIONES')),
                    'categoria_id': categoria_id,
                    'subcategoria_id': subcategoria_id,
                    'latitud': self.clean_coordinate(row.get('LATITUD')),
                    'longitud': self.clean_coordinate(row.get('LONGITUD')),
                    'direccion': self.clean_text(row.get('DIRECCION_NORMALIZADA')),
                    'calle': self.clean_text(row.get('CALLE')),
                    'altura': str(row.get('ALTURA')) if pd.notna(row.get('ALTURA')) else None,
                    'piso': None,
                    'codigo_postal': self.clean_text(row.get('CODIGO_POSTAL_ARGENTINO')),
                    'barrio': self.clean_text(row.get('BARRIO')),
                    'comuna': self.extract_comuna_number(row.get('COMUNA')),
                    'telefono': None,
                    'codigo_area': None,
                    'email': None,
                    'web': None,
                    'tipo_cocina': None,
                    'tipo_ambiente': None,
                    'horario': None,
                    'material': self.clean_text(row.get('MATERIAL')),
                    'autor': self.clean_text(row.get('AUTORES')),
                    'denominacion_simboliza': nombre,
                    'fuente_original': 'csv_monumentos',
                    'id_fuente_original': self.clean_text(row.get('ID'))
                }
                
                # Validar datos mínimos requeridos
                if poi_data['latitud'] is None or poi_data['longitud'] is None:
                    logger.warning(f"Monumento sin coordenadas: {nombre}")
                    continue
                    
                poi_id = self.insert_poi(poi_data)
                count += 1
                
                if count % 10 == 0:
                    logger.info(f"Procesados {count} monumentos...")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error procesando monumento {row.get('DENOMINACION_SIMBOLIZA', 'sin nombre')}: {e}")
                
        self.operational_conn.commit()
        logger.info(f"Monumentos procesados: {count} exitosos, {errors} errores")
        return count

    def process_lugares_historicos_csv(self) -> int:
        """Procesar CSV de lugares históricos"""
        logger.info("Procesando lugares históricos...")
        
        csv_path = os.path.join(self.csv_base_path, "monumentos-y-lugares-historicos-filtrado.csv")
        print(f"Intentando leer archivo: {csv_path}")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No se encuentra el archivo: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        categoria_id = self.get_categoria_id('lugares históricos')
        subcategoria_id = self.get_subcategoria_id(categoria_id, 'monumento histórico')  # Default, ajustar según necesidad
        
        count = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                nombre = self.clean_text(row.get('nombre', ''))
                if not nombre:
                    continue
                
                poi_data = {
                    'nombre': nombre,
                    'descripcion': self.clean_text(row.get('descripcion')),
                    'categoria_id': categoria_id,
                    'subcategoria_id': subcategoria_id,
                    'latitud': self.clean_coordinate(row.get('latitud')),
                    'longitud': self.clean_coordinate(row.get('longitud')),
                    'direccion': self.clean_text(row.get('direccion')),
                    'calle': None,
                    'altura': None,
                    'piso': None,
                    'codigo_postal': None,
                    'barrio': None,
                    'comuna': None,
                    'telefono': None,
                    'codigo_area': None,
                    'email': None,
                    'web': None,
                    'tipo_cocina': None,
                    'tipo_ambiente': None,
                    'horario': None,
                    'material': None,
                    'autor': None,
                    'denominacion_simboliza': self.clean_text(row.get('denominacion_especifica')),
                    'fuente_original': 'csv_lugares_historicos',
                    'id_fuente_original': self.clean_text(row.get('espacio_cultural_id'))
                }
                
                # Validar datos mínimos requeridos
                if poi_data['latitud'] is None or poi_data['longitud'] is None:
                    logger.warning(f"Lugar histórico sin coordenadas: {nombre}")
                    continue
                    
                poi_id = self.insert_poi(poi_data)
                count += 1
                
                if count % 10 == 0:
                    logger.info(f"Procesados {count} lugares históricos...")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error procesando lugar histórico {row.get('nombre', 'sin nombre')}: {e}")
                
        self.operational_conn.commit()
        logger.info(f"Lugares históricos procesados: {count} exitosos, {errors} errores")
        return count

    def process_cines_csv(self) -> int:
        """Procesar CSV de salas de cine"""
        logger.info("Procesando salas de cine...")
        
        csv_path = os.path.join(self.csv_base_path, "salas-cine-filtrado.csv")
        print(f"Intentando leer archivo: {csv_path}")
        if not os.path.exists(csv_path):
            raise FileNotFoundError(f"No se encuentra el archivo: {csv_path}")
        df = pd.read_csv(csv_path, encoding='utf-8')
        
        categoria_id = self.get_categoria_id('entretenimiento')
        subcategoria_id = self.get_subcategoria_id(categoria_id, 'salas de cine')
        
        count = 0
        errors = 0
        
        for _, row in df.iterrows():
            try:
                nombre = self.clean_text(row.get('nombre', ''))
                if not nombre:
                    continue
                
                # Convertir campos numéricos
                pantallas = None
                butacas = None
                try:
                    pantallas = int(row.get('pantallas', 0)) if pd.notna(row.get('pantallas')) else None
                    butacas = int(row.get('butacas', 0)) if pd.notna(row.get('butacas')) else None
                except (ValueError, TypeError):
                    pass
                
                poi_data = {
                    'nombre': nombre,
                    'descripcion': None,
                    'categoria_id': categoria_id,
                    'subcategoria_id': subcategoria_id,
                    'latitud': self.clean_coordinate(row.get('latitud')),
                    'longitud': self.clean_coordinate(row.get('longitud')),
                    'direccion': self.clean_text(row.get('direccion')),
                    'calle': None,
                    'altura': None,
                    'piso': self.clean_text(row.get('piso')),
                    'codigo_postal': self.clean_text(row.get('cp')),
                    'barrio': None,
                    'comuna': None,
                    'telefono': None,
                    'codigo_area': None,
                    'email': None,
                    'web': self.clean_text(row.get('web')),
                    'tipo_cocina': None,
                    'tipo_ambiente': None,
                    'horario': None,
                    'material': None,
                    'autor': None,
                    'denominacion_simboliza': None,
                    'fuente_original': 'csv_cines',
                    'id_fuente_original': self.clean_text(row.get('cod_localidad'))
                }
                
                # Validar datos mínimos requeridos
                if poi_data['latitud'] is None or poi_data['longitud'] is None:
                    logger.warning(f"Cine sin coordenadas: {nombre}")
                    continue
                    
                poi_id = self.insert_poi(poi_data)
                count += 1
                
                if count % 5 == 0:
                    logger.info(f"Procesados {count} cines...")
                    
            except Exception as e:
                errors += 1
                logger.error(f"Error procesando cine {row.get('nombre', 'sin nombre')}: {e}")
                
        self.operational_conn.commit()
        logger.info(f"Cines procesados: {count} exitosos, {errors} errores")
        return count

    def verify_csv_files(self) -> bool:
        """Verificar que todos los archivos CSV existan"""
        required_files = [
            "museos-filtrado.csv",
            "oferta-gastronomica.csv",
            "monumentos-caba.csv",
            "monumentos-y-lugares-historicos-filtrado.csv",
            "salas-cine-filtrado.csv"
        ]
        
        print(f"Directorio base de CSVs: {self.csv_base_path}")
        print("Verificando archivos:")
        
        all_exist = True
        for file in required_files:
            file_path = os.path.join(self.csv_base_path, file)
            exists = os.path.exists(file_path)
            print(f"  {'[OK]' if exists else '[X]'} {file_path}")
            if not exists:
                all_exist = False
                
        return all_exist

    def process_all_csvs(self) -> Dict[str, int]:
        """Procesar todos los CSVs"""
        logger.info("Iniciando procesamiento de todos los CSVs...")
        
        # Verificar archivos antes de empezar
        if not self.verify_csv_files():
            raise FileNotFoundError("Faltan archivos CSV necesarios")
        
        results = {}
        
        try:
            self.connect_databases()
            self.load_categoria_mappings()
            
            # Procesar cada CSV
            results['museos'] = self.process_museos_csv()
            results['gastronomia'] = self.process_gastronomia_csv()
            results['monumentos'] = self.process_monumentos_csv()
            results['lugares_historicos'] = self.process_lugares_historicos_csv()
            results['cines'] = self.process_cines_csv()
            
            total_processed = sum(results.values())
            logger.info(f"Procesamiento completado! Total de POIs procesados: {total_processed}")
            
            # Mostrar resumen
            for categoria, count in results.items():
                logger.info(f"   {categoria.title()}: {count} POIs")
            
            # Mostrar estadísticas de geocoding
            geocoding_stats = self.geocoder.get_stats()
            logger.info("[INFO] Estadisticas de Geocoding:")
            logger.info(f"   Entradas en cache: {geocoding_stats['cache_size']}")
            logger.info(f"   Barrios unicos encontrados: {len(geocoding_stats['cached_barrios'])}")
            if geocoding_stats['cached_barrios']:
                logger.info(f"   Barrios: {', '.join(sorted(geocoding_stats['cached_barrios']))}")
                
        except Exception as e:
            logger.error(f"Error general en procesamiento: {e}")
            if self.operational_conn:
                self.operational_conn.rollback()
            raise
        finally:
            self.disconnect_databases()
            
        return results

def main():
    """Función principal"""
    processor = CSVProcessor()
    
    try:
        results = processor.process_all_csvs()
        print("\n" + "="*50)
        print("RESUMEN DE PROCESAMIENTO")
        print("="*50)
        for categoria, count in results.items():
            print(f"{categoria.title():20}: {count:4} POIs")
        print(f"{'TOTAL':20}: {sum(results.values()):4} POIs")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error ejecutando procesamiento: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
