-- =================================================================
-- BAXperience - Base de Datos Operacional (PARCHEADA)
-- =================================================================

-- Eliminar tablas si existen (para recrear el esquema)
DROP TABLE IF EXISTS itinerario_pois CASCADE;
DROP TABLE IF EXISTS itinerarios CASCADE;
DROP TABLE IF EXISTS valoraciones CASCADE;
DROP TABLE IF EXISTS eventos CASCADE;
DROP TABLE IF EXISTS preferencias_usuario CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;
DROP TABLE IF EXISTS pois CASCADE;
DROP TABLE IF EXISTS subcategorias CASCADE;
DROP TABLE IF EXISTS categorias CASCADE;

-- =================================================================
-- TABLA: CATEGORIAS
-- =================================================================
CREATE TABLE categorias (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL UNIQUE,
    descripcion TEXT,
    icono VARCHAR(50),
    color VARCHAR(7),
    activo BOOLEAN DEFAULT TRUE,
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Insertar categorías base
INSERT INTO categorias (nombre, descripcion, icono, color) VALUES 
('Museos', 'Espacios de exhibición patrimonial y cultural', 'museum', '#8B4513'),
('Gastronomía', 'Restaurantes, cafés, bares y espacios gastronómicos', 'restaurant', '#FF6347'),
('Monumentos', 'Monumentos históricos y obras de arte público', 'monument', '#2F4F4F'),
('Lugares Históricos', 'Sitios de importancia histórica y patrimonial', 'history', '#800080'),
('Entretenimiento', 'Cines, teatros y espacios de entretenimiento', 'theater', '#FF1493'),
('Eventos', 'Eventos temporales y actividades culturales', 'event', '#FFD700');

-- =================================================================
-- TABLA: SUBCATEGORIAS
-- =================================================================
CREATE TABLE subcategorias (
    id SERIAL PRIMARY KEY,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    nombre VARCHAR(100) NOT NULL,
    descripcion TEXT,
    activo BOOLEAN DEFAULT TRUE,

    UNIQUE (categoria_id, nombre),

    -- Necesario para la FK compuesta desde POIs
    UNIQUE (id, categoria_id)
);

-- Insertar subcategorías para museos
INSERT INTO subcategorias (categoria_id, nombre, descripcion) VALUES 
(1, 'Museos de Arte', 'Museos especializados en arte y cultura visual'),
(1, 'Museos de Historia', 'Museos de historia argentina e internacional'),
(1, 'Museos de Ciencia', 'Museos de ciencias naturales y tecnología'),
(1, 'Museos Especializados', 'Museos temáticos y especializados');

-- Insertar subcategorías para gastronomía
INSERT INTO subcategorias (categoria_id, nombre, descripcion) VALUES 
(2, 'Restaurante', 'Restaurantes de comida completa'),
(2, 'Café', 'Cafeterías y espacios de café'),
(2, 'Bar', 'Bares y espacios de bebidas'),
(2, 'Parrilla', 'Parrillas y asados'),
(2, 'Vinería', 'Espacios especializados en vinos'),
(2, 'Pizzería', 'Pizzerías y comida italiana'),
(2, 'Comida Internacional', 'Restaurantes de cocina internacional');

-- Insertar subcategorías para monumentos
INSERT INTO subcategorias (categoria_id, nombre, descripcion) VALUES 
(3, 'Monumento Histórico', 'Monumentos de importancia histórica'),
(3, 'Obra de Arte Público', 'Esculturas y arte en espacios públicos'),
(3, 'Plazas y Espacios', 'Plazas con monumentos significativos');

-- Insertar subcategorías para entretenimiento
INSERT INTO subcategorias (categoria_id, nombre, descripcion) VALUES 
(5, 'Salas de Cine', 'Complejos cinematográficos'),
(5, 'Teatros', 'Teatros y espacios escénicos'),
(5, 'Centros Culturales', 'Espacios culturales multidisciplinarios');

-- =================================================================
-- TABLA: POIS (Points of Interest)
-- =================================================================
CREATE TABLE pois (
    id SERIAL PRIMARY KEY,

    -- Información básica
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),
    subcategoria_id INTEGER REFERENCES subcategorias(id),

    -- Ubicación geográfica
    latitud DECIMAL(10, 8) NOT NULL,
    longitud DECIMAL(11, 8) NOT NULL,
    direccion TEXT,
    direccion_normalizada TEXT,
    calle VARCHAR(150),
    altura VARCHAR(10),
    piso VARCHAR(50),
    codigo_postal VARCHAR(10),
    barrio VARCHAR(100),
    comuna INTEGER,

    -- Información de contacto
    telefono VARCHAR(50),
    codigo_area VARCHAR(10),
    email VARCHAR(255),
    web VARCHAR(500),

    -- Para gastronomía
    tipo_cocina VARCHAR(100),
    tipo_ambiente VARCHAR(100),
    horario TEXT,

    -- Para museos y cultura
    jurisdiccion VARCHAR(100),
    año_inauguracion INTEGER,

    -- Para monumentos
    material VARCHAR(200),
    autor VARCHAR(200),
    denominacion_simboliza TEXT,

    -- Para cines
    numero_pantallas INTEGER,
    numero_butacas INTEGER,
    tipo_gestion VARCHAR(50),

    -- Métricas y valoraciones
    valoracion_promedio DECIMAL(3,2) DEFAULT 0.0,
    numero_valoraciones INTEGER DEFAULT 0,

    -- Metadata
    fuente_original VARCHAR(100) NOT NULL,
    id_fuente_original VARCHAR(100),
    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    verificado BOOLEAN DEFAULT FALSE,

    -- Constraints
    CONSTRAINT check_valoracion_poi CHECK (valoracion_promedio >= 0 AND valoracion_promedio <= 5),
    CONSTRAINT check_comuna CHECK (comuna >= 1 AND comuna <= 15),

    -- REEMPLAZA AL CHECK CON SUBCONSULTA:
    -- Garantiza que la subcategoría pertenezca a la misma categoría del POI
    FOREIGN KEY (subcategoria_id, categoria_id)
        REFERENCES subcategorias (id, categoria_id)
);

-- =================================================================
-- TABLA: USUARIOS
-- =================================================================
CREATE TABLE usuarios (
    id SERIAL PRIMARY KEY,

    username VARCHAR(50) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,

    nombre VARCHAR(100),
    apellido VARCHAR(100),
    fecha_nacimiento DATE,
    genero VARCHAR(20),

    telefono VARCHAR(20),
    pais_origen VARCHAR(100),
    ciudad_origen VARCHAR(100),

    idioma_preferido VARCHAR(10) DEFAULT 'es',

    notificaciones_email BOOLEAN DEFAULT TRUE,
    notificaciones_push BOOLEAN DEFAULT TRUE,
    notificaciones_marketing BOOLEAN DEFAULT FALSE,

    tipo_viajero VARCHAR(50),
    duracion_viaje_promedio INTEGER,
    frecuencia_visita VARCHAR(20),

    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_ultimo_acceso TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT TRUE,
    email_verificado BOOLEAN DEFAULT FALSE,

    CONSTRAINT check_edad CHECK (fecha_nacimiento IS NULL OR fecha_nacimiento <= CURRENT_DATE - INTERVAL '13 years')
);

-- =================================================================
-- TABLA: PREFERENCIAS_USUARIO
-- =================================================================
CREATE TABLE preferencias_usuario (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    categoria_id INTEGER NOT NULL REFERENCES categorias(id),

    le_gusta BOOLEAN NOT NULL DEFAULT TRUE,

    tipos_cocina_preferidos TEXT[],
    prefiere_ambiente VARCHAR(50),

    temas_interes TEXT[],

    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (usuario_id, categoria_id)
);

-- =================================================================
-- TABLA: ITINERARIOS
-- =================================================================
CREATE TABLE itinerarios (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,

    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,

    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,

    modo_transporte_preferido VARCHAR(50),

    estado VARCHAR(20) DEFAULT 'planificado',
    es_publico BOOLEAN DEFAULT FALSE,

    hotel_latitud DECIMAL(10, 8),
    hotel_longitud DECIMAL(11, 8),
    hotel_direccion TEXT,

    distancia_total_km DECIMAL(8,2),
    tiempo_estimado_horas DECIMAL(6,2),

    valoracion_itinerario DECIMAL(3,2),
    comentarios_itinerario TEXT,
    recomendaria BOOLEAN,

    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT check_fechas_itinerario CHECK (fecha_fin >= fecha_inicio),
    CONSTRAINT check_valoracion_itinerario CHECK (
        valoracion_itinerario IS NULL OR (valoracion_itinerario >= 0 AND valoracion_itinerario <= 5)
    )
);

-- =================================================================
-- TABLA: ITINERARIO_POIS
-- =================================================================
CREATE TABLE itinerario_pois (
    id SERIAL PRIMARY KEY,
    itinerario_id INTEGER NOT NULL REFERENCES itinerarios(id) ON DELETE CASCADE,
    poi_id INTEGER NOT NULL REFERENCES pois(id),

    dia_visita INTEGER NOT NULL,
    orden_en_dia INTEGER NOT NULL,

    hora_inicio_planificada TIME,
    hora_fin_planificada TIME,
    tiempo_estimado_minutos INTEGER,

    hora_inicio_real TIME,
    hora_fin_real TIME,
    fue_visitado BOOLEAN DEFAULT FALSE,
    razon_no_visitado TEXT,

    notas_planificacion TEXT,
    notas_visita TEXT,

    fecha_agregado TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (itinerario_id, poi_id),
    CONSTRAINT check_orden CHECK (dia_visita > 0 AND orden_en_dia > 0),
    CONSTRAINT check_tiempo CHECK (tiempo_estimado_minutos IS NULL OR tiempo_estimado_minutos > 0)
);

-- =================================================================
-- TABLA: VALORACIONES
-- =================================================================
CREATE TABLE valoraciones (
    id SERIAL PRIMARY KEY,
    usuario_id INTEGER NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    poi_id INTEGER NOT NULL REFERENCES pois(id) ON DELETE CASCADE,
    itinerario_id INTEGER REFERENCES itinerarios(id),

    puntuacion_general DECIMAL(3,2) NOT NULL,

    puntuacion_ubicacion DECIMAL(3,2),
    puntuacion_servicio DECIMAL(3,2),
    puntuacion_ambiente DECIMAL(3,2),
    puntuacion_accesibilidad DECIMAL(3,2),

    titulo_review VARCHAR(200),
    comentario TEXT,
    aspectos_positivos TEXT,
    aspectos_negativos TEXT,
    consejos_otros_viajeros TEXT,

    fecha_visita DATE,
    tipo_visita VARCHAR(50),
    duracion_visita_minutos INTEGER,

    es_verificada BOOLEAN DEFAULT FALSE,
    es_destacada BOOLEAN DEFAULT FALSE,
    util_count INTEGER DEFAULT 0,

    fecha_creacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    UNIQUE (usuario_id, poi_id),

    CONSTRAINT check_puntuaciones CHECK (
        puntuacion_general >= 0 AND puntuacion_general <= 5 AND
        (puntuacion_ubicacion IS NULL OR (puntuacion_ubicacion >= 0 AND puntuacion_ubicacion <= 5)) AND
        (puntuacion_servicio IS NULL OR (puntuacion_servicio >= 0 AND puntuacion_servicio <= 5)) AND
        (puntuacion_ambiente IS NULL OR (puntuacion_ambiente >= 0 AND puntuacion_ambiente <= 5)) AND
        (puntuacion_accesibilidad IS NULL OR (puntuacion_accesibilidad >= 0 AND puntuacion_accesibilidad <= 5))
    )
);

-- =================================================================
-- TABLA: EVENTOS
-- =================================================================
CREATE TABLE eventos (
    id SERIAL PRIMARY KEY,

    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    categoria_evento VARCHAR(100),
    tematica VARCHAR(100),

    poi_id INTEGER REFERENCES pois(id),
    ubicacion_especifica TEXT,
    direccion_evento TEXT,
    latitud DECIMAL(10, 8),
    longitud DECIMAL(11, 8),
    barrio VARCHAR(100),

    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    hora_inicio TIME,
    hora_fin TIME,
    dias_semana VARCHAR(7),

    entrada_libre BOOLEAN DEFAULT TRUE,
    requiere_inscripcion BOOLEAN DEFAULT FALSE,
    capacidad_maxima INTEGER,
    edad_minima INTEGER,
    edad_maxima INTEGER,

    url_evento VARCHAR(500),
    url_inscripcion VARCHAR(500),
    url_compra_tickets VARCHAR(500),
    telefono_contacto VARCHAR(50),
    email_contacto VARCHAR(255),

    organizador VARCHAR(200),
    patrocinadores TEXT,
    requisitos_especiales TEXT,
    que_llevar TEXT,

    fecha_scraping TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    url_fuente VARCHAR(500),
    hash_contenido VARCHAR(64),

    estado VARCHAR(20) DEFAULT 'programado',
    verificado BOOLEAN DEFAULT FALSE,
    destacado BOOLEAN DEFAULT FALSE,

    visualizaciones INTEGER DEFAULT 0,
    interesados INTEGER DEFAULT 0,
    asistentes_confirmados INTEGER DEFAULT 0,

    CONSTRAINT check_fechas_evento CHECK (fecha_fin IS NULL OR fecha_fin >= fecha_inicio),
    CONSTRAINT check_capacidad CHECK (capacidad_maxima IS NULL OR capacidad_maxima > 0),
    CONSTRAINT check_edades CHECK (edad_maxima IS NULL OR edad_minima IS NULL OR edad_maxima >= edad_minima)
);

-- =================================================================
-- ÍNDICES
-- =================================================================

-- Geoespaciales (point usa GiST nativo)
CREATE INDEX idx_pois_geolocation ON pois USING GIST (point(longitud, latitud));
CREATE INDEX idx_eventos_geolocation ON eventos USING GIST (point(longitud, latitud))
    WHERE longitud IS NOT NULL AND latitud IS NOT NULL;
CREATE INDEX idx_itinerarios_hotel_location ON itinerarios USING GIST (point(hotel_longitud, hotel_latitud))
    WHERE hotel_longitud IS NOT NULL AND hotel_latitud IS NOT NULL;

-- Búsquedas frecuentes
CREATE INDEX idx_pois_categoria ON pois(categoria_id, activo);
CREATE INDEX idx_pois_barrio ON pois(barrio) WHERE barrio IS NOT NULL;
CREATE INDEX idx_pois_valoracion ON pois(valoracion_promedio DESC, numero_valoraciones DESC) WHERE activo = true;

CREATE INDEX idx_usuarios_email ON usuarios(email) WHERE activo = true;
CREATE INDEX idx_usuarios_fecha_registro ON usuarios(fecha_registro);

CREATE INDEX idx_itinerarios_usuario ON itinerarios(usuario_id, fecha_inicio DESC);
CREATE INDEX idx_itinerarios_fechas ON itinerarios(fecha_inicio, fecha_fin) WHERE estado != 'cancelado';
CREATE INDEX idx_itinerario_pois_orden ON itinerario_pois(itinerario_id, dia_visita, orden_en_dia);

CREATE INDEX idx_eventos_fechas ON eventos(fecha_inicio, fecha_fin) WHERE estado = 'programado';
CREATE INDEX idx_eventos_categoria ON eventos(categoria_evento, tematica);
CREATE INDEX idx_eventos_poi ON eventos(poi_id) WHERE poi_id IS NOT NULL;

CREATE INDEX idx_valoraciones_poi ON valoraciones(poi_id, puntuacion_general DESC);
CREATE INDEX idx_valoraciones_usuario ON valoraciones(usuario_id, fecha_creacion DESC);

-- =================================================================
-- FUNCIONES
-- =================================================================

CREATE OR REPLACE FUNCTION calcular_distancia_km(
    lat1 DECIMAL, lon1 DECIMAL, 
    lat2 DECIMAL, lon2 DECIMAL
) RETURNS DECIMAL AS $$
BEGIN
    RETURN (
        6371 * acos(
            cos(radians(lat1)) * cos(radians(lat2)) * 
            cos(radians(lon2) - radians(lon1)) + 
            sin(radians(lat1)) * sin(radians(lat2))
        )
    );
END;
$$ LANGUAGE plpgsql IMMUTABLE;

CREATE OR REPLACE FUNCTION actualizar_valoracion_poi(poi_id_param INTEGER) 
RETURNS VOID AS $$
BEGIN
    UPDATE pois 
    SET 
        valoracion_promedio = (
            SELECT AVG(puntuacion_general) 
            FROM valoraciones 
            WHERE valoraciones.poi_id = poi_id_param
        ),
        numero_valoraciones = (
            SELECT COUNT(*) 
            FROM valoraciones 
            WHERE valoraciones.poi_id = poi_id_param
        ),
        fecha_actualizacion = CURRENT_TIMESTAMP
    WHERE id = poi_id_param;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION limpiar_eventos_vencidos() 
RETURNS INTEGER AS $$
DECLARE
    eventos_eliminados INTEGER;
BEGIN
    UPDATE eventos 
    SET estado = 'finalizado'
    WHERE fecha_fin < CURRENT_DATE 
      AND estado = 'programado';
    
    GET DIAGNOSTICS eventos_eliminados = ROW_COUNT;
    RETURN eventos_eliminados;
END;
$$ LANGUAGE plpgsql;

-- =================================================================
-- TRIGGERS
-- =================================================================

CREATE OR REPLACE FUNCTION actualizar_fecha_modificacion()
RETURNS TRIGGER AS $$
BEGIN
    NEW.fecha_actualizacion = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_pois_fecha_actualizacion
    BEFORE UPDATE ON pois
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_modificacion();

CREATE TRIGGER trigger_usuarios_fecha_actualizacion
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_modificacion();

CREATE TRIGGER trigger_itinerarios_fecha_actualizacion
    BEFORE UPDATE ON itinerarios
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_fecha_modificacion();

CREATE OR REPLACE FUNCTION trigger_actualizar_valoraciones_poi()
RETURNS TRIGGER AS $$
BEGIN
    IF TG_OP = 'DELETE' THEN
        PERFORM actualizar_valoracion_poi(OLD.poi_id);
        RETURN OLD;
    ELSE
        PERFORM actualizar_valoracion_poi(NEW.poi_id);
        RETURN NEW;
    END IF;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_valoraciones_poi_cambio
    AFTER INSERT OR UPDATE OR DELETE ON valoraciones
    FOR EACH ROW
    EXECUTE FUNCTION trigger_actualizar_valoraciones_poi();

-- =================================================================
-- COMENTARIOS
-- =================================================================

COMMENT ON TABLE categorias IS 'Categorías principales de puntos de interés';
COMMENT ON TABLE subcategorias IS 'Subcategorías específicas dentro de cada categoría';
COMMENT ON TABLE pois IS 'Tabla principal normalizada de todos los puntos de interés de CABA';
COMMENT ON TABLE usuarios IS 'Información completa de usuarios registrados en el sistema';
COMMENT ON TABLE preferencias_usuario IS 'Preferencias específicas de cada usuario por categoría';
COMMENT ON TABLE itinerarios IS 'Itinerarios de viaje creados por los usuarios';
COMMENT ON TABLE itinerario_pois IS 'Relación detallada entre itinerarios y POIs visitados';
COMMENT ON TABLE valoraciones IS 'Valoraciones y reviews de usuarios sobre POIs visitados';
COMMENT ON TABLE eventos IS 'Eventos temporales scrapeados del sitio oficial de turismo';

COMMENT ON COLUMN pois.fuente_original IS 'Fuente del dato original (csv_museos, csv_gastronomia, etc.)';
COMMENT ON COLUMN pois.id_fuente_original IS 'ID original en el dataset fuente para trazabilidad';
COMMENT ON COLUMN eventos.hash_contenido IS 'Hash MD5 del contenido para detectar cambios';
COMMENT ON COLUMN itinerarios.es_publico IS 'Si otros usuarios pueden ver y copiar este itinerario';
