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
    
    def filter_pois_and_events_by_clusters(self, user_prefs: Dict) -> Dict[str, List[Dict]]:
        """
        Filtrar POIs y eventos usando clusters geográficos y temáticos
        """
        logger.info("Filtrando POIs y eventos por clusters...")
        
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Construir filtros basados en preferencias
            categorias = user_prefs.get('categorias_preferidas', [])
            zona = user_prefs.get('zona_preferida', '')
            actividades_evitar = user_prefs.get('actividades_evitar', [])
            fecha_visita = user_prefs.get('fecha_visita', datetime.now().date().isoformat())
            
            # === OBTENER POIs ===
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
                RANDOM()
            LIMIT 100
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
            AND fecha_inicio >= CURRENT_DATE
            AND latitud IS NOT NULL 
            AND longitud IS NOT NULL
            """
            
            # Filtrar eventos por zona
            if zona and zona.strip():
                eventos_query += f" AND (barrio ILIKE '%{zona}%' OR barrio IS NULL)"
            
            eventos_query += """
            ORDER BY fecha_inicio ASC, RANDOM()
            LIMIT 50
            """
            
            cursor.execute(eventos_query)
            eventos_result = cursor.fetchall()
            
            # Procesar eventos para que tengan el formato esperado
            eventos = []
            for evento_row in eventos_result:
                evento = dict(evento_row)
                
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
        """
        logger.info("Calculando scores personalizados...")
        
        if not pois:
            return []
        
        scored_pois = []
        
        for poi in pois:
            score = 0.0
            
            # Score base aleatorio para simular popularidad (ya que no tenemos datos reales)
            import random
            score += random.uniform(0.3, 0.8)
            
            # Score por valoración (simulada ya que todas están en 0)
            valoracion = float(poi.get('valoracion_promedio', 0))
            if valoracion > 0:
                score += valoracion * 0.2
            else:
                # Simular valoración basada en categoría
                category_scores = {
                    'Gastronomía': 0.4,
                    'Museos': 0.35,
                    'Monumentos': 0.3,
                    'Lugares Históricos': 0.32,
                    'Entretenimiento': 0.38
                }
                score += category_scores.get(poi.get('categoria', ''), 0.3)
            
            # Bonus por características específicas
            if poi.get('tiene_web'):
                score += 0.1
            
            if poi.get('tiene_telefono'):
                score += 0.05
            
            if poi.get('es_gratuito'):
                score += 0.15
            
            # Bonus por zona preferida
            zona_pref = user_prefs.get('zona_preferida', '')
            barrio_poi = poi.get('barrio', '') or ''
            if zona_pref and zona_pref.lower() in barrio_poi.lower():
                score += 0.2
            
            # Bonus por tipo de compañía
            if user_prefs.get('tipo_compania') == 'pareja':
                if poi.get('categoria') == 'Gastronomía':
                    score += 0.15  # Gastronomía ideal para parejas
                elif poi.get('categoria') == 'Museos':
                    score += 0.1   # Museos también buenos para parejas
            
            # Bonus/penalización por presupuesto
            if user_prefs.get('presupuesto') == 'bajo':
                if poi.get('es_gratuito'):
                    score += 0.2  # Gran bonus para actividades gratuitas
                else:
                    score -= 0.1  # Penalización para actividades de pago
            elif user_prefs.get('presupuesto') == 'alto':
                if poi.get('categoria') == 'Gastronomía':
                    score += 0.1  # Bonus para gastronomía con presupuesto alto
            
            # Garantizar score mínimo
            score = max(score, 0.1)
            
            poi['score_personalizado'] = round(score, 3)
            scored_pois.append(poi)
        
        # Ordenar por score
        scored_pois.sort(key=lambda x: x['score_personalizado'], reverse=True)
        
        logger.info(f"Scores calculados para {len(scored_pois)} POIs")
        return scored_pois
    
    def calculate_event_scores(self, eventos: List[Dict], user_prefs: Dict) -> List[Dict]:
        """
        Calcular scores personalizados para eventos
        """
        logger.info("Calculando scores para eventos...")
        
        if not eventos:
            return []
        
        scored_events = []
        
        for evento in eventos:
            score = 0.0
            
            # Score base más alto para eventos (son únicos y temporales)
            score += 0.8
            
            # Bonus por ser gratuito (la mayoría de eventos lo son)
            if evento.get('es_gratuito'):
                score += 0.15
            
            # Bonus por zona preferida
            zona_pref = user_prefs.get('zona_preferida', '')
            barrio_evento = evento.get('barrio', '') or ''
            if zona_pref and zona_pref.lower() in barrio_evento.lower():
                score += 0.2
            
            # Bonus por duración del evento (eventos de varios días son más valiosos)
            duracion_dias = evento.get('duracion_dias', 1)
            if duracion_dias and duracion_dias > 1:
                score += 0.1
            
            # Bonus por presupuesto bajo (eventos suelen ser gratuitos)
            if user_prefs.get('presupuesto') == 'bajo':
                score += 0.25
            
            # Bonus por categoría cultural para ciertos tipos de compañía
            categoria_evento = evento.get('categoria', '').lower()
            if user_prefs.get('tipo_compania') == 'familia' and 'cultural' in categoria_evento:
                score += 0.15
            
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
                        score += 0.2  # Muy cercano
                    elif dias_diferencia <= 7:
                        score += 0.1  # Cercano
                except:
                    pass  # Si hay error, no aplicar bonus temporal
            
            # Garantizar score mínimo
            score = max(score, 0.5)  # Eventos tienen score mínimo más alto
            
            evento['score_personalizado'] = round(score, 3)
            evento['item_type'] = 'evento'  # Asegurar que esté marcado
            scored_events.append(evento)
        
        # Ordenar por score
        scored_events.sort(key=lambda x: x['score_personalizado'], reverse=True)
        
        logger.info(f"Scores calculados para {len(scored_events)} eventos")
        return scored_events
    
    def optimize_route_with_events(self, items_selected: List[Dict], duracion_horas: int) -> List[Dict]:
        """
        Optimizar ruta incluyendo eventos con consideraciones temporales
        """
        logger.info("Optimizando ruta con POIs y eventos...")
        
        if not items_selected:
            return []
        
        # Separar POIs y eventos
        pois = [item for item in items_selected if item.get('item_type') != 'evento']
        eventos = [item for item in items_selected if item.get('item_type') == 'evento']
        
        # Agrupar POIs por categoría
        categorias_pois = {}
        for poi in pois:
            cat = poi.get('categoria', 'General')
            if cat not in categorias_pois:
                categorias_pois[cat] = []
            categorias_pois[cat].append(poi)
        
        # Crear itinerario balanceado
        itinerario = []
        max_actividades = min(duracion_horas // 2, 8)  # 2 horas por actividad
        
        # Insertar eventos primero (tienen horarios específicos)
        eventos_insertados = 0
        for evento in eventos[:2]:  # Máximo 2 eventos por día
            hora_inicio = 10 + (eventos_insertados * 3)  # Espaciar eventos
            if hora_inicio >= 17:  # No después de las 17
                break
            
            actividad = self._create_activity_from_item(evento, hora_inicio, 120, eventos_insertados + 1)
            itinerario.append(actividad)
            eventos_insertados += 1
            max_actividades -= 1
        
        # Llenar con POIs
        if max_actividades > 0 and categorias_pois:
            categorias_list = list(categorias_pois.keys())
            actividades_agregadas = eventos_insertados
            
            for i in range(max_actividades):
                categoria_idx = i % len(categorias_list)
                categoria = categorias_list[categoria_idx]
                
                if categorias_pois[categoria]:
                    poi = categorias_pois[categoria].pop(0)
                    
                    # Encontrar hora libre (evitar conflictos con eventos)
                    hora_inicio = self._find_free_time_slot(itinerario, 9, 18)
                    if hora_inicio is None:
                        break
                    
                    # Determinar duración según categoría
                    if poi.get('categoria') == 'Gastronomía':
                        duracion = 90  # 1.5 horas para comer
                    else:
                        duracion = 120  # 2 horas para visitas
                    
                    actividad = self._create_activity_from_item(poi, hora_inicio, duracion, actividades_agregadas + 1)
                    itinerario.append(actividad)
                    actividades_agregadas += 1
        
        # Ordenar por horario
        itinerario.sort(key=lambda x: x['horario_inicio'])
        
        # Reordenar números de orden
        for i, actividad in enumerate(itinerario):
            actividad['orden_visita'] = i + 1
        
        logger.info(f"Ruta optimizada: {len(itinerario)} actividades ({eventos_insertados} eventos)")
        return itinerario
    
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
            # 1. Obtener preferencias del usuario
            user_prefs = self.get_user_preferences(user_id)
            
            # Combinar con request específico
            user_prefs.update(request_data)
            
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
            
            # 5. Combinar y seleccionar mejores items
            all_items = pois_scored + eventos_scored
            all_items.sort(key=lambda x: x['score_personalizado'], reverse=True)
            
            # Seleccionar mix balanceado (70% POIs, 30% eventos)
            total_items = min(12, len(all_items))
            max_eventos = min(4, len(eventos_scored))  # Máximo 4 eventos
            
            items_seleccionados = []
            eventos_agregados = 0
            
            for item in all_items:
                if len(items_seleccionados) >= total_items:
                    break
                
                if item.get('item_type') == 'evento':
                    if eventos_agregados < max_eventos:
                        items_seleccionados.append(item)
                        eventos_agregados += 1
                else:
                    items_seleccionados.append(item)
            
            # 6. Optimizar ruta
            actividades = self.optimize_route_with_events(items_seleccionados, user_prefs.get('duracion_preferida', 8))
            
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
                    'version_modelo': '1.1'
                }
            }
            
            # 9. Guardar itinerario (opcional)
            self.save_itinerary(itinerario)
            
            logger.info(f"Itinerario generado exitosamente: {len(actividades)} actividades ({eventos_agregados} eventos)")
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
