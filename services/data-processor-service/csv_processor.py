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
from typing import Dict, List, Optional, Tuple

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('csv_processor.log'),
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
        """Insertar POI en base de datos operacional"""
        cursor = self.operational_conn.cursor()
        
        insert_query = """
        INSERT INTO pois (
            nombre, descripcion, categoria_id, subcategoria_id,
            latitud, longitud, direccion, direccion_normalizada,
            calle, altura, piso, codigo_postal, barrio, comuna,
            telefono, codigo_area, email, web,
            tipo_cocina, tipo_ambiente, horario,
            jurisdiccion, año_inauguracion,
            material, autor, denominacion_simboliza,
            numero_pantallas, numero_butacas, tipo_gestion,
            fuente_original, id_fuente_original,
            activo, verificado
        ) VALUES (
            %(nombre)s, %(descripcion)s, %(categoria_id)s, %(subcategoria_id)s,
            %(latitud)s, %(longitud)s, %(direccion)s, %(direccion_normalizada)s,
            %(calle)s, %(altura)s, %(piso)s, %(codigo_postal)s, %(barrio)s, %(comuna)s,
            %(telefono)s, %(codigo_area)s, %(email)s, %(web)s,
            %(tipo_cocina)s, %(tipo_ambiente)s, %(horario)s,
            %(jurisdiccion)s, %(año_inauguracion)s,
            %(material)s, %(autor)s, %(denominacion_simboliza)s,
            %(numero_pantallas)s, %(numero_butacas)s, %(tipo_gestion)s,
            %(fuente_original)s, %(id_fuente_original)s,
            %(activo)s, %(verificado)s
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
                    'direccion_normalizada': None,
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
                    'jurisdiccion': self.clean_text(row.get('jurisdiccion')),
                    'año_inauguracion': int(float(row.get('año_inauguracion'))) if pd.notna(row.get('año_inauguracion')) else None,
                    'material': None,
                    'autor': None,
                    'denominacion_simboliza': None,
                    'numero_pantallas': None,
                    'numero_butacas': None,
                    'tipo_gestion': None,
                    'fuente_original': 'csv_museos',
                    'id_fuente_original': self.clean_text(row.get('Cod_Loc')),
                    'activo': True,
                    'verificado': False
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
                    'direccion_normalizada': None,
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
                    'jurisdiccion': None,
                    'año_inauguracion': None,
                    'material': None,
                    'autor': None,
                    'denominacion_simboliza': None,
                    'numero_pantallas': None,
                    'numero_butacas': None,
                    'tipo_gestion': None,
                    'fuente_original': 'csv_gastronomia',
                    'id_fuente_original': self.clean_text(row.get('id')),
                    'activo': True,
                    'verificado': False
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
                    'direccion_normalizada': self.clean_text(row.get('DIRECCION_NORMALIZADA')),
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
                    'jurisdiccion': None,
                    'año_inauguracion': None,
                    'material': self.clean_text(row.get('MATERIAL')),
                    'autor': self.clean_text(row.get('AUTORES')),
                    'denominacion_simboliza': nombre,
                    'numero_pantallas': None,
                    'numero_butacas': None,
                    'tipo_gestion': None,
                    'fuente_original': 'csv_monumentos',
                    'id_fuente_original': self.clean_text(row.get('ID')),
                    'activo': True,
                    'verificado': False
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
                    'direccion_normalizada': None,
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
                    'jurisdiccion': self.clean_text(row.get('jurisdiccion _declaratoria')),
                    'año_inauguracion': None,  # La fecha viene en formato dd/mm/yyyy, necesitaríamos parsearla
                    'material': None,
                    'autor': None,
                    'denominacion_simboliza': self.clean_text(row.get('denominacion_especifica')),
                    'numero_pantallas': None,
                    'numero_butacas': None,
                    'tipo_gestion': None,
                    'fuente_original': 'csv_lugares_historicos',
                    'id_fuente_original': self.clean_text(row.get('espacio_cultural_id')),
                    'activo': True,
                    'verificado': False
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
                    'direccion_normalizada': None,
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
                    'jurisdiccion': None,
                    'año_inauguracion': self.clean_text(row.get('año_actualizacion')),
                    'material': None,
                    'autor': None,
                    'denominacion_simboliza': None,
                    'numero_pantallas': pantallas,
                    'numero_butacas': butacas,
                    'tipo_gestion': self.clean_text(row.get('tipo_de_gestion')),
                    'fuente_original': 'csv_cines',
                    'id_fuente_original': self.clean_text(row.get('cod_localidad')),
                    'activo': True,
                    'verificado': False
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
