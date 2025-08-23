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
    
    def disconnect_database(self):
        """Desconectar de BD"""
        if self.conn:
            self.conn.close()
            logger.info("Desconectado de BD Data Processor")
    
    def load_ml_models(self):
        """Cargar modelos ML entrenados desde BD"""
        logger.info("Cargando modelos ML...")
        
        # Por ahora, no cargamos modelos específicos
        # Los clusters ya están aplicados en lugares_clustering
        logger.info("Usando clusters ya aplicados en lugares_clustering")
        
        # En el futuro, aquí cargaríamos modelos pickle guardados
        # Por ahora, los resultados de clustering están en clustering_results
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """
        Obtener preferencias del usuario desde BD Operacional
        En el futuro esto vendría del API Gateway
        """
        # Simulación: en realidad consultaría BD Operacional
        return {
            'categorias_preferidas': ['Museos', 'Gastronomía'],
            'zona_preferida': 'Palermo',
            'presupuesto': 'medio',
            'tipo_compania': 'pareja',
            'duracion_preferida': 8,  # horas
            'actividades_evitar': ['Entretenimiento']
        }
    
    def filter_pois_by_clusters(self, user_prefs: Dict) -> List[Dict]:
        """
        Filtrar POIs usando clusters geográficos y temáticos
        """
        logger.info("Filtrando POIs por clusters...")
        
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Construir query basada en preferencias
            categorias = user_prefs.get('categorias_preferidas', [])
            zona = user_prefs.get('zona_preferida', '')
            actividades_evitar = user_prefs.get('actividades_evitar', [])
            
            # Query base
            query = """
            SELECT 
                id, poi_id, nombre, categoria, subcategoria,
                latitud, longitud, barrio, comuna,
                valoracion_promedio, popularidad_score,
                tipo_cocina, tipo_ambiente,
                tiene_web, tiene_telefono, es_gratuito
            FROM lugares_clustering 
            WHERE latitud IS NOT NULL AND longitud IS NOT NULL
            """
            
            # Filtrar por categorías preferidas
            if categorias:
                categorias_sql = "', '".join(categorias)
                query += f" AND categoria IN ('{categorias_sql}')"
            
            # Filtrar por zona
            if zona:
                query += f" AND barrio ILIKE '%{zona}%'"
            
            # Excluir actividades no deseadas
            if actividades_evitar:
                evitar_sql = "', '".join(actividades_evitar)
                query += f" AND categoria NOT IN ('{evitar_sql}')"
            
            # Ordenar por relevancia
            query += """
            ORDER BY popularidad_score DESC, valoracion_promedio DESC
            LIMIT 100
            """
            
            cursor.execute(query)
            pois = cursor.fetchall()
            
            logger.info(f"POIs filtrados: {len(pois)}")
            return [dict(poi) for poi in pois]
            
        except Exception as e:
            logger.error(f"Error filtrando POIs: {e}")
            return []
        finally:
            cursor.close()
    
    def calculate_poi_scores(self, pois: List[Dict], user_prefs: Dict) -> List[Dict]:
        """
        Calcular scores personalizados para cada POI
        """
        logger.info("Calculando scores personalizados...")
        
        if not pois:
            return []
        
        scored_pois = []
        
        for poi in pois:
            score = 0.0
            
            # Score base por popularidad
            popularidad = float(poi.get('popularidad_score', 0))
            score += popularidad * 0.3
            
            # Score por valoración
            valoracion = float(poi.get('valoracion_promedio', 0))
            score += valoracion * 0.2
            
            # Bonus por características específicas
            if poi.get('tiene_web'):
                score += 0.1
            
            if poi.get('tiene_telefono'):
                score += 0.05
            
            if poi.get('es_gratuito'):
                score += 0.15
            
            # Bonus por zona preferida
            if user_prefs.get('zona_preferida') and user_prefs['zona_preferida'].lower() in poi.get('barrio', '').lower():
                score += 0.2
            
            # Bonus por tipo de compañía
            if user_prefs.get('tipo_compania') == 'pareja':
                if poi.get('tipo_ambiente') in ['romantico', 'intimo', 'elegante']:
                    score += 0.1
            
            # Penalización por presupuesto
            if user_prefs.get('presupuesto') == 'bajo' and not poi.get('es_gratuito'):
                score -= 0.1
            
            poi['score_personalizado'] = round(score, 3)
            scored_pois.append(poi)
        
        # Ordenar por score
        scored_pois.sort(key=lambda x: x['score_personalizado'], reverse=True)
        
        logger.info(f"Scores calculados para {len(scored_pois)} POIs")
        return scored_pois
    
    def optimize_route(self, pois_selected: List[Dict], duracion_horas: int) -> List[Dict]:
        """
        Optimizar ruta usando algoritmos de optimización
        """
        logger.info("Optimizando ruta...")
        
        if not pois_selected:
            return []
        
        # Agrupar POIs por categoría
        categorias = {}
        for poi in pois_selected:
            cat = poi['categoria']
            if cat not in categorias:
                categorias[cat] = []
            categorias[cat].append(poi)
        
        # Crear itinerario balanceado
        itinerario = []
        max_actividades = min(duracion_horas // 2, 8)  # 2 horas por actividad
        
        # Alternar entre categorías
        categorias_list = list(categorias.keys())
        for i in range(max_actividades):
            categoria_idx = i % len(categorias_list)
            categoria = categorias_list[categoria_idx]
            
            if categorias[categoria]:
                poi = categorias[categoria].pop(0)
                
                # Calcular horario sugerido
                hora_inicio = 9 + (i * 2)  # Empezar a las 9, cada 2 horas
                if hora_inicio >= 18:  # No después de las 18
                    break
                
                # Determinar duración según categoría
                if categoria == 'Gastronomía':
                    duracion = 90  # 1.5 horas para comer
                    tipo_actividad = 'Comida'
                else:
                    duracion = 120  # 2 horas para visitas
                    tipo_actividad = 'Visita cultural'
                
                actividad = {
                    **poi,
                    'horario_inicio': f"{hora_inicio:02d}:00",
                    'horario_fin': f"{hora_inicio + (duracion // 60):02d}:{duracion % 60:02d}",
                    'duracion_minutos': duracion,
                    'tipo_actividad': tipo_actividad,
                    'orden_visita': i + 1
                }
                
                itinerario.append(actividad)
        
        logger.info(f"Ruta optimizada: {len(itinerario)} actividades")
        return itinerario
    
    def generate_itinerary(self, user_id: int, request_data: Dict) -> Dict:
        """
        Generar itinerario personalizado completo
        """
        logger.info(f"Generando itinerario para usuario {user_id}")
        
        try:
            # 1. Obtener preferencias del usuario
            user_prefs = self.get_user_preferences(user_id)
            
            # Combinar con request específico
            user_prefs.update(request_data)
            
            # 2. Filtrar POIs usando clusters
            pois_candidatos = self.filter_pois_by_clusters(user_prefs)
            
            if not pois_candidatos:
                return {
                    'error': 'No se encontraron POIs relevantes para tus preferencias',
                    'sugerencias': ['Ampliar zona de búsqueda', 'Cambiar categorías']
                }
            
            # 3. Calcular scores personalizados
            pois_scored = self.calculate_poi_scores(pois_candidatos, user_prefs)
            
            # 4. Seleccionar mejores POIs
            pois_seleccionados = pois_scored[:12]  # Top 12
            
            # 5. Optimizar ruta
            actividades = self.optimize_route(pois_seleccionados, user_prefs.get('duracion_preferida', 8))
            
            if not actividades:
                return {
                    'error': 'No se pudo generar itinerario con los POIs disponibles'
                }
            
            # 6. Calcular estadísticas
            stats = self.calculate_itinerary_stats(actividades)
            
            # 7. Formatear respuesta
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
                    'algoritmos_usados': list(self.models.keys()),
                    'version_modelo': '1.0'
                }
            }
            
            # 8. Guardar itinerario (opcional)
            self.save_itinerary(itinerario)
            
            logger.info(f"Itinerario generado exitosamente: {len(actividades)} actividades")
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
        """Guardar itinerario en BD (opcional)"""
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
    service = RecommendationService()
    
    try:
        service.connect_database()
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
