-- =================================================================
-- BAXperience Data Processor - Migración: Agregar columna is_imperdible
-- =================================================================
-- Descripción: Agrega la columna is_imperdible a lugares_clustering
--              para dar más peso a lugares imperdibles en recomendaciones
-- Fecha: Octubre 2025
-- Autor: BAXperience Team
-- =================================================================

-- 1. Agregar columna is_imperdible (default FALSE)
ALTER TABLE lugares_clustering
ADD COLUMN IF NOT EXISTS is_imperdible BOOLEAN DEFAULT FALSE;

-- 2. Crear índice para búsquedas rápidas de lugares imperdibles
CREATE INDEX IF NOT EXISTS idx_lugares_clustering_imperdibles 
ON lugares_clustering(is_imperdible) 
WHERE is_imperdible = TRUE;

-- 3. Comentario descriptivo
COMMENT ON COLUMN lugares_clustering.is_imperdible IS 
'Indica si el lugar es considerado imperdible de Buenos Aires. Los lugares imperdibles reciben mayor peso en las recomendaciones.';

-- 4. Verificación de la migración
DO $$
BEGIN
    -- Verificar que la columna existe
    IF EXISTS (
        SELECT 1 
        FROM information_schema.columns 
        WHERE table_name = 'lugares_clustering' 
        AND column_name = 'is_imperdible'
    ) THEN
        RAISE NOTICE '✓ Columna is_imperdible agregada exitosamente';
    ELSE
        RAISE EXCEPTION '✗ Error: La columna is_imperdible no fue creada';
    END IF;

    -- Verificar que el índice existe
    IF EXISTS (
        SELECT 1 
        FROM pg_indexes 
        WHERE tablename = 'lugares_clustering' 
        AND indexname = 'idx_lugares_clustering_imperdibles'
    ) THEN
        RAISE NOTICE '✓ Índice idx_lugares_clustering_imperdibles creado exitosamente';
    ELSE
        RAISE EXCEPTION '✗ Error: El índice no fue creado';
    END IF;
END $$;

-- 5. Estadísticas post-migración
SELECT 
    COUNT(*) as total_lugares,
    COUNT(*) FILTER (WHERE is_imperdible = TRUE) as lugares_imperdibles,
    COUNT(*) FILTER (WHERE is_imperdible = FALSE) as lugares_normales
FROM lugares_clustering;

-- =================================================================
-- NOTAS IMPORTANTES:
-- =================================================================
-- 1. Esta migración es IDEMPOTENTE - se puede ejecutar múltiples veces sin error
-- 2. La columna se crea con valor por defecto FALSE para no afectar datos existentes
-- 3. Después de ejecutar esta migración, se debe:
--    a) Ejecutar el ETL para sincronizar datos desde Operational DB
--    b) Verificar que los lugares imperdibles tengan is_imperdible = TRUE
-- 4. El índice parcial (WHERE is_imperdible = TRUE) optimiza búsquedas de imperdibles
-- =================================================================
