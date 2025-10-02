# 🚲 API de EcoBici - Documentación

Endpoints para consultar estaciones de bicicletas públicas de Buenos Aires en tiempo real.

---

## 📍 Endpoints Disponibles

### 1. Obtener Estaciones Cercanas

**Endpoint principal** - Obtiene las 3 estaciones más cercanas a una ubicación.

```http
GET /api/bikes/nearby?lat=-34.6037&lon=-58.3816&limit=3
```

#### Query Parameters

| Parámetro | Tipo | Requerido | Default | Descripción |
|-----------|------|-----------|---------|-------------|
| `lat` | number | ✅ Sí | - | Latitud (-35 a -34) |
| `lon` | number | ✅ Sí | - | Longitud (-59 a -58) |
| `limit` | number | ❌ No | 3 | Cantidad de estaciones (max: 10) |

#### Validaciones

- ✅ Solo estaciones en servicio (`status = 'IN_SERVICE'`)
- ✅ Solo estaciones que permiten préstamo (`is_renting = 1`)
- ✅ Solo estaciones con bicicletas disponibles (`num_bikes_mechanical > 0`)
- ✅ Ordenadas por distancia (más cercana primero)

#### Respuesta Exitosa (200)

```json
{
  "ubicacionConsulta": {
    "latitud": -34.6037,
    "longitud": -58.3816
  },
  "cantidadEncontrada": 3,
  "estaciones": [
    {
      "stationId": "004",
      "nombre": "004 - Plaza Roma",
      "ubicacion": {
        "latitud": -34.60300823,
        "longitud": -58.36885646,
        "direccion": "Av. Corrientes 100",
        "barrios": ["SAN NICOLAS"]
      },
      "disponibilidad": {
        "bicisDisponibles": 8,
        "docksDisponibles": 12,
        "capacidadTotal": 20
      },
      "estado": {
        "enServicio": true,
        "permitePrestamo": true,
        "permiteDevolucion": true
      },
      "distanciaKm": 0.52
    },
    {
      "stationId": "003",
      "nombre": "003 - ADUANA",
      "ubicacion": {
        "latitud": -34.61220714,
        "longitud": -58.36912906,
        "direccion": "Av. Paseo Colón 380",
        "barrios": ["MONSERRAT"]
      },
      "disponibilidad": {
        "bicisDisponibles": 5,
        "docksDisponibles": 23,
        "capacidadTotal": 28
      },
      "estado": {
        "enServicio": true,
        "permitePrestamo": true,
        "permiteDevolucion": true
      },
      "distanciaKm": 0.93
    }
  ]
}
```

#### Respuesta Sin Resultados (404)

```json
{
  "message": "No se encontraron estaciones disponibles cerca de tu ubicación",
  "estaciones": []
}
```

#### Errores

**400 - Bad Request**
```json
{
  "error": "Se requieren los parámetros lat y lon"
}
```

```json
{
  "error": "Los parámetros lat y lon deben ser números válidos"
}
```

```json
{
  "error": "Las coordenadas están fuera del rango de Buenos Aires"
}
```

**500 - Internal Server Error**
```json
{
  "error": "Error interno al buscar estaciones cercanas"
}
```

---

### 2. Listar Todas las Estaciones

Obtiene todas las estaciones con paginación.

```http
GET /api/bikes/stations?pagina=1&limite=20&conBicis=true
```

#### Query Parameters

| Parámetro | Tipo | Default | Descripción |
|-----------|------|---------|-------------|
| `pagina` | number | 1 | Número de página |
| `limite` | number | 20 | Estaciones por página |
| `conBicis` | boolean | true | Solo con bicis disponibles |

#### Respuesta Exitosa (200)

```json
{
  "estaciones": [
    {
      "stationId": "002",
      "nombre": "002 - Retiro I",
      "ubicacion": {
        "latitud": -34.59242413,
        "longitud": -58.37470989,
        "direccion": "AV. Dr. José María Ramos Mejía 1300",
        "barrios": ["RETIRO"]
      },
      "disponibilidad": {
        "bicisDisponibles": 15,
        "docksDisponibles": 25,
        "capacidadTotal": 40
      },
      "estado": {
        "enServicio": true,
        "permitePrestamo": true,
        "permiteDevolucion": true
      }
    }
  ],
  "paginacion": {
    "pagina": 1,
    "limite": 20,
    "total": 393,
    "totalPaginas": 20
  }
}
```

---

### 3. Estadísticas Generales

Obtiene estadísticas del sistema EcoBici.

```http
GET /api/bikes/stats
```

#### Respuesta Exitosa (200)

```json
{
  "estadisticas": {
    "totalEstaciones": 393,
    "estacionesConBicis": 327,
    "totalBicisDisponibles": 2254,
    "totalDocksDisponibles": 4306,
    "promedioBicisPorEstacion": 5.7
  },
  "topBarrios": [
    {
      "barrio": "PALERMO",
      "cantidadEstaciones": 47,
      "bicisDisponibles": 312
    },
    {
      "barrio": "BELGRANO",
      "cantidadEstaciones": 22,
      "bicisDisponibles": 145
    },
    {
      "barrio": "CABALLITO",
      "cantidadEstaciones": 20,
      "bicisDisponibles": 98
    }
  ]
}
```

---

## 🧪 Ejemplos de Uso

### cURL

```bash
# Estaciones cercanas a Plaza de Mayo
curl "http://localhost:3000/api/bikes/nearby?lat=-34.6037&lon=-58.3816&limit=5"

# Todas las estaciones (página 1)
curl "http://localhost:3000/api/bikes/stations?pagina=1&limite=20"

# Estadísticas
curl "http://localhost:3000/api/bikes/stats"
```

### JavaScript (Fetch)

```javascript
// Buscar estaciones cercanas
async function buscarEstacionesCercanas(lat, lon) {
  const response = await fetch(
    `http://localhost:3000/api/bikes/nearby?lat=${lat}&lon=${lon}&limit=3`
  );
  const data = await response.json();
  return data.estaciones;
}

// Usar con geolocalización del navegador
navigator.geolocation.getCurrentPosition(async (position) => {
  const { latitude, longitude } = position.coords;
  const estaciones = await buscarEstacionesCercanas(latitude, longitude);
  console.log('Estaciones cercanas:', estaciones);
});
```

### React Example

```jsx
import { useState, useEffect } from 'react';

function EstacionesCercanas() {
  const [estaciones, setEstaciones] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    navigator.geolocation.getCurrentPosition(async (position) => {
      const { latitude, longitude } = position.coords;
      
      const response = await fetch(
        `http://localhost:3000/api/bikes/nearby?lat=${latitude}&lon=${longitude}&limit=3`
      );
      const data = await response.json();
      
      setEstaciones(data.estaciones);
      setLoading(false);
    });
  }, []);

  if (loading) return <div>Buscando estaciones...</div>;

  return (
    <div>
      <h2>Estaciones Cercanas</h2>
      {estaciones.map(estacion => (
        <div key={estacion.stationId}>
          <h3>{estacion.nombre}</h3>
          <p>📍 {estacion.distanciaKm} km</p>
          <p>🚲 {estacion.disponibilidad.bicisDisponibles} bicis disponibles</p>
          <p>📫 {estacion.ubicacion.direccion}</p>
        </div>
      ))}
    </div>
  );
}
```

---

## 🔑 Variables de Entorno

Agregar al `.env` del API Gateway:

```env
# Base de datos EcoBici
ECOBICI_DB_HOST=localhost
ECOBICI_DB_PORT=5432
ECOBICI_DB_NAME=eco_bicis
ECOBICI_DB_USER=postgres
ECOBICI_DB_PASSWORD=admin
```

---

## 📊 Cálculo de Distancia

Se utiliza la **fórmula de Haversine** para calcular la distancia entre dos puntos en la superficie terrestre:

```
distancia = R × acos(
  cos(lat1) × cos(lat2) × cos(lon2 - lon1) + 
  sin(lat1) × sin(lat2)
)
```

Donde R = 6371 km (radio de la Tierra)

---

## 🗺️ Ubicaciones de Referencia en Buenos Aires

Para testing:

| Lugar | Latitud | Longitud |
|-------|---------|----------|
| Plaza de Mayo | -34.6037 | -58.3816 |
| Obelisco | -34.6037 | -58.3816 |
| Plaza Italia | -34.5805 | -58.4210 |
| Puerto Madero | -34.6118 | -58.3629 |
| Recoleta | -34.5889 | -58.3967 |
| Palermo | -34.5790 | -58.4272 |

---

## 🚀 Testing Rápido

```bash
# Test 1: Estaciones cerca de Plaza de Mayo
curl "http://localhost:3000/api/bikes/nearby?lat=-34.6037&lon=-58.3816"

# Test 2: Sin parámetros (debe fallar)
curl "http://localhost:3000/api/bikes/nearby"

# Test 3: Estadísticas
curl "http://localhost:3000/api/bikes/stats"
```

---

## 📝 Notas

- Las coordenadas se validan para estar dentro de Buenos Aires (-35 a -34 lat, -59 a -58 lon)
- Solo retorna estaciones en servicio con bicicletas disponibles
- Los datos provienen de la BD `eco_bicis` actualizada por el servicio GCBA
- El límite máximo de estaciones retornadas es 10
- La distancia se retorna en kilómetros con 2 decimales

---

## 🔄 Actualización de Datos

Los datos de las estaciones se actualizan ejecutando:

```bash
cd baxperience-backend/services/gcba-api-service
python main.py
```

Se recomienda ejecutar cada 10-15 minutos para mantener la disponibilidad actualizada.

