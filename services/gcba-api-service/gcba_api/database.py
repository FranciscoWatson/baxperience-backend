"""
Módulo para manejar la conexión y operaciones con la base de datos PostgreSQL
"""
import psycopg2
from psycopg2.extras import execute_values
import os
import logging
from datetime import datetime
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

logger = logging.getLogger(__name__)

class EcobiciDatabase:
    """Manejador de base de datos para EcoBicis"""
    
    def __init__(self):
        """Inicializa la conexión a la base de datos desde variables de entorno"""
        self.conn = None
        self.db_config = {
            'host': os.getenv('ECOBICI_DB_HOST', 'localhost'),
            'port': os.getenv('ECOBICI_DB_PORT', '5432'),
            'database': os.getenv('ECOBICI_DB_NAME', 'eco_bicis'),
            'user': os.getenv('ECOBICI_DB_USER', 'postgres'),
            'password': os.getenv('ECOBICI_DB_PASSWORD', 'admin')
        }
    
    def connect(self):
        """Conecta a la base de datos"""
        try:
            self.conn = psycopg2.connect(**self.db_config)
            self.conn.autocommit = False
            logger.info(f"✓ Conectado a base de datos: {self.db_config['database']}")
        except Exception as e:
            logger.error(f"✗ Error conectando a base de datos: {e}")
            raise
    
    def disconnect(self):
        """Cierra la conexión a la base de datos"""
        if self.conn:
            self.conn.close()
            logger.info("✓ Desconectado de base de datos")
    
    def upsert_stations(self, stations):
        """
        Inserta o actualiza información de estaciones
        
        Args:
            stations: Lista de diccionarios con información de estaciones
            
        Returns:
            int: Número de estaciones insertadas/actualizadas
        """
        if not stations:
            logger.warning("No hay estaciones para insertar")
            return 0
        
        cursor = self.conn.cursor()
        
        # SQL para INSERT ... ON CONFLICT UPDATE
        sql = """
        INSERT INTO stations (
            station_id, name, physical_configuration, lat, lon,
            address, cross_street, post_code, capacity,
            is_charging_station, groups, nearby_distance, updated_at
        ) VALUES %s
        ON CONFLICT (station_id) DO UPDATE SET
            name = EXCLUDED.name,
            physical_configuration = EXCLUDED.physical_configuration,
            lat = EXCLUDED.lat,
            lon = EXCLUDED.lon,
            address = EXCLUDED.address,
            cross_street = EXCLUDED.cross_street,
            post_code = EXCLUDED.post_code,
            capacity = EXCLUDED.capacity,
            is_charging_station = EXCLUDED.is_charging_station,
            groups = EXCLUDED.groups,
            nearby_distance = EXCLUDED.nearby_distance,
            updated_at = EXCLUDED.updated_at
        """
        
        # Preparar valores
        values = []
        for station in stations:
            values.append((
                station['station_id'],
                station['name'],
                station['physical_configuration'],
                station['lat'],
                station['lon'],
                station['address'],
                station.get('cross_street'),
                station['post_code'],
                station['capacity'],
                station['is_charging_station'],
                station['groups'],  # PostgreSQL array
                station['nearby_distance'],
                datetime.now()
            ))
        
        try:
            execute_values(cursor, sql, values)
            self.conn.commit()
            count = len(values)
            logger.info(f"✓ Insertadas/actualizadas {count} estaciones")
            cursor.close()
            return count
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Error insertando estaciones: {e}")
            cursor.close()
            raise
    
    def insert_station_status(self, statuses):
        """
        Inserta registros de estado de estaciones (histórico)
        
        Args:
            statuses: Lista de diccionarios con estado de estaciones
            
        Returns:
            int: Número de registros insertados
        """
        if not statuses:
            logger.warning("No hay estados para insertar")
            return 0
        
        cursor = self.conn.cursor()
        
        sql = """
        INSERT INTO station_status (
            station_id, num_bikes_mechanical, num_bikes_disabled,
            num_docks_available, num_docks_disabled, last_reported,
            is_charging_station, status, is_installed,
            is_renting, is_returning, traffic
        ) VALUES %s
        """
        
        # Preparar valores
        values = []
        for status in statuses:
            values.append((
                status['station_id'],
                status['num_bikes_mechanical'],
                status['num_bikes_disabled'],
                status['num_docks_available'],
                status['num_docks_disabled'],
                status['last_reported'],
                status['is_charging_station'],
                status['status'],
                status['is_installed'],
                status['is_renting'],
                status['is_returning'],
                status.get('traffic')
            ))
        
        try:
            execute_values(cursor, sql, values)
            self.conn.commit()
            count = len(values)
            logger.info(f"✓ Insertados {count} registros de estado")
            cursor.close()
            return count
        except Exception as e:
            self.conn.rollback()
            logger.error(f"✗ Error insertando estados: {e}")
            cursor.close()
            raise
    
    def get_latest_status(self, limit=10):
        """
        Obtiene el último estado de las estaciones
        
        Args:
            limit: Número máximo de registros a retornar
            
        Returns:
            list: Lista de tuplas con información de estaciones
        """
        cursor = self.conn.cursor()
        
        sql = """
        SELECT * FROM latest_station_status
        ORDER BY num_bikes_mechanical DESC
        LIMIT %s
        """
        
        cursor.execute(sql, (limit,))
        results = cursor.fetchall()
        cursor.close()
        
        return results
    
    def get_stations_count(self):
        """Retorna el número total de estaciones"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM stations")
        count = cursor.fetchone()[0]
        cursor.close()
        return count
    
    def get_status_records_count(self):
        """Retorna el número total de registros de estado"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM station_status")
        count = cursor.fetchone()[0]
        cursor.close()
        return count
    
    def cleanup_old_records(self, days=7):
        """
        Elimina registros antiguos de station_status
        
        Args:
            days: Número de días a mantener (por defecto 7)
            
        Returns:
            int: Número de registros eliminados
        """
        cursor = self.conn.cursor()
        cursor.execute("SELECT cleanup_old_status_records()")
        deleted_count = cursor.fetchone()[0]
        self.conn.commit()
        cursor.close()
        
        logger.info(f"✓ Eliminados {deleted_count} registros antiguos")
        return deleted_count
    
    def get_statistics(self):
        """
        Obtiene estadísticas generales de la base de datos
        
        Returns:
            dict: Diccionario con estadísticas
        """
        cursor = self.conn.cursor()
        
        stats = {}
        
        # Total de estaciones
        cursor.execute("SELECT COUNT(*) FROM stations")
        stats['total_stations'] = cursor.fetchone()[0]
        
        # Total de registros de estado
        cursor.execute("SELECT COUNT(*) FROM station_status")
        stats['total_status_records'] = cursor.fetchone()[0]
        
        # Estaciones con bicicletas disponibles ahora
        cursor.execute("""
            SELECT COUNT(*) FROM latest_station_status 
            WHERE num_bikes_mechanical > 0
        """)
        stats['stations_with_bikes'] = cursor.fetchone()[0]
        
        # Total de bicicletas mecánicas disponibles
        cursor.execute("""
            SELECT COALESCE(SUM(num_bikes_mechanical), 0) FROM latest_station_status
        """)
        stats['total_bikes_available'] = cursor.fetchone()[0]
        
        # Total de docks disponibles
        cursor.execute("""
            SELECT COALESCE(SUM(num_docks_available), 0) FROM latest_station_status
        """)
        stats['total_docks_available'] = cursor.fetchone()[0]
        
        # Barrios con más estaciones
        cursor.execute("""
            SELECT barrio, total_stations 
            FROM stations_by_group 
            ORDER BY total_stations DESC 
            LIMIT 5
        """)
        stats['top_neighborhoods'] = cursor.fetchall()
        
        cursor.close()
        return stats


def test_database_connection():
    """Función de prueba para verificar conexión a la base de datos"""
    try:
        db = EcobiciDatabase()
        print("\n[TEST] Probando conexión a base de datos...")
        db.connect()
        
        # Obtener estadísticas
        stats = db.get_statistics()
        print(f"\n✓ Conexión exitosa a: {db.db_config['database']}")
        print(f"\nEstadísticas:")
        print(f"  Total de estaciones: {stats['total_stations']}")
        print(f"  Total de registros de estado: {stats['total_status_records']}")
        print(f"  Estaciones con bicicletas: {stats['stations_with_bikes']}")
        print(f"  Bicicletas mecánicas disponibles: {stats['total_bikes_available']}")
        print(f"  Docks disponibles: {stats['total_docks_available']}")
        
        if stats['top_neighborhoods']:
            print(f"\n  Top 5 barrios:")
            for barrio, count in stats['top_neighborhoods']:
                print(f"    - {barrio}: {count} estaciones")
        
        db.disconnect()
        print("\n✓ TEST EXITOSO")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FALLIDO: {e}")
        return False


if __name__ == "__main__":
    # Ejecutar test si se corre directamente
    test_database_connection()

