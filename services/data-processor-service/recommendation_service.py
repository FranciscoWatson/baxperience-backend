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
        logger.info("Cargando modelos ML...")
        
        # Por ahora, no cargamos modelos específicos
        # Los clusters ya están aplicados en lugares_clustering
        logger.info("Usando clusters ya aplicados en lugares_clustering")
        
        # En el futuro, aquí cargaríamos modelos pickle guardados
        # Por ahora, los resultados de clustering están en clustering_results
    
    def get_user_preferences(self, user_id: int) -> Dict:
        """
        Obtener preferencias del usuario desde BD Operacional
        Lee las preferencias reales de la base de datos
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
                    'presupuesto': 'medio',
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
                    'presupuesto': 'medio',
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
            
            # Mapear tipo_viajero a zona preferida y presupuesto
            zona_preferida = 'Palermo'  # Default
            presupuesto = 'medio'       # Default
            tipo_compania = 'solo'      # Default
            
            if user_info[1]:  # tipo_viajero
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
                
                # Mapear presupuesto según tipo
                if 'low-cost' in tipo_lower:
                    presupuesto = 'bajo'
                elif 'foodie' in tipo_lower or 'gastrónomo' in tipo_lower:
                    presupuesto = 'alto'
                else:
                    presupuesto = 'medio'
                
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
                'presupuesto': presupuesto,
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
                'presupuesto': 'medio',
                'tipo_compania': 'pareja',
                'duracion_preferida': 8,
                'actividades_evitar': ['Entretenimiento']
            }
    
    def filter_pois_and_events_by_clusters(self, user_prefs: Dict) -> Dict[str, List[Dict]]:
        """
        Filtrar POIs y eventos usando clusters geográficos y temáticos
        CON SAMPLING BALANCEADO POR CATEGORÍA para itinerarios realistas
        """
        logger.info("Filtrando POIs y eventos por clusters...")
        
        cursor = self.conn.cursor(cursor_factory=RealDictCursor)
        
        try:
            # Construir filtros basados en preferencias
            categorias = user_prefs.get('categorias_preferidas', [])
            zona = user_prefs.get('zona_preferida', '')
            actividades_evitar = user_prefs.get('actividades_evitar', [])
            fecha_visita = user_prefs.get('fecha_visita', datetime.now().date().isoformat())
            
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
                        limit_categoria = 40  # Limitar gastronomía
                    else:
                        limit_categoria = 60  # Priorizar cultural/entretenimiento
                    
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
            
            # Filtros más flexibles para eventos
            # No filtrar por fecha para tener más eventos disponibles para testing
            # En producción se puede activar: AND fecha_inicio >= CURRENT_DATE - INTERVAL '7 days'
            
            # Filtrar eventos por categorías si están especificadas
            if categorias:
                # Mapear categorías de usuario a categorías de eventos
                categorias_eventos = []
                for cat in categorias:
                    if cat in ['Entretenimiento', 'Museos', 'Gastronomía']:
                        categorias_eventos.append('Entretenimiento')  # La mayoría son entretenimiento
                    elif cat in ['Lugares Históricos', 'Monumentos']:
                        categorias_eventos.append('Entretenimiento')  # También pueden incluir eventos culturales
                
                if categorias_eventos:
                    categorias_sql = "', '".join(set(categorias_eventos))
                    eventos_query += f" AND categoria_evento IN ('{categorias_sql}')"
            
            # Filtrar eventos por zona
            if zona and zona.strip():
                eventos_query += f" AND (barrio ILIKE '%{zona}%' OR barrio IS NULL)"
            
            eventos_query += """
            ORDER BY 
                CASE WHEN fecha_inicio IS NOT NULL THEN 0 ELSE 1 END,
                fecha_inicio ASC, 
                RANDOM()
            LIMIT 100
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
            if poi.get('es_gratuito') and user_prefs.get('presupuesto') == 'bajo':
                score += 0.2  # Más puntos si necesita bajo presupuesto
            
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
        Optimizar ruta incluyendo eventos con consideraciones temporales y geográficas
        """
        logger.info("Optimizando ruta con POIs y eventos...")
        
        if not items_selected:
            return []
        
        # Separar POIs y eventos
        pois = [item for item in items_selected if item.get('item_type') != 'evento']
        eventos = [item for item in items_selected if item.get('item_type') == 'evento']
        
        logger.info(f"Optimizando: {len(pois)} POIs y {len(eventos)} eventos")
        
        # Crear itinerario inicial
        itinerario = []
        max_actividades = min(duracion_horas // 2, 10)  # Más actividades posibles
        
        # PASO 1: Insertar eventos con sus horarios reales (si los tienen)
        eventos_insertados = 0
        eventos_programados = []
        
        for evento in eventos[:3]:  # Máximo 3 eventos por día
            if eventos_insertados >= max_actividades // 3:  # No más del 33% eventos
                break
                
            # Usar horario real del evento si está disponible
            hora_evento = self._extract_event_time(evento)
            if hora_evento is None:
                hora_evento = 10 + (eventos_insertados * 3)  # Distribuir si no hay horario
            
            if hora_evento >= 18:  # No después de las 18
                continue
                
            actividad = self._create_activity_from_item(evento, hora_evento, 120, eventos_insertados + 1)
            eventos_programados.append(actividad)
            eventos_insertados += 1
        
        # PASO 2: Optimizar POIs geográficamente
        pois_optimizados = self._optimize_geographic_route(pois, max_actividades - eventos_insertados)
        
        # PASO 3: Intercalar eventos y POIs optimizando horarios
        itinerario_final = self._merge_events_and_pois(eventos_programados, pois_optimizados, duracion_horas)
        
        logger.info(f"Ruta optimizada: {len(itinerario_final)} actividades ({eventos_insertados} eventos)")
        return itinerario_final
    
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
    
    def _optimize_geographic_route(self, pois: List[Dict], max_pois: int) -> List[Dict]:
        """
        Optimizar POIs por proximidad geográfica usando algoritmo greedy
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
        
        # Algoritmo greedy para ruta más corta
        ruta_optimizada = []
        pois_disponibles = pois_con_coords[:]
        
        # Empezar con el POI con mejor score
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
        """
        logger.info("Seleccionando items balanceados...")
        
        categorias_preferidas = user_prefs.get('categorias_preferidas', [])
        duracion_horas = user_prefs.get('duracion_preferida', 8)
        
        # Calcular distribución objetivo
        total_items = min(duracion_horas // 2 + 2, 12)  # Entre 4-12 items
        max_eventos = min(3, max(1, total_items // 4))  # 25% máximo eventos, mínimo 1
        items_pois = total_items - max_eventos
        
        logger.info(f"Objetivo: {total_items} items total ({items_pois} POIs + {max_eventos} eventos)")
        
        items_seleccionados = []
        
        # PASO 1: Seleccionar eventos (tienen prioridad por ser únicos)
        eventos_elegidos = eventos_scored[:max_eventos]
        items_seleccionados.extend(eventos_elegidos)
        
        logger.info(f"Eventos seleccionados: {len(eventos_elegidos)}")
        
        # PASO 2: Seleccionar POIs balanceando categorías preferidas
        if categorias_preferidas and len(categorias_preferidas) > 1:
            # Múltiples categorías: distribuir equitativamente
            pois_por_categoria = self._distribute_pois_by_category(
                pois_scored, categorias_preferidas, items_pois
            )
            items_seleccionados.extend(pois_por_categoria)
        else:
            # Una sola categoría o sin preferencias: tomar los mejores
            items_seleccionados.extend(pois_scored[:items_pois])
        
        logger.info(f"Items finales seleccionados: {len(items_seleccionados)} ({len([i for i in items_seleccionados if i.get('item_type') == 'evento'])} eventos)")
        
        return items_seleccionados
    
    def _distribute_pois_by_category(self, pois_scored: List[Dict], categorias_preferidas: List[str], total_pois: int) -> List[Dict]:
        """
        Distribuir POIs equitativamente entre categorías preferidas
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
        
        pois_por_cat = total_pois // len(categorias_disponibles)
        pois_extra = total_pois % len(categorias_disponibles)
        
        pois_seleccionados = []
        
        for i, categoria in enumerate(categorias_disponibles):
            # Asignar POIs base + extras a las primeras categorías
            cantidad = pois_por_cat + (1 if i < pois_extra else 0)
            categoria_pois = pois_por_categoria[categoria][:cantidad]
            pois_seleccionados.extend(categoria_pois)
            
            logger.info(f"Categoría '{categoria}': {len(categoria_pois)} POIs seleccionados")
        
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
            # 1. Obtener preferencias del usuario
            user_prefs = self.get_user_preferences(user_id)
            
            # Combinar con request específico (solo valores no None)
            for key, value in request_data.items():
                if value is not None:
                    user_prefs[key] = value
            
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
