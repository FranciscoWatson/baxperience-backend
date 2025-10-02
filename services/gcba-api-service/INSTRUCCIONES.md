# Instrucciones para el Servicio GCBA API - EcoBici

## ✅ Estado Actual

El servicio ya está **completamente configurado y funcionando**. La base de datos `eco_bicis` contiene:

- **393 estaciones** con información completa (ubicación, capacidad, barrio)
- **393 registros de estado** con disponibilidad en tiempo real
- **329 estaciones activas** con bicicletas disponibles
- **2,228 bicicletas mecánicas** disponibles en toda la ciudad

### Top 5 Barrios con más estaciones:
1. **PALERMO**: 47 estaciones
2. **BELGRANO**: 22 estaciones  
3. **CABALLITO**: 20 estaciones
4. **SAN NICOLAS**: 17 estaciones
5. **RECOLETA**: 17 estaciones

---

## 🚀 Uso del Servicio

### Actualizar datos manualmente (una vez)

```bash
cd baxperience-backend/services/gcba-api-service

# Configurar variables de entorno
export GCBA_CLIENT_ID=0eda5677aea347e1be6f902a7726ffc9
export GCBA_CLIENT_SECRET=41A740d9db16481D9C9B26E7Fd3Ac6e4
export ECOBICI_DB_HOST=localhost
export ECOBICI_DB_PORT=5432
export ECOBICI_DB_NAME=eco_bicis
export ECOBICI_DB_USER=postgres
export ECOBICI_DB_PASSWORD=admin

# Ejecutar el servicio
python main.py
```

### Verificar datos en la base de datos

```bash
python check_data.py
```

### Actualizar periódicamente (recomendado)

Para mantener los datos actualizados, configura un **cron job** o **tarea programada**:

#### Linux/Mac (crontab):

```bash
# Editar crontab
crontab -e

# Agregar línea para ejecutar cada 10 minutos:
*/10 * * * * cd /path/to/gcba-api-service && /usr/bin/python main.py >> logs/ecobici.log 2>&1
```

#### Windows (Task Scheduler):

1. Abre "Programador de tareas" (Task Scheduler)
2. Crea una nueva tarea básica
3. Configura para que se ejecute cada 10 minutos
4. Acción: Ejecutar `python.exe`
5. Argumentos: `C:\path\to\gcba-api-service\main.py`

---

## 📊 Consultas SQL Útiles

### Ver últimas estaciones con bicicletas disponibles

```sql
SELECT name, num_bikes_mechanical, num_docks_available, status
FROM latest_station_status
WHERE num_bikes_mechanical > 0
ORDER BY num_bikes_mechanical DESC
LIMIT 20;
```

### Estaciones por barrio

```sql
SELECT barrio, total_stations, total_capacity
FROM stations_by_group
ORDER BY total_stations DESC;
```

### Buscar estaciones cerca de una ubicación

```sql
SELECT 
    station_id, 
    name, 
    address,
    ST_Distance(
        ST_MakePoint(lon, lat)::geography,
        ST_MakePoint(-58.3816, -34.6037)::geography  -- Plaza de Mayo
    ) / 1000 as distance_km
FROM stations
ORDER BY distance_km
LIMIT 10;
```

### Estaciones con más actividad (promedio histórico)

```sql
SELECT name, address, avg_bikes_mechanical, max_bikes_mechanical
FROM top_stations_with_bikes
LIMIT 20;
```

---

## 🔧 Mantenimiento

### Limpiar registros antiguos (más de 7 días)

```sql
SELECT cleanup_old_status_records();
```

O desde Python:

```python
from gcba_api.database import EcobiciDatabase

db = EcobiciDatabase()
db.connect()
deleted = db.cleanup_old_records(days=7)
print(f"Eliminados {deleted} registros antiguos")
db.disconnect()
```

---

## 🗂️ Estructura de la Base de Datos

### Tabla: `stations`
Información estática de estaciones (actualizada periódicamente)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| station_id | VARCHAR(10) | ID único de la estación |
| name | VARCHAR(255) | Nombre de la estación |
| lat | DECIMAL(10,8) | Latitud |
| lon | DECIMAL(11,8) | Longitud |
| address | VARCHAR(500) | Dirección completa |
| post_code | VARCHAR(20) | Código postal |
| capacity | INTEGER | Capacidad total (bicis + docks) |
| groups | TEXT[] | Barrios/zonas (array PostgreSQL) |

### Tabla: `station_status`
Estado en tiempo real de las estaciones (histórico)

| Campo | Tipo | Descripción |
|-------|------|-------------|
| station_id | VARCHAR(10) | ID de la estación (FK) |
| num_bikes_mechanical | INTEGER | **Bicis mecánicas disponibles** |
| num_docks_available | INTEGER | Docks libres disponibles |
| last_reported | BIGINT | Timestamp Unix del último reporte |
| status | VARCHAR(50) | Estado (IN_SERVICE, etc.) |
| recorded_at | TIMESTAMP | Cuándo se guardó en nuestra BD |

**Nota**: No se almacenan ebikes, solo bicicletas mecánicas.

---

## 🔗 Integración con BAXperience

Este servicio puede integrarse con tu plataforma de turismo para:

✅ **Mostrar estaciones cercanas a POIs**
```sql
-- Encontrar estaciones cerca de un museo
SELECT s.name, s.address, ls.num_bikes_mechanical
FROM stations s
JOIN latest_station_status ls ON s.station_id = ls.station_id
WHERE ST_DWithin(
    ST_MakePoint(s.lon, s.lat)::geography,
    ST_MakePoint(-58.3725, -34.6083)::geography,  -- MALBA
    500  -- 500 metros
)
AND ls.num_bikes_mechanical > 0
ORDER BY ls.num_bikes_mechanical DESC;
```

✅ **Recomendar transporte sustentable** en itinerarios

✅ **Filtrar POIs accesibles por EcoBici**

✅ **Análisis de movilidad** por barrio y horario

---

## 📝 Próximos Pasos (Opcional)

1. **Integración con Kafka**: Enviar eventos cuando estaciones estén vacías/llenas
2. **API REST**: Crear endpoints para consultar desde otros servicios
3. **Machine Learning**: Predecir disponibilidad futura
4. **Dashboard**: Visualización en tiempo real con Grafana
5. **Alertas**: Notificar cuando estaciones críticas tengan baja disponibilidad

---

## 🐛 Troubleshooting

### Error: "no existe la relación stations"
**Solución**: Ejecutar `python create_database.py`

### Error de Unicode en Windows
**Solución**: Es un problema cosmético con emojis en la consola de Windows. Los datos se guardan correctamente. Usar `python main.py > output.log 2>&1` para evitar ver los errores.

### No se actualizan los datos
**Solución**: Verificar que las variables de entorno estén configuradas correctamente, especialmente `GCBA_CLIENT_ID` y `GCBA_CLIENT_SECRET`.

---

## 📚 Recursos

- [API Transport BA](https://apitransporte.buenosaires.gob.ar/)
- [GBFS Specification](https://github.com/NABSA/gbfs)
- [EcoBici Buenos Aires](https://baecobici.com.ar/)
- [PostgreSQL PostGIS](https://postgis.net/) (para consultas geoespaciales avanzadas)

---

**Última actualización**: Octubre 2025
**Estado**: ✅ Operativo

