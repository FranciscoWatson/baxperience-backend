# BAXperience DataProcessor - Explicación Completa del Sistema

## Índice
1. [Visión General del Sistema](#visión-general-del-sistema)
2. [Flujo Inicial: Scraper → DataProcessor](#flujo-inicial-scraper--dataprocessor)
3. [Pipeline de Procesamiento de Datos](#pipeline-de-procesamiento-de-datos)
4. [Algoritmos de Machine Learning y Clustering](#algoritmos-de-machine-learning-y-clustering)
5. [Generación de Itinerarios: Flujo Detallado](#generación-de-itinerarios-flujo-detallado)
6. [Uso de Algoritmos y Optimización de Rutas](#uso-de-algoritmos-y-optimización-de-rutas)
7. [Sistema de Scoring y Personalización](#sistema-de-scoring-y-personalización)
8. [Arquitectura de Bases de Datos](#arquitectura-de-bases-de-datos)

---

## Visión General del Sistema

El BAXperience DataProcessor es el cerebro del sistema de recomendaciones turísticas. Actúa como un intermediario inteligente que:

- **Procesa** datos de múltiples fuentes (CSVs estáticos + scraper dinámico)
- **Entrena** modelos de machine learning para clustering geográfico y categórico
- **Genera** itinerarios personalizados usando algoritmos de optimización
- **Optimiza** rutas considerando ubicación, preferencias y tiempo disponible

### Componentes Principales
```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  Scraper Service │ -> │ DataProcessor   │ -> │ API Gateway     │
│  (eventos)      │    │ (clustering ML) │    │ (itinerarios)   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                              ↕
                    ┌─────────────────┐
                    │ CSVs Estáticos  │
                    │ (POIs CABA)     │
                    └─────────────────┘
```

---

## Flujo Inicial: Scraper → DataProcessor

### 1. Llegada de Eventos del Scraper

Cuando el **scraper-service** encuentra nuevos eventos en el sitio web del Gobierno de CABA, envía los datos al DataProcessor:

```python
# Estructura de evento desde scraper
evento_data = {
    'nombre': 'Festival de Jazz en Puerto Madero',
    'categoria_evento': 'Evento',
    'tematica': 'Música',
    'fecha_inicio': '2025-09-15',
    'fecha_fin': '2025-09-17', 
    'hora_inicio': '20:00',
    'direccion_evento': 'Dique 4, Puerto Madero',
    'barrio': 'Puerto Madero',
    'latitud': -34.6143,
    'longitud': -58.3641,
    'url_evento': 'https://turismo.buenosaires.gob.ar/...',
    'descripcion': 'Festival gratuito de jazz...'
}
```

### 2. Inserción en BD Operacional

El **ETLProcessor** recibe estos eventos y los procesa:

```python
def insertar_eventos_desde_scraper(self, eventos_data) -> int:
    """
    - Valida coordenadas (rango Buenos Aires: -35.0 a -34.0 lat, -59.0 a -58.0 lng)
    - Convierte fechas y horarios a formatos de BD
    - Genera hash único para evitar duplicados
    - Asigna barrios faltantes usando geocodificación
    """
```

**Proceso detallado:**
1. **Validación**: Coordenadas en rango de CABA, formatos de fecha válidos
2. **Deduplicación**: Hash basado en (nombre + fecha + ubicación)
3. **Geocodificación**: Si falta barrio, usa APIs para determinarlo
4. **Inserción**: Guarda en tabla `eventos` de BD operacional

### 3. Trigger Automático de ETL

Después de insertar eventos nuevos, se dispara automáticamente el ETL completo:

```python
def run_full_etl(self) -> Dict[str, int]:
    """
    PASO 1: Asignar barrios faltantes usando geocodificación interna
    PASO 2: Crear esquema optimizado en BD Data Processor  
    PASO 3: Transferir POIs (solo si no existen previamente)
    PASO 4: Transferir eventos (siempre se recargan)
    """
```

---

## Pipeline de Procesamiento de Datos

### Arquitectura de Datos
```
CSV Estáticos (POIs CABA) ──┐
                            ├──> BD Operacional ──> ETL ──> BD Data Processor ──> ML Models
Scraper (Eventos) ──────────┘                                      │
                                                                   ├──> Clustering Results
                                                                   └──> Recommendation Engine
```

### 1. Procesamiento de CSVs (Ejecución Inicial)

**csv_processor.py** maneja 5 tipos de POIs de CABA:

#### A. Museos (`museos_datosabiertos.csv`)
```python
def process_museos_csv(self):
    # Campos procesados:
    # - nombre_museo, direccion, barrio, latitud, longitud
    # - telefono, web, mail
    # - categoria = 'Museos'
    # - subcategoria basada en tipo de museo
    # - valoracion_promedio = 0 (sin datos previos)
```

#### B. Gastronomía (`oferta_gastronomica.csv`)
```python
def process_gastronomia_csv(self):
    # Campos procesados:
    # - nombre, direccion, telefono, web
    # - tipo_cocina (italiana, argentina, etc.)
    # - tipo_ambiente (casual, elegante, etc.)
    # - categoria = 'Gastronomía'
    # - precio promedio estimado
```

#### C. Monumentos y Lugares Históricos
```python
def process_monumentos_csv(self):
    # Campos procesados:
    # - nombre_oficial, direccion, barrio
    # - material, epoca, estilo_arquitectonico
    # - categoria = 'Monumentos' o 'Lugares Históricos'
    # - es_gratuito = True (por defecto)
```

#### D. Salas de Cine (`salas_cine.csv`)
```python
def process_cine_csv(self):
    # Campos procesados:
    # - nombre_sala, direccion, telefono
    # - capacidad, tecnologia (2D, 3D, IMAX)
    # - categoria = 'Entretenimiento'
    # - subcategoria = 'Cine'
```

### 2. ETL: BD Operacional → BD Data Processor

**etl_to_processor.py** optimiza los datos para machine learning:

#### A. Transformación de POIs
```python
def extract_transform_load_pois(self) -> int:
    """
    EXTRACT: POIs de BD operacional con joins a categorías
    TRANSFORM: 
    - Calcular popularity_score basado en valoraciones y completitud
    - Determinar es_gratuito según categoría
    - Normalizar campos categóricos
    LOAD: Insertar en tabla lugares_clustering optimizada
    """
```

**Features calculadas para ML:**
- `popularidad_score`: Algoritmo que combina valoraciones + completitud de datos
- `tiene_web`, `tiene_telefono`: Features binarios para clustering  
- `es_gratuito`: Determinado por categoría (museos=true, gastronomía=false)

#### B. Transformación de Eventos
```python
def extract_transform_load_eventos(self) -> int:
    """
    EXTRACT: Eventos activos de BD operacional
    TRANSFORM:
    - Calcular features temporales (mes_inicio, dia_semana_inicio)
    - Determinar duracion_dias entre fecha_inicio y fecha_fin
    - Asociar con POIs si tienen misma ubicación
    LOAD: Insertar en tabla eventos_clustering
    """
```

**Features temporales para clustering:**
- `mes_inicio`: Para clustering estacional
- `dia_semana_inicio`: Para patrones de días de semana
- `duracion_dias`: Para clasificar eventos cortos vs largos

---

## Algoritmos de Machine Learning y Clustering

Después del ETL, **clustering_processor.py** ejecuta 3 algoritmos ML optimizados:

### 1. K-Means Clustering (Geográfico)

**Objetivo**: Agrupar POIs por proximidad geográfica

```python
def geographic_clustering(self, df: pd.DataFrame, n_clusters: Optional[int] = None) -> Dict:
    """
    ENTRADA: DataFrame con latitud, longitud de POIs
    PROCESO:
    1. Normalizar coordenadas con StandardScaler
    2. Determinar número óptimo de clusters (método del codo)
    3. Aplicar K-means con n_init=10 para estabilidad
    4. Calcular métricas de calidad (silhouette score)
    
    SALIDA: {
        'cluster_stats': [centroide, radio, categorías por cluster]
        'silhouette_score': calidad del clustering
        'poi_clusters': mapeo poi_id -> cluster_id
    }
    """
```

**Algoritmo de detección automática de clusters:**
```python
def find_optimal_clusters(self, coords_scaled: np.ndarray, max_k: int = 15) -> int:
    """
    Método del codo mejorado:
    1. Probar K de 2 a max_k
    2. Calcular inercia (sum of squared distances)
    3. Encontrar punto donde mejora se estabiliza (curvatura máxima)
    4. Retornar K óptimo
    """
```

### 2. DBSCAN Clustering (Densidad)

**Objetivo**: Detectar clusters de densidad variable y ruido

```python
def dbscan_clustering(self, df: pd.DataFrame, eps: float = 0.01, min_samples: int = 3) -> Dict:
    """
    PARÁMETROS OPTIMIZADOS PARA CABA:
    - eps=0.01: ~1km de radio en coordenadas normalizadas
    - min_samples=3: Mínimo 3 POIs para formar cluster
    
    VENTAJAS:
    - Detecta clusters de forma irregular
    - Identifica outliers (ruido = -1)
    - No requiere especificar número de clusters
    
    SALIDA: {
        'cluster_stats': información por cluster denso
        'n_noise': cantidad de POIs en ruido
        'noise_ratio': porcentaje de ruido
    }
    """
```

### 3. Clustering Jerárquico (Categorías)

**Objetivo**: Encontrar relaciones entre categorías de POIs

```python
def hierarchical_clustering(self, df: pd.DataFrame, n_clusters: int = 6) -> Dict:
    """
    ALGORITMO: Agglomerative Clustering con linkage='ward'
    
    FEATURES UTILIZADAS:
    - Coordenadas geográficas normalizadas
    - One-hot encoding de categorías
    - Features numéricas (valoración, popularidad)
    
    APLICACIÓN: 
    - Identificar qué categorías se agrupan naturalmente
    - Usar para bonus en scoring de POIs similares
    """
```

### 4. Almacenamiento de Resultados ML

```python
def save_clustering_results(self, results: Dict):
    """
    Guarda en tabla clustering_results:
    - algorithm_type: 'geographic', 'dbscan', 'hierarchical'
    - results_json: Resultados completos serializados
    - silhouette_score: Métrica de calidad
    - n_clusters: Número de clusters detectados
    - fecha_calculo: Timestamp para versionado
    """
```

**Importante**: Los algoritmos NO se recalculan en cada generación de itinerario. Se ejecutan solo cuando hay:
- Nuevos POIs/eventos en cantidades significativas
- Cambios en el pipeline ETL
- Actualizaciones manuales del sistema

---

## Generación de Itinerarios: Flujo Detallado

### Entrada: Request del Usuario

Cuando llega un request del API Gateway:

```python
def generate_itinerary_request(user_id: int, request_data: Dict) -> Dict:
    """
    REQUEST TÍPICO:
    {
        'fecha_visita': '2025-09-15',
        'hora_inicio': '10:00',
        'duracion_horas': 8,
        'latitud_origen': -34.6118,    # OBLIGATORIO
        'longitud_origen': -58.3960,   # OBLIGATORIO  
        'zona_preferida': 'Palermo',   # Opcional
        'tipo_compania': 'pareja'      # Opcional
    }
    
    NOTA: categorias_preferidas SIEMPRE vienen de la BD del usuario
    """
```

### PASO 1: Obtener Preferencias del Usuario

```python
def get_user_preferences(self, user_id: int) -> Dict:
    """
    LEE DESDE BD OPERACIONAL:
    
    1. Tabla usuarios: tipo_viajero, duracion_viaje_promedio
    2. Tabla preferencias_usuario: categorías que le gustan/disgustan
    
    MAPEO INTELIGENTE:
    - tipo_viajero='cultural' -> zona_preferida='San Telmo'
    - tipo_viajero='foodie' -> zona_preferida='Puerto Madero'  
    - tipo_viajero='nocturno' -> zona_preferida='Palermo'
    
    RESULTADO FINAL:
    {
        'categorias_preferidas': ['Museos', 'Gastronomía'],  # Desde BD
        'zona_preferida': 'San Telmo',    # Mapeado desde tipo_viajero  
        'tipo_compania': 'pareja',        # Desde request
        'duracion_preferida': 8,          # Desde BD o default
        'actividades_evitar': []          # Desde preferencias_usuario
    }
    """
```

### PASO 2: Filtrado Inteligente con Clustering

```python
def filter_pois_and_events_by_clusters(self, user_prefs: Dict) -> Dict[str, List[Dict]]:
    """
    ESTRATEGIA DE FILTRADO BALANCEADO:
    
    A. USAR CLUSTERING DBSCAN PARA ZONA PREFERIDA:
       1. Buscar cluster DBSCAN que contenga la zona preferida
       2. Filtrar POIs geográficamente usando ese cluster
       
    B. SAMPLING BALANCEADO POR CATEGORÍA:
       - Si user prefiere múltiples categorías -> distribuir equitativamente
       - Gastronomía: máximo 20 POIs (evitar oversaturation)
       - Otras categorías: hasta 80 POIs cada una
       
    C. FILTRADO TEMPORAL DE EVENTOS:
       - Solo eventos activos en fecha_visita
       - Filtrar por categoría relevante al usuario
    """
```

**Lógica de balanceado por categorías:**
```python
if categorias and len(categorias) > 1:
    # ESTRATEGIA BALANCEADA: Por categoría separada
    for categoria in categorias:
        if categoria == 'Gastronomía':
            limit_categoria = 20  # Reducido para evitar exceso
        else:
            limit_categoria = 80  # Priorizar cultura/entretenimiento
```

### PASO 3: Scoring Personalizado

#### A. Scoring de POIs

```python
def calculate_poi_scores(self, pois: List[Dict], user_prefs: Dict) -> List[Dict]:
    """
    ALGORITMO DE SCORING MULTI-FACTOR:
    
    1. SCORE BASE (Datos Reales):
       - popularidad_score: de BD (0.1-1.0)
       - valoracion_promedio: normalizada 0-5 -> 0-0.5 puntos
    
    2. BONUS POR CARACTERÍSTICAS:
       - tiene_web: +0.05
       - tiene_telefono: +0.05  
       - es_gratuito: +0.1
    
    3. BONUS POR PREFERENCIAS USUARIO:
       - zona_preferida match: +0.3
       - categoria en preferidas: +0.6 (ALTO)
       - tipo_compania match: +0.15
    
    4. BONUS POR CLUSTERING:
       - categoria en cluster jerárquico similar: +0.15
       - perfil usuario K-means match: +0.25
    
    5. BONUS POR PROXIMIDAD GEOGRÁFICA:
       - ≤2km del origen: +0.2
       - 2-5km: +0.15
       - 5-10km: +0.1
       - >10km: sin bonus
    """
```

#### B. Scoring de Eventos

```python
def calculate_event_scores(self, eventos: List[Dict], user_prefs: Dict) -> List[Dict]:
    """
    PRIORIDAD ALTA PARA EVENTOS (únicos y temporales):
    
    1. SCORE BASE: 1.0 (mayor que POIs)
    
    2. BONUS TEMPORAL:
       - eventos en fecha_visita ±3 días: +0.3
       - eventos ±7 días: +0.15
    
    3. BONUS POR CARACTERÍSTICAS:
       - es_gratuito (mayoría): +0.2
       - eventos multi-día: +0.15
       - tiene URL: +0.1
    
    4. BONUS GEOGRÁFICO: (igual que POIs)
       - proximidad al origen
    """
```

### PASO 4: Selección Balanceada de Items

```python
def _select_balanced_items(self, pois_scored: List[Dict], eventos_scored: List[Dict], user_prefs: Dict) -> List[Dict]:
    """
    DISTRIBUCIÓN REALISTA POR DURACIÓN:
    
    4 horas: 3 items (2 POIs + 1 evento)
    6 horas: 4 items (3 POIs + 1 evento) 
    8+ horas: 5 items (3-4 POIs + 2 eventos)
    
    GARANTÍAS:
    - Eventos: prioridad por ser únicos
    - Gastronomía: SOLO si está en preferencias del usuario
    - Distribución equitativa entre categorías preferidas
    """
```

---

## Uso de Algoritmos y Optimización de Rutas

### PASO 5: Optimización Geográfica con DBSCAN

```python
def optimize_route_with_events(self, items_selected: List[Dict], duracion_horas: int, hora_inicio: str, lat_origen: float, lng_origen: float, user_prefs: Dict) -> List[Dict]:
    """
    ESTRATEGIA HÍBRIDA DE OPTIMIZACIÓN:
    
    1. OPTIMIZAR EVENTOS:
       - Eventos con hora_inicio fija: respetar horario
       - Eventos flexibles: optimizar geográficamente
    
    2. OPTIMIZAR POIs CON CLUSTERING DBSCAN:
       - Agrupar POIs por clusters DBSCAN
       - Priorizar POIs del mismo cluster geográfico
       - Algoritmo greedy dentro de cada cluster
    
    3. INTERCALAR TEMPORALMENTE:
       - Combinar eventos y POIs respetando horarios
       - Gastronomía en horarios de comida (si está en preferencias)
       - Buffer de 1 hora entre actividades
    """
```

### Algoritmo DBSCAN para Rutas

```python
def _group_pois_by_dbscan_clusters(self, pois: List[Dict]) -> Optional[Dict]:
    """
    USA RESULTADOS DBSCAN GUARDADOS EN BD:
    
    1. Cargar mapeo poi_id -> cluster_id de clustering_results
    2. Agrupar POIs seleccionados por cluster DBSCAN
    3. Priorizar clusters densos (más POIs)
    4. Separar POIs en "ruido" (-1) para manejo especial
    
    VENTAJA: POIs del mismo cluster están geográficamente cerca
    """
```

### Optimización Greedy Tradicional

```python
def _optimize_route_greedy_traditional(self, pois: List[Dict], max_pois: int, lat_origen: float, lng_origen: float) -> List[Dict]:
    """
    ALGORITMO GREEDY PONDERADO:
    
    1. INICIO: POI más cercano al origen (70% distancia + 30% score)
    2. ITERACIÓN: Siguiente POI más cercano al actual (misma ponderación)
    3. RESULTADO: Ruta que minimiza distancia total preservando calidad
    
    FÓRMULA: factor_combinado = (distancia_km * 0.7) - (score_normalizado * 0.3)
    """
```

### PASO 6: Programación Temporal Inteligente

```python
def _merge_events_and_pois_improved(self, eventos: List[Dict], pois: List[Dict], duracion_horas: int, hora_inicio_int: int, user_prefs: Dict) -> List[Dict]:
    """
    ALGORITMO DE SCHEDULING:
    
    1. HORARIOS DE COMIDA (solo si Gastronomía en preferencias):
       - Almuerzo: 13:00 (90 min) si itinerario incluye 12:00-15:00
       - Cena: 19:00 (90 min) si itinerario ≥6h y termina después 19:00
    
    2. EVENTOS CON HORARIO FIJO:
       - Respetar hora_inicio del evento
       - Verificar que esté dentro del horario del itinerario
    
    3. OTROS POIs:
       - Duración: 120 min (museos, monumentos), 90 min (gastronomía)
       - Buscar slots libres evitando conflictos
       - Buffer de 1 hora entre actividades
    
    4. ORDENAMIENTO FINAL:
       - Ordenar todas las actividades por horario_inicio
       - Renumerar orden_visita secuencialmente
    """
```

### Detección de Conflictos Temporales

```python
def _hour_conflicts_with_events(self, hora: int, duracion_min: int, eventos: List[Dict]) -> bool:
    """
    VERIFICA SOLAPAMIENTO TEMPORAL:
    
    Para cada evento programado:
    1. Extraer horario_inicio y horario_fin del evento
    2. Verificar si [hora, hora + duracion] se solapa con [evento_inicio, evento_fin]
    3. Retornar True si hay conflicto
    
    APLICACIÓN: Evitar programar POIs en horarios de eventos fijos
    """
```

---

## Sistema de Scoring y Personalización

### Personalización por Perfil de Usuario

El sistema utiliza múltiples capas de personalización:

#### 1. Clustering de Perfiles K-Means

```python
def _get_user_cluster_profile(self, user_id: int) -> Optional[int]:
    """
    MAPEO SIMPLE A CLUSTERS DE COMPORTAMIENTO:
    
    Cluster 0 (Foodie): Usuario prefiere 'Gastronomía'
    -> Bonus +0.25 para gastronomía
    -> Bonus +0.05 para tipo_cocina específico
    
    Cluster 1 (Cultural): Usuario prefiere 'Museos'/'Monumentos' 
    -> Bonus +0.25 para actividades culturales
    -> Bonus +0.05 si POI tiene_web (mejor información)
    
    Cluster 2 (Entretenimiento): Usuario prefiere 'Entretenimiento'
    -> Bonus +0.25 para cines, espectáculos
    -> Bonus +0.05 para actividades de pago (mayor calidad)
    """
```

#### 2. Clustering Jerárquico de Categorías

```python
def _calculate_category_cluster_bonus(self, categoria: str, user_prefs: Dict) -> float:
    """
    USA RESULTADOS DE CLUSTERING JERÁRQUICO:
    
    Si el usuario prefiere 'Museos' y el clustering jerárquico detectó
    que 'Monumentos' está en el mismo cluster:
    -> Aplicar bonus de categoría relacionada
    
    FÓRMULA: similarity_score * 0.15
    """
```

### Optimización de Distancias

#### Cálculo de Distancias Reales

```python
def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    FÓRMULA HAVERSINE PARA DISTANCIAS REALES:
    
    1. Convertir coordenadas a radianes
    2. Aplicar fórmula haversine: 
       a = sin²(Δlat/2) + cos(lat1) * cos(lat2) * sin²(Δlng/2)
       c = 2 * asin(√a)
       distancia = R * c  (R = 6371 km)
    
    APLICACIÓN: 
    - Bonus de proximidad en scoring
    - Optimización de rutas geográficas  
    - Estimación de tiempos de viaje
    """
```

### Gestión de Preferencias Complejas

#### Evitar Actividades No Deseadas

```python
# En el filtrado de POIs:
if actividades_evitar:
    evitar_sql = "', '".join(actividades_evitar)
    pois_query += f" AND categoria NOT IN ('{evitar_sql}')"
```

#### Adaptación por Tipo de Compañía

```python
if user_prefs.get('tipo_compania') == 'pareja':
    if poi.get('categoria') == 'Gastronomía':
        score += 0.15  # Gastronomía ideal para parejas
    elif poi.get('categoria') == 'Museos':
        score += 0.1   # Museos también buenos para parejas
```

---

## Arquitectura de Bases de Datos

### BD Operacional (Completa)

**Tabla: pois**
```sql
CREATE TABLE pois (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    categoria_id INTEGER REFERENCES categorias(id),
    subcategoria_id INTEGER REFERENCES subcategorias(id),
    direccion TEXT,
    latitud DECIMAL(10,8),
    longitud DECIMAL(11,8),
    barrio VARCHAR(100),
    comuna INTEGER,
    telefono VARCHAR(50),
    web VARCHAR(500),
    email VARCHAR(255),
    valoracion_promedio DECIMAL(3,2),
    numero_valoraciones INTEGER,
    tipo_cocina VARCHAR(100),    -- Para gastronomía
    tipo_ambiente VARCHAR(100),  -- Para gastronomía  
    material VARCHAR(200),       -- Para monumentos
    fuente_original VARCHAR(100)
);
```

**Tabla: eventos**
```sql
CREATE TABLE eventos (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    descripcion TEXT,
    categoria_evento VARCHAR(100),
    tematica VARCHAR(100),
    direccion_evento TEXT,
    ubicacion_especifica VARCHAR(255),
    latitud DECIMAL(10,8),
    longitud DECIMAL(11,8), 
    barrio VARCHAR(100),
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE,
    dias_semana VARCHAR(7),      -- 'LMXJVSD'
    hora_inicio TIME,
    hora_fin TIME,
    url_evento VARCHAR(500),
    fecha_scraping TIMESTAMP,
    url_fuente VARCHAR(500),
    hash_evento VARCHAR(64) UNIQUE,  -- Para evitar duplicados
    activo BOOLEAN DEFAULT TRUE
);
```

**Tabla: preferencias_usuario**
```sql
CREATE TABLE preferencias_usuario (
    usuario_id INTEGER REFERENCES usuarios(id),
    categoria_id INTEGER REFERENCES categorias(id),
    le_gusta BOOLEAN NOT NULL,    -- true/false
    PRIMARY KEY (usuario_id, categoria_id)
);
```

### BD Data Processor (Optimizada para ML)

**Tabla: lugares_clustering**
```sql
CREATE TABLE lugares_clustering (
    id SERIAL PRIMARY KEY,
    poi_id INTEGER NOT NULL,     -- Referencia a pois.id
    nombre VARCHAR(255) NOT NULL,
    categoria VARCHAR(50) NOT NULL,
    subcategoria VARCHAR(100),
    
    -- Ubicación normalizada
    latitud DECIMAL(10,8) NOT NULL,
    longitud DECIMAL(11,8) NOT NULL,
    barrio VARCHAR(100),
    comuna INTEGER,
    
    -- Features calculadas para ML
    valoracion_promedio DECIMAL(3,2) DEFAULT 0.0,
    numero_valoraciones INTEGER DEFAULT 0,
    popularidad_score DECIMAL(5,2) DEFAULT 0.0,
    
    -- Features categóricos
    tipo_cocina VARCHAR(100),
    tipo_ambiente VARCHAR(100),
    material VARCHAR(200),
    
    -- Features binarios para clustering
    tiene_web BOOLEAN DEFAULT FALSE,
    tiene_telefono BOOLEAN DEFAULT FALSE,
    es_gratuito BOOLEAN DEFAULT TRUE,
    
    fecha_actualizacion TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

**Tabla: clustering_results**
```sql
CREATE TABLE clustering_results (
    id SERIAL PRIMARY KEY,
    algorithm_type VARCHAR(50) NOT NULL,  -- 'geographic', 'dbscan', 'hierarchical'
    results_json JSONB NOT NULL,          -- Resultados completos del clustering
    silhouette_score DECIMAL(5,3),        -- Métrica de calidad
    n_clusters INTEGER,                   -- Número de clusters detectados
    total_pois INTEGER,                   -- POIs procesados
    fecha_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Ejemplo de clustering_results.results_json

```json
{
  "status": "success",
  "algorithm": "dbscan",
  "n_clusters": 8,
  "silhouette_score": 0.642,
  "cluster_stats": [
    {
      "cluster_id": 0,
      "num_pois": 45,
      "centroide_lat": -34.6118,
      "centroide_lng": -58.3960,
      "categorias": {"Gastronomía": 25, "Museos": 15, "Entretenimiento": 5},
      "barrios": ["Palermo", "Recoleta"],
      "radius_km": 2.3
    }
  ],
  "poi_clusters": {
    "123": 0,    // poi_id 123 está en cluster 0
    "124": 0,
    "125": -1,   // poi_id 125 es ruido (outlier)
    "126": 1
  }
}
```

---

## Flujo Completo: Ejemplo Práctico

### Escenario: Usuario 456 solicita itinerario

**1. Request recibido:**
```json
{
  "fecha_visita": "2025-09-15",
  "hora_inicio": "10:00", 
  "duracion_horas": 6,
  "latitud_origen": -34.6118,
  "longitud_origen": -58.3960,
  "zona_preferida": "Palermo",
  "tipo_compania": "pareja"
}
```

**2. Preferencias desde BD:**
```python
user_prefs = {
    'categorias_preferidas': ['Museos', 'Gastronomía'],  # De preferencias_usuario
    'zona_preferida': 'Palermo',
    'tipo_compania': 'pareja', 
    'duracion_preferida': 6,
    'actividades_evitar': ['Entretenimiento']  # Usuario marcó que no le gusta
}
```

**3. Filtrado con clustering DBSCAN:**
- Buscar cluster DBSCAN que contenga POIs de Palermo
- Cluster 2 encontrado: centroide en (-34.6118, -58.3960), 45 POIs
- Filtrar: 15 museos + 8 restaurantes de Palermo

**4. Eventos filtrados:**
- "Festival de Jazz en Puerto Madero" (2025-09-15, 20:00)
- "Exposición de Arte en Malba" (2025-09-10 a 2025-09-20)

**5. Scoring aplicado:**
```python
# Museo Malba:
score = 0.8 (popularidad) + 0.4 (valoracion 4.2/5) + 0.6 (categoria preferida) + 0.2 (zona match) = 2.0

# Restaurante Don Julio:  
score = 0.9 (popularidad) + 0.5 (valoracion 4.8/5) + 0.6 (categoria preferida) + 0.15 (pareja) = 2.15

# Festival Jazz:
score = 1.0 (evento base) + 0.3 (fecha match) + 0.1 (tiene URL) = 1.4
```

**6. Selección balanceada:**
- 4 items para 6 horas: 3 POIs + 1 evento
- 1 museo (Malba), 1 gastronomía (Don Julio), 1 cultural adicional, 1 evento

**7. Optimización de ruta:**
```
10:00-12:00: Museo Malba (cercano al origen)
12:30-14:00: Almuerzo en Don Julio (optimizado geográficamente)  
14:30-16:30: Monumento a Evita (mismo cluster que Malba)
20:00-22:00: Festival de Jazz (horario fijo del evento)
```

**8. Itinerario final:**
```json
{
  "itinerario_id": "it_456_1693344000",
  "actividades": [
    {
      "orden_visita": 1,
      "nombre": "Museo de Arte Latinoamericano",
      "horario_inicio": "10:00",
      "horario_fin": "12:00", 
      "duracion_minutos": 120,
      "tipo_actividad": "Visita cultural"
    },
    {
      "orden_visita": 2,
      "nombre": "Don Julio",
      "horario_inicio": "12:30", 
      "horario_fin": "14:00",
      "duracion_minutos": 90,
      "tipo_actividad": "Comida (almuerzo)"
    },
    {
      "orden_visita": 3,
      "nombre": "Festival de Jazz en Puerto Madero",
      "horario_inicio": "20:00",
      "horario_fin": "22:00", 
      "duracion_minutos": 120,
      "tipo_actividad": "Evento cultural"
    }
  ],
  "estadisticas": {
    "total_actividades": 3,
    "duracion_total_horas": 5.5,
    "distancia_total_km": 8.2,
    "costo_estimado": "Medio"
  }
}
```

---

## Conclusión: Fortalezas del Sistema

### 1. **Inteligencia Basada en Datos Reales**
- Utiliza POIs oficiales de CABA + eventos en tiempo real
- Scoring basado en valoraciones reales y características verificables
- No depende de datos sintéticos o hardcodeados

### 2. **Machine Learning Aplicado Inteligentemente**  
- 3 algoritmos de clustering complementarios (K-means, DBSCAN, jerárquico)
- Los modelos se entrenan una vez y se reutilizan eficientemente
- Optimización geográfica basada en clusters reales

### 3. **Personalización Profunda**
- Preferencias desde BD de usuario real
- Múltiples capas de scoring (preferencias + proximidad + clustering)
- Adaptación por tipo de compañía y duración

### 4. **Optimización Temporal y Geográfica**
- Respeta horarios fijos de eventos
- Minimiza distancias usando algoritmos probados
- Programación inteligente de comidas y tiempos de viaje

### 5. **Escalabilidad y Mantenibilidad**
- Arquitectura modular (CSV → ETL → ML → Recommendations)
- BD optimizada para consultas rápidas
- Logging detallado para debugging y mejoras

### 6. **Balance Realista**
- Itinerarios factibles con duración y distancias reales
- Balance entre categorías preferidas 
- Incluye eventos únicos y temporales para mayor valor

Este sistema representa un enfoque sofisticado pero práctico para la generación de itinerarios turísticos, combinando machine learning, optimización geográfica y personalización basada en datos reales de usuarios y POIs de Buenos Aires.
