"""
BAXperience Recommendation Service
=================================

Sistema de recomendaciones para generar itinerarios personalizados.
Usa los clusters y modelos ML ya entrenados.

Flujo:
1. Recibe request de usuario con preferencias
2. Usa clusters para filtrar POIs relevantes
3. Aplica algoritmos de optimización de rutas
4. Genera itinerario personalizado

Autor: BAXperience Team
"""

import logging
import json
import pickle
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import psycopg2
from psycopg2.extras import RealDictCursor
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler

from csv_processor import DatabaseConfig

logger = logging.getLogger(__name__)

class RecommendationService:
    """
    Servicio de recomendaciones para itinerarios personalizados
    """
    
    def __init__(self):
        self.conn = None
        self.operational_conn = None
        self.models = {}
        self.scalers = {}
        
    def connect_database(self):
        """Conectar a BD Data Processor"""
        try:
            self.conn = psycopg2.connect(**DatabaseConfig.PROCESSOR_DB)
            logger.info("Conectado a BD Data Processor para recomendaciones")
        except Exception as e:
            logger.error(f"Error conectando a BD: {e}")
            raise
    
    def connect_operational_database(self):
        """Conectar a BD Operacional (opcional)"""
        try:
            self.operational_conn = psycopg2.connect(**DatabaseConfig.OPERATIONAL_DB)
            logger.info("Conectado a BD Operacional para guardado completo")
        except Exception as e:
            logger.warning(f"No se pudo conectar a BD Operacional: {e}")
            self.operational_conn = None
    
    def disconnect_database(self):
        """Desconectar de BD"""
        if self.conn:
            self.conn.close()
            logger.info("Desconectado de BD Data Processor")
        if self.operational_conn:
            self.operational_conn.close()
            logger.info("Desconectado de BD Operacional")
    
    def load_ml_models(self):
        """Cargar modelos ML entrenados desde BD"""
        logger.info("Cargando resultados de clustering desde BD...")
        
        try:
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            
            # Cargar resultados de clustering más recientes
            cursor.execute("""
                SELECT algorithm_type, results_json, silhouette_score, n_clusters
                FROM clustering_results 
                ORDER BY id DESC 
                LIMIT 20
            """)
            
            clustering_results = cursor.fetchall()
            
            # Organizar resultados por algoritmo
            for result in clustering_results:
                algorithm = result['algorithm_type']
                if algorithm not in self.models:
                    self.models[algorithm] = {
                        'results': result['results_json'],
                        'silhouette_score': float(result['silhouette_score']) if result['silhouette_score'] else 0,
                        'n_clusters': result['n_clusters'],
                        'created_at': 'recent'
                    }
                    logger.info(f"Cargado clustering {algorithm}: {result['n_clusters']} clusters, silhouette={result['silhouette_score']:.3f}")
            
            logger.info(f"Modelos ML cargados: {list(self.models.keys())}")
            
        except Exception as e:
            logger.warning(f"No se pudieron cargar modelos ML: {e}")
            # Rollback en caso de error SQL
            if self.conn:
                try:
                    self.conn.rollback()
                except:
                    pass
            # Fallback: usar lógica simple sin clustering avanzado
    
    def get_user_preferences(self, user_id: int, request_data: Dict = None) -> Dict:
        """
        Obtener preferencias del usuario desde BD Operacional
        Lee las preferencias reales de la base de datos
        MEJORADO: Considera coordenadas de origen para determinar zona automáticamente
        """
        # Asegurar conexión a BD Operacional
        if not hasattr(self, 'operational_conn') or not self.operational_conn:
            try:
                self.operational_conn = psycopg2.connect(**DatabaseConfig.OPERATIONAL_DB)
                logger.info("Conectado a BD Operacional para obtener preferencias")
            except Exception as e:
                logger.error(f"Error conectando a BD Operacional: {e}")
            # Retornar preferencias por defecto si no se puede conectar
                return {
                    'categorias_preferidas': ['Museos', 'Gastronomía'],
                    'zona_preferida': 'Palermo',
                    'tipo_compania': 'pareja',
                    'duracion_preferida': 8,  # horas
                    'actividades_evitar': ['Entretenimiento']
                }
        
        try:
            cursor = self.operational_conn.cursor()
            
            # Obtener información básica del usuario
            cursor.execute("""
                SELECT nombre, tipo_viajero, duracion_viaje_promedio, ciudad_origen
                FROM usuarios 
                WHERE id = %s
            """, (user_id,))
            
            user_info = cursor.fetchone()
            if not user_info:
                logger.warning(f"Usuario {user_id} no encontrado, usando preferencias por defecto")
                return {
                    'categorias_preferidas': ['Museos', 'Gastronomía'],
                    'zona_preferida': 'Palermo',
                    'tipo_compania': 'pareja',
                    'duracion_preferida': 8,
                    'actividades_evitar': ['Entretenimiento']
                }
            
            # Obtener preferencias de categorías del usuario
            cursor.execute("""
                SELECT c.nombre, p.le_gusta
                FROM preferencias_usuario p 
                JOIN categorias c ON p.categoria_id = c.id
                WHERE p.usuario_id = %s
            """, (user_id,))
            
            preferencias_raw = cursor.fetchall()
            
            # Procesar preferencias
            categorias_preferidas = []
            actividades_evitar = []
            
            for categoria, le_gusta in preferencias_raw:
                if le_gusta:
                    categorias_preferidas.append(categoria)
                else:
                    actividades_evitar.append(categoria)
            
            # Si no hay preferencias específicas, usar defaults
            if not categorias_preferidas:
                categorias_preferidas = ['Museos', 'Gastronomía']
            
            # NUEVO: Determinar zona preferida basándose en coordenadas de origen si están disponibles
            zona_preferida = None
            tipo_compania = 'solo'      # Default
            
            # 1. Prioridad: Si se especifica zona_preferida en request_data, usarla
            if request_data and request_data.get('zona_preferida'):
                zona_preferida = request_data['zona_preferida']
                logger.info(f"Zona especificada en request: {zona_preferida}")
            
            # 2. Si no hay zona en request pero SÍ hay coordenadas, calcular zona automáticamente
            elif request_data and request_data.get('latitud_origen') is not None and request_data.get('longitud_origen') is not None:
                try:
                    lat_origen = float(request_data['latitud_origen'])
                    lng_origen = float(request_data['longitud_origen'])
                    zona_calculada = self._determinar_zona_por_coordenadas(lat_origen, lng_origen)
                    if zona_calculada:
                        zona_preferida = zona_calculada
                        logger.info(f"Zona calculada por coordenadas ({lat_origen}, {lng_origen}): {zona_preferida}")
                    else:
                        logger.warning(f"No se pudo determinar zona para coordenadas ({lat_origen}, {lng_origen})")
                except (ValueError, TypeError) as e:
                    logger.warning(f"Error procesando coordenadas de origen: {e}")
            
            # 3. Fallback: Mapear zona según tipo de viajero si está disponible
            if not zona_preferida and user_info[1]:  # tipo_viajero
                tipo_lower = user_info[1].lower()
                
                # Mapear zona según tipo de viajero
                if 'cultural' in tipo_lower:
                    zona_preferida = 'San Telmo'
                elif 'foodie' in tipo_lower or 'gastrónomo' in tipo_lower:
                    zona_preferida = 'Puerto Madero'
                elif 'aventurer' in tipo_lower:
                    zona_preferida = 'La Boca'
                elif 'nocturno' in tipo_lower:
                    zona_preferida = 'Palermo'
                elif 'fotógrafo' in tipo_lower:
                    zona_preferida = 'Puerto Madero'
                else:
                    zona_preferida = 'Palermo'  # Default para urbano, etc.
                    
                logger.info(f"Zona asignada por tipo_viajero '{user_info[1]}': {zona_preferida}")
            
            # 4. Último fallback: Palermo
            if not zona_preferida:
                zona_preferida = 'Palermo'
                logger.info("Zona fallback: Palermo")
                
                # Mapear tipo de compañía
                if 'pareja' in tipo_lower:
                    tipo_compania = 'pareja'
                elif 'solo' in tipo_lower:
                    tipo_compania = 'solo'
                else:
                    tipo_compania = 'solo'  # Default
            
            # Duración preferida desde BD o default
            duracion_preferida = user_info[2] if user_info[2] and user_info[2] > 0 else 8
            
            resultado = {
                'categorias_preferidas': categorias_preferidas,
                'zona_preferida': zona_preferida,
                'tipo_compania': tipo_compania,
                'duracion_preferida': duracion_preferida,
                'actividades_evitar': actividades_evitar
            }
            
            logger.info(f"Preferencias obtenidas para usuario {user_id}: {resultado}")
            return resultado
            
        except Exception as e:
            logger.error(f"Error obteniendo preferencias del usuario {user_id}: {e}")
            # Retornar preferencias por defecto en caso de error
            return {
                'categorias_preferidas': ['Museos', 'Gastronomía'],
                'zona_preferida': 'Palermo',
                'tipo_compania': 'pareja',
                'duracion_preferida': 8,
                'actividades_evitar': ['Entretenimiento']
            }
    
    def _determinar_zona_por_coordenadas(self, lat_origen: float, lng_origen: float) -> Optional[str]:
        """
        Determinar zona/barrio basándose en coordenadas de origen
        Usa POIs cercanos para inferir la zona más probable
        """
        try:
            if not self.conn:
                logger.warning("No hay conexión a BD para determinar zona por coordenadas")
                return None
                
            cursor = self.conn.cursor(cursor_factory=RealDictCursor)
            
            # Buscar POIs cercanos (dentro de 2km) que tengan barrio asignado
            query = """
            SELECT 
                barrio, 
                COUNT(*) as pois_count,
                AVG(
                    6371 * 2 * ASIN(SQRT(
                        POWER(SIN((latitud - %s) * PI() / 180 / 2), 2) +
                        COS(%s * PI() / 180) * COS(latitud * PI() / 180) *
                        POWER(SIN((longitud - %s) * PI() / 180 / 2), 2)
                    ))
                ) as distancia_promedio_km
            FROM lugares_clustering
            WHERE latitud IS NOT NULL 
            AND longitud IS NOT NULL
            AND barrio IS NOT NULL
            AND barrio != ''
            AND (
                6371 * 2 * ASIN(SQRT(
                    POWER(SIN((latitud - %s) * PI() / 180 / 2), 2) +
                    COS(%s * PI() / 180) * COS(latitud * PI() / 180) *
                    POWER(SIN((longitud - %s) * PI() / 180 / 2), 2)
                )) < 2.0
            )
            GROUP BY barrio
            ORDER BY pois_count DESC, distancia_promedio_km ASC
            LIMIT 5
            """
            
            cursor.execute(query, (lat_origen, lat_origen, lng_origen, lat_origen, lat_origen, lng_origen))
            results = cursor.fetchall()
            
            if results:
                barrio_mas_probable = results[0]['barrio']
                pois_count = results[0]['pois_count']
                distancia = results[0]['distancia_promedio_km']
                
                logger.info(f"Zona determinada por coordenadas: {barrio_mas_probable} ({pois_count} POIs, {distancia:.2f}km promedio)")
                
                # Normalizar nombres de barrios comunes
                barrio_normalizado = self._normalizar_nombre_barrio(barrio_mas_probable)
                
                cursor.close()
                return barrio_normalizado
            else:
                logger.info(f"No se encontraron POIs cercanos a las coordenadas ({lat_origen}, {lng_origen})")
                cursor.close()
                return None
                
        except Exception as e:
            logger.error(f"Error determinando zona por coordenadas: {e}")
            return None
    
    def _normalizar_nombre_barrio(self, barrio: str) -> str:
        """
        Normalizar nombres de barrios para consistencia
        """
        if not barrio:
            return barrio
            
        barrio_lower = barrio.lower().strip()
        
        # Mapeo de nombres comunes/alternativos
        mapeo_barrios = {
            'puerto madero': 'Puerto Madero',
            'san telmo': 'San Telmo',
            'la boca': 'La Boca',
            'palermo': 'Palermo',
            'recoleta': 'Recoleta',
            'belgrano': 'Belgrano',
            'villa crespo': 'Villa Crespo',
            'barracas': 'Barracas',
            'constitución': 'Constitución',
            'microcentro': 'Microcentro',
            'centro': 'Microcentro',
            'retiro': 'Retiro',
            'once': 'Once',
            'abasto': 'Abasto'
        }
        
        return mapeo_barrios.get(barrio_lower, barrio.title())
    
    def _find_geographic_cluster_for_zone(self, zona: str) -> Optional[int]:
        """
        Encontrar el cluster geográfico DBSCAN que contiene la zona preferida
        Usa los resultados de clustering guardados en BD
        """
        try:
            if 'dbscan' not in self.models:
                logger.warning("No hay resultados DBSCAN disponibles")
                return None
                
            dbscan_results = self.models['dbscan']['results']
            
            # Buscar en cluster_stats si hay información de barrios
            if 'cluster_stats' in dbscan_results:
                cluster_stats = dbscan_results['cluster_stats']
                
                # Manejar tanto formato dict como list
                if isinstance(cluster_stats, dict):
                    # Formato diccionario: {cluster_id: stats}
                    for cluster_id, stats in cluster_stats.items():
                        if isinstance(stats, dict) and 'barrios_incluidos' in stats:
                            barrios = stats['barrios_incluidos']
                            # Buscar coincidencia parcial con la zona preferida
                            for barrio in barrios:
                                if zona.lower() in barrio.lower() or barrio.lower() in zona.lower():
                                    logger.info(f"Zona '{zona}' encontrada en cluster DBSCAN {cluster_id} (barrio: {barrio})")
                                    return int(cluster_id)
                
                elif isinstance(cluster_stats, list):
                    # Formato lista: [{cluster_id: ..., barrios: ...}, ...]
                    for item in cluster_stats:
                        if isinstance(item, dict):
                            cluster_id = item.get('cluster_id')
                            barrios = item.get('barrios_incluidos', item.get('barrios', []))
                            
                            if cluster_id is not None and barrios:
                                # Buscar coincidencia parcial con la zona preferida
                                for barrio in barrios:
                                    if zona.lower() in barrio.lower() or barrio.lower() in zona.lower():
                                        logger.info(f"Zona '{zona}' encontrada en cluster DBSCAN {cluster_id} (barrio: {barrio})")
                                        return int(cluster_id)
            
            logger.info(f"No se encontró cluster específico para zona '{zona}', usando filtrado tradicional")
            return None
            
        except Exception as e:
            logger.warning(f"Error buscando cluster para zona '{zona}': {e}")
            return None
    
    def _apply_clustering_filters(self, base_query: str, params: List, cluster_geografico: Optional[int] = None) -> Tuple[str, List]:
        """
        Aplicar filtros de clustering a una query base
        Usa DBSCAN para filtrado geográfico si está disponible
        """
        if cluster_geografico is not None and 'dbscan' in self.models:
            try:
                # Obtener POIs del cluster específico usando DBSCAN
                dbscan_results = self.models['dbscan']['results']
                
                if 'poi_clusters' in dbscan_results:
                    # Filtrar POIs que pertenecen al cluster geográfico
                    cluster_poi_ids = []
                    poi_clusters = dbscan_results['poi_clusters']
                    
                    # Manejar tanto formato dict como list
                    if isinstance(poi_clusters, dict):
                        # Formato diccionario: {poi_id: cluster_id}
                        for poi_id, poi_cluster in poi_clusters.items():
                            if poi_cluster == cluster_geografico:
                                cluster_poi_ids.append(poi_id)
                    
                    elif isinstance(poi_clusters, list):
                        # Formato lista: [{poi_id: ..., cluster_id: ...}, ...]
                        for item in poi_clusters:
                            if isinstance(item, dict):
                                poi_id = item.get('poi_id')
                                poi_cluster = item.get('cluster_id', item.get('cluster'))
                                if poi_cluster == cluster_geografico and poi_id is not None:
                                    cluster_poi_ids.append(poi_id)
                    
                    if cluster_poi_ids:
                        # Agregar filtro por IDs de POIs del cluster
                        ids_str = ', '.join(['%s'] * len(cluster_poi_ids))
                        base_query += f" AND poi_id IN ({ids_str})"
                        params.extend(cluster_poi_ids)
                        logger.info(f"Aplicado filtro DBSCAN: {len(cluster_poi_ids)} POIs en cluster {cluster_geografico}")
                
            except Exception as e:
                logger.warning(f"Error aplicando filtro DBSCAN: {e}")
        
        return base_query, params
    
    def _get_user_cluster_profile(self, user_id: int) -> Optional[int]:
        """
        Obtener el cluster de perfil de usuario usando K-means
        Para segmentación de comportamiento de usuario
        """
        try:
            if 'kmeans' not in self.models:
                return None
                
            # Por ahora, usar lógica simple basada en preferencias
            # En el futuro, esto usaría un modelo K-means entrenado sobre comportamiento de usuarios
            user_prefs = self.get_user_preferences(user_id, None)  # Sin request_data aquí
            
            # Mapeo simple a clusters de usuario (a mejorar con datos reales)
            if 'Gastronomía' in user_prefs.get('categorias_preferidas', []):
                return 0  # Cluster foodie
            elif 'Museos' in user_prefs.get('categorias_preferidas', []):
                return 1  # Cluster cultural  
            elif 'Entretenimiento' in user_prefs.get('categorias_preferidas', []):
                return 2  # Cluster entretenimiento
            else:
                return None
                
        except Exception as e:
            logger.warning(f"Error obteniendo cluster de usuario: {e}")
            return None

    def filter_pois_and_events_by_clusters(self, user_prefs: Dict) -> Dict[str, List[Dict]]:
        """
        Filtrar POIs y eventos usando clusters geográficos y temáticos
        CON SAMPLING BALANCEADO POR CATEGORÍA para itinerarios realistas
        INTEGRADO CON DBSCAN PARA CLUSTERING GEOGRÁFICO INTELIGENTE
        """
        logger.info("Filtrando POIs y eventos por clusters...")
        
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Construir filtros basados en preferencias
            categorias = user_prefs.get('categorias_preferidas', [])
            zona = user_prefs.get('zona_preferida', '')  # Puede ser None o string
            actividades_evitar = user_prefs.get('actividades_evitar', [])
            fecha_visita = user_prefs.get('fecha_visita', datetime.now().date().isoformat())
            
            # Obtener coordenadas de origen para cálculos de distancia (futuro uso)
            latitud_origen = user_prefs.get('latitud_origen')
            longitud_origen = user_prefs.get('longitud_origen')
            
            logger.info(f"Filtrando POIs desde punto origen: lat={latitud_origen}, lng={longitud_origen}, zona_pref={zona}")
            
            # === USAR CLUSTERING DBSCAN PARA FILTRADO GEOGRÁFICO INTELIGENTE ===
            cluster_geografico_preferido = None
            if zona and zona.strip() and 'dbscan' in self.models:
                cluster_geografico_preferido = self._find_geographic_cluster_for_zone(zona)
                logger.info(f"Cluster geográfico detectado para zona '{zona}': {cluster_geografico_preferido}")
            
            # === IMPLEMENTAR SAMPLING BALANCEADO POR CATEGORÍA ===
            pois_balanceados = []
            
            if categorias and len(categorias) > 1:
                # ESTRATEGIA BALANCEADA: Obtener POIs por categoría por separado
                for categoria in categorias:
                    pois_query = """
                    SELECT 
                        id, poi_id, nombre, categoria, subcategoria,
                        latitud, longitud, 
                        COALESCE(barrio, 'Sin especificar') as barrio, 
                        comuna,
                        COALESCE(valoracion_promedio, 0) as valoracion_promedio, 
                        COALESCE(popularidad_score, 0) as popularidad_score,
                        tipo_cocina, tipo_ambiente,
                        COALESCE(tiene_web, false) as tiene_web, 
                        COALESCE(tiene_telefono, false) as tiene_telefono, 
                        COALESCE(es_gratuito, false) as es_gratuito,
                        'poi' as item_type
                    FROM lugares_clustering 
                    WHERE latitud IS NOT NULL AND longitud IS NOT NULL
                    AND categoria = %s
                    """
                    
                    # Filtrar por zona si se especifica
                    if zona and zona.strip():
                        pois_query += " AND (barrio ILIKE %s OR barrio IS NULL)"
                        params = [categoria, f"%{zona}%"]
                    else:
                        params = [categoria]
                    
                    # Excluir actividades no deseadas
                    if actividades_evitar:
                        evitar_sql = "', '".join(actividades_evitar)
                        pois_query += f" AND categoria NOT IN ('{evitar_sql}')"
                    
                    # LÓGICA BALANCEADA: Más POIs para categorías no-gastronómicas
                    if categoria == 'Gastronomía':
                        limit_categoria = 20  # Reducido de 40 a 20 para limitar gastronomía
                    else:
                        limit_categoria = 80  # Aumentado de 60 a 80 para priorizar cultural/entretenimiento
                    
                    pois_query += f"""
                    ORDER BY 
                        CASE WHEN barrio IS NOT NULL THEN 1 ELSE 0 END DESC,
                        popularidad_score DESC NULLS LAST,
                        RANDOM()
                    LIMIT {limit_categoria}
                    """
                    
                    cursor.execute(pois_query, params)
                    pois_categoria = cursor.fetchall()
                    
                    logger.info(f"  {categoria}: {len(pois_categoria)} POIs obtenidos")
                    pois_balanceados.extend([dict(poi) for poi in pois_categoria])
                
                pois = pois_balanceados
                
            else:
                # ESTRATEGIA ORIGINAL: Una sola categoría o sin preferencias específicas
                pois_query = """
                SELECT 
                    id, poi_id, nombre, categoria, subcategoria,
                    latitud, longitud, 
                    COALESCE(barrio, 'Sin especificar') as barrio, 
                    comuna,
                    COALESCE(valoracion_promedio, 0) as valoracion_promedio, 
                    COALESCE(popularidad_score, 0) as popularidad_score,
                    tipo_cocina, tipo_ambiente,
                    COALESCE(tiene_web, false) as tiene_web, 
                    COALESCE(tiene_telefono, false) as tiene_telefono, 
                    COALESCE(es_gratuito, false) as es_gratuito,
                    'poi' as item_type
                FROM lugares_clustering 
                WHERE latitud IS NOT NULL AND longitud IS NOT NULL
                """
                
                # Filtrar POIs por categorías
                if categorias:
                    categorias_sql = "', '".join(categorias)
                    pois_query += f" AND categoria IN ('{categorias_sql}')"
                
                # Filtrar POIs por zona
                if zona and zona.strip():
                    pois_query += f" AND (barrio ILIKE '%{zona}%' OR barrio IS NULL)"
                
                # Excluir actividades no deseadas en POIs
                if actividades_evitar:
                    evitar_sql = "', '".join(actividades_evitar)
                    pois_query += f" AND categoria NOT IN ('{evitar_sql}')"
                
                pois_query += """
                ORDER BY 
                    CASE WHEN barrio IS NOT NULL THEN 1 ELSE 0 END DESC,
                    popularidad_score DESC NULLS LAST,
                    RANDOM()
                LIMIT 200
                """
                
                cursor.execute(pois_query)
                pois_result = cursor.fetchall()
                pois = [dict(poi) for poi in pois_result]
            
            # === OBTENER EVENTOS ===
            eventos_query = """
            SELECT 
                id, evento_id, nombre, 
                categoria_evento as categoria, tematica as subcategoria,
                CAST(latitud AS FLOAT) as latitud, 
                CAST(longitud AS FLOAT) as longitud,
                COALESCE(barrio, 'Sin especificar') as barrio,
                fecha_inicio, fecha_fin, duracion_dias,
                url_evento,
                'evento' as item_type
            FROM eventos_clustering 
            WHERE activo = true 
            """
            
            # Inicializar lista de parámetros
            params = []
            
            # MEJORADO: Filtrar eventos por fecha del itinerario
            # Solo incluir eventos que estén activos en la fecha de visita
            if fecha_visita:
                try:
                    # Convertir fecha_visita a formato de fecha
                    if isinstance(fecha_visita, str):
                        from datetime import datetime as dt
                        fecha_visita_dt = dt.strptime(fecha_visita, '%Y-%m-%d').date()
                    else:
                        fecha_visita_dt = fecha_visita
                    
                    # Filtrar eventos donde la fecha de visita esté entre fecha_inicio y fecha_fin
                    eventos_query += """
                    AND (
                        (fecha_inicio IS NOT NULL AND fecha_inicio <= %s)
                        AND 
                        (fecha_fin IS NULL OR fecha_fin >= %s)
                    )
                    """
                    # Agregar parámetros para la fecha
                    params.extend([fecha_visita_dt, fecha_visita_dt])
                    
                    logger.info(f"Filtrando eventos para fecha: {fecha_visita_dt}")
                except Exception as e:
                    logger.warning(f"Error procesando fecha de visita {fecha_visita}: {e}")
                    # Si hay error, no filtrar por fecha
                    pass
            
            # MEJORADO: Incluir eventos con categoría "Evento" (que es la categoría real)
            # Filtrar eventos por categorías si están especificadas
            if categorias:
                # Mapear categorías de usuario a categorías de eventos
                categorias_eventos = []
                for cat in categorias:
                    if cat in ['Entretenimiento', 'Museos', 'Gastronomía', 'Lugares Históricos', 'Monumentos']:
                        # Todos estos tipos pueden tener eventos asociados
                        categorias_eventos.append('Evento')  # La categoría real es "Evento"
                
                if categorias_eventos:
                    # Incluir eventos de categoría "Evento" que coincidan con las preferencias
                    eventos_query += " AND categoria_evento = 'Evento'"
            else:
                # Si no hay categorías específicas, incluir todos los eventos
                eventos_query += " AND categoria_evento = 'Evento'"
            
            # Filtrar eventos por zona
            if zona and zona.strip():
                eventos_query += " AND (barrio ILIKE %s OR barrio IS NULL)"
                params.append(f"%{zona}%")
            
            eventos_query += """
            ORDER BY 
                CASE WHEN fecha_inicio IS NOT NULL THEN 0 ELSE 1 END,
                fecha_inicio ASC, 
                RANDOM()
            LIMIT 50
            """
            
            # Ejecutar query con parámetros
            cursor.execute(eventos_query, params)
            
            eventos_result = cursor.fetchall()
            
            # Procesar eventos para que tengan el formato esperado
            eventos = []
            for evento_row in eventos_result:
                evento = dict(evento_row)
                
                # Convertir objetos date a strings para JSON serialization
                if evento.get('fecha_inicio') and hasattr(evento['fecha_inicio'], 'isoformat'):
                    evento['fecha_inicio'] = evento['fecha_inicio'].isoformat()
                if evento.get('fecha_fin') and hasattr(evento['fecha_fin'], 'isoformat'):
                    evento['fecha_fin'] = evento['fecha_fin'].isoformat()
                
                # Agregar campos faltantes para compatibilidad
                evento['poi_id'] = evento['evento_id']
                evento['comuna'] = None
                evento['valoracion_promedio'] = 0.0
                evento['popularidad_score'] = 0.8
                evento['tipo_cocina'] = None
                evento['tipo_ambiente'] = None
                evento['tiene_web'] = bool(evento.get('url_evento'))
                evento['tiene_telefono'] = False
                evento['es_gratuito'] = True
                
                eventos.append(evento)
            
            logger.info(f"POIs filtrados: {len(pois)}, Eventos filtrados: {len(eventos)}")
            
            return {
                'pois': pois,
                'eventos': eventos
            }
            
        except Exception as e:
            logger.error(f"Error filtrando POIs y eventos: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
            return {'pois': [], 'eventos': []}
        finally:
            cursor.close()
    
    def filter_pois_by_clusters(self, user_prefs: Dict) -> List[Dict]:
        """
        Filtrar POIs usando clusters geográficos y temáticos (retrocompatibilidad)
        """
        result = self.filter_pois_and_events_by_clusters(user_prefs)
        return result['pois']
    
    def calculate_poi_scores(self, pois: List[Dict], user_prefs: Dict) -> List[Dict]:
        """
        Calcular scores personalizados para cada POI
        MEJORADO: Considera distancia desde punto de origen + CLUSTERING INTELIGENTE
        """
        logger.info("Calculando scores personalizados con clustering...")
        
        if not pois:
            return []
        
        # Obtener coordenadas de origen para cálculos de proximidad
        lat_origen = user_prefs.get('latitud_origen')
        lng_origen = user_prefs.get('longitud_origen')
        
        # Obtener información de clusters para el usuario
        user_id = user_prefs.get('user_id')
        user_cluster_profile = self._get_user_cluster_profile(user_id) if user_id else None
        
        scored_pois = []
        
        for poi in pois:
            score = 0.0
            
            # Score base usando datos reales de popularidad
            popularidad = float(poi.get('popularidad_score', 0))
            if popularidad > 0:
                score += min(popularidad, 1.0)  # Normalizar a máximo 1.0
            else:
                # Solo si no hay datos, usar score mínimo
                score += 0.1
            
            # Score por valoración real de la BD
            valoracion = float(poi.get('valoracion_promedio', 0))
            if valoracion > 0:
                score += (valoracion / 5.0) * 0.5  # Normalizar de 0-5 a 0-0.5
            
            # Score adicional por características verificables
            if poi.get('tiene_web'):
                score += 0.05  # Reducido de 0.1
            if poi.get('tiene_telefono'):
                score += 0.05
            if poi.get('email') and poi.get('email').strip():
                score += 0.05  # Nuevo: puntos por tener email
            
            # Bonus por características específicas
            if poi.get('es_gratuito'):
                score += 0.1  # Pequeño bonus por ser gratuito
            
            # Bonus por zona preferida - con más peso si se especifica zona
            zona_pref = user_prefs.get('zona_preferida', '')
            barrio_poi = poi.get('barrio', '') or ''
            if zona_pref and zona_pref.lower() in barrio_poi.lower():
                score += 0.3  # Aumentado el bonus por zona preferida
            
            # Bonus por tipo de compañía
            if user_prefs.get('tipo_compania') == 'pareja':
                if poi.get('categoria') == 'Gastronomía':
                    score += 0.15  # Gastronomía ideal para parejas
                elif poi.get('categoria') == 'Museos':
                    score += 0.1   # Museos también buenos para parejas
            
            # NUEVO: Bonus por categorías preferidas del usuario (desde BD) - AUMENTADO
            categorias_preferidas = user_prefs.get('categorias_preferidas', [])
            if categorias_preferidas and poi.get('categoria') in categorias_preferidas:
                score += 0.6  # Bonus MUY ALTO para categorías preferidas del usuario
                logger.debug(f"Bonus categoría preferida aplicado a {poi.get('nombre')}: {poi.get('categoria')}")
            
            # 🆕 BONUS POR CLUSTERING JERÁRQUICO DE CATEGORÍAS
            if 'hierarchical' in self.models and poi.get('categoria'):
                cluster_bonus = self._calculate_category_cluster_bonus(poi.get('categoria'), user_prefs)
                if cluster_bonus > 0:
                    score += cluster_bonus
                    logger.debug(f"Bonus clustering jerárquico aplicado: +{cluster_bonus:.2f}")
            
            # 🆕 BONUS POR CLUSTER DE PERFIL DE USUARIO (K-MEANS)
            if user_cluster_profile is not None:
                profile_bonus = self._calculate_user_profile_bonus(poi, user_cluster_profile)
                if profile_bonus > 0:
                    score += profile_bonus
                    logger.debug(f"Bonus perfil de usuario aplicado: +{profile_bonus:.2f}")
            
            # Bonus adicional para actividades gratuitas (sin considerar presupuesto)
            if poi.get('es_gratuito'):
                score += 0.05  # Pequeño bonus adicional
            
            # NUEVO: Bonus por proximidad al punto de origen
            if lat_origen is not None and lng_origen is not None:
                lat_poi = poi.get('latitud')
                lng_poi = poi.get('longitud')
                
                if lat_poi is not None and lng_poi is not None:
                    try:
                        distancia_km = self._calculate_distance(
                            lat_origen, lng_origen, 
                            float(lat_poi), float(lng_poi)
                        )
                        
                        # Bonus inversamente proporcional a la distancia
                        # POIs a menos de 2km: bonus máximo (0.2)
                        # POIs a más de 10km: bonus mínimo (0.0)
                        if distancia_km <= 2.0:
                            score += 0.2
                        elif distancia_km <= 5.0:
                            score += 0.15
                        elif distancia_km <= 10.0:
                            score += 0.1
                        # Sin bonus para POIs muy lejanos
                        
                        poi['distancia_origen_km'] = round(distancia_km, 2)
                        
                    except (ValueError, TypeError):
                        poi['distancia_origen_km'] = None
                else:
                    poi['distancia_origen_km'] = None
            else:
                poi['distancia_origen_km'] = None
            
            # Garantizar score mínimo
            score = max(score, 0.1)
            
            poi['score_personalizado'] = round(score, 3)
            scored_pois.append(poi)
        
        # Ordenar por score
        scored_pois.sort(key=lambda x: x['score_personalizado'], reverse=True)
        
        logger.info(f"Scores calculados para {len(scored_pois)} POIs")
        if lat_origen is not None and lng_origen is not None:
            pois_con_distancia = [p for p in scored_pois if p.get('distancia_origen_km') is not None]
            if pois_con_distancia:
                dist_promedio = sum(p['distancia_origen_km'] for p in pois_con_distancia) / len(pois_con_distancia)
                logger.info(f"Distancia promedio desde origen: {dist_promedio:.2f}km")
        
        return scored_pois
    
    def _calculate_category_cluster_bonus(self, categoria: str, user_prefs: Dict) -> float:
        """
        Calcular bonus basado en clustering jerárquico de categorías
        Usa relaciones entre categorías detectadas por clustering
        """
        try:
            if 'hierarchical' not in self.models:
                return 0.0
                
            hierarchical_results = self.models['hierarchical']['results']
            
            # Buscar categorías relacionadas en el clustering jerárquico
            if 'category_relationships' in hierarchical_results:
                user_categories = user_prefs.get('categorias_preferidas', [])
                
                for user_cat in user_categories:
                    if user_cat in hierarchical_results['category_relationships']:
                        related_categories = hierarchical_results['category_relationships'][user_cat]
                        
                        if categoria in related_categories:
                            # Bonus por categoría relacionada detectada por clustering
                            similarity_score = related_categories[categoria]
                            return similarity_score * 0.15  # Máximo 0.15 bonus
            
            return 0.0
            
        except Exception as e:
            logger.debug(f"Error calculando bonus clustering jerárquico: {e}")
            return 0.0
    
    def _calculate_user_profile_bonus(self, poi: Dict, user_cluster_profile: int) -> float:
        """
        Calcular bonus basado en el perfil de cluster del usuario (K-means)
        Usa características del POI que coinciden con el perfil de usuario
        """
        try:
            bonus = 0.0
            categoria = poi.get('categoria', '')
            
            # Bonuses específicos por cluster de perfil de usuario
            if user_cluster_profile == 0:  # Cluster foodie
                if categoria == 'Gastronomía':
                    bonus += 0.25
                    # Bonus adicional por características gastronómicas
                    if poi.get('tipo_cocina'):
                        bonus += 0.05
                    if poi.get('tipo_ambiente') == 'Elegante':
                        bonus += 0.05
                        
            elif user_cluster_profile == 1:  # Cluster cultural
                if categoria in ['Museos', 'Monumentos', 'Lugares Históricos']:
                    bonus += 0.25
                    # Bonus adicional por características culturales
                    if poi.get('tiene_web'):  # Lugares culturales suelen tener buena información
                        bonus += 0.05
                        
            elif user_cluster_profile == 2:  # Cluster entretenimiento
                if categoria == 'Entretenimiento':
                    bonus += 0.25
                    # Bonus por características de entretenimiento
                    if not poi.get('es_gratuito'):  # Entretenimiento de pago suele ser de mejor calidad
                        bonus += 0.05
            
            return bonus
            
        except Exception as e:
            logger.debug(f"Error calculando bonus perfil de usuario: {e}")
            return 0.0

    def calculate_event_scores(self, eventos: List[Dict], user_prefs: Dict) -> List[Dict]:
        """
        Calcular scores personalizados para eventos
        MEJORADO: Mayor prioridad para eventos y mejor scoring
        """
        logger.info("Calculando scores para eventos...")
        
        if not eventos:
            return []
        
        scored_events = []
        
        for evento in eventos:
            score = 0.0
            
            # Score base más alto para eventos (son únicos y temporales)
            score += 1.0  # Aumentado de 0.8 a 1.0 para dar más prioridad
            
            # Bonus por ser gratuito (la mayoría de eventos lo son)
            if evento.get('es_gratuito'):
                score += 0.2  # Aumentado de 0.15
            
            # Bonus por zona preferida
            zona_pref = user_prefs.get('zona_preferida', '')
            barrio_evento = evento.get('barrio', '') or ''
            if zona_pref and zona_pref.lower() in barrio_evento.lower():
                score += 0.3  # Aumentado de 0.2
            
            # NUEVO: Bonus por categorías preferidas del usuario (desde BD)
            # Los eventos son considerados una categoría especial "Eventos"
            categorias_preferidas = user_prefs.get('categorias_preferidas', [])
            if categorias_preferidas and 'Eventos' in categorias_preferidas:
                score += 0.6  # Bonus MUY ALTO si el usuario prefiere eventos
                logger.debug(f"Bonus categoría 'Eventos' aplicado a evento {evento.get('nombre')}")
            elif categorias_preferidas:
                # Bonus menor si no prefiere eventos específicamente pero tiene otras preferencias
                score += 0.2  # Bonus estándar para eventos cuando hay otras preferencias
            
            # Bonus por duración del evento (eventos de varios días son más valiosos)
            duracion_dias = evento.get('duracion_dias', 1)
            if duracion_dias and duracion_dias > 1:
                score += 0.15  # Aumentado de 0.1
            
            # Bonus general para eventos gratuitos (suelen ser gratuitos)
            if evento.get('es_gratuito'):
                score += 0.2  # Aumentado de 0.15
            
            # Bonus por categoría cultural para ciertos tipos de compañía
            categoria_evento = evento.get('categoria', '').lower()
            if user_prefs.get('tipo_compania') == 'familia' and 'cultural' in categoria_evento:
                score += 0.2  # Aumentado de 0.15
            
            # Bonus por proximidad temporal (eventos más cercanos son más relevantes)
            fecha_inicio = evento.get('fecha_inicio')
            if fecha_inicio:
                try:
                    # Convertir fecha si es string
                    if isinstance(fecha_inicio, str):
                        from datetime import datetime as dt
                        fecha_evento = dt.strptime(fecha_inicio, '%Y-%m-%d').date()
                    else:
                        fecha_evento = fecha_inicio
                    
                    fecha_visita = user_prefs.get('fecha_visita', datetime.now().date().isoformat())
                    if isinstance(fecha_visita, str):
                        fecha_visita = dt.strptime(fecha_visita, '%Y-%m-%d').date()
                    
                    dias_diferencia = abs((fecha_evento - fecha_visita).days)
                    if dias_diferencia <= 3:
                        score += 0.3  # Aumentado de 0.2 - Muy cercano
                    elif dias_diferencia <= 7:
                        score += 0.15  # Aumentado de 0.1 - Cercano
                except:
                    pass  # Si hay error, no aplicar bonus temporal
            
            # Bonus por tener URL (eventos con más información son más confiables)
            if evento.get('url_evento'):
                score += 0.1
            
            # NUEVO: Bonus por proximidad al punto de origen (mismo que POIs)
            lat_origen = user_prefs.get('latitud_origen')
            lng_origen = user_prefs.get('longitud_origen')
            
            if lat_origen is not None and lng_origen is not None:
                lat_evento = evento.get('latitud')
                lng_evento = evento.get('longitud')
                
                if lat_evento is not None and lng_evento is not None:
                    try:
                        distancia_km = self._calculate_distance(
                            lat_origen, lng_origen, 
                            float(lat_evento), float(lng_evento)
                        )
                        
                        # Bonus inversamente proporcional a la distancia (mismo sistema que POIs)
                        if distancia_km <= 2.0:
                            score += 0.2
                        elif distancia_km <= 5.0:
                            score += 0.15
                        elif distancia_km <= 10.0:
                            score += 0.1
                        # Sin bonus para eventos muy lejanos
                        
                        evento['distancia_origen_km'] = round(distancia_km, 2)
                        
                    except (ValueError, TypeError):
                        evento['distancia_origen_km'] = None
                else:
                    evento['distancia_origen_km'] = None
            else:
                evento['distancia_origen_km'] = None
            
            # Garantizar score mínimo
            score = max(score, 0.8)  # Aumentado de 0.5 - Eventos tienen score mínimo más alto
            
            evento['score_personalizado'] = round(score, 3)
            evento['item_type'] = 'evento'  # Asegurar que esté marcado
            scored_events.append(evento)
        
        # Ordenar por score
        scored_events.sort(key=lambda x: x['score_personalizado'], reverse=True)
        
        logger.info(f"Scores calculados para {len(scored_events)} eventos")
        return scored_events
    
    def optimize_route_with_events(self, items_selected: List[Dict], duracion_horas: int, hora_inicio: str = '10:00', lat_origen: float = None, lng_origen: float = None, user_prefs: Dict = None) -> List[Dict]:
        """
        Optimizar ruta incluyendo eventos con consideraciones temporales y geográficas
        MEJORADO: Considera horario de inicio real del itinerario y punto de origen
        """
        logger.info(f"Optimizando ruta con POIs y eventos para {duracion_horas}h desde {hora_inicio}...")
        logger.info(f"Punto de origen: lat={lat_origen}, lng={lng_origen}")
        
        if not items_selected:
            return []
        
        # Separar POIs y eventos
        pois = [item for item in items_selected if item.get('item_type') != 'evento']
        eventos = [item for item in items_selected if item.get('item_type') == 'evento']
        
        logger.info(f"Optimizando: {len(pois)} POIs y {len(eventos)} eventos")
        
        # Convertir hora de inicio a entero
        try:
            hora_inicio_int = int(hora_inicio.split(':')[0])
        except (ValueError, AttributeError):
            hora_inicio_int = 10  # Default 10:00 AM
        
        # Crear itinerario inicial
        itinerario = []
        max_actividades = min(duracion_horas // 2, 10)  # Más actividades posibles
        
        # PASO 1: Optimizar eventos geográficamente ANTES de programar horarios
        eventos_insertados = 0
        eventos_programados = []
        
        # Optimizar eventos por proximidad al origen (igual que POIs)
        eventos_optimizados = self._optimize_events_geographically(eventos[:3], lat_origen, lng_origen)
        
        for evento in eventos_optimizados:
            if eventos_insertados >= max_actividades // 3:  # No más del 33% eventos
                break
                
            # Usar horario real del evento si está disponible
            hora_evento = self._extract_event_time(evento)
            if hora_evento is None:
                # Distribuir eventos a lo largo del día
                hora_evento = hora_inicio_int + (eventos_insertados * 2)  # Cada 2 horas
            
            # Verificar que el evento no sea muy tarde
            if hora_evento >= 20:  # No después de las 8 PM
                continue
                
            actividad = self._create_activity_from_item(evento, hora_evento, 120, eventos_insertados + 1)
            eventos_programados.append(actividad)
            eventos_insertados += 1
        
        # PASO 2: Optimizar POIs geográficamente desde el punto de origen
        pois_optimizados = self._optimize_geographic_route(pois, max_actividades - eventos_insertados, lat_origen, lng_origen)
        
        # PASO 3: Intercalar eventos y POIs optimizando horarios
        itinerario_final = self._merge_events_and_pois_improved(
            eventos_programados, pois_optimizados, duracion_horas, hora_inicio_int, user_prefs
        )
        
        logger.info(f"Ruta optimizada: {len(itinerario_final)} actividades ({eventos_insertados} eventos)")
        return itinerario_final
    
    def _optimize_events_geographically(self, eventos: List[Dict], lat_origen: float = None, lng_origen: float = None) -> List[Dict]:
        """
        Optimizar eventos considerando horarios fijos y optimización geográfica
        
        ESTRATEGIA HÍBRIDA:
        1. Eventos con hora_inicio fija: Se colocan en orden cronológico
        2. Eventos flexibles (sin hora_inicio): Se optimizan geográficamente
        3. Se evitan conflictos de horarios
        """
        if not eventos:
            return []

        logger.info(f"Optimizando {len(eventos)} eventos (híbrido: horarios fijos + geográfico)")

        # Separar eventos por tipo de horario
        eventos_fijos = []      # Con hora_inicio específica
        eventos_flexibles = []  # Sin hora_inicio (pueden optimizarse)

        for evento in eventos:
            hora_inicio = evento.get('hora_inicio')
            if hora_inicio is not None:
                # Evento con horario fijo
                try:
                    if isinstance(hora_inicio, str):
                        if ':' in hora_inicio:
                            hora = int(hora_inicio.split(':')[0])
                        else:
                            hora = int(hora_inicio)
                    else:
                        hora = int(hora_inicio)
                    
                    evento['hora_programada'] = hora
                    eventos_fijos.append(evento)
                    logger.info(f"Evento FIJO: {evento['nombre']} a las {hora_inicio}")
                except (ValueError, TypeError):
                    # Si hay error parsing, tratarlo como flexible
                    eventos_flexibles.append(evento)
            else:
                # Evento flexible
                eventos_flexibles.append(evento)

        logger.info(f"Eventos con horario fijo: {len(eventos_fijos)}")
        logger.info(f"Eventos flexibles: {len(eventos_flexibles)}")

        # 1. ORDENAR EVENTOS FIJOS POR HORARIO
        eventos_fijos.sort(key=lambda x: x.get('hora_programada', 24))

        # 2. OPTIMIZAR EVENTOS FLEXIBLES GEOGRÁFICAMENTE
        eventos_flexibles_optimizados = []
        if eventos_flexibles and lat_origen is not None and lng_origen is not None:
            # Filtrar eventos flexibles con coordenadas válidas
            eventos_con_coords = []
            for evento in eventos_flexibles:
                lat = evento.get('latitud')
                lng = evento.get('longitud')
                if lat is not None and lng is not None:
                    try:
                        evento['lat_float'] = float(lat)
                        evento['lng_float'] = float(lng)
                        eventos_con_coords.append(evento)
                    except (ValueError, TypeError):
                        eventos_flexibles_optimizados.append(evento)  # Sin coords válidas

            # Optimizar geográficamente los que tienen coordenadas
            if eventos_con_coords:
                eventos_scored = []
                for evento in eventos_con_coords:
                    distancia = self._calculate_distance(
                        lat_origen, lng_origen,
                        evento['lat_float'], evento['lng_float']
                    )
                    
                    # Ponderar distancia vs score (70% distancia, 30% score)
                    score_normalizado = evento.get('score_personalizado', 0) / 2.0
                    factor_combinado = (distancia * 0.7) - (score_normalizado * 0.3)
                    
                    evento['factor_optimizacion'] = factor_combinado
                    eventos_scored.append(evento)

                # Ordenar por factor combinado (menor es mejor)
                eventos_con_coords_optimizados = sorted(eventos_scored, key=lambda x: x['factor_optimizacion'])
                eventos_flexibles_optimizados.extend(eventos_con_coords_optimizados)
                logger.info(f"Optimizados geográficamente: {len(eventos_con_coords_optimizados)} eventos flexibles")
        else:
            # Sin coordenadas de origen, ordenar por score
            eventos_flexibles_optimizados = sorted(eventos_flexibles, key=lambda x: x.get('score_personalizado', 0), reverse=True)

        # 3. COMBINAR ESTRATÉGICAMENTE
        # Priorizar eventos fijos por su horario, intercalar flexibles optimizados
        resultado_final = []
        
        # Si hay eventos fijos, respetamos sus horarios
        if eventos_fijos:
            resultado_final.extend(eventos_fijos)
            # Intercalar eventos flexibles si quedan espacios
            resultado_final.extend(eventos_flexibles_optimizados)
        else:
            # Solo eventos flexibles, usar optimización geográfica pura
            resultado_final = eventos_flexibles_optimizados

        logger.info(f"Optimización híbrida completada: {len(resultado_final)} eventos ordenados")
        return resultado_final
    
    def _extract_event_time(self, evento: Dict) -> int:
        """
        Extraer hora del evento si está disponible
        """
        hora_inicio = evento.get('hora_inicio')
        if hora_inicio:
            try:
                if isinstance(hora_inicio, str):
                    # Formatos posibles: "10:00", "10:00:00", "10"
                    if ':' in hora_inicio:
                        hour = int(hora_inicio.split(':')[0])
                    else:
                        hour = int(hora_inicio)
                    
                    # Validar rango
                    if 8 <= hour <= 22:
                        return hour
            except (ValueError, TypeError):
                pass
        return None
    
    def _optimize_geographic_route(self, pois: List[Dict], max_pois: int, lat_origen: float = None, lng_origen: float = None) -> List[Dict]:
        """
        Optimizar POIs por proximidad geográfica usando algoritmo greedy + CLUSTERING DBSCAN
        MEJORADO: Usa clusters DBSCAN para optimización de rutas inteligente
        """
        if not pois or max_pois <= 0:
            return []
        
        # Filtrar POIs con coordenadas válidas
        pois_con_coords = []
        for poi in pois:
            lat = poi.get('latitud')
            lng = poi.get('longitud')
            if lat is not None and lng is not None:
                try:
                    poi['lat_float'] = float(lat)
                    poi['lng_float'] = float(lng)
                    pois_con_coords.append(poi)
                except (ValueError, TypeError):
                    pass
        
        if not pois_con_coords:
            # Si no hay coordenadas, usar los primeros POIs
            return pois[:max_pois]
        
        # 🆕 OPTIMIZACIÓN CON CLUSTERING DBSCAN
        if 'dbscan' in self.models:
            try:
                clustered_pois = self._group_pois_by_dbscan_clusters(pois_con_coords)
                if clustered_pois:
                    logger.info(f"Usando clustering DBSCAN para optimizar ruta: {len(clustered_pois)} grupos")
                    return self._optimize_route_within_clusters(clustered_pois, max_pois, lat_origen, lng_origen)
            except Exception as e:
                logger.warning(f"Error usando clustering DBSCAN, fallback a algoritmo greedy: {e}")
        
        # Fallback: Algoritmo greedy tradicional
        return self._optimize_route_greedy_traditional(pois_con_coords, max_pois, lat_origen, lng_origen)
    
    def _group_pois_by_dbscan_clusters(self, pois: List[Dict]) -> Optional[Dict]:
        """
        Agrupar POIs por clusters DBSCAN para optimización de ruta
        """
        try:
            dbscan_results = self.models['dbscan']['results']
            
            if 'poi_clusters' not in dbscan_results:
                return None
            
            # Agrupar POIs por cluster DBSCAN
            clusters = {}
            noise_pois = []
            poi_clusters = dbscan_results['poi_clusters']
            
            # Manejar tanto formato dict como list para poi_clusters
            if isinstance(poi_clusters, dict):
                # Formato diccionario: {poi_id: cluster_id}
                for poi in pois:
                    poi_id = poi.get('poi_id')
                    if poi_id and str(poi_id) in poi_clusters:
                        cluster_id = poi_clusters[str(poi_id)]
                        
                        if cluster_id == -1:  # Ruido en DBSCAN
                            noise_pois.append(poi)
                        else:
                            if cluster_id not in clusters:
                                clusters[cluster_id] = []
                            clusters[cluster_id].append(poi)
                    else:
                        noise_pois.append(poi)
            
            elif isinstance(poi_clusters, list):
                # Formato lista: [{poi_id: ..., cluster_id: ...}, ...]
                # Crear un diccionario temporal para búsqueda rápida
                poi_cluster_map = {}
                for item in poi_clusters:
                    if isinstance(item, dict):
                        poi_id = item.get('poi_id')
                        cluster_id = item.get('cluster_id', item.get('cluster'))
                        if poi_id is not None and cluster_id is not None:
                            poi_cluster_map[str(poi_id)] = cluster_id
                
                # Agrupar POIs usando el mapa
                for poi in pois:
                    poi_id = poi.get('poi_id')
                    if poi_id and str(poi_id) in poi_cluster_map:
                        cluster_id = poi_cluster_map[str(poi_id)]
                        
                        if cluster_id == -1:  # Ruido en DBSCAN
                            noise_pois.append(poi)
                        else:
                            if cluster_id not in clusters:
                                clusters[cluster_id] = []
                            clusters[cluster_id].append(poi)
                    else:
                        noise_pois.append(poi)
            
            # Ordenar clusters por número de POIs (priorizar clusters densos)
            sorted_clusters = sorted(clusters.items(), key=lambda x: len(x[1]), reverse=True)
            
            return {
                'clusters': dict(sorted_clusters),
                'noise': noise_pois,
                'total_clusters': len(clusters)
            }
            
        except Exception as e:
            logger.warning(f"Error agrupando POIs por DBSCAN: {e}")
            return None
    
    def _optimize_route_within_clusters(self, clustered_pois: Dict, max_pois: int, lat_origen: float = None, lng_origen: float = None) -> List[Dict]:
        """
        Optimizar ruta usando clusters DBSCAN: priorizar POIs del mismo cluster
        """
        ruta_optimizada = []
        pois_por_cluster = clustered_pois['clusters']
        noise_pois = clustered_pois['noise']
        
        # Estrategia: Seleccionar POIs principalmente de 1-2 clusters principales
        clusters_a_usar = list(pois_por_cluster.keys())[:2]  # Máximo 2 clusters principales
        
        for cluster_id in clusters_a_usar:
            cluster_pois = pois_por_cluster[cluster_id]
            
            # Optimizar POIs dentro del cluster usando algoritmo greedy
            cluster_optimizado = self._optimize_route_greedy_traditional(
                cluster_pois, 
                min(max_pois - len(ruta_optimizada), len(cluster_pois)), 
                lat_origen, 
                lng_origen
            )
            
            ruta_optimizada.extend(cluster_optimizado)
            logger.info(f"Cluster {cluster_id}: {len(cluster_optimizado)} POIs agregados")
            
            if len(ruta_optimizada) >= max_pois:
                break
        
        # Completar con POIs de ruido si es necesario
        if len(ruta_optimizada) < max_pois and noise_pois:
            remaining_slots = max_pois - len(ruta_optimizada)
            noise_optimizado = self._optimize_route_greedy_traditional(
                noise_pois, remaining_slots, lat_origen, lng_origen
            )
            ruta_optimizada.extend(noise_optimizado)
            logger.info(f"Ruido: {len(noise_optimizado)} POIs agregados")
        
        return ruta_optimizada[:max_pois]
    
    def _optimize_route_greedy_traditional(self, pois: List[Dict], max_pois: int, lat_origen: float = None, lng_origen: float = None) -> List[Dict]:
        """
        Algoritmo greedy tradicional para optimización de rutas
        """
        if not pois or max_pois <= 0:
            return []
        
        # Algoritmo greedy para ruta más corta desde punto de origen
        ruta_optimizada = []
        pois_disponibles = pois[:]
        
        # Si tenemos punto de origen, empezar desde el POI más cercano al origen
        if lat_origen is not None and lng_origen is not None:
            logger.debug(f"Iniciando ruta desde origen: lat={lat_origen}, lng={lng_origen}")
            
            # Encontrar el POI más cercano al punto de origen
            mejor_poi = None
            menor_distancia = float('inf')
            
            for poi in pois_disponibles:
                distancia = self._calculate_distance(
                    lat_origen, lng_origen,
                    poi['lat_float'], poi['lng_float']
                )
                
                # Ponderar distancia vs score (70% distancia, 30% score)
                score_normalizado = poi.get('score_personalizado', 0) / 2.0
                factor_combinado = (distancia * 0.7) - (score_normalizado * 0.3)
                
                if factor_combinado < menor_distancia:
                    menor_distancia = factor_combinado
                    mejor_poi = poi
            
            if mejor_poi:
                actual = mejor_poi
                pois_disponibles.remove(actual)
                ruta_optimizada.append(actual)
            else:
                # Fallback: empezar con el POI con mejor score
                pois_disponibles.sort(key=lambda x: x.get('score_personalizado', 0), reverse=True)
                actual = pois_disponibles.pop(0)
                ruta_optimizada.append(actual)
        else:
            # Sin punto de origen: empezar con el POI con mejor score
            pois_disponibles.sort(key=lambda x: x.get('score_personalizado', 0), reverse=True)
            actual = pois_disponibles.pop(0)
            ruta_optimizada.append(actual)
        
        # Añadir POIs más cercanos iterativamente
        while len(ruta_optimizada) < max_pois and pois_disponibles:
            lat_actual = actual['lat_float']
            lng_actual = actual['lng_float']
            
            # Encontrar el POI más cercano
            mejor_poi = None
            menor_distancia = float('inf')
            
            for poi in pois_disponibles:
                distancia = self._calculate_distance(
                    lat_actual, lng_actual,
                    poi['lat_float'], poi['lng_float']
                )
                
                # Ponderar distancia vs score (70% distancia, 30% score)
                score_normalizado = poi.get('score_personalizado', 0) / 2.0  # Normalizar score
                factor_combinado = (distancia * 0.7) - (score_normalizado * 0.3)
                
                if factor_combinado < menor_distancia:
                    menor_distancia = factor_combinado
                    mejor_poi = poi
            
            if mejor_poi:
                ruta_optimizada.append(mejor_poi)
                pois_disponibles.remove(mejor_poi)
                actual = mejor_poi
        
        logger.info(f"Ruta geográfica optimizada: {len(ruta_optimizada)} POIs")
        return ruta_optimizada
    
    def _calculate_distance(self, lat1: float, lng1: float, lat2: float, lng2: float) -> float:
        """
        Calcular distancia entre dos puntos usando fórmula haversine simplificada
        """
        import math
        
        # Convertir grados a radianes
        lat1_rad = math.radians(lat1)
        lng1_rad = math.radians(lng1)
        lat2_rad = math.radians(lat2)
        lng2_rad = math.radians(lng2)
        
        # Diferencias
        dlat = lat2_rad - lat1_rad
        dlng = lng2_rad - lng1_rad
        
        # Fórmula haversine
        a = math.sin(dlat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlng/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radio de la Tierra en km
        r = 6371
        
        return r * c
    
    def _merge_events_and_pois(self, eventos: List[Dict], pois: List[Dict], duracion_horas: int) -> List[Dict]:
        """
        Combinar eventos y POIs en un itinerario temporal coherente
        """
        itinerario_final = []
        
        # Convertir POIs a actividades con horarios
        actividades_pois = []
        hora_actual = 9  # Empezar a las 9 AM
        
        for i, poi in enumerate(pois):
            # Determinar duración según categoría
            if poi.get('categoria') == 'Gastronomía':
                duracion = 90  # 1.5 horas para comer
                # Programar comidas en horarios apropiados
                if len(actividades_pois) == 0:
                    hora_actual = 12  # Primera comida al mediodía
                elif len(actividades_pois) >= 3:
                    hora_actual = max(hora_actual, 19)  # Cena
            else:
                duracion = 120  # 2 horas para visitas
            
            # Evitar conflictos con eventos ya programados
            while self._hour_conflicts_with_events(hora_actual, duracion, eventos):
                hora_actual += 1
                if hora_actual >= 20:  # No más allá de las 8 PM
                    break
            
            if hora_actual < 20:
                actividad = self._create_activity_from_item(poi, hora_actual, duracion, i + 1)
                actividades_pois.append(actividad)
                hora_actual += (duracion // 60) + 1  # +1 hora de buffer
        
        # Combinar eventos y POIs
        todas_actividades = eventos + actividades_pois
        
        # Ordenar por horario
        todas_actividades.sort(key=lambda x: x['horario_inicio'])
        
        # Reordenar números de orden
        for i, actividad in enumerate(todas_actividades):
            actividad['orden_visita'] = i + 1
        
        return todas_actividades
    
    def _merge_events_and_pois_improved(self, eventos: List[Dict], pois: List[Dict], duracion_horas: int, hora_inicio_int: int, user_prefs: Dict = None) -> List[Dict]:
        """
        Combinar eventos y POIs en un itinerario temporal coherente
        MEJORADO: Considera horario de inicio real del itinerario y horarios de comida SOLO si gastronomía está en preferencias
        """
        itinerario_final = []
        
        # Convertir POIs a actividades con horarios
        actividades_pois = []
        hora_actual = hora_inicio_int  # Empezar a la hora de inicio del itinerario
        
        # Separar gastronomía del resto para programación inteligente
        pois_gastronomia = [poi for poi in pois if poi.get('categoria') == 'Gastronomía']
        pois_otros = [poi for poi in pois if poi.get('categoria') != 'Gastronomía']
        
        logger.info(f"Programando actividades: {len(pois_gastronomia)} gastronomía, {len(pois_otros)} otros")
        
        # Verificar si gastronomía está en preferencias del usuario
        categorias_preferidas = user_prefs.get('categorias_preferidas', []) if user_prefs else []
        incluir_horarios_comida = 'Gastronomía' in categorias_preferidas
        
        # Identificar horarios de comida según duración del itinerario SOLO si gastronomía está en preferencias
        horarios_comida = []
        if incluir_horarios_comida:
            hora_fin_itinerario = hora_inicio_int + duracion_horas
            
            # Almuerzo (12:00-15:00)
            if hora_inicio_int <= 13 and hora_fin_itinerario >= 12:
                horarios_comida.append(('almuerzo', 13, 90))  # 13:00, 1.5 horas
            
            # Cena (19:00-21:00) - solo si el itinerario es suficientemente largo
            if duracion_horas >= 6 and hora_fin_itinerario >= 19:
                horarios_comida.append(('cena', 19, 90))  # 19:00, 1.5 horas
            
            logger.info(f"Horarios de comida identificados (gastronomía en preferencias): {[h[0] for h in horarios_comida]}")
        else:
            logger.info("No se programarán horarios específicos de comida - gastronomía no está en preferencias del usuario")
        
        # Programar gastronomía en horarios de comida SOLO si está en preferencias
        gastronomia_programada = 0
        if incluir_horarios_comida:
            for tipo_comida, hora_comida, duracion in horarios_comida:
                if gastronomia_programada < len(pois_gastronomia):
                    # Verificar que no conflicte con eventos
                    if not self._hour_conflicts_with_events(hora_comida, duracion, eventos):
                        poi_gastro = pois_gastronomia[gastronomia_programada]
                        actividad = self._create_activity_from_item(poi_gastro, hora_comida, duracion, len(actividades_pois) + 1)
                        actividad['tipo_actividad'] = f'Comida ({tipo_comida})'
                        actividades_pois.append(actividad)
                        gastronomia_programada += 1
                        logger.info(f"Gastronomía programada en {tipo_comida}: {poi_gastro.get('nombre')}")
        
        # Programar el resto de POIs en horarios disponibles
        pois_restantes = pois_gastronomia[gastronomia_programada:] + pois_otros
        hora_fin_itinerario = hora_inicio_int + duracion_horas
        
        for i, poi in enumerate(pois_restantes):
            # Determinar duración según categoría
            if poi.get('categoria') == 'Gastronomía':
                duracion = 90  # 1.5 horas para comer
            else:
                duracion = 120  # 2 horas para visitas
            
            # Encontrar horario disponible
            hora_disponible = self._find_available_hour(hora_actual, hora_fin_itinerario, duracion, eventos, actividades_pois)
            
            if hora_disponible and hora_disponible < hora_fin_itinerario:
                actividad = self._create_activity_from_item(poi, hora_disponible, duracion, len(actividades_pois) + 1)
                actividades_pois.append(actividad)
                hora_actual = hora_disponible + (duracion // 60) + 1  # +1 hora de buffer
        
        # Combinar eventos y POIs
        todas_actividades = eventos + actividades_pois
        
        # Ordenar por horario
        todas_actividades.sort(key=lambda x: x['horario_inicio'])
        
        # Reordenar números de orden
        for i, actividad in enumerate(todas_actividades):
            actividad['orden_visita'] = i + 1
        
        return todas_actividades
    
    def _find_available_hour(self, hora_inicio: int, hora_fin: int, duracion_min: int, eventos: List[Dict], actividades_programadas: List[Dict]) -> int:
        """Encontrar horario disponible evitando conflictos"""
        for hora in range(hora_inicio, hora_fin):
            if hora + (duracion_min // 60) > hora_fin:
                break
                
            # Verificar conflictos con eventos
            if self._hour_conflicts_with_events(hora, duracion_min, eventos):
                continue
            
            # Verificar conflictos con actividades ya programadas
            conflicto = False
            for act in actividades_programadas:
                act_inicio = int(act['horario_inicio'].split(':')[0])
                act_duracion = act.get('duracion_minutos', 120)
                act_fin = act_inicio + (act_duracion // 60)
                
                # Verificar solapamiento
                if not (hora + (duracion_min // 60) <= act_inicio or hora >= act_fin):
                    conflicto = True
                    break
            
            if not conflicto:
                return hora
        
        return None
    
    def _hour_conflicts_with_events(self, hora: int, duracion_min: int, eventos: List[Dict]) -> bool:
        """
        Verificar si una hora conflicta con eventos programados
        """
        hora_fin = hora + (duracion_min // 60)
        
        for evento in eventos:
            evento_inicio = int(evento['horario_inicio'].split(':')[0])
            evento_fin = int(evento['horario_fin'].split(':')[0])
            
            # Verificar solapamiento
            if not (hora_fin <= evento_inicio or hora >= evento_fin):
                return True
        
        return False
    
    def _select_balanced_items(self, pois_scored: List[Dict], eventos_scored: List[Dict], user_prefs: Dict) -> List[Dict]:
        """
        Seleccionar items balanceando categorías preferidas y eventos
        MEJORADO: Considera horario de inicio y balance realista + garantiza gastronomía si es preferida
        """
        logger.info("Seleccionando items balanceados...")
        
        categorias_preferidas = user_prefs.get('categorias_preferidas', [])
        duracion_horas = user_prefs.get('duracion_horas', user_prefs.get('duracion_preferida', 8))
        hora_inicio = user_prefs.get('hora_inicio', '10:00')
        
        # Calcular distribución objetivo más realista
        # Para 6 horas: 3-4 actividades principales + 1-2 eventos
        # Para 4 horas: 2-3 actividades principales + 1 evento
        # Para 8 horas: 4-5 actividades principales + 2-3 eventos
        if duracion_horas <= 4:
            total_items = 3
            max_eventos = 1
        elif duracion_horas <= 6:
            total_items = 4
            max_eventos = 1
        else:  # 8+ horas
            total_items = 5
            max_eventos = 2
        
        items_pois = total_items - max_eventos
        
        logger.info(f"Objetivo: {total_items} items total ({items_pois} POIs + {max_eventos} eventos) para {duracion_horas}h")
        
        items_seleccionados = []
        
        # PASO 1: Seleccionar eventos (tienen prioridad por ser únicos)
        eventos_elegidos = eventos_scored[:max_eventos]
        items_seleccionados.extend(eventos_elegidos)
        
        logger.info(f"Eventos seleccionados: {len(eventos_elegidos)}")
        
        # PASO 2: GARANTIZAR GASTRONOMÍA SOLO SI ESTÁ EN PREFERENCIAS DEL USUARIO
        pois_gastronomia = [poi for poi in pois_scored if poi.get('categoria') == 'Gastronomía']
        pois_no_gastronomia = [poi for poi in pois_scored if poi.get('categoria') != 'Gastronomía']

        gastronomia_incluida = False
        pois_finales = []

        # SOLO incluir gastronomía si está en categorías preferidas del usuario
        categorias_preferidas = user_prefs.get('categorias_preferidas', [])
        if categorias_preferidas and 'Gastronomía' in categorias_preferidas and pois_gastronomia:
            # Incluir al menos 1 gastronomía
            pois_finales.append(pois_gastronomia[0])
            gastronomia_incluida = True
            logger.info(f"Gastronomía garantizada incluida (está en preferencias): {pois_gastronomia[0].get('nombre')}")
            
            # Para itinerarios largos, incluir más gastronomía
            if duracion_horas >= 8 and len(pois_gastronomia) > 1:
                pois_finales.append(pois_gastronomia[1])
                logger.info(f"Segunda gastronomía incluida para itinerario largo")
        else:
            if not categorias_preferidas or 'Gastronomía' not in categorias_preferidas:
                logger.info(f"Gastronomía NO incluida - no está en preferencias del usuario: {categorias_preferidas}")        # PASO 3: Completar con otros POIs balanceando categorías preferidas
        pois_restantes_necesarios = items_pois - len(pois_finales)
        
        if categorias_preferidas and len(categorias_preferidas) > 1:
            # Múltiples categorías: distribuir equitativamente
            pois_por_categoria = self._distribute_pois_by_category_improved(
                pois_no_gastronomia if gastronomia_incluida else pois_scored, 
                categorias_preferidas, 
                pois_restantes_necesarios, 
                duracion_horas
            )
            pois_finales.extend(pois_por_categoria)
        else:
            # Una sola categoría o sin preferencias: tomar los mejores
            pois_disponibles = pois_no_gastronomia if gastronomia_incluida else pois_scored
            pois_finales.extend(pois_disponibles[:pois_restantes_necesarios])
        
        items_seleccionados.extend(pois_finales)
        
        logger.info(f"Items finales seleccionados: {len(items_seleccionados)} ({len([i for i in items_seleccionados if i.get('item_type') == 'evento'])} eventos)")
        
        # Log de categorías seleccionadas
        categorias_seleccionadas = {}
        for item in items_seleccionados:
            if item.get('item_type') != 'evento':
                cat = item.get('categoria', 'Otros')
                categorias_seleccionadas[cat] = categorias_seleccionadas.get(cat, 0) + 1
        
        logger.info(f"Distribución por categorías: {categorias_seleccionadas}")
        
        return items_seleccionados
    
    def _distribute_pois_by_category_improved(self, pois_scored: List[Dict], categorias_preferidas: List[str], total_pois: int, duracion_horas: int) -> List[Dict]:
        """
        Distribuir POIs equitativamente entre categorías preferidas
        MEJORADO: Considera duración y evita desbalance gastronómico
        """
        # Agrupar POIs por categoría
        pois_por_categoria = {}
        for poi in pois_scored:
            categoria = poi.get('categoria', 'Otros')
            if categoria not in pois_por_categoria:
                pois_por_categoria[categoria] = []
            pois_por_categoria[categoria].append(poi)
        
        # Calcular distribución por categoría
        categorias_disponibles = [cat for cat in categorias_preferidas if cat in pois_por_categoria]
        if not categorias_disponibles:
            # Si no hay POIs de las categorías preferidas, usar todos
            return pois_scored[:total_pois]
        
        # NUEVA LÓGICA: Distribución más inteligente
        pois_seleccionados = []
        
        if len(categorias_disponibles) == 2:
            # Dos categorías: distribuir según duración
            if duracion_horas <= 4:
                # Para 4 horas: 1-2 por categoría
                cat1, cat2 = categorias_disponibles[0], categorias_disponibles[1]
                pois_cat1 = min(2, len(pois_por_categoria[cat1]))
                pois_cat2 = total_pois - pois_cat1
                
                pois_seleccionados.extend(pois_por_categoria[cat1][:pois_cat1])
                pois_seleccionados.extend(pois_por_categoria[cat2][:pois_cat2])
                
            else:
                # Para 6+ horas: distribución más equilibrada
                pois_por_cat = total_pois // len(categorias_disponibles)
                pois_extra = total_pois % len(categorias_disponibles)
                
                for i, categoria in enumerate(categorias_disponibles):
                    cantidad = pois_por_cat + (1 if i < pois_extra else 0)
                    categoria_pois = pois_por_categoria[categoria][:cantidad]
                    pois_seleccionados.extend(categoria_pois)
        else:
            # Una categoría o más de 2: distribución estándar
            pois_por_cat = total_pois // len(categorias_disponibles)
            pois_extra = total_pois % len(categorias_disponibles)
            
            for i, categoria in enumerate(categorias_disponibles):
                cantidad = pois_por_cat + (1 if i < pois_extra else 0)
                categoria_pois = pois_por_categoria[categoria][:cantidad]
                pois_seleccionados.extend(categoria_pois)
        
        # Si no llegamos al total, completar con mejores POIs restantes
        if len(pois_seleccionados) < total_pois:
            pois_usados = set(poi['poi_id'] for poi in pois_seleccionados)
            pois_restantes = [poi for poi in pois_scored if poi['poi_id'] not in pois_usados]
            faltantes = total_pois - len(pois_seleccionados)
            pois_seleccionados.extend(pois_restantes[:faltantes])
        
        return pois_seleccionados
    
    def _create_activity_from_item(self, item: Dict, hora_inicio: int, duracion_minutos: int, orden: int) -> Dict:
        """
        Crear actividad formateada desde POI o evento
        """
        # Determinar tipo de actividad
        if item.get('item_type') == 'evento':
            tipo_actividad = 'Evento cultural'
            # Para eventos, intentar usar horarios reales si están disponibles
            fecha_inicio = item.get('fecha_inicio')
            if fecha_inicio:
                tipo_actividad = f"Evento - {fecha_inicio}"
        elif item.get('categoria') == 'Gastronomía':
            tipo_actividad = 'Comida'
        else:
            tipo_actividad = 'Visita cultural'
        
        hora_fin = hora_inicio + (duracion_minutos // 60)
        minutos_fin = duracion_minutos % 60
        
        actividad = {
            **item,
            'horario_inicio': f"{hora_inicio:02d}:00",
            'horario_fin': f"{hora_fin:02d}:{minutos_fin:02d}",
            'duracion_minutos': duracion_minutos,
            'tipo_actividad': tipo_actividad,
            'orden_visita': orden
        }
        
        return actividad
    
    def _find_free_time_slot(self, itinerario: List[Dict], hora_min: int, hora_max: int) -> int:
        """
        Encontrar un slot de tiempo libre en el itinerario
        """
        occupied_slots = []
        
        for actividad in itinerario:
            inicio = int(actividad['horario_inicio'].split(':')[0])
            fin_str = actividad['horario_fin'].split(':')
            fin = int(fin_str[0])
            if int(fin_str[1]) > 0:
                fin += 1  # Redondear hacia arriba si hay minutos
            
            occupied_slots.append((inicio, fin))
        
        # Buscar slot libre
        for hora in range(hora_min, hora_max - 1):  # -1 para dejar al menos 1 hora
            slot_libre = True
            for inicio_ocupado, fin_ocupado in occupied_slots:
                if not (hora + 2 <= inicio_ocupado or hora >= fin_ocupado):
                    slot_libre = False
                    break
            
            if slot_libre:
                return hora
        
        return None
    
    def generate_itinerary(self, user_id: int, request_data: Dict) -> Dict:
        """
        Generar itinerario personalizado completo incluyendo eventos
        """
        logger.info(f"Generando itinerario para usuario {user_id}")
        
        try:
            # 1. Obtener preferencias del usuario CON request_data para coordenadas
            user_prefs = self.get_user_preferences(user_id, request_data)
            
            # Combinar con request específico (EXCEPTO categorias_preferidas que siempre vienen de BD)
            for key, value in request_data.items():
                if value is not None and key != 'categorias_preferidas':  # NUNCA override categorías
                    user_prefs[key] = value
            
            # Log para verificar que categorías vienen de BD y zona se determina correctamente
            logger.info(f"Categorías preferidas (siempre de BD): {user_prefs.get('categorias_preferidas', [])}")
            logger.info(f"Zona determinada: {user_prefs.get('zona_preferida')} (origen: lat={request_data.get('latitud_origen')}, lng={request_data.get('longitud_origen')})")
            logger.info(f"Preferencias finales utilizadas: {user_prefs}")
            
            # 2. Filtrar POIs y eventos usando clusters
            filtered_data = self.filter_pois_and_events_by_clusters(user_prefs)
            pois_candidatos = filtered_data['pois']
            eventos_candidatos = filtered_data['eventos']
            
            if not pois_candidatos and not eventos_candidatos:
                return {
                    'error': 'No se encontraron POIs o eventos relevantes para tus preferencias',
                    'sugerencias': ['Ampliar zona de búsqueda', 'Cambiar categorías', 'Verificar fechas']
                }
            
            # 3. Calcular scores personalizados para POIs
            pois_scored = self.calculate_poi_scores(pois_candidatos, user_prefs)
            
            # 4. Calcular scores para eventos
            eventos_scored = self.calculate_event_scores(eventos_candidatos, user_prefs)
            
            # 5. Selección inteligente con balance de categorías y eventos
            items_seleccionados = self._select_balanced_items(
                pois_scored, eventos_scored, user_prefs
            )
            
            # 6. Optimizar ruta desde punto de origen
            hora_inicio = user_prefs.get('hora_inicio', '10:00')
            lat_origen = user_prefs.get('latitud_origen')
            lng_origen = user_prefs.get('longitud_origen')
            
            actividades = self.optimize_route_with_events(
                items_seleccionados, 
                user_prefs.get('duracion_horas', user_prefs.get('duracion_preferida', 8)),
                hora_inicio,
                lat_origen,
                lng_origen,
                user_prefs
            )
            
            if not actividades:
                return {
                    'error': 'No se pudo generar itinerario con los POIs y eventos disponibles'
                }
            
            # 7. Calcular estadísticas
            stats = self.calculate_itinerary_stats(actividades)
            
            # 8. Formatear respuesta
            itinerario = {
                'itinerario_id': f"it_{user_id}_{int(datetime.now().timestamp())}",
                'usuario_id': user_id,
                'fecha_generacion': datetime.now().isoformat(),
                'fecha_visita': request_data.get('fecha_visita', datetime.now().date().isoformat()),
                'preferencias_usadas': user_prefs,
                'actividades': actividades,
                'estadisticas': stats,
                'metadata': {
                    'total_pois_analizados': len(pois_candidatos),
                    'total_eventos_analizados': len(eventos_candidatos),
                    'eventos_incluidos': len([act for act in actividades if act.get('item_type') == 'evento']),
                    'algoritmos_usados': list(self.models.keys()),
                    'version_modelo': '1.2'
                }
            }
            
            # 9. Guardar itinerario (temporal y completo)
            self.save_itinerary(itinerario)
            # self.save_itinerary_to_operational_db(itinerario)
            
            eventos_en_itinerario = len([act for act in actividades if act.get('item_type') == 'evento'])
            logger.info(f"Itinerario generado exitosamente: {len(actividades)} actividades ({eventos_en_itinerario} eventos)")
            return itinerario
            
        except Exception as e:
            logger.error(f"Error generando itinerario: {e}")
            return {
                'error': 'Error interno del sistema',
                'details': str(e)
            }
    
    def calculate_itinerary_stats(self, actividades: List[Dict]) -> Dict:
        """Calcular estadísticas del itinerario"""
        if not actividades:
            return {}
        
        # Conteos por categoría
        categorias = {}
        for act in actividades:
            cat = act['categoria']
            categorias[cat] = categorias.get(cat, 0) + 1
        
        # Calcular distancias (simplificado)
        total_distance = 0
        if len(actividades) > 1:
            for i in range(len(actividades) - 1):
                # Distancia aproximada entre POIs consecutivos
                total_distance += 2.5  # km promedio
        
        # Calcular costo estimado
        costo_estimado = 'Medio'
        if any(act.get('es_gratuito') for act in actividades):
            costo_estimado = 'Bajo'
        elif len([act for act in actividades if act['categoria'] == 'Gastronomía']) > 2:
            costo_estimado = 'Alto'
        
        return {
            'total_actividades': len(actividades),
            'categorias': categorias,
            'duracion_total_horas': sum(act['duracion_minutos'] for act in actividades) / 60,
            'distancia_total_km': round(total_distance, 1),
            'costo_estimado': costo_estimado,
            'valoracion_promedio': round(
                sum(float(act.get('valoracion_promedio', 0)) for act in actividades) / len(actividades), 2
            )
        }
    
    def save_itinerary(self, itinerario: Dict):
        """Guardar itinerario en BD (temporal para clustering)"""
        cursor = self.conn.cursor()
        
        try:
            # Crear tabla si no existe
            create_table = """
            CREATE TABLE IF NOT EXISTS itinerarios_generados (
                id SERIAL PRIMARY KEY,
                itinerario_id VARCHAR(100) UNIQUE,
                usuario_id INTEGER,
                fecha_generacion TIMESTAMP,
                itinerario_json JSONB,
                activo BOOLEAN DEFAULT TRUE
            );
            """
            cursor.execute(create_table)
            
            # Insertar itinerario
            insert_query = """
            INSERT INTO itinerarios_generados 
            (itinerario_id, usuario_id, fecha_generacion, itinerario_json)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (itinerario_id) DO UPDATE SET
            fecha_generacion = EXCLUDED.fecha_generacion,
            itinerario_json = EXCLUDED.itinerario_json
            """
            
            cursor.execute(insert_query, (
                itinerario['itinerario_id'],
                itinerario['usuario_id'],
                datetime.now(),
                json.dumps(itinerario, default=str)
            ))
            
            self.conn.commit()
            logger.info(f"Itinerario guardado: {itinerario['itinerario_id']}")
            
        except Exception as e:
            self.conn.rollback()
            logger.error(f"Error guardando itinerario: {e}")
        finally:
            cursor.close()
    
    def save_itinerary_to_operational_db(self, itinerario: Dict):
        """
        Guardar itinerario completo en la BD operacional
        Incluye POIs y eventos en itinerario_actividades
        """
        if not hasattr(self, 'operational_conn') or not self.operational_conn:
            logger.warning("No hay conexión a BD operacional. Saltando guardado completo.")
            return
            
        cursor = self.operational_conn.cursor()
        
        try:
            # 1. Insertar itinerario principal
            insert_itinerario = """
            INSERT INTO itinerarios (
                usuario_id, nombre, descripcion, fecha_inicio, fecha_fin,
                estado, distancia_total_km, tiempo_estimado_horas
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            RETURNING id
            """
            
            cursor.execute(insert_itinerario, (
                itinerario['usuario_id'],
                f"Itinerario BAX {itinerario['itinerario_id']}",
                f"Itinerario generado automáticamente para {itinerario.get('parametros', {}).get('tipo_compania', 'usuario')}",
                itinerario.get('fecha_inicio', datetime.now().date()),
                itinerario.get('fecha_fin', datetime.now().date()),
                'planificado',
                itinerario.get('distancia_total_km', 0),
                itinerario.get('tiempo_total_horas', 0)
            ))
            
            itinerario_bd_id = cursor.fetchone()[0]
            logger.info(f"Itinerario BD creado con ID: {itinerario_bd_id}")
            
            # 2. Insertar actividades (POIs y eventos)
            insert_actividad = """
            INSERT INTO itinerario_actividades (
                itinerario_id, poi_id, evento_id, tipo_actividad,
                dia_visita, orden_en_dia, hora_inicio_planificada, hora_fin_planificada,
                tiempo_estimado_minutos, notas_planificacion
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            
            for i, actividad in enumerate(itinerario.get('actividades', []), 1):
                # Determinar si es POI o evento
                if actividad.get('item_type') == 'evento':
                    poi_id = None
                    evento_id = actividad.get('evento_id') or actividad.get('id')
                    tipo_actividad = 'evento'
                else:
                    poi_id = actividad.get('poi_id') or actividad.get('id')
                    evento_id = None
                    tipo_actividad = 'poi'
                
                # Extraer horarios
                horario_inicio = actividad.get('horario_inicio')
                horario_fin = actividad.get('horario_fin')
                
                cursor.execute(insert_actividad, (
                    itinerario_bd_id,
                    poi_id,
                    evento_id,
                    tipo_actividad,
                    1,  # dia_visita - por ahora todos en día 1
                    i,  # orden_en_dia
                    horario_inicio,
                    horario_fin,
                    actividad.get('duracion_minutos', 90),
                    f"{tipo_actividad.title()}: {actividad.get('nombre', 'Sin nombre')}"
                ))
            
            self.operational_conn.commit()
            logger.info(f"Itinerario completo guardado en BD operacional: {len(itinerario.get('actividades', []))} actividades")
            
        except Exception as e:
            self.operational_conn.rollback()
            logger.error(f"Error guardando itinerario completo: {e}")
        finally:
            cursor.close()
    
    def get_recommendations_for_poi(self, poi_id: int, limit: int = 5) -> List[Dict]:
        """
        Obtener recomendaciones similares para un POI específico
        Usa Collaborative Filtering
        """
        logger.info(f"Generando recomendaciones para POI {poi_id}")
        
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Buscar POI base
            query = """
            SELECT * FROM lugares_clustering 
            WHERE poi_id = %s
            """
            cursor.execute(query, (poi_id,))
            poi_base = cursor.fetchone()
            
            if not poi_base:
                return []
            
            # Buscar POIs similares por categoría y características
            similar_query = """
            SELECT 
                poi_id, nombre, categoria, barrio,
                valoracion_promedio, popularidad_score,
                tipo_cocina, tipo_ambiente
            FROM lugares_clustering 
            WHERE categoria = %s
            AND poi_id != %s
            ORDER BY popularidad_score DESC, valoracion_promedio DESC
            LIMIT %s
            """
            
            cursor.execute(similar_query, (poi_base['categoria'], poi_id, limit))
            similares = cursor.fetchall()
            
            return [dict(poi) for poi in similares]
            
        except Exception as e:
            logger.error(f"Error obteniendo recomendaciones: {e}")
            return []
        finally:
            cursor.close()

# Función principal para usar desde API Gateway
def generate_itinerary_request(user_id: int, request_data: Dict) -> Dict:
    """
    Función principal para generar itinerario
    Esta es la función que llamará el API Gateway
    """
    
    # Validar coordenadas obligatorias
    if 'latitud_origen' not in request_data or 'longitud_origen' not in request_data:
        return {
            'error': 'Las coordenadas de origen (latitud_origen, longitud_origen) son obligatorias'
        }
    
    if request_data['latitud_origen'] is None or request_data['longitud_origen'] is None:
        return {
            'error': 'Las coordenadas de origen no pueden ser null'
        }
    
    service = RecommendationService()
    
    try:
        service.connect_database()
        service.connect_operational_database()  # Conexión opcional
        service.load_ml_models()
        
        result = service.generate_itinerary(user_id, request_data)
        
        return result
        
    except Exception as e:
        logger.error(f"Error en servicio de recomendaciones: {e}")
        return {
            'error': 'Error interno del sistema',
            'details': str(e)
        }
    finally:
        service.disconnect_database()

# Función para actualización diaria (llamada por scraper)
def update_processor_database():
    """
    Actualizar BD Data Processor con nuevos datos del scraper
    Esta función se ejecutará diariamente después del scraper
    """
    logger.info("Iniciando actualización diaria de BD Data Processor...")
    
    try:
        # Importar ETL processor
        from etl_to_processor import ETLProcessor
        
        # Ejecutar ETL completo
        etl = ETLProcessor()
        etl.connect_databases()
        etl.create_processor_schema()
        etl.run_full_etl()
        etl.disconnect_databases()
        
        # Re-ejecutar clustering con nuevos datos
        from clustering_processor import ClusteringProcessor
        
        clustering = ClusteringProcessor(DatabaseConfig.PROCESSOR_DB)
        clustering.run_full_clustering()
        
        logger.info("Actualización diaria completada exitosamente")
        return {'status': 'success', 'message': 'BD actualizada'}
        
    except Exception as e:
        logger.error(f"Error en actualización diaria: {e}")
        return {'status': 'error', 'message': str(e)}
