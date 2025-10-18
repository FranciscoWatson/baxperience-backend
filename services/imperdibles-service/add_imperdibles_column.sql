-- =================================================================
-- MIGRATION: Agregar campo is_imperdible a tabla POIs
-- Fecha: 2025-01-17
-- Descripción: Permite marcar POIs como "imperdibles" para darles
--              más peso en el sistema de recomendaciones
-- =================================================================

-- 1. Agregar columna is_imperdible (default FALSE)
ALTER TABLE pois 
ADD COLUMN IF NOT EXISTS is_imperdible BOOLEAN DEFAULT FALSE;

-- 2. Crear índice para optimizar queries de imperdibles
CREATE INDEX IF NOT EXISTS idx_pois_imperdibles 
ON pois(is_imperdible) 
WHERE is_imperdible = TRUE;

-- 3. Agregar comentario descriptivo a la columna
COMMENT ON COLUMN pois.is_imperdible IS 
'Marca si el POI es considerado "imperdible" según el sitio oficial de turismo de Buenos Aires. Los POIs imperdibles reciben mayor peso en el sistema de recomendaciones.';

-- 4. (Opcional) Crear vista para consultar solo imperdibles
CREATE OR REPLACE VIEW pois_imperdibles AS
SELECT 
    p.id,
    p.nombre,
    p.descripcion,
    p.categoria_id,
    c.nombre AS categoria_nombre,
    p.subcategoria_id,
    s.nombre AS subcategoria_nombre,
    p.latitud,
    p.longitud,
    p.direccion,
    p.barrio,
    p.valoracion_promedio,
    p.numero_valoraciones,
    p.fecha_creacion,
    p.fecha_actualizacion
FROM pois p
LEFT JOIN categorias c ON p.categoria_id = c.id
LEFT JOIN subcategorias s ON p.subcategoria_id = s.id
WHERE p.is_imperdible = TRUE
ORDER BY p.valoracion_promedio DESC, p.nombre;

COMMENT ON VIEW pois_imperdibles IS 
'Vista de solo lectura que muestra únicamente los POIs marcados como imperdibles';

-- =================================================================
-- VERIFICACIÓN
-- =================================================================

-- Verificar que la columna fue creada
SELECT 
    column_name, 
    data_type, 
    column_default,
    is_nullable
FROM information_schema.columns
WHERE table_name = 'pois' 
  AND column_name = 'is_imperdible';

-- Verificar que el índice fue creado
SELECT 
    indexname,
    indexdef
FROM pg_indexes
WHERE tablename = 'pois' 
  AND indexname = 'idx_pois_imperdibles';

-- Contar POIs imperdibles actuales
SELECT 
    COUNT(*) AS total_imperdibles
FROM pois
WHERE is_imperdible = TRUE;

-- =================================================================
-- QUERIES ÚTILES PARA GESTIÓN DE IMPERDIBLES
-- =================================================================

-- Ver todos los POIs imperdibles con su información completa
/*
SELECT 
    p.id,
    p.nombre,
    c.nombre AS categoria,
    p.barrio,
    p.valoracion_promedio,
    p.fecha_actualizacion
FROM pois p
JOIN categorias c ON p.categoria_id = c.id
WHERE p.is_imperdible = TRUE
ORDER BY p.nombre;
*/

-- Marcar un POI específico como imperdible (ejemplo)
/*
UPDATE pois 
SET is_imperdible = TRUE,
    fecha_actualizacion = NOW()
WHERE nombre ILIKE '%teatro colón%';
*/

-- Desmarcar un POI como imperdible
/*
UPDATE pois 
SET is_imperdible = FALSE,
    fecha_actualizacion = NOW()
WHERE id = <poi_id>;
*/

-- Estadísticas de imperdibles por categoría
/*
SELECT 
    c.nombre AS categoria,
    COUNT(p.id) AS cantidad_imperdibles,
    ROUND(AVG(p.valoracion_promedio), 2) AS valoracion_promedio
FROM pois p
JOIN categorias c ON p.categoria_id = c.id
WHERE p.is_imperdible = TRUE
GROUP BY c.nombre
ORDER BY cantidad_imperdibles DESC;
*/

-- Ver POIs que podrían ser imperdibles (alta valoración pero no marcados)
/*
SELECT 
    p.id,
    p.nombre,
    c.nombre AS categoria,
    p.valoracion_promedio,
    p.numero_valoraciones
FROM pois p
JOIN categorias c ON p.categoria_id = c.id
WHERE p.is_imperdible = FALSE
  AND p.valoracion_promedio >= 4.5
  AND p.numero_valoraciones >= 100
ORDER BY p.valoracion_promedio DESC, p.numero_valoraciones DESC
LIMIT 20;
*/

-- =================================================================
-- ROLLBACK (en caso de necesitar revertir los cambios)
-- =================================================================

/*
-- Eliminar vista
DROP VIEW IF EXISTS pois_imperdibles;

-- Eliminar índice
DROP INDEX IF EXISTS idx_pois_imperdibles;

-- Eliminar columna
ALTER TABLE pois DROP COLUMN IF EXISTS is_imperdible;
*/
