"""
BAXperience - ETL: BD Operacional → BD Data Processor
====================================================

Script ETL que transfiere y transforma datos de la base de datos operacional
a la base de datos optimizada para clustering y análisis.

Flujo:
1. BD Operacional (completa) → BD Data Processor (optimizada)
2. Agregar métricas calculadas para clustering
3. Normalizar datos para algoritmos de ML

Autor: BAXperience Team
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import logging
import sys
import hashlib
import math
from typing import Dict, List, Optional, Tuple
from csv_processor import DatabaseConfig

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('etl_processor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class ETLProcessor:
    """Procesador ETL de BD Operacional a BD Data Processor"""
    
    def __init__(self):
        self.operational_conn = None
        self.processor_conn = None
    
    def calculate_distance_km(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calcular distancia entre dos puntos usando fórmula de Haversine
        """
        # Radio de la Tierra en km
        R = 6371.0
        
        # Convertir grados a radianes
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # Diferencias
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        # Fórmula de Haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
        
        return R * c
    
    def get_barrio_from_coordinates(self, latitud: float, longitud: float) -> Tuple[Optional[str], Optional[int]]:
        """
        Determinar barrio y comuna basándose en coordenadas usando POIs de referencia
        """
        if not latitud or not longitud:
            return None, None
        
        # Obtener POIs de referencia que tengan barrio asignado
        op_cursor = self.operational_conn.cursor(cursor_factory=RealDictCursor)
        
        reference_query = """
        SELECT DISTINCT 
            barrio, comuna, latitud, longitud,
            COUNT(*) as pois_en_barrio
        FROM pois 
        WHERE barrio IS NOT NULL 
        AND barrio != ''
        AND latitud IS NOT NULL 
        AND longitud IS NOT NULL
        GROUP BY barrio, comuna, latitud, longitud
        HAVING COUNT(*) >= 1
        ORDER BY pois_en_barrio DESC
        """
        
        op_cursor.execute(reference_query)
        referencias = op_cursor.fetchall()
        op_cursor.close()
        
        if not referencias:
            return None, None
        
        # Encontrar el barrio más cercano
        mejor_barrio = None
        mejor_comuna = None
        distancia_minima = float('inf')
        
        for ref in referencias:
            try:
                ref_lat = float(ref['latitud'])
                ref_lng = float(ref['longitud'])
                
                distancia = self.calculate_distance_km(latitud, longitud, ref_lat, ref_lng)
                
                # Si está muy cerca (menos de 2km), es muy probable que sea el mismo barrio
                if distancia < distancia_minima:
                    distancia_minima = distancia
                    mejor_barrio = ref['barrio']
                    mejor_comuna = ref['comuna']
                    
                    # Si está muy cerca, no necesitamos seguir buscando
                    if distancia < 0.5:  # Menos de 500 metros
                        break
                        
            except (ValueError, TypeError):
                continue
        
        # Solo asignar si está razonablemente cerca (menos de 3km)
        if distancia_minima < 3.0:
            return mejor_barrio, mejor_comuna
        
        return None, None
    
    def assign_missing_barrios(self) -> int:
        """
        Asignar barrios faltantes usando geocodificación inversa interna
        """
        logger.info("🗺️ Asignando barrios faltantes usando coordenadas...")
        
        # Obtener POIs sin barrio
        op_cursor = self.operational_conn.cursor(cursor_factory=RealDictCursor)
        
        missing_barrios_query = """
        SELECT id, nombre, latitud, longitud, categoria_id
        FROM pois 
        WHERE (barrio IS NULL OR barrio = '')
        AND latitud IS NOT NULL 
        AND longitud IS NOT NULL
        ORDER BY id
        """
        
        op_cursor.execute(missing_barrios_query)
        pois_sin_barrio = op_cursor.fetchall()
        op_cursor.close()
        
        logger.info(f"📍 Encontrados {len(pois_sin_barrio)} POIs sin barrio asignado")
        
        if not pois_sin_barrio:
            return 0
        
        # Actualizar POIs con barrios calculados
        update_cursor = self.operational_conn.cursor()
        update_query = """
        UPDATE pois 
        SET barrio = %s, comuna = %s 
        WHERE id = %s
        """
        
        actualizados = 0
        errores = 0
        
        for poi in pois_sin_barrio:
            try:
                latitud = float(poi['latitud'])
                longitud = float(poi['longitud'])
                
                # Calcular barrio usando geocodificación interna
                barrio, comuna = self.get_barrio_from_coordinates(latitud, longitud)
                
                if barrio:
                    update_cursor.execute(update_query, (barrio, comuna, poi['id']))
                    actualizados += 1
                    
                    if actualizados % 50 == 0:
                        logger.info(f"   Actualizados {actualizados}/{len(pois_sin_barrio)} POIs...")
                        self.operational_conn.commit()  # Commit intermedio
                        
                    # Log de ejemplo para los primeros 5
                    if actualizados <= 5:
                        logger.info(f"   ✅ {poi['nombre'][:30]}... → {barrio}")
                        
            except Exception as e:
                errores += 1
                if errores <= 3:  # Solo log los primeros errores
                    logger.error(f"Error procesando POI {poi['id']}: {e}")
        
        # Commit final
        self.operational_conn.commit()
        update_cursor.close()
        
        logger.info(f"✅ Asignación de barrios completada: {actualizados} actualizados, {errores} errores")
        return actualizados
        """
        Genera un hash único para un evento basado en nombre, fecha e ubicación
        """
        # Normalizar datos para el hash
        datos_hash = (
            (nombre or '').strip().lower() +
            (fecha_inicio or '') +
            (ubicacion or '').strip().lower()
        )
        
        # Generar hash SHA-256
        return hashlib.sha256(datos_hash.encode('utf-8')).hexdigest()
        
    def connect_databases(self):
        """Conectar a ambas bases de datos"""
        try:
            # Conexión a BD Operacional
            self.operational_conn = psycopg2.connect(**DatabaseConfig.OPERATIONAL_DB)
            self.operational_conn.autocommit = False
            logger.info("Conectado a BD Operacional")
            
            # Conexión a BD Data Processor
            self.processor_conn = psycopg2.connect(**DatabaseConfig.PROCESSOR_DB)
            self.processor_conn.autocommit = False
            logger.info("Conectado a BD Data Processor")
            
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
            
    def create_processor_schema(self):
        """Crear esquema optimizado en BD Data Processor"""
        logger.info("Creando esquema en BD Data Processor...")
        
        cursor = self.processor_conn.cursor()
        
        # Esquema simplificado para clustering
        schema_sql = """
        -- Tabla de lugares para clustering
        DROP TABLE IF EXISTS lugares_clustering CASCADE;
        CREATE TABLE lugares_clustering (
            id SERIAL PRIMARY KEY,
            poi_id INTEGER NOT NULL, -- referencia al POI original
            nombre VARCHAR(255) NOT NULL,
            categoria VARCHAR(50) NOT NULL,
            subcategoria VARCHAR(100),
            
            -- Ubicación normalizada
            latitud DECIMAL(10, 8) NOT NULL,
            longitud DECIMAL(11, 8) NOT NULL,
            barrio VARCHAR(100),
            comuna INTEGER,
            
            -- Features para clustering
            valoracion_promedio DECIMAL(3,2) DEFAULT 0.0,
            numero_valoraciones INTEGER DEFAULT 0,
            popularidad_score DECIMAL(5,2) DEFAULT 0.0,
            
            -- Features categóricos (para one-hot encoding)
            tipo_cocina VARCHAR(100),
            tipo_ambiente VARCHAR(100),
            material VARCHAR(200),
            
            -- Features binarios
            tiene_web BOOLEAN DEFAULT FALSE,
            tiene_telefono BOOLEAN DEFAULT FALSE,
            es_gratuito BOOLEAN DEFAULT TRUE, -- museos/monumentos generalmente gratis
            
            -- Metadata
            fuente_original VARCHAR(100) NOT NULL,
            fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            activo BOOLEAN DEFAULT TRUE
        );
        
        -- Índices para clustering
        CREATE INDEX idx_clustering_geolocation ON lugares_clustering USING GIST (point(longitud, latitud));
        CREATE INDEX idx_clustering_categoria ON lugares_clustering(categoria, subcategoria);
        CREATE INDEX idx_clustering_barrio ON lugares_clustering(barrio) WHERE barrio IS NOT NULL;
        CREATE INDEX idx_clustering_valoracion ON lugares_clustering(valoracion_promedio DESC, numero_valoraciones DESC);
        
        -- Tabla de eventos activos para clustering temporal
        DROP TABLE IF EXISTS eventos_clustering CASCADE;
        CREATE TABLE eventos_clustering (
            id SERIAL PRIMARY KEY,
            evento_id INTEGER NOT NULL, -- referencia al evento original
            nombre VARCHAR(255) NOT NULL,
            categoria_evento VARCHAR(100),
            tematica VARCHAR(100),
            
            -- Ubicación
            poi_id INTEGER, -- si está asociado a un POI
            latitud DECIMAL(10, 8),
            longitud DECIMAL(11, 8),
            barrio VARCHAR(100),
            
            -- Fechas (para clustering temporal)
            fecha_inicio DATE NOT NULL,
            fecha_fin DATE,
            duracion_dias INTEGER,
            mes_inicio INTEGER, -- 1-12 para clustering estacional
            dia_semana_inicio INTEGER, -- 1-7 para clustering por día
            
            -- Features (campos simplificados)
            url_evento VARCHAR(500),
            
            -- Metadata
            fecha_scraping TIMESTAMP,
            activo BOOLEAN DEFAULT TRUE
        );
        
        CREATE INDEX idx_eventos_clustering_fecha ON eventos_clustering(fecha_inicio, fecha_fin);
        CREATE INDEX idx_eventos_clustering_ubicacion ON eventos_clustering(poi_id, barrio);
        CREATE INDEX idx_eventos_clustering_categoria ON eventos_clustering(categoria_evento, tematica);
        """
        
        cursor.execute(schema_sql)
        self.processor_conn.commit()
        cursor.close()
        logger.info("Esquema de BD Data Processor creado")
        
    def extract_transform_load_pois(self) -> int:
        """ETL principal: POIs de BD Operacional → BD Data Processor"""
        logger.info("Ejecutando ETL de POIs...")
        
        # Extract: Obtener datos de BD Operacional
        op_cursor = self.operational_conn.cursor(cursor_factory=RealDictCursor)
        
        extract_query = """
        SELECT 
            p.id,
            p.nombre,
            c.nombre as categoria,
            s.nombre as subcategoria,
            p.latitud,
            p.longitud,
            p.barrio,
            p.comuna,
            p.valoracion_promedio,
            p.numero_valoraciones,
            p.tipo_cocina,
            p.tipo_ambiente,
            p.material,
            p.web,
            p.telefono,
            p.fuente_original
        FROM pois p
        JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id
        WHERE p.latitud IS NOT NULL 
        AND p.longitud IS NOT NULL
        ORDER BY p.id
        """
        
        op_cursor.execute(extract_query)
        pois_data = op_cursor.fetchall()
        op_cursor.close()
        
        logger.info(f"Extraídos {len(pois_data)} POIs de BD Operacional")
        
        # Transform & Load: Procesar y cargar en BD Data Processor
        proc_cursor = self.processor_conn.cursor()
        
        insert_query = """
        INSERT INTO lugares_clustering (
            poi_id, nombre, categoria, subcategoria,
            latitud, longitud, barrio, comuna,
            valoracion_promedio, numero_valoraciones, popularidad_score,
            tipo_cocina, tipo_ambiente, material,
            tiene_web, tiene_telefono, es_gratuito,
            fuente_original, activo
        ) VALUES (
            %(poi_id)s, %(nombre)s, %(categoria)s, %(subcategoria)s,
            %(latitud)s, %(longitud)s, %(barrio)s, %(comuna)s,
            %(valoracion_promedio)s, %(numero_valoraciones)s, %(popularidad_score)s,
            %(tipo_cocina)s, %(tipo_ambiente)s, %(material)s,
            %(tiene_web)s, %(tiene_telefono)s, %(es_gratuito)s,
            %(fuente_original)s, %(activo)s
        )
        """
        
        count = 0
        for poi in pois_data:
            try:
                # Transform: Calcular features adicionales
                popularidad_score = self.calculate_popularity_score(poi)
                es_gratuito = self.determine_if_free(poi)
                
                transformed_data = {
                    'poi_id': poi['id'],
                    'nombre': poi['nombre'],
                    'categoria': poi['categoria'],
                    'subcategoria': poi['subcategoria'],
                    'latitud': poi['latitud'],
                    'longitud': poi['longitud'],
                    'barrio': poi['barrio'],
                    'comuna': poi['comuna'],
                    'valoracion_promedio': poi['valoracion_promedio'] or 0.0,
                    'numero_valoraciones': poi['numero_valoraciones'] or 0,
                    'popularidad_score': popularidad_score,
                    'tipo_cocina': poi['tipo_cocina'],
                    'tipo_ambiente': poi['tipo_ambiente'],
                    'material': poi['material'],
                    'tiene_web': bool(poi['web']),
                    'tiene_telefono': bool(poi['telefono']),
                    'es_gratuito': es_gratuito,
                    'fuente_original': poi['fuente_original'],
                    'activo': True  # Por defecto activo ya que no existe el campo
                }
                
                proc_cursor.execute(insert_query, transformed_data)
                count += 1
                
                if count % 100 == 0:
                    logger.info(f"Procesados {count}/{len(pois_data)} POIs...")
                    
            except Exception as e:
                logger.error(f"Error procesando POI {poi['id']}: {e}")
                
        self.processor_conn.commit()
        proc_cursor.close()
        
        logger.info(f"ETL POIs completado: {count} registros cargados")
        return count
        
    def calculate_popularity_score(self, poi: Dict) -> float:
        """Calcular score de popularidad basado en datos reales disponibles"""
        import math
        
        score = 0.0
        
        # Score basado en valoraciones reales
        valoracion = float(poi.get('valoracion_promedio', 0))
        num_valoraciones = int(poi.get('numero_valoraciones', 0))
        
        if valoracion > 0 and num_valoraciones > 0:
            # Score por calidad de valoración (0-5 → 0-0.6)
            score += (valoracion / 5.0) * 0.6
            
            # Score por cantidad de valoraciones (logarítmico para evitar dominio)
            review_score = math.log(num_valoraciones + 1) / math.log(100)  # Normalizado a ~100 reviews
            score += min(review_score, 0.3)  # Máximo 0.3 puntos por reviews
        else:
            # Si no hay valoraciones, score mínimo base
            score += 0.2
        
        # Score por completitud de información (indica calidad/popularidad)
        if poi.get('web') and poi.get('web').strip():
            score += 0.1
        if poi.get('telefono') and poi.get('telefono').strip():
            score += 0.1
        if poi.get('barrio') and poi.get('barrio').strip():
            score += 0.05
        if poi.get('tipo_cocina') and poi.get('tipo_cocina').strip():
            score += 0.05
        if poi.get('tipo_ambiente') and poi.get('tipo_ambiente').strip():
            score += 0.05
        
        # Ajuste leve por categoría (basado en datos típicos de turismo)
        categoria = poi.get('categoria', '').lower()
        if 'gastronomía' in categoria:
            score *= 1.05  # Gastronomía ligeramente más popular
        elif 'entretenimiento' in categoria:
            score *= 1.1   # Entretenimiento más demandado
        elif 'museo' in categoria:
            score *= 0.95  # Museos algo menos populares en general
        
        # Mantener en rango realista 0.1 - 1.0
        final_score = max(0.1, min(1.0, score))
        
        return round(final_score, 3)
        
    def determine_if_free(self, poi: Dict) -> bool:
        """Determinar si un POI es generalmente gratuito"""
        categoria = poi['categoria'].lower()
        
        # Museos y monumentos generalmente son gratuitos o de bajo costo
        if categoria in ['museos', 'monumentos', 'lugares históricos']:
            return True
        # Gastronomía generalmente es paga
        elif categoria in ['gastronomía']:
            return False
        # Entretenimiento depende del tipo
        elif categoria in ['entretenimiento']:
            # Algunos cines pueden tener promociones gratuitas, pero generalmente no
            return False
        
        return True  # Default conservador
        
    def extract_transform_load_eventos(self) -> int:
        """ETL de eventos activos"""
        logger.info("Ejecutando ETL de eventos...")
        
        # Extract eventos activos
        op_cursor = self.operational_conn.cursor(cursor_factory=RealDictCursor)
        
        eventos_query = """
        SELECT 
            id, nombre, categoria_evento, tematica,
            poi_id, latitud, longitud, barrio,
            fecha_inicio, fecha_fin,
            url_evento,
            fecha_scraping
        FROM eventos
        WHERE activo = TRUE
          AND (fecha_fin IS NULL OR fecha_fin >= CURRENT_DATE)
        ORDER BY fecha_inicio
        """
        
        op_cursor.execute(eventos_query)
        eventos_data = op_cursor.fetchall()
        op_cursor.close()
        
        logger.info(f"Extraídos {len(eventos_data)} eventos activos")
        
        # Transform & Load eventos
        proc_cursor = self.processor_conn.cursor()
        
        # Limpiar eventos anteriores
        proc_cursor.execute("DELETE FROM eventos_clustering")
        
        insert_eventos_query = """
        INSERT INTO eventos_clustering (
            evento_id, nombre, categoria_evento, tematica,
            poi_id, latitud, longitud, barrio,
            fecha_inicio, fecha_fin, duracion_dias,
            mes_inicio, dia_semana_inicio,
            url_evento,
            fecha_scraping, activo
        ) VALUES (
            %(evento_id)s, %(nombre)s, %(categoria_evento)s, %(tematica)s,
            %(poi_id)s, %(latitud)s, %(longitud)s, %(barrio)s,
            %(fecha_inicio)s, %(fecha_fin)s, %(duracion_dias)s,
            %(mes_inicio)s, %(dia_semana_inicio)s,
            %(url_evento)s,
            %(fecha_scraping)s, %(activo)s
        )
        """
        
        count = 0
        for evento in eventos_data:
            try:
                # Transform: Calcular features temporales
                fecha_inicio = evento['fecha_inicio']
                fecha_fin = evento['fecha_fin']
                
                duracion_dias = None
                if fecha_fin:
                    duracion_dias = (fecha_fin - fecha_inicio).days
                    
                mes_inicio = fecha_inicio.month
                dia_semana_inicio = fecha_inicio.weekday() + 1  # 1=Monday, 7=Sunday
                
                transformed_evento = {
                    'evento_id': evento['id'],
                    'nombre': evento['nombre'],
                    'categoria_evento': evento['categoria_evento'],
                    'tematica': evento['tematica'],
                    'poi_id': evento['poi_id'],
                    'latitud': evento['latitud'],
                    'longitud': evento['longitud'],
                    'barrio': evento['barrio'],
                    'fecha_inicio': fecha_inicio,
                    'fecha_fin': fecha_fin,
                    'duracion_dias': duracion_dias,
                    'mes_inicio': mes_inicio,
                    'dia_semana_inicio': dia_semana_inicio,
                    'url_evento': evento['url_evento'],
                    'fecha_scraping': evento['fecha_scraping'],
                    'activo': True
                }
                
                proc_cursor.execute(insert_eventos_query, transformed_evento)
                count += 1
                
            except Exception as e:
                logger.error(f"Error procesando evento {evento['id']}: {e}")
                
        self.processor_conn.commit()
        proc_cursor.close()
        
        logger.info(f"ETL Eventos completado: {count} registros cargados")
        return count
    
    def insertar_eventos_desde_scraper(self, eventos_data) -> int:
        """
        Insertar eventos obtenidos del scraper en la BD operacional
        Solo incluye campos que existen en el nuevo esquema
        """
        logger.info("Insertando eventos desde scraper...")
        logger.info(f"Tipo de datos recibidos: {type(eventos_data)}")
        logger.info(f"Claves disponibles: {list(eventos_data.keys()) if isinstance(eventos_data, dict) else 'No es dict'}")
        
        if isinstance(eventos_data, dict) and 'eventos' in eventos_data:
            logger.info(f"Número de eventos: {len(eventos_data['eventos'])}")
            if eventos_data['eventos']:
                logger.info(f"Ejemplo de evento: {eventos_data['eventos'][0].get('nombre', 'Sin nombre')}")
        else:
            logger.warning("No se encontraron eventos en los datos")
            return 0
        
        cursor = self.operational_conn.cursor()
        
        # Verificar que la tabla eventos existe
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = 'eventos'
            );
        """)
        tabla_existe = cursor.fetchone()[0]
        logger.info(f"Tabla eventos existe: {tabla_existe}")
        
        if not tabla_existe:
            logger.error("La tabla eventos no existe en la base de datos operacional")
            return 0
        
        # Query ajustada al nuevo esquema con control de hash
        insert_query = """
        INSERT INTO eventos (
            nombre, descripcion, categoria_evento, tematica,
            direccion_evento, ubicacion_especifica, latitud, longitud, barrio,
            fecha_inicio, dias_semana, hora_inicio, hora_fin,
            url_evento, fecha_scraping, url_fuente, hash_evento, activo
        ) VALUES (
            %(nombre)s, %(descripcion)s, %(categoria_evento)s, %(tematica)s,
            %(direccion_evento)s, %(ubicacion_especifica)s, %(latitud)s, %(longitud)s, %(barrio)s,
            CURRENT_DATE, %(dias_semana)s, %(hora_inicio)s, %(hora_fin)s,
            %(url_evento)s, %(fecha_scraping)s, %(url_fuente)s, %(hash_evento)s, TRUE
        )
        ON CONFLICT (hash_evento) WHERE activo = TRUE DO UPDATE SET
            fecha_scraping = EXCLUDED.fecha_scraping,
            activo = TRUE
        """
        
        count = 0
        errores = 0
        
        for evento in eventos_data.get('eventos', []):
            try:
                # Convertir fecha_scraping a timestamp si es string
                fecha_scraping = evento.get('fecha_scraping')
                if isinstance(fecha_scraping, str):
                    from datetime import datetime
                    try:
                        fecha_scraping = datetime.fromisoformat(fecha_scraping.replace('Z', '+00:00'))
                    except:
                        fecha_scraping = datetime.now()
                elif fecha_scraping is None:
                    fecha_scraping = datetime.now()
                
                # Convertir horas a formato TIME si son strings
                hora_inicio = evento.get('hora_inicio')
                hora_fin = evento.get('hora_fin')
                
                if hora_inicio and isinstance(hora_inicio, str):
                    # Asegurar formato HH:MM:SS
                    if len(hora_inicio.split(':')) == 2:
                        hora_inicio = hora_inicio + ':00'
                
                if hora_fin and isinstance(hora_fin, str):
                    # Asegurar formato HH:MM:SS
                    if len(hora_fin.split(':')) == 2:
                        hora_fin = hora_fin + ':00'
                
                # Validar y limpiar coordenadas
                latitud = evento.get('latitud')
                longitud = evento.get('longitud')
                
                if latitud is not None:
                    try:
                        latitud = float(latitud)
                        # Validar rango para Buenos Aires
                        if not (-35.0 <= latitud <= -34.0):
                            latitud = None
                    except (ValueError, TypeError):
                        latitud = None
                
                if longitud is not None:
                    try:
                        longitud = float(longitud)
                        # Validar rango para Buenos Aires
                        if not (-59.0 <= longitud <= -58.0):
                            longitud = None
                    except (ValueError, TypeError):
                        longitud = None
                
                # Generar hash único para el evento
                ubicacion_completa = f"{evento.get('direccion_evento', '')} {evento.get('ubicacion_especifica', '')} {evento.get('barrio', '')}"
                hash_evento = self.generar_hash_evento(
                    evento.get('nombre', ''),
                    str(fecha_scraping.date()) if fecha_scraping else '',
                    ubicacion_completa
                )
                
                # Extraer solo los campos que van a la BD (sin campos extra)
                evento_bd = {
                    "nombre": str(evento.get('nombre', ''))[:255],  # Limitar longitud
                    "descripcion": evento.get('descripcion', ''),
                    "categoria_evento": str(evento.get('categoria_evento', ''))[:100],
                    "tematica": str(evento.get('tematica', ''))[:100],
                    "direccion_evento": evento.get('direccion_evento', ''),
                    "ubicacion_especifica": evento.get('ubicacion_especifica', ''),
                    "latitud": latitud,
                    "longitud": longitud,
                    "barrio": str(evento.get('barrio', ''))[:100],
                    "dias_semana": str(evento.get('dias_semana', ''))[:7],  # Máximo 7 caracteres LMXJVSD
                    "hora_inicio": hora_inicio,
                    "hora_fin": hora_fin,
                    "url_evento": str(evento.get('url_evento', ''))[:500],
                    "fecha_scraping": fecha_scraping,
                    "url_fuente": str(evento.get('url_fuente', '') or 'https://turismo.buenosaires.gob.ar/es/que-hacer-en-la-ciudad')[:500],
                    "hash_evento": hash_evento
                }
                
                # Debug: mostrar el primer evento
                if count == 0:
                    logger.info(f"Primer evento a insertar: {evento_bd}")
                
                cursor.execute(insert_query, evento_bd)
                count += 1
                
                if count % 50 == 0:
                    logger.info(f"Insertados {count} eventos...")
                    
            except Exception as e:
                errores += 1
                logger.error(f"Error insertando evento {evento.get('nombre', 'Sin nombre')}: {e}")
                logger.error(f"Tipo de error: {type(e).__name__}")
                if count < 3:  # Solo mostrar detalles de los primeros errores
                    logger.error(f"Datos del evento que falló: {evento}")
                continue
        
        self.operational_conn.commit()
        cursor.close()
        
        logger.info(f"Inserción de eventos completada: {count} exitosos, {errores} errores")
        return count
        
    def run_full_etl(self) -> Dict[str, int]:
        """Ejecutar ETL completo con control de duplicación y asignación de barrios"""
        logger.info("🚀 Iniciando ETL completo...")
        
        results = {}
        
        try:
            self.connect_databases()
            
            # PASO 1: Asignar barrios faltantes usando geocodificación interna
            logger.info("🗺️ PASO 1: Asignando barrios usando coordenadas...")
            results['barrios_asignados'] = self.assign_missing_barrios()
            
            # PASO 2: Crear esquema optimizado
            self.create_processor_schema()
            
            # Verificar si ya tenemos POIs de CSV cargados
            proc_cursor = self.processor_conn.cursor()
            proc_cursor.execute("SELECT COUNT(*) FROM lugares_clustering")
            existing_pois = proc_cursor.fetchone()[0]
            proc_cursor.close()
            
            # PASO 3: Solo cargar POIs de CSV si no existen (evitar duplicación)
            if existing_pois == 0:
                logger.info("📋 PASO 3: Primera carga - Procesando POIs desde CSV...")
                results['pois'] = self.extract_transform_load_pois()
            else:
                logger.info(f"📋 PASO 3: POIs ya existen ({existing_pois}), saltando carga de CSV")
                results['pois'] = existing_pois
            
            # PASO 4: Siempre procesar eventos (se limpian y recargan)
            logger.info("📅 PASO 4: Procesando eventos desde BD operacional...")
            results['eventos'] = self.extract_transform_load_eventos()
            
            logger.info("✅ ETL completado exitosamente!")
            
        except Exception as e:
            logger.error(f"❌ Error en ETL: {e}")
            if self.processor_conn:
                self.processor_conn.rollback()
            raise
        finally:
            self.disconnect_databases()
            
        return results

def main():
    """Función principal"""
    etl = ETLProcessor()
    
    try:
        results = etl.run_full_etl()
        
        print("\n" + "="*50)
        print("RESUMEN ETL")
        print("="*50)
        print(f"Barrios asignados:      {results.get('barrios_asignados', 0):4}")
        print(f"POIs transferidos:      {results.get('pois', 0):4}")
        print(f"Barrios analizados:     {results.get('barrios', 0):4}")
        print(f"Eventos transferidos:   {results.get('eventos', 0):4}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error ejecutando ETL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
