-- Base de datos para EcoBicis de la Ciudad de Buenos Aires
-- Este esquema almacena información de estaciones y su estado en tiempo real

CREATE DATABASE eco_bicis;

\c eco_bicis;

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
CREATE INDEX idx_stations_location ON stations(lat, lon);
CREATE INDEX idx_stations_groups ON stations USING GIN(groups);
CREATE INDEX idx_station_status_station_id ON station_status(station_id);
CREATE INDEX idx_station_status_recorded_at ON station_status(recorded_at DESC);
CREATE INDEX idx_station_status_bikes ON station_status(num_bikes_mechanical) WHERE num_bikes_mechanical > 0;

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

-- Comentarios para documentación
COMMENT ON TABLE stations IS 'Información estática de estaciones de EcoBici (actualizada periódicamente)';
COMMENT ON TABLE station_status IS 'Estado en tiempo real de las estaciones (histórico)';
COMMENT ON COLUMN station_status.num_bikes_mechanical IS 'Cantidad de bicicletas mecánicas disponibles (no incluye ebikes)';
COMMENT ON COLUMN station_status.last_reported IS 'Timestamp Unix del último reporte de la estación';
COMMENT ON COLUMN station_status.recorded_at IS 'Timestamp de cuando se guardó este registro en nuestra BD';

-- Crear usuario para el servicio (opcional)
-- CREATE USER gcba_api_service WITH PASSWORD 'your_secure_password';
-- GRANT CONNECT ON DATABASE eco_bicis TO gcba_api_service;
-- GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO gcba_api_service;
-- GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO gcba_api_service;

