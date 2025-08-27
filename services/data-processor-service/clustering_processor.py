"""
BAXperience Clustering Processor
===============================

Implementa algoritmos de clustering para POIs y análisis de datos geográficos.

- Clustering geográfico (K-means) para POIs
- Clustering por categorías y características  
- Análisis de densidad por barrios
- Detección de zonas turísticas
- Métricas de calidad de clusters

Autor: BAXperience Team
"""

import logging
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import silhouette_score
from sklearn.decomposition import PCA
import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Dict, List, Tuple, Optional
import json
from datetime import datetime

logger = logging.getLogger(__name__)

class ClusteringProcessor:
    """Procesador de clustering para POIs y análisis geográfico"""
    
    def __init__(self, proc_db_config: Dict):
        """
        Inicializar procesador de clustering
        
        Args:
            proc_db_config: Configuración de BD Data Processor
        """
        self.proc_db_config = proc_db_config
        self.proc_conn = None
        self.results = {}
        
    def connect_processor_db(self):
        """Conectar a BD Data Processor"""
        try:
            self.proc_conn = psycopg2.connect(**self.proc_db_config)
            logger.info("Conectado a BD Data Processor para clustering")
        except Exception as e:
            logger.error(f"Error conectando a BD Data Processor: {e}")
            raise
    
    def disconnect_processor_db(self):
        """Desconectar de BD Data Processor"""
        if self.proc_conn:
            self.proc_conn.close()
            logger.info("Desconectado de BD Data Processor")
    
    def load_pois_data(self) -> pd.DataFrame:
        """Cargar datos de POIs para clustering"""
        logger.info("Cargando datos de POIs para clustering...")
        
        query = """
        SELECT 
            id, nombre, categoria, subcategoria,
            latitud, longitud, barrio, comuna,
            valoracion_promedio, numero_valoraciones,
            tipo_cocina, tipo_ambiente
        FROM lugares_clustering
        WHERE latitud IS NOT NULL AND longitud IS NOT NULL
        ORDER BY id
        """
        
        cursor = self.proc_conn.cursor(cursor_factory=RealDictCursor)
        cursor.execute(query)
        data = cursor.fetchall()
        cursor.close()
        
        if not data:
            logger.warning("No se encontraron POIs para clustering")
            return pd.DataFrame()
        
        df = pd.DataFrame(data)
        logger.info(f"Cargados {len(df)} POIs para clustering")
        return df
    
    def geographic_clustering(self, df: pd.DataFrame, n_clusters: int = 8) -> Dict:
        """
        Clustering geográfico usando K-means
        
        Args:
            df: DataFrame con POIs
            n_clusters: Número de clusters geográficos
            
        Returns:
            Dict con resultados del clustering
        """
        logger.info(f"Ejecutando clustering geográfico con {n_clusters} clusters...")
        
        if df.empty:
            return {'status': 'no_data', 'clusters': 0}
        
        # Preparar datos geográficos
        coords = df[['latitud', 'longitud']].values
        
        # Normalizar coordenadas
        scaler = StandardScaler()
        coords_scaled = scaler.fit_transform(coords)
        
        # K-means clustering
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        cluster_labels = kmeans.fit_predict(coords_scaled)
        
        # Calcular métricas de calidad
        silhouette = silhouette_score(coords_scaled, cluster_labels)
        
        # Agregar clusters al DataFrame
        df_clustered = df.copy()
        df_clustered['cluster_geografico'] = cluster_labels
        
        # Calcular estadísticas por cluster
        cluster_stats = []
        for i in range(n_clusters):
            cluster_data = df_clustered[df_clustered['cluster_geografico'] == i]
            
            if len(cluster_data) > 0:
                # Centroide real (promedio de coordenadas)
                centroide_lat = cluster_data['latitud'].mean()
                centroide_lng = cluster_data['longitud'].mean()
                
                # Estadísticas del cluster
                stats = {
                    'cluster_id': int(i),
                    'num_pois': len(cluster_data),
                    'centroide_lat': float(centroide_lat),
                    'centroide_lng': float(centroide_lng),
                    'categorias': cluster_data['categoria'].value_counts().to_dict(),
                    'barrios': cluster_data['barrio'].value_counts().to_dict(),
                    'valoracion_promedio': float(cluster_data['valoracion_promedio'].mean()) if cluster_data['valoracion_promedio'].notna().any() else 0.0,
                    'radius_km': self._calculate_cluster_radius(cluster_data)
                }
                cluster_stats.append(stats)
        
        results = {
            'status': 'success',
            'algorithm': 'kmeans',
            'n_clusters': n_clusters,
            'silhouette_score': float(silhouette),
            'total_pois': len(df),
            'cluster_stats': cluster_stats,
            'dataframe': df_clustered
        }
        
        logger.info(f"Clustering geográfico completado. Silhouette score: {silhouette:.3f}")
        return results
    
    def category_clustering(self, df: pd.DataFrame) -> Dict:
        """
        Clustering por categorías y características
        
        Args:
            df: DataFrame con POIs
            
        Returns:
            Dict con análisis por categorías
        """
        logger.info("Ejecutando análisis de clustering por categorías...")
        
        if df.empty:
            return {'status': 'no_data'}
        
        # Análisis por categoría
        category_analysis = {}
        
        for categoria in df['categoria'].unique():
            if pd.isna(categoria):
                continue
                
            cat_data = df[df['categoria'] == categoria]
            
            analysis = {
                'total_pois': len(cat_data),
                'barrios_distribution': cat_data['barrio'].value_counts().head(10).to_dict(),
                'subcategorias': cat_data['subcategoria'].value_counts().to_dict(),
                'valoracion_promedio': float(cat_data['valoracion_promedio'].mean()) if cat_data['valoracion_promedio'].notna().any() else 0.0,
                'densidade_geografica': self._calculate_geographic_density(cat_data)
            }
            
            # Análisis específico para gastronomía
            if categoria.lower() == 'gastronomía':
                analysis['tipos_cocina'] = cat_data['tipo_cocina'].value_counts().head(10).to_dict()
                analysis['tipos_ambiente'] = cat_data['tipo_ambiente'].value_counts().head(10).to_dict()
            
            # Análisis específico para monumentos (campos disponibles limitados)
            elif categoria.lower() == 'monumentos':
                analysis['subcategorias_detalle'] = cat_data['subcategoria'].value_counts().head(10).to_dict()
            
            category_analysis[categoria] = analysis
        
        results = {
            'status': 'success',
            'total_categories': len(category_analysis),
            'category_analysis': category_analysis
        }
        
        logger.info(f"Análisis por categorías completado: {len(category_analysis)} categorías")
        return results
    
    def neighborhood_clustering(self, df: pd.DataFrame) -> Dict:
        """
        Análisis de clusters por barrios
        
        Args:
            df: DataFrame con POIs
            
        Returns:
            Dict con análisis por barrios
        """
        logger.info("Ejecutando análisis de clustering por barrios...")
        
        if df.empty:
            return {'status': 'no_data'}
        
        neighborhood_analysis = {}
        
        for barrio in df['barrio'].unique():
            if pd.isna(barrio):
                continue
            
            barrio_data = df[df['barrio'] == barrio]
            
            if len(barrio_data) < 2:  # Muy pocos POIs para análisis
                continue
            
            analysis = {
                'total_pois': len(barrio_data),
                'densidad_poi_km2': self._estimate_poi_density(barrio_data),
                'categorias_distribution': barrio_data['categoria'].value_counts().to_dict(),
                'valoracion_promedio': float(barrio_data['valoracion_promedio'].mean()) if barrio_data['valoracion_promedio'].notna().any() else 0.0,
                'centroide_lat': float(barrio_data['latitud'].astype(float).mean()),
                'centroide_lng': float(barrio_data['longitud'].astype(float).mean()),
                'diversidad_categoria': len(barrio_data['categoria'].unique()),
                'poi_mejor_valorado': self._get_best_poi(barrio_data)
            }
            
            neighborhood_analysis[barrio] = analysis
        
        # Ranking de barrios por diferentes métricas
        rankings = self._calculate_neighborhood_rankings(neighborhood_analysis)
        
        results = {
            'status': 'success',
            'total_neighborhoods': len(neighborhood_analysis),
            'neighborhood_analysis': neighborhood_analysis,
            'rankings': rankings
        }
        
        logger.info(f"Análisis por barrios completado: {len(neighborhood_analysis)} barrios")
        return results
    
    def detect_tourist_zones(self, geographic_results: Dict, category_results: Dict) -> Dict:
        """
        Detectar zonas turísticas basado en clustering
        
        Args:
            geographic_results: Resultados de clustering geográfico
            category_results: Resultados de clustering por categorías
            
        Returns:
            Dict con zonas turísticas detectadas
        """
        logger.info("Detectando zonas turísticas...")
        
        if geographic_results.get('status') != 'success':
            return {'status': 'no_data'}
        
        tourist_zones = []
        
        for cluster in geographic_results['cluster_stats']:
            cluster_id = cluster['cluster_id']
            
            # Criterios para zona turística:
            # 1. Diversidad de categorías
            # 2. Alta densidad de POIs
            # 3. Buena valoración promedio
            
            num_categories = len(cluster['categorias'])
            poi_density = cluster['num_pois']
            avg_rating = cluster['valoracion_promedio']
            
            # Puntaje turístico (0-100)
            tourist_score = 0
            
            # Diversidad de categorías (0-30 puntos)
            tourist_score += min(num_categories * 5, 30)
            
            # Densidad de POIs (0-30 puntos)  
            tourist_score += min(poi_density * 2, 30)
            
            # Valoración promedio (0-40 puntos)
            tourist_score += avg_rating * 8
            
            if tourist_score >= 50:  # Umbral para zona turística
                zone = {
                    'cluster_id': cluster_id,
                    'tourist_score': round(tourist_score, 1),
                    'centroide_lat': cluster['centroide_lat'],
                    'centroide_lng': cluster['centroide_lng'],
                    'num_pois': cluster['num_pois'],
                    'diversidad_categorias': num_categories,
                    'categorias_principales': list(cluster['categorias'].keys())[:3],
                    'barrios_incluidos': list(cluster['barrios'].keys()),
                    'radius_km': cluster['radius_km'],
                    'descripcion': self._generate_zone_description(cluster)
                }
                tourist_zones.append(zone)
        
        # Ordenar por puntaje turístico
        tourist_zones.sort(key=lambda x: x['tourist_score'], reverse=True)
        
        results = {
            'status': 'success',
            'total_zones': len(tourist_zones),
            'tourist_zones': tourist_zones,
            'algorithm_params': {
                'min_tourist_score': 50,
                'diversity_weight': 0.3,
                'density_weight': 0.3,
                'rating_weight': 0.4
            }
        }
        
        logger.info(f"Detectadas {len(tourist_zones)} zonas turísticas")
        return results
    
    def save_clustering_results(self, results: Dict):
        """
        Guardar resultados de clustering en BD
        
        Args:
            results: Diccionario con todos los resultados
        """
        logger.info("Guardando resultados de clustering en BD...")
        
        cursor = self.proc_conn.cursor()
        
        try:
            # Crear tabla de resultados de clustering si no existe
            create_table_sql = """
            CREATE TABLE IF NOT EXISTS clustering_results (
                id SERIAL PRIMARY KEY,
                algorithm_type VARCHAR(50) NOT NULL,
                results_json JSONB NOT NULL,
                silhouette_score DECIMAL(5,3),
                n_clusters INTEGER,
                total_pois INTEGER,
                fecha_calculo TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            
            CREATE INDEX IF NOT EXISTS idx_clustering_type ON clustering_results(algorithm_type);
            CREATE INDEX IF NOT EXISTS idx_clustering_fecha ON clustering_results(fecha_calculo);
            """
            cursor.execute(create_table_sql)
            
            # Limpiar resultados anteriores del mismo día
            cursor.execute("""
                DELETE FROM clustering_results 
                WHERE algorithm_type IN ('geographic', 'category', 'neighborhood', 'tourist_zones')
                AND DATE(fecha_calculo) = CURRENT_DATE
            """)
            
            # Insertar resultados
            for algorithm_type, result_data in results.items():
                if result_data.get('status') == 'success':
                    # Limpiar DataFrame antes de guardar
                    clean_results = result_data.copy()
                    if 'dataframe' in clean_results:
                        del clean_results['dataframe']
                    
                    insert_sql = """
                    INSERT INTO clustering_results 
                    (algorithm_type, results_json, silhouette_score, n_clusters, total_pois)
                    VALUES (%s, %s, %s, %s, %s)
                    """
                    
                    params = (
                        algorithm_type,
                        json.dumps(clean_results, default=str, ensure_ascii=False),
                        result_data.get('silhouette_score'),
                        result_data.get('n_clusters'),
                        result_data.get('total_pois')
                    )
                    
                    cursor.execute(insert_sql, params)
            
            self.proc_conn.commit()
            logger.info("Resultados de clustering guardados exitosamente")
            
        except Exception as e:
            self.proc_conn.rollback()
            logger.error(f"Error guardando resultados de clustering: {e}")
            raise
        finally:
            cursor.close()
    
    def run_full_clustering(self) -> Dict:
        """
        Ejecutar pipeline completo de clustering
        
        Returns:
            Dict con todos los resultados
        """
        logger.info("Iniciando pipeline completo de clustering...")
        
        try:
            self.connect_processor_db()
            
            # Cargar datos
            df = self.load_pois_data()
            
            if df.empty:
                logger.warning("No hay datos para clustering")
                return {'status': 'no_data', 'message': 'Sin datos para procesar'}
            
            # Ejecutar diferentes tipos de clustering
            results = {}
            
            # 1. Clustering geográfico
            results['geographic'] = self.geographic_clustering(df, n_clusters=8)
            
            # 2. Análisis por categorías
            results['category'] = self.category_clustering(df)
            
            # 3. Análisis por barrios
            results['neighborhood'] = self.neighborhood_clustering(df)
            
            # 4. Detección de zonas turísticas
            results['tourist_zones'] = self.detect_tourist_zones(
                results['geographic'], 
                results['category']
            )
            
            # Guardar resultados
            self.save_clustering_results(results)
            
            # Resumen general
            successful_algorithms = []
            for alg_name, result in results.items():
                if isinstance(result, dict) and result.get('status') == 'success':
                    successful_algorithms.append(alg_name)
            
            results['summary'] = {
                'total_pois_processed': len(df),
                'algorithms_executed': len(successful_algorithms),
                'successful_algorithms': successful_algorithms,
                'best_silhouette_score': results['geographic'].get('silhouette_score', 0),
                'tourist_zones_detected': results['tourist_zones'].get('total_zones', 0),
                'neighborhoods_analyzed': results['neighborhood'].get('total_neighborhoods', 0),
                'execution_time': datetime.now().isoformat()
            }
            
            logger.info("Pipeline de clustering completado exitosamente")
            results['status'] = 'success'  # Agregar status de éxito
            return results
            
        except Exception as e:
            logger.error(f"Error en pipeline de clustering: {e}")
            return {'status': 'error', 'message': str(e)}
        finally:
            self.disconnect_processor_db()
    
    # Métodos auxiliares
    def _calculate_cluster_radius(self, cluster_data: pd.DataFrame) -> float:
        """Calcular radio del cluster en km"""
        if len(cluster_data) < 2:
            return 0.0
        
        coords = cluster_data[['latitud', 'longitud']].values
        center = coords.mean(axis=0)
        
        # Calcular distancia máxima al centro (aproximación simple)
        distances = np.sqrt(np.sum((coords - center) ** 2, axis=1))
        max_distance = np.max(distances)
        
        # Convertir de grados a km (aproximado)
        return float(max_distance * 111)  # 1 grado ≈ 111 km
    
    def _calculate_geographic_density(self, data: pd.DataFrame) -> float:
        """Calcular densidad geográfica de POIs"""
        if len(data) < 2:
            return 0.0
        
        coords = data[['latitud', 'longitud']].values
        lat_range = coords[:, 0].max() - coords[:, 0].min()
        lng_range = coords[:, 1].max() - coords[:, 1].min()
        
        if lat_range == 0 or lng_range == 0:
            return 0.0
        
        # Área aproximada en km²
        area_km2 = lat_range * lng_range * 111 * 111
        return len(data) / area_km2 if area_km2 > 0 else 0.0
    
    def _estimate_poi_density(self, barrio_data: pd.DataFrame) -> float:
        """Estimar densidad de POIs por km² en un barrio"""
        # Estimación simple basada en dispersión de coordenadas
        if len(barrio_data) < 2:
            return 0.0
        
        lat_std = barrio_data['latitud'].astype(float).std()
        lng_std = barrio_data['longitud'].astype(float).std()
        
        # Área estimada (muy aproximada)
        area_estimate = lat_std * lng_std * 111 * 111 * 4  # 4 = factor de área elíptica
        
        return len(barrio_data) / area_estimate if area_estimate > 0 else 0.0
    
    def _get_best_poi(self, data: pd.DataFrame) -> Dict:
        """Obtener el POI mejor valorado de un grupo"""
        if len(data) == 0:
            return {}
        
        # Filtrar POIs con valoración
        rated_pois = data[data['valoracion_promedio'] > 0]
        
        if len(rated_pois) == 0:
            # Si no hay valoraciones, tomar el primero
            best_poi = data.iloc[0]
        else:
            # Tomar el mejor valorado
            best_poi = rated_pois.loc[rated_pois['valoracion_promedio'].idxmax()]
        
        return {
            'nombre': best_poi['nombre'],
            'categoria': best_poi['categoria'],
            'valoracion': float(best_poi['valoracion_promedio']) if pd.notna(best_poi['valoracion_promedio']) else 0.0
        }
    
    def _calculate_neighborhood_rankings(self, neighborhood_analysis: Dict) -> Dict:
        """Calcular rankings de barrios por diferentes métricas"""
        if not neighborhood_analysis:
            return {}
        
        # Ranking por densidad de POIs
        density_ranking = sorted(
            neighborhood_analysis.items(),
            key=lambda x: x[1]['densidad_poi_km2'],
            reverse=True
        )[:10]
        
        # Ranking por valoración promedio
        rating_ranking = sorted(
            neighborhood_analysis.items(),
            key=lambda x: x[1]['valoracion_promedio'],
            reverse=True
        )[:10]
        
        # Ranking por diversidad de categorías
        diversity_ranking = sorted(
            neighborhood_analysis.items(),
            key=lambda x: x[1]['diversidad_categoria'],
            reverse=True
        )[:10]
        
        return {
            'top_density': [{'barrio': name, 'valor': data['densidad_poi_km2']} for name, data in density_ranking],
            'top_rating': [{'barrio': name, 'valor': data['valoracion_promedio']} for name, data in rating_ranking],
            'top_diversity': [{'barrio': name, 'valor': data['diversidad_categoria']} for name, data in diversity_ranking]
        }
    
    def _generate_zone_description(self, cluster: Dict) -> str:
        """Generar descripción textual de una zona turística"""
        main_categories = list(cluster['categorias'].keys())[:2]
        main_neighborhoods = list(cluster['barrios'].keys())[:2]
        
        desc = f"Zona turística con {cluster['num_pois']} POIs"
        
        if main_categories:
            desc += f", principalmente {' y '.join(main_categories).lower()}"
        
        if main_neighborhoods:
            desc += f", ubicada en {' y '.join(main_neighborhoods)}"
        
        return desc
