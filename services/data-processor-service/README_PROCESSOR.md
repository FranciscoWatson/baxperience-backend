# BAXperience Data Processor

Servicio encargado de procesar datos crudos de CSVs y transformarlos para el sistema de recomendaciones y clustering.

## Arquitectura de Datos

```
CSVs Filtrados → BD Operacional → BD Data Processor → Clustering/ML
     ↓              ↓                    ↓               ↓
   Raw Data    Complete Data      Optimized Data    Recommendations
```

### Bases de Datos

1. **BD Operacional**: Base de datos completa con todos los usuarios, POIs, itinerarios y valoraciones
2. **BD Data Processor**: Base de datos optimizada para clustering y análisis con datos normalizados

## Instalación

### 1. Dependencias

```bash
cd baxperience-backend/services/data-processor-service
pip install -r requirements.txt
```

### 2. Configuración de Base de Datos

Copia el archivo de configuración:
```bash
cp env.example .env
```

Edita `.env` con tus credenciales de base de datos:
```env
# BD Operacional
OPERATIONAL_DB_HOST=localhost
OPERATIONAL_DB_PORT=5432
OPERATIONAL_DB_NAME=baxperience_operational
OPERATIONAL_DB_USER=postgres
OPERATIONAL_DB_PASSWORD=tu_password

# BD Data Processor
PROCESSOR_DB_HOST=localhost
PROCESSOR_DB_PORT=5433
PROCESSOR_DB_NAME=baxperience_processor
PROCESSOR_DB_USER=postgres
PROCESSOR_DB_PASSWORD=tu_password
```

### 3. Crear Bases de Datos

```sql
-- BD Operacional
CREATE DATABASE baxperience_operational;

-- BD Data Processor  
CREATE DATABASE baxperience_processor;
```

### 4. Crear Esquema Operacional

```bash
psql -h localhost -p 5432 -U postgres -d baxperience_operational -f baxperience_operational_db.sql
```

## Uso

### Pipeline Completo (Recomendado)

```bash
python main.py --mode=full
```

Este comando ejecuta:
1. ✅ Procesamiento de CSVs → BD Operacional
2. ✅ ETL: BD Operacional → BD Data Processor
3. 🔄 Clustering (próximamente)

### Solo Procesamiento de CSVs

```bash
python main.py --mode=csv
```

### Solo ETL

```bash
python main.py --mode=etl
```

### Modo Verbose

```bash
python main.py --mode=full --verbose
```

## Estructura de Archivos

```
data-processor-service/
├── main.py                        # Orquestador principal
├── csv_processor.py               # Procesador de CSVs → BD Operacional
├── etl_to_processor.py           # ETL: BD Operacional → BD Data Processor
├── baxperience_operational_db.sql # Esquema BD Operacional
├── requirements.txt               # Dependencias Python
├── env.example                   # Configuración de ejemplo
└── README_PROCESSOR.md           # Esta documentación
```

## Procesamiento de CSVs

### CSVs Soportados

| CSV | Categoría | Registros Aprox. | Campos Clave |
|-----|-----------|------------------|--------------|
| `museos-filtrado.csv` | Museos | ~130 | nombre, direccion, latitud, longitud |
| `oferta-gastronomica.csv` | Gastronomía | ~2800 | nombre, categoria, cocina, barrio |
| `monumentos-caba.csv` | Monumentos | ~140 | denominacion, material, autor |
| `lugares-historicos-filtrado.csv` | Lugares Históricos | ~400 | nombre, jurisdiccion |
| `salas-cine-filtrado.csv` | Entretenimiento | ~40 | nombre, pantallas, butacas |

### Funciones de Procesamiento

Cada CSV tiene su propia función especializada:

- `process_museos_csv()`: Procesa museos con lógica de subcategorización automática
- `process_gastronomia_csv()`: Mapea categorías gastronómicas (restaurante, café, bar, etc.)
- `process_monumentos_csv()`: Extrae información de material y autor
- `process_lugares_historicos_csv()`: Procesa sitios patrimoniales
- `process_cines_csv()`: Procesa salas de cine con capacidad

### Mapeo de Categorías

```python
# Ejemplo de mapeo automático
if 'arte' in nombre.lower():
    subcategoria = 'Museos de Arte'
elif 'historia' in nombre.lower():
    subcategoria = 'Museos de Historia'
```

## ETL a Data Processor

### Transformaciones Aplicadas

1. **Normalización de Coordenadas**: Validación y limpieza de lat/lng
2. **Score de Popularidad**: Calculado como `valoración * log(reviews + 1)`
3. **Features Binarios**: `tiene_web`, `tiene_telefono`, `es_gratuito`
4. **Métricas por Barrio**: Agregaciones para clustering geográfico
5. **Features Temporales**: Para eventos (mes, día de semana, duración)

### Esquema Data Processor

```sql
lugares_clustering (
    poi_id, nombre, categoria,
    latitud, longitud, barrio,
    valoracion_promedio, popularidad_score,
    tipo_cocina, tipo_ambiente,
    tiene_web, tiene_telefono, es_gratuito
)

metricas_barrio (
    barrio, total_pois, total_museos,
    valoracion_promedio_barrio,
    centroide_lat, centroide_lng
)

eventos_clustering (
    evento_id, categoria_evento,
    fecha_inicio, mes_inicio, dia_semana_inicio,
    entrada_libre, capacidad_maxima
)
```

## Logs y Monitoreo

### Archivos de Log

- `csv_processor.log`: Logs del procesamiento de CSVs
- `etl_processor.log`: Logs del ETL
- `data_processor_main.log`: Logs del orquestador principal

### Métricas de Procesamiento

El sistema reporta:
- ✅ Registros procesados exitosamente
- ❌ Errores y registros omitidos
- ⏱️ Tiempo de ejecución
- 📊 Estadísticas por categoría

## Troubleshooting

### Error de Conexión a BD

```
❌ Error conectando a bases de datos: FATAL: database "baxperience_operational" does not exist
```

**Solución**: Crear la base de datos:
```sql
CREATE DATABASE baxperience_operational;
```

### Error de Coordenadas

```
⚠️ Museo sin coordenadas: Nombre del Museo
```

**Causa**: El CSV tiene valores nulos en latitud/longitud
**Resultado**: El registro se omite (se requieren coordenadas para clustering)

### Error de Categoría No Encontrada

```
❌ Error: Categoría 'nueva_categoria' no existe
```

**Solución**: Verificar que las categorías estén insertadas en la BD:
```sql
SELECT * FROM categorias;
```

## Próximos Pasos

### Clustering (En Desarrollo)

1. **K-Means Geográfico**: Agrupar POIs por proximidad
2. **Clustering Temático**: Agrupar por categoría y características
3. **Clustering Temporal**: Para eventos por fechas y estacionalidad
4. **Clustering Híbrido**: Combinar ubicación, tema y tiempo

### Integración con Scraper

El sistema está preparado para recibir eventos del scraper service:
- Tabla `eventos` lista para nuevos registros
- ETL automático de eventos activos
- Limpieza automática de eventos vencidos

### API de Recomendaciones

Próximamente se agregará una API que consuma los clusters para generar recomendaciones personalizadas basadas en:
- Ubicación del usuario
- Preferencias de categorías
- Fechas de viaje
- Patrones de clustering

## Contribuir

Para agregar nuevos CSVs:

1. Crear función `process_nuevo_csv()` en `csv_processor.py`
2. Agregar mapeo de categorías correspondiente
3. Actualizar `process_all_csvs()` para incluir la nueva función
4. Probar con datos de ejemplo

Para modificar el ETL:

1. Actualizar transformaciones en `etl_to_processor.py`
2. Modificar esquema de `lugares_clustering` si es necesario
3. Regenerar datos con `python main.py --mode=etl`
