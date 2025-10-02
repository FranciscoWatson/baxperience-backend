# GCBA API Service - EcoBici

Servicio que se conecta con la API pública del Gobierno de la Ciudad de Buenos Aires (GCBA) para obtener información en tiempo real sobre las estaciones de EcoBici (sistema de bicicletas públicas de Buenos Aires).

## Características

- 🚲 Consulta información de todas las estaciones de EcoBici
- 📊 Almacena datos históricos de disponibilidad de bicicletas
- 🔄 Actualización periódica de estados en tiempo real
- 💾 Base de datos PostgreSQL optimizada para consultas rápidas
- 📈 Vistas SQL para análisis estadísticos

## Estructura del Proyecto

```
gcba-api-service/
├── gcba_api/
│   ├── __init__.py          # Inicialización del paquete
│   ├── ecobici.py           # Cliente de la API de EcoBici
│   └── database.py          # Manejador de base de datos
├── responses/               # Ejemplos de respuestas de la API
├── eco_bicis_db.sql        # Schema de base de datos
├── main.py                 # Servicio principal
├── requirements.txt        # Dependencias Python
└── README.md              # Esta documentación

## Instalación

### 1. Crear la Base de Datos

Primero, crea la base de datos PostgreSQL ejecutando el script SQL:

```bash
psql -U postgres -f eco_bicis_db.sql
```

Esto creará:
- Base de datos `eco_bicis`
- Tabla `stations` (información estática de estaciones)
- Tabla `station_status` (estados históricos en tiempo real)
- Vistas para consultas optimizadas
- Índices para búsquedas rápidas

### 2. Instalar Dependencias

```bash
cd baxperience-backend/services/gcba-api-service
pip install -r requirements.txt
```

### 3. Configurar Variables de Entorno

Configura las siguientes variables en tu `.env` (o en el entorno):

```env
# API del GCBA
GCBA_CLIENT_ID=tu_client_id
GCBA_CLIENT_SECRET=tu_client_secret

# Base de datos PostgreSQL
ECOBICI_DB_HOST=localhost
ECOBICI_DB_PORT=5432
ECOBICI_DB_NAME=eco_bicis
ECOBICI_DB_USER=postgres
ECOBICI_DB_PASSWORD=tu_password
```

## Uso

### Ejecutar el Servicio (Una vez)

Para actualizar los datos una vez:

```bash
python main.py
```

Esto:
1. ✅ Consulta la API del GCBA (stationInformation y stationStatus)
2. ✅ Procesa y formatea los datos
3. ✅ Actualiza/inserta estaciones en la BD
4. ✅ Guarda registros históricos de estado
5. ✅ Muestra estadísticas actualizadas

### Ejecutar Periódicamente (Cron)

Para actualizar automáticamente cada X minutos, configura un cron job:

```bash
# Actualizar cada 10 minutos
*/10 * * * * cd /path/to/gcba-api-service && python main.py >> logs/ecobici.log 2>&1

# Actualizar cada hora
0 * * * * cd /path/to/gcba-api-service && python main.py >> logs/ecobici.log 2>&1
```

### Ejecutar con Supervisor (Producción)

Para entornos de producción, usa Supervisor o systemd:

```ini
[program:gcba-ecobici]
command=/usr/bin/python /path/to/main.py
directory=/path/to/gcba-api-service
autostart=true
autorestart=true
stderr_logfile=/var/log/gcba-ecobici.err.log
stdout_logfile=/var/log/gcba-ecobici.out.log
```

## Modelo de Datos

### Tabla: stations

Información estática de cada estación:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| station_id | VARCHAR(10) | ID único de la estación |
| name | VARCHAR(255) | Nombre de la estación |
| lat | DECIMAL(10,8) | Latitud |
| lon | DECIMAL(11,8) | Longitud |
| address | VARCHAR(500) | Dirección |
| post_code | VARCHAR(20) | Código postal |
| capacity | INTEGER | Capacidad total (bicis + docks) |
| groups | TEXT[] | Barrios/zonas (array) |

### Tabla: station_status

Estados históricos en tiempo real:

| Campo | Tipo | Descripción |
|-------|------|-------------|
| station_id | VARCHAR(10) | ID de la estación (FK) |
| num_bikes_mechanical | INTEGER | Bicis mecánicas disponibles |
| num_docks_available | INTEGER | Docks disponibles |
| last_reported | BIGINT | Timestamp Unix del reporte |
| status | VARCHAR(50) | Estado (IN_SERVICE, etc.) |
| recorded_at | TIMESTAMP | Cuando se guardó en nuestra BD |

### Vistas SQL Útiles

**latest_station_status**: Último estado de cada estación

```sql
SELECT * FROM latest_station_status 
WHERE num_bikes_mechanical > 5 
ORDER BY num_bikes_mechanical DESC;
```

**top_stations_with_bikes**: Estaciones con más disponibilidad promedio

```sql
SELECT * FROM top_stations_with_bikes LIMIT 20;
```

**stations_by_group**: Estaciones agrupadas por barrio

```sql
SELECT * FROM stations_by_group ORDER BY total_stations DESC;
```

## API del GCBA

Este servicio consume dos endpoints de la API GBFS (General Bikeshare Feed Specification):

### 1. Station Information

```
GET https://apitransporte.buenosaires.gob.ar/ecobici/gbfs/stationInformation
```

Retorna información estática de todas las estaciones.

### 2. Station Status

```
GET https://apitransporte.buenosaires.gob.ar/ecobici/gbfs/stationStatus
```

Retorna el estado en tiempo real de todas las estaciones.

**Nota**: Ambos endpoints requieren `client_id` y `client_secret` como parámetros GET.

## Testing

### Probar la API

```bash
python -c "from gcba_api.ecobici import test_api; test_api()"
```

### Probar la Base de Datos

```bash
python -c "from gcba_api.database import test_database_connection; test_database_connection()"
```

## Mantenimiento

### Limpiar Registros Antiguos

La BD guarda históricos. Para limpiar registros de más de 7 días:

```python
from gcba_api.database import EcobiciDatabase
db = EcobiciDatabase()
db.connect()
db.cleanup_old_records(days=7)
db.disconnect()
```

O ejecuta directamente en PostgreSQL:

```sql
SELECT cleanup_old_status_records();
```

## Logs

Los logs se guardan en:
- Consola (stdout)
- Archivo: `gcba_service_YYYYMMDD.log`

Formato de log:
```
2025-02-10 14:30:00 - gcba_api.ecobici - INFO - ✓ Respuesta recibida de stationInformation
```

## Integración con BAXperience

Este servicio provee datos de transporte público que pueden ser integrados en:

- **Recomendaciones de itinerarios**: Sugerir estaciones cercanas a POIs
- **Información en tiempo real**: Mostrar disponibilidad de bicicletas
- **Análisis de movilidad**: Estudiar patrones de uso por barrio
- **Filtros de búsqueda**: "POIs cerca de estaciones con bicicletas"

## Próximas Mejoras

- [ ] Integración con Kafka para eventos en tiempo real
- [ ] API REST para consultar datos desde otros servicios
- [ ] Alertas cuando estaciones estén vacías/llenas
- [ ] Machine Learning para predecir disponibilidad
- [ ] Integración con otros sistemas de transporte (subte, colectivos)

## Recursos

- [API Transport BA](https://apitransporte.buenosaires.gob.ar/)
- [GBFS Specification](https://github.com/NABSA/gbfs)
- [EcoBici Buenos Aires](https://baecobici.com.ar/)
