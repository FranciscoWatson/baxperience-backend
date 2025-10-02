# 🚲 Guía Rápida - Servicio EcoBici

## ✨ Actualizar Datos (SIMPLE)

### Windows
```bash
actualizar.bat
```

### Linux/Mac
```bash
./actualizar.sh
```

### O directamente
```bash
python main.py
```

---

## 🔄 ¿Qué hace `main.py` cada vez que lo ejecutas?

```
┌─────────────────────────────────────┐
│  1. Consulta API del GCBA           │
│     • stationInformation            │
│     • stationStatus                 │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  2. Procesa y Formatea Datos        │
│     • 393 estaciones                │
│     • 393 estados actuales          │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  3. ACTUALIZA Estaciones (UPSERT)   │
│     ✅ NO crea duplicados           │
│     ✅ Actualiza info existente     │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  4. INSERTA Estados (Histórico)     │
│     ✅ Agrega nuevo snapshot        │
│     ✅ Mantiene histórico           │
└──────────────┬──────────────────────┘
               │
               ▼
┌─────────────────────────────────────┐
│  ✅ LISTO - Datos Actualizados      │
└─────────────────────────────────────┘
```

---

## 📊 Verificar Datos

```bash
python check_data.py
```

**Salida:**
```
Total de estaciones: 393
Total de registros de estado: 786 (crece con cada actualización)
Estaciones con bicicletas: 327
Total bicicletas disponibles: 2232
```

---

## ⚡ Datos Importantes

### ✅ Estaciones (tabla `stations`)
- **NO se duplican** - Se usa UPSERT
- Se actualizan si cambia algo (dirección, capacidad, etc.)
- Siempre 393 registros (una por estación)

### 📈 Estados (tabla `station_status`)
- **SÍ se acumulan** - Es histórico
- Cada ejecución agrega 393 registros nuevos
- Útil para análisis de disponibilidad en el tiempo

**Ejemplo:**
```
1ra ejecución: 393 estados
2da ejecución: 786 estados (393 + 393)
3ra ejecución: 1179 estados (786 + 393)
```

---

## 🗑️ Limpiar Histórico Antiguo

Para mantener solo los últimos 7 días:

```bash
python -c "from gcba_api.database import EcobiciDatabase; db = EcobiciDatabase(); db.connect(); print(f'Eliminados: {db.cleanup_old_records(7)}'); db.disconnect()"
```

---

## ⏰ Programar Actualizaciones Automáticas

### Cada 10 minutos (Recomendado)

**Linux/Mac:**
```bash
crontab -e
# Agregar:
*/10 * * * * cd /ruta/a/gcba-api-service && ./actualizar.sh >> logs/updates.log 2>&1
```

**Windows (Task Scheduler):**
1. Abre "Programador de tareas"
2. Nueva tarea básica
3. Repetir cada: 10 minutos
4. Ejecutar: `C:\ruta\a\actualizar.bat`

---

## 📖 Consultas SQL Útiles

### Ver últimas estaciones con bicicletas
```sql
SELECT name, num_bikes_mechanical, num_docks_available
FROM latest_station_status
WHERE num_bikes_mechanical > 0
ORDER BY num_bikes_mechanical DESC;
```

### Histórico de una estación específica
```sql
SELECT 
    station_id,
    num_bikes_mechanical,
    recorded_at
FROM station_status
WHERE station_id = '005'  -- Plaza Italia
ORDER BY recorded_at DESC
LIMIT 10;
```

### Promedio de disponibilidad por hora
```sql
SELECT 
    EXTRACT(HOUR FROM recorded_at) as hora,
    AVG(num_bikes_mechanical) as promedio_bicis
FROM station_status
WHERE station_id = '005'
GROUP BY hora
ORDER BY hora;
```

---

## 🎯 Resumen

| Comando | Qué hace |
|---------|----------|
| `python main.py` | Actualiza todos los datos |
| `./actualizar.sh` | Lo mismo pero más fácil |
| `python check_data.py` | Verifica el estado actual |
| `python create_database.py` | Solo la primera vez (setup) |

---

## ❓ FAQ

**P: ¿Puedo ejecutar `main.py` varias veces seguidas?**  
R: Sí, sin problema. No creará duplicados en estaciones, solo agregará snapshots al histórico.

**P: ¿Cada cuánto debería actualizar?**  
R: Recomendado: cada 10-15 minutos. La API del GCBA actualiza frecuentemente.

**P: ¿Qué pasa si falla una actualización?**  
R: Los datos anteriores quedan intactos. Puedes volver a ejecutar sin problema.

**P: ¿Cómo veo el histórico de una estación?**  
R: Consulta la tabla `station_status` filtrando por `station_id`.

**P: ¿Cómo integro esto con mi app?**  
R: Lee de la vista `latest_station_status` para datos en tiempo real.

---

**🚀 ¡Listo para usar!**

