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
from typing import Dict, List, Optional
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
            jurisdiccion VARCHAR(100),
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
        
        -- Tabla de métricas agregadas por barrio/comuna
        DROP TABLE IF EXISTS metricas_barrio CASCADE;
        CREATE TABLE metricas_barrio (
            id SERIAL PRIMARY KEY,
            barrio VARCHAR(100),
            comuna INTEGER,
            
            -- Conteos por categoría
            total_pois INTEGER DEFAULT 0,
            total_museos INTEGER DEFAULT 0,
            total_gastronomia INTEGER DEFAULT 0,
            total_monumentos INTEGER DEFAULT 0,
            total_entretenimiento INTEGER DEFAULT 0,
            
            -- Métricas de calidad
            valoracion_promedio_barrio DECIMAL(3,2) DEFAULT 0.0,
            densidad_poi_km2 DECIMAL(8,2) DEFAULT 0.0,
            
            -- Coordenadas del centroide del barrio
            centroide_lat DECIMAL(10, 8),
            centroide_lng DECIMAL(11, 8),
            
            fecha_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            
            UNIQUE(barrio, comuna)
        );
        
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
            
            -- Features
            entrada_libre BOOLEAN DEFAULT TRUE,
            requiere_inscripcion BOOLEAN DEFAULT FALSE,
            capacidad_maxima INTEGER,
            
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
            p.jurisdiccion,
            p.material,
            p.web,
            p.telefono,
            p.fuente_original,
            p.activo
        FROM pois p
        JOIN categorias c ON p.categoria_id = c.id
        LEFT JOIN subcategorias s ON p.subcategoria_id = s.id
        WHERE p.activo = TRUE
        AND p.latitud IS NOT NULL 
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
            tipo_cocina, tipo_ambiente, jurisdiccion, material,
            tiene_web, tiene_telefono, es_gratuito,
            fuente_original, activo
        ) VALUES (
            %(poi_id)s, %(nombre)s, %(categoria)s, %(subcategoria)s,
            %(latitud)s, %(longitud)s, %(barrio)s, %(comuna)s,
            %(valoracion_promedio)s, %(numero_valoraciones)s, %(popularidad_score)s,
            %(tipo_cocina)s, %(tipo_ambiente)s, %(jurisdiccion)s, %(material)s,
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
                    'jurisdiccion': poi['jurisdiccion'],
                    'material': poi['material'],
                    'tiene_web': bool(poi['web']),
                    'tiene_telefono': bool(poi['telefono']),
                    'es_gratuito': es_gratuito,
                    'fuente_original': poi['fuente_original'],
                    'activo': poi['activo']
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
        """Calcular score de popularidad basado en valoraciones"""
        valoracion = poi['valoracion_promedio'] or 0.0
        num_reviews = poi['numero_valoraciones'] or 0
        
        # Fórmula simple: (valoración * log(reviews + 1))
        import math
        if num_reviews > 0:
            score = valoracion * math.log(num_reviews + 1)
        else:
            score = valoracion * 0.5  # Penalizar POIs sin reviews
            
        return round(score, 2)
        
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
        
    def calculate_barrio_metrics(self) -> int:
        """Calcular métricas agregadas por barrio"""
        logger.info("Calculando métricas por barrio...")
        
        proc_cursor = self.processor_conn.cursor()
        
        # Limpiar tabla existente
        proc_cursor.execute("DELETE FROM metricas_barrio")
        
        # Calcular métricas agregadas
        metrics_query = """
        INSERT INTO metricas_barrio (
            barrio, comuna,
            total_pois, total_museos, total_gastronomia, 
            total_monumentos, total_entretenimiento,
            valoracion_promedio_barrio,
            centroide_lat, centroide_lng
        )
        SELECT 
            barrio,
            comuna,
            COUNT(*) as total_pois,
            SUM(CASE WHEN categoria = 'Museos' THEN 1 ELSE 0 END) as total_museos,
            SUM(CASE WHEN categoria = 'Gastronomía' THEN 1 ELSE 0 END) as total_gastronomia,
            SUM(CASE WHEN categoria = 'Monumentos' THEN 1 ELSE 0 END) as total_monumentos,
            SUM(CASE WHEN categoria = 'Entretenimiento' THEN 1 ELSE 0 END) as total_entretenimiento,
            AVG(valoracion_promedio) as valoracion_promedio_barrio,
            AVG(latitud) as centroide_lat,
            AVG(longitud) as centroide_lng
        FROM lugares_clustering
        WHERE barrio IS NOT NULL AND activo = TRUE
        GROUP BY barrio, comuna
        HAVING COUNT(*) >= 2  -- Solo barrios con al menos 2 POIs
        """
        
        proc_cursor.execute(metrics_query)
        rows_affected = proc_cursor.rowcount
        
        self.processor_conn.commit()
        proc_cursor.close()
        
        logger.info(f"Métricas por barrio calculadas: {rows_affected} barrios")
        return rows_affected
        
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
            entrada_libre, requiere_inscripcion, capacidad_maxima,
            fecha_scraping, estado
        FROM eventos
        WHERE estado = 'programado'
        AND fecha_inicio >= CURRENT_DATE
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
            entrada_libre, requiere_inscripcion, capacidad_maxima,
            fecha_scraping, activo
        ) VALUES (
            %(evento_id)s, %(nombre)s, %(categoria_evento)s, %(tematica)s,
            %(poi_id)s, %(latitud)s, %(longitud)s, %(barrio)s,
            %(fecha_inicio)s, %(fecha_fin)s, %(duracion_dias)s,
            %(mes_inicio)s, %(dia_semana_inicio)s,
            %(entrada_libre)s, %(requiere_inscripcion)s, %(capacidad_maxima)s,
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
                    'entrada_libre': evento['entrada_libre'],
                    'requiere_inscripcion': evento['requiere_inscripcion'],
                    'capacidad_maxima': evento['capacidad_maxima'],
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
        
    def run_full_etl(self) -> Dict[str, int]:
        """Ejecutar ETL completo"""
        logger.info("Iniciando ETL completo...")
        
        results = {}
        
        try:
            self.connect_databases()
            self.create_processor_schema()
            
            # ETL de POIs
            results['pois'] = self.extract_transform_load_pois()
            
            # Calcular métricas por barrio
            results['barrios'] = self.calculate_barrio_metrics()
            
            # ETL de eventos
            results['eventos'] = self.extract_transform_load_eventos()
            
            logger.info("ETL completado exitosamente!")
            
        except Exception as e:
            logger.error(f"Error en ETL: {e}")
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
        print(f"POIs transferidos:      {results.get('pois', 0):4}")
        print(f"Barrios analizados:     {results.get('barrios', 0):4}")
        print(f"Eventos transferidos:   {results.get('eventos', 0):4}")
        print("="*50)
        
    except Exception as e:
        logger.error(f"Error ejecutando ETL: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
