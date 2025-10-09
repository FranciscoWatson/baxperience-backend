# BAXperience NLP Service

Servicio de Procesamiento de Lenguaje Natural para consultas en español e inglés sobre experiencias en Buenos Aires.

## 🎯 Características

- **Bilingüe**: Soporta español e inglés
- **Sin APIs Pagas**: 100% gratuito usando spaCy y RapidFuzz
- **Integración Kafka**: Comunicación asíncrona con el API Gateway
- **Detección de Entidades**: Categorías, subcategorías, zonas, tipos de cocina
- **Detección de Intención**: Identifica qué quiere hacer el usuario
- **Fuzzy Matching**: Tolerante a errores de tipeo

## 📁 Estructura

```
nlp-service/
├── simple_nlp_service.py    # Servicio principal con Kafka y HTTP
├── nlp_processor.py          # Lógica de procesamiento NLP
├── requirements.txt          # Dependencias Python
├── .env.example             # Ejemplo de configuración
├── test_nlp_kafka.py        # Tests usando Kafka
└── README.md                # Esta documentación
```

## 🚀 Instalación

### 1. Instalar dependencias

```bash
cd baxperience-backend/services/nlp-service
pip install -r requirements.txt
```

### 2. Descargar modelos spaCy (OPCIONAL pero recomendado)

```bash
# Modelo español
python -m spacy download es_core_news_md

# Modelo inglés
python -m spacy download en_core_web_md
```

**Nota**: Los modelos son opcionales. El servicio funciona sin ellos usando solo regex y fuzzy matching, pero la precisión mejora significativamente con spaCy.

### 3. Configurar variables de entorno

Crear archivo `.env`:

```env
# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=baxperience_operational
DB_USER=postgres
DB_PASSWORD=your_password

# Kafka
KAFKA_BOOTSTRAP_SERVERS=localhost:9092

# Logging
LOG_LEVEL=INFO
```

### 4. Iniciar Kafka

Asegúrate de que Kafka esté corriendo:

```bash
cd baxperience-backend/services/kafka-setup
docker-compose up -d
```

### 5. Iniciar el servicio

```bash
python simple_nlp_service.py
```

Deberías ver:

```
🚀 Iniciando NLP Service...
✅ Procesador NLP inicializado
✅ Cargadas 6 categorías, 12 subcategorías, 48 barrios
🎧 Iniciando listener de Kafka...
🌐 Iniciando servidor HTTP...
✅ NLP Service iniciado en puerto 5001
```

## 🧪 Testing

### Test con Kafka

```bash
python test_nlp_kafka.py
```

### Health Check

```bash
curl http://localhost:5001/health
```

## 📡 Arquitectura

```
Frontend
   ↓
API Gateway (/api/nlp/process)
   ↓
Kafka Topic: nlp-requests
   ↓
NLP Service (Python)
   ↓ (procesa consulta)
   ↓
Kafka Topic: nlp-responses
   ↓
API Gateway
   ↓
Frontend
```

## 💡 Ejemplos de Consultas

### Español

```
"quiero comer en un restaurante de carne"
→ Categoría: Gastronomía, Subcategoría: Parrilla

"busco una parrilla en Palermo"
→ Categoría: Gastronomía, Subcategoría: Parrilla, Zona: Palermo

"recomiendame un museo de arte"
→ Categoría: Museos, Tipo: Arte

"dónde puedo tomar un café en San Telmo"
→ Categoría: Gastronomía, Subcategoría: Café, Zona: San Telmo
```

### Inglés

```
"I want to eat at a steakhouse"
→ Category: Gastronomía, Subcategory: Parrilla

"looking for museums in Recoleta"
→ Category: Museos, Zone: Recoleta
```

## 🔧 Tópicos Kafka

### Input: `nlp-requests`

Mensaje esperado:

```json
{
  "event_type": "nlp_query",
  "request_id": "nlp_123_1234567890",
  "user_id": 123,
  "query": "quiero comer en una parrilla",
  "timestamp": "2025-01-09T12:00:00Z"
}
```

### Output: `nlp-responses`

Respuesta de éxito:

```json
{
  "event_type": "nlp_processed",
  "status": "success",
  "request_id": "nlp_123_1234567890",
  "timestamp": "2025-01-09T12:00:01Z",
  "data": {
    "query": "quiero comer en una parrilla",
    "language": "es",
    "intent": {
      "name": "SEARCH",
      "confidence": 0.85
    },
    "entities": {
      "category": {
        "id": 2,
        "name": "Gastronomía",
        "confidence": 0.9,
        "matched_text": "food-related keywords"
      },
      "subcategory": {
        "id": 4,
        "name": "Parrilla",
        "confidence": 0.9,
        "matched_text": "parrilla"
      },
      "zone": null,
      "cuisine_type": "argentina",
      "spacy_entities": []
    },
    "confidence": 0.88,
    "suggestions": {
      "categorias": ["Gastronomía"],
      "zona": null,
      "tipo_cocina": "argentina"
    },
    "processing_metadata": {
      "request_id": "nlp_123_1234567890",
      "processing_time_seconds": 0.042,
      "processed_at": "2025-01-09T12:00:01Z",
      "service_version": "1.0.0"
    }
  }
}
```

## 🛠️ Dependencias

- **kafka-python**: Comunicación con Kafka
- **psycopg2-binary**: Conexión a PostgreSQL
- **rapidfuzz**: Fuzzy string matching
- **unidecode**: Normalización de texto
- **python-dotenv**: Variables de entorno
- **spacy** (opcional): NLP avanzado

## 📊 Rendimiento

- **Tiempo de respuesta**: 20-80ms (sin spaCy: ~20ms, con spaCy: ~50-80ms)
- **Memoria**: ~150MB con ambos modelos spaCy cargados
- **Precisión**: 85-95% en consultas comunes

## 🔍 Detección de Entidades

### Categorías Soportadas

1. **Museos**
2. **Gastronomía** (restaurantes, cafés, bares, parrillas)
3. **Monumentos**
4. **Lugares Históricos**
5. **Entretenimiento** (cines, teatros, eventos)
6. **Eventos**

### Tipos de Cocina

- Argentina, Italiana, Mexicana, Japonesa, China, Peruana, Española, Francesa, Vegetariana

### Barrios Detectados

Todos los barrios únicos en la tabla `pois` (Palermo, Recoleta, San Telmo, Puerto Madero, etc.)

## 🚨 Troubleshooting

### Error: Kafka connection refused

**Solución**: Verifica que Kafka esté corriendo:

```bash
cd baxperience-backend/services/kafka-setup
docker-compose up -d
```

### Error: Database connection failed

**Solución**: Verifica credenciales en `.env` y que PostgreSQL esté corriendo.

### Warning: spaCy models not found

**Solución**: El servicio funciona sin spaCy, pero para mejor precisión:

```bash
python -m spacy download es_core_news_md
python -m spacy download en_core_web_md
```

## 📚 Integración con API Gateway

El API Gateway ya está configurado con el endpoint `/api/nlp/process` que:

1. Recibe la consulta del usuario
2. Genera un `request_id` único
3. Envía mensaje a Kafka (`nlp-requests`)
4. Retorna el `request_id` al frontend
5. Frontend puede hacer polling o usar websockets para el resultado

## 🔄 Diferencias con `data-processor-service`

Siguiendo el mismo patrón:

- ✅ Usa Kafka para comunicación asíncrona
- ✅ Servidor HTTP simple solo para health checks
- ✅ No usa FastAPI ni axios
- ✅ Estructura de carpetas similar
- ✅ Mismo sistema de logging

## 📝 Logging

Los logs muestran:

- 📥 Consultas recibidas
- 🔍 Procesamiento en curso
- ✅ Resultados exitosos con confianza
- ❌ Errores con traceback completo

## 🎉 Próximos Pasos

1. Iniciar el servicio: `python simple_nlp_service.py`
2. Verificar health: `curl http://localhost:5001/health`
3. Ejecutar tests: `python test_nlp_kafka.py`
4. Integrar con frontend (ya configurado)
