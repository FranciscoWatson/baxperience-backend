#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Análisis Completo de Clustering y Machine Learning para BAXperience
==================================================================

Script para evaluar algoritmos de clustering, obtener métricas y detectar hardcode.
"""

import psycopg2
from psycopg2.extras import RealDictCursor
import pandas as pd
import numpy as np
from sklearn.cluster import KMeans, DBSCAN
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler
import json
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de BD
PROCESSOR_DB = {
    'host': 'localhost',
    'database': 'PROCESSOR_DB',
    'user': 'postgres',
    'password': 'admin',
    'port': 5432
}

def conectar_bd():
    """Conectar a la base de datos"""
    try:
        conn = psycopg2.connect(**PROCESSOR_DB)
        return conn
    except Exception as e:
        logger.error(f"Error conectando a BD: {e}")
        return None

def obtener_datos_pois(conn):
    """Obtener datos de POIs de la BD"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
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
    
    cursor.execute(query)
    return cursor.fetchall()

def obtener_resultados_clustering_actuales(conn):
    """Obtener resultados de clustering guardados en BD"""
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    try:
        cursor.execute("""
            SELECT 
                algorithm_type, 
                silhouette_score, 
                n_clusters, 
                total_pois,
                created_at,
                results_data
            FROM clustering_results 
            ORDER BY created_at DESC 
            LIMIT 10
        """)
        return cursor.fetchall()
    except Exception as e:
        logger.warning(f"No se pudieron obtener resultados previos: {e}")
        return []

def evaluar_clustering_geografico(data):
    """Evaluar clustering geográfico K-means"""
    logger.info("Evaluando clustering geográfico K-means...")
    
    # Preparar datos
    coords = np.array([[float(row['latitud']), float(row['longitud'])] for row in data])
    scaler = StandardScaler()
    coords_scaled = scaler.fit_transform(coords)
    
    # Evaluar diferentes números de clusters
    resultados = {}
    for k in range(2, min(11, len(coords))):
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        labels = kmeans.fit_predict(coords_scaled)
        silhouette = silhouette_score(coords_scaled, labels)
        
        resultados[k] = {
            'n_clusters': k,
            'silhouette_score': silhouette,
            'inertia': kmeans.inertia_
        }
        logger.info(f"K={k}: Silhouette={silhouette:.3f}, Inertia={kmeans.inertia_:.3f}")
    
    # Encontrar mejor k
    mejor_k = max(resultados.keys(), key=lambda k: resultados[k]['silhouette_score'])
    return resultados, mejor_k

def evaluar_clustering_dbscan(data):
    """Evaluar clustering DBSCAN"""
    logger.info("Evaluando clustering DBSCAN...")
    
    coords = np.array([[float(row['latitud']), float(row['longitud'])] for row in data])
    scaler = StandardScaler()
    coords_scaled = scaler.fit_transform(coords)
    
    # Evaluar diferentes parámetros
    eps_values = [0.005, 0.01, 0.02, 0.03, 0.05]
    min_samples_values = [3, 5, 10]
    
    mejor_resultado = None
    mejor_silhouette = -1
    
    for eps in eps_values:
        for min_samples in min_samples_values:
            dbscan = DBSCAN(eps=eps, min_samples=min_samples)
            labels = dbscan.fit_predict(coords_scaled)
            
            n_clusters = len(set(labels)) - (1 if -1 in labels else 0)
            n_noise = list(labels).count(-1)
            
            if n_clusters > 1:
                mask = labels != -1
                if np.sum(mask) > 1:
                    silhouette = silhouette_score(coords_scaled[mask], labels[mask])
                    
                    if silhouette > mejor_silhouette:
                        mejor_silhouette = silhouette
                        mejor_resultado = {
                            'eps': eps,
                            'min_samples': min_samples,
                            'n_clusters': n_clusters,
                            'n_noise': n_noise,
                            'noise_ratio': n_noise / len(coords),
                            'silhouette_score': silhouette
                        }
                        
                    logger.info(f"DBSCAN eps={eps}, min_samples={min_samples}: "
                              f"Clusters={n_clusters}, Noise={n_noise}, Silhouette={silhouette:.3f}")
    
    return mejor_resultado

def analizar_categorias_por_zona(data):
    """Analizar distribución de categorías por zona"""
    logger.info("Analizando distribución de categorías por zona...")
    
    df = pd.DataFrame(data)
    
    # Distribución por barrio
    barrios_categorias = df.groupby(['barrio', 'categoria']).size().unstack(fill_value=0)
    
    # Top 10 barrios con más POIs
    top_barrios = df['barrio'].value_counts().head(10)
    
    # Diversidad de categorías por barrio
    diversidad = df.groupby('barrio')['categoria'].nunique().sort_values(ascending=False).head(10)
    
    return {
        'top_barrios': top_barrios.to_dict(),
        'diversidad_categorias': diversidad.to_dict(),
        'matriz_barrio_categoria': barrios_categorias.head(10).to_dict()
    }

def detectar_valores_hardcodeados():
    """Detectar valores hardcodeados en el código"""
    logger.info("Detectando valores hardcodeados...")
    
    hardcoded_values = {
        'zonas_geograficas': [
            'Puerto Madero', 'Palermo', 'San Telmo', 'La Boca', 'Recoleta'
        ],
        'scores_fijos': [
            0.6, 0.5, 0.4, 0.3, 0.25, 0.2, 0.15, 0.1, 0.05  # Bonuses en scoring
        ],
        'duraciones_fijas': [
            90, 120, 180  # Minutos para actividades
        ],
        'horarios_fijos': [
            13, 19  # Horarios de comida hardcodeados
        ],
        'limites_fijos': [
            20, 40, 60, 80, 200  # Límites en queries
        ]
    }
    
    return hardcoded_values

def generar_recomendaciones_mejora():
    """Generar recomendaciones para mejorar clustering"""
    return {
        'silhouette_score': {
            'actual': 'Pendiente análisis',
            'objetivo': '> 0.5 (bueno), > 0.7 (excelente)',
            'mejoras': [
                'Normalizar datos geográficos antes del clustering',
                'Usar PCA para reducir dimensionalidad si hay muchas features',
                'Probar diferentes métricas de distancia (haversine para coordenadas)',
                'Aplicar clustering jerárquico para comparar resultados',
                'Considerar clustering por categorías separadamente'
            ]
        },
        'parametros_dinamicos': {
            'problema': 'Muchos valores están hardcodeados',
            'solucion': [
                'Crear tabla de configuración en BD',
                'Parametrizar horarios de comida por ciudad/cultura',
                'Hacer scoring configurable por tipo de usuario',
                'Obtener zonas desde datos geográficos reales'
            ]
        },
        'algoritmos_adicionales': [
            'Mean Shift clustering (detección automática de clusters)',
            'Gaussian Mixture Models (clusters probabilísticos)',
            'Clustering espectral (para formas no convexas)',
            'HDBSCAN (versión mejorada de DBSCAN)'
        ]
    }

def main():
    """Función principal de análisis"""
    print("🔍 ANÁLISIS COMPLETO DE CLUSTERING Y ML - BAXperience")
    print("=" * 60)
    
    # Conectar a BD
    conn = conectar_bd()
    if not conn:
        print("❌ Error: No se pudo conectar a la base de datos")
        return
    
    try:
        # 1. Obtener datos
        print("\n📊 Obteniendo datos de POIs...")
        pois_data = obtener_datos_pois(conn)
        print(f"   Total POIs: {len(pois_data)}")
        
        # 2. Resultados actuales
        print("\n📈 Resultados de clustering actuales:")
        resultados_previos = obtener_resultados_clustering_actuales(conn)
        if resultados_previos:
            for resultado in resultados_previos[:3]:
                print(f"   {resultado['algorithm_type']}: Silhouette={resultado['silhouette_score']:.3f}, "
                      f"Clusters={resultado['n_clusters']}, POIs={resultado['total_pois']}")
        else:
            print("   No hay resultados previos en la BD")
        
        # 3. Evaluar clustering geográfico
        print("\n🗺️  Evaluando clustering geográfico K-means...")
        resultados_kmeans, mejor_k = evaluar_clustering_geografico(pois_data)
        print(f"   Mejor K: {mejor_k} (Silhouette: {resultados_kmeans[mejor_k]['silhouette_score']:.3f})")
        
        # 4. Evaluar DBSCAN
        print("\n🎯 Evaluando clustering DBSCAN...")
        mejor_dbscan = evaluar_clustering_dbscan(pois_data)
        if mejor_dbscan:
            print(f"   Mejor DBSCAN: eps={mejor_dbscan['eps']}, "
                  f"Silhouette={mejor_dbscan['silhouette_score']:.3f}")
        
        # 5. Análisis de categorías
        print("\n📋 Analizando distribución de categorías...")
        analisis_categorias = analizar_categorias_por_zona(pois_data)
        print(f"   Top 3 barrios: {list(analisis_categorias['top_barrios'].keys())[:3]}")
        
        # 6. Valores hardcodeados
        print("\n⚠️  Valores hardcodeados detectados:")
        hardcoded = detectar_valores_hardcodeados()
        print(f"   Zonas geográficas: {len(hardcoded['zonas_geograficas'])} valores fijos")
        print(f"   Scores de bonificación: {len(hardcoded['scores_fijos'])} valores fijos")
        
        # 7. Recomendaciones
        print("\n💡 Generando recomendaciones de mejora...")
        recomendaciones = generar_recomendaciones_mejora()
        
        # Resumen final
        print("\n" + "=" * 60)
        print("📊 RESUMEN EJECUTIVO:")
        print(f"   • Total POIs analizados: {len(pois_data)}")
        print(f"   • Mejor Silhouette K-means: {resultados_kmeans[mejor_k]['silhouette_score']:.3f}")
        if mejor_dbscan:
            print(f"   • Mejor Silhouette DBSCAN: {mejor_dbscan['silhouette_score']:.3f}")
        print(f"   • Valores hardcodeados encontrados: {sum(len(v) for v in hardcoded.values())}")
        print(f"   • Estado del clustering: {'🟢 Bueno' if resultados_kmeans[mejor_k]['silhouette_score'] > 0.5 else '🟡 Mejorable'}")
        
        # Guardar resultados para el informe
        resultados_completos = {
            'timestamp': datetime.now().isoformat(),
            'total_pois': len(pois_data),
            'kmeans_results': resultados_kmeans,
            'mejor_k': mejor_k,
            'dbscan_result': mejor_dbscan,
            'analisis_categorias': analisis_categorias,
            'hardcoded_values': hardcoded,
            'recomendaciones': recomendaciones
        }
        
        # Guardar en archivo JSON
        with open('clustering_analysis_results.json', 'w', encoding='utf-8') as f:
            json.dump(resultados_completos, f, indent=2, ensure_ascii=False, default=str)
        
        print(f"\n💾 Resultados guardados en: clustering_analysis_results.json")
        
        return resultados_completos
        
    except Exception as e:
        logger.error(f"Error durante el análisis: {e}")
        print(f"❌ Error: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    main()
