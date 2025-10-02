"""
Script para crear la base de datos y tablas de EcoBici
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

# Configuración de conexión
DB_CONFIG = {
    'host': os.getenv('ECOBICI_DB_HOST', 'localhost'),
    'port': os.getenv('ECOBICI_DB_PORT', '5432'),
    'user': os.getenv('ECOBICI_DB_USER', 'postgres'),
    'password': os.getenv('ECOBICI_DB_PASSWORD', 'admin')
}

DB_NAME = os.getenv('ECOBICI_DB_NAME', 'eco_bicis')

# SQL para crear las tablas (sin CREATE DATABASE)
CREATE_TABLES_SQL = """
-- Tabla de estaciones (información estática)
CREATE TABLE IF NOT EXISTS stations (
    station_id VARCHAR(10) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    physical_configuration VARCHAR(50),
    lat DECIMAL(10, 8) NOT NULL,
    lon DECIMAL(11, 8) NOT NULL,
    address VARCHAR(500),
    cross_street VARCHAR(255),
    post_code VARCHAR(20),
    capacity INTEGER NOT NULL,
    is_charging_station BOOLEAN DEFAULT FALSE,
    groups TEXT[], -- Array de barrios/zonas (ej: ['RETIRO', 'PALERMO'])
    nearby_distance INTEGER DEFAULT 1000,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabla de estado de estaciones (información en tiempo real)
CREATE TABLE IF NOT EXISTS station_status (
    id SERIAL PRIMARY KEY,
    station_id VARCHAR(10) NOT NULL REFERENCES stations(station_id) ON DELETE CASCADE,
    num_bikes_mechanical INTEGER NOT NULL DEFAULT 0, -- Solo bicicletas mecánicas
    num_bikes_disabled INTEGER DEFAULT 0,
    num_docks_available INTEGER NOT NULL DEFAULT 0,
    num_docks_disabled INTEGER DEFAULT 0,
    last_reported BIGINT, -- Timestamp Unix
    is_charging_station BOOLEAN DEFAULT FALSE,
    status VARCHAR(50), -- IN_SERVICE, OUT_OF_SERVICE, etc.
    is_installed INTEGER DEFAULT 1,
    is_renting INTEGER DEFAULT 1,
    is_returning INTEGER DEFAULT 1,
    traffic VARCHAR(50),
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP -- Cuando se guardó este registro
);

-- Índices para mejorar performance
CREATE INDEX IF NOT EXISTS idx_stations_location ON stations(lat, lon);
CREATE INDEX IF NOT EXISTS idx_stations_groups ON stations USING GIN(groups);
CREATE INDEX IF NOT EXISTS idx_station_status_station_id ON station_status(station_id);
CREATE INDEX IF NOT EXISTS idx_station_status_recorded_at ON station_status(recorded_at DESC);
CREATE INDEX IF NOT EXISTS idx_station_status_bikes ON station_status(num_bikes_mechanical) WHERE num_bikes_mechanical > 0;

-- Vista para obtener el último estado de cada estación
CREATE OR REPLACE VIEW latest_station_status AS
SELECT DISTINCT ON (ss.station_id)
    s.station_id,
    s.name,
    s.lat,
    s.lon,
    s.address,
    s.post_code,
    s.capacity,
    s.groups,
    ss.num_bikes_mechanical,
    ss.num_docks_available,
    ss.status,
    ss.is_renting,
    ss.is_returning,
    to_timestamp(ss.last_reported) as last_reported_time,
    ss.recorded_at
FROM stations s
LEFT JOIN station_status ss ON s.station_id = ss.station_id
ORDER BY ss.station_id, ss.recorded_at DESC;

-- Vista para análisis histórico (estaciones con más bicicletas disponibles)
CREATE OR REPLACE VIEW top_stations_with_bikes AS
SELECT 
    s.station_id,
    s.name,
    s.address,
    s.groups,
    AVG(ss.num_bikes_mechanical) as avg_bikes_mechanical,
    MAX(ss.num_bikes_mechanical) as max_bikes_mechanical,
    COUNT(*) as total_records
FROM stations s
JOIN station_status ss ON s.station_id = ss.station_id
WHERE ss.num_bikes_mechanical > 0
GROUP BY s.station_id, s.name, s.address, s.groups
ORDER BY avg_bikes_mechanical DESC;

-- Vista para estaciones por barrio/grupo
CREATE OR REPLACE VIEW stations_by_group AS
SELECT 
    unnest(groups) as barrio,
    COUNT(*) as total_stations,
    SUM(capacity) as total_capacity
FROM stations
WHERE groups IS NOT NULL AND array_length(groups, 1) > 0
GROUP BY barrio
ORDER BY total_stations DESC;

-- Función para limpiar registros antiguos (mantener solo últimos 7 días)
CREATE OR REPLACE FUNCTION cleanup_old_status_records()
RETURNS INTEGER AS $$
DECLARE
    deleted_count INTEGER;
BEGIN
    DELETE FROM station_status
    WHERE recorded_at < CURRENT_TIMESTAMP - INTERVAL '7 days';
    
    GET DIAGNOSTICS deleted_count = ROW_COUNT;
    RETURN deleted_count;
END;
$$ LANGUAGE plpgsql;
"""

def create_database_if_not_exists():
    """Crea la base de datos si no existe"""
    try:
        # Conectar a la base de datos por defecto (postgres)
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Verificar si la base de datos existe
        cursor.execute(f"SELECT 1 FROM pg_database WHERE datname = '{DB_NAME}'")
        exists = cursor.fetchone()
        
        if not exists:
            print(f"Creando base de datos '{DB_NAME}'...")
            cursor.execute(f'CREATE DATABASE {DB_NAME}')
            print(f"OK Base de datos '{DB_NAME}' creada exitosamente")
        else:
            print(f"OK Base de datos '{DB_NAME}' ya existe")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR creando base de datos: {e}")
        return False

def create_tables():
    """Crea las tablas en la base de datos"""
    try:
        # Conectar a la base de datos eco_bicis
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_NAME
        )
        cursor = conn.cursor()
        
        print(f"\nCreando tablas en '{DB_NAME}'...")
        cursor.execute(CREATE_TABLES_SQL)
        conn.commit()
        
        print("OK Tablas creadas exitosamente:")
        print("  - stations")
        print("  - station_status")
        print("  - latest_station_status (vista)")
        print("  - top_stations_with_bikes (vista)")
        print("  - stations_by_group (vista)")
        print("  - cleanup_old_status_records() (funcion)")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"ERROR creando tablas: {e}")
        return False

def main():
    print("=" * 70)
    print("CREACION DE BASE DE DATOS ECOBICI")
    print("=" * 70)
    
    # Crear base de datos
    if not create_database_if_not_exists():
        print("\nERROR: No se pudo crear la base de datos")
        return 1
    
    # Crear tablas
    if not create_tables():
        print("\nERROR: No se pudieron crear las tablas")
        return 1
    
    print("\n" + "=" * 70)
    print("SETUP COMPLETADO EXITOSAMENTE")
    print("=" * 70)
    print("\nAhora puedes ejecutar:")
    print("  python main.py")
    print("\npara actualizar los datos de EcoBici")
    
    return 0

if __name__ == "__main__":
    exit(main())

