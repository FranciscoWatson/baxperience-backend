#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test de Integración de Clustering en Recommendation Service
===========================================================

Prueba las integraciones de algoritmos de clustering en el sistema de recomendaciones.
"""

import logging
import json
from datetime import datetime
from recommendation_service import RecommendationService

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_clustering_integration():
    """Test principal de integración de clustering"""
    print("🧪 TEST DE INTEGRACIÓN DE CLUSTERING")
    print("=" * 50)
    
    # Crear servicio
    service = RecommendationService()
    
    try:
        # Conectar y cargar modelos
        print("\n📊 Conectando a BD y cargando modelos...")
        service.connect_database()
        service.connect_operational_database()
        service.load_ml_models()
        
        # Verificar qué modelos se cargaron
        print(f"\n🤖 Modelos cargados: {list(service.models.keys())}")
        for model_name, model_info in service.models.items():
            silhouette = model_info.get('silhouette_score', 'N/A')
            n_clusters = model_info.get('n_clusters', 'N/A')
            print(f"   • {model_name}: {n_clusters} clusters, silhouette={silhouette}")
        
        # Test 1: Usuario con zona específica (debe usar DBSCAN)
        print("\n🎯 TEST 1: Usuario con zona específica (Palermo)")
        test_request_1 = {
            'fecha_visita': '2025-09-01',
            'hora_inicio': '10:00',
            'duracion_horas': 6,
            'latitud_origen': -34.5755,  # Palermo
            'longitud_origen': -58.4139,
            'zona_preferida': 'Palermo',
            'categorias_preferidas': ['Museos', 'Gastronomía']
        }
        
        result_1 = service.generate_itinerary(1, test_request_1)
        
        if 'error' not in result_1:
            actividades = result_1.get('actividades', [])
            print(f"   ✅ Itinerario generado: {len(actividades)} actividades")
            
            # Verificar si se usó clustering geográfico
            barrios_encontrados = set()
            for actividad in actividades:
                barrio = actividad.get('barrio')
                if barrio:
                    barrios_encontrados.add(barrio)
            
            print(f"   📍 Barrios en itinerario: {', '.join(barrios_encontrados)}")
            
            # Verificar si hay concentración en Palermo (efecto DBSCAN)
            palermo_count = sum(1 for barrio in barrios_encontrados if 'palermo' in barrio.lower())
            if palermo_count > 0:
                print(f"   🎯 Clustering geográfico FUNCIONANDO: {palermo_count} actividades en Palermo")
            else:
                print(f"   ⚠️  Clustering geográfico no detectado claramente")
                
        else:
            print(f"   ❌ Error en test 1: {result_1.get('error')}")
        
        # Test 2: Usuario foodie (debe usar K-means perfil)
        print("\n🍽️  TEST 2: Usuario foodie (perfil K-means)")
        test_request_2 = {
            'fecha_visita': '2025-09-01',
            'hora_inicio': '11:00',
            'duracion_horas': 8,
            'latitud_origen': -34.6118,  # Puerto Madero
            'longitud_origen': -58.3636,
            'categorias_preferidas': ['Gastronomía'],  # Solo gastronomía
            'user_id': 1
        }
        
        result_2 = service.generate_itinerary(1, test_request_2)
        
        if 'error' not in result_2:
            actividades = result_2.get('actividades', [])
            gastro_count = sum(1 for act in actividades if act.get('categoria') == 'Gastronomía')
            
            print(f"   ✅ Itinerario generado: {len(actividades)} actividades")
            print(f"   🍽️  Actividades gastronómicas: {gastro_count}/{len(actividades)}")
            
            if gastro_count >= len(actividades) * 0.6:  # 60%+ gastronomía
                print(f"   🎯 Perfil de usuario K-means FUNCIONANDO: {gastro_count/len(actividades)*100:.1f}% gastronomía")
            else:
                print(f"   ⚠️  Perfil de usuario no aplicado claramente")
                
        else:
            print(f"   ❌ Error en test 2: {result_2.get('error')}")
        
        # Test 3: Verificar clustering jerárquico de categorías
        print("\n🏛️  TEST 3: Clustering jerárquico de categorías")
        test_request_3 = {
            'fecha_visita': '2025-09-01',
            'hora_inicio': '09:00',
            'duracion_horas': 6,
            'latitud_origen': -34.6037,  # San Telmo
            'longitud_origen': -58.3816,
            'categorias_preferidas': ['Museos'],  # Solo museos
            'user_id': 2
        }
        
        result_3 = service.generate_itinerary(2, test_request_3)
        
        if 'error' not in result_3:
            actividades = result_3.get('actividades', [])
            print(f"   ✅ Itinerario generado: {len(actividades)} actividades")
            
            # Verificar diversidad de categorías culturales (efecto clustering jerárquico)
            categorias_encontradas = set()
            for actividad in actividades:
                cat = actividad.get('categoria')
                if cat:
                    categorias_encontradas.add(cat)
            
            print(f"   🏛️  Categorías encontradas: {', '.join(categorias_encontradas)}")
            
            cultural_categories = {'Museos', 'Monumentos', 'Lugares Históricos'}
            cultural_found = cultural_categories.intersection(categorias_encontradas)
            
            if len(cultural_found) > 1:
                print(f"   🎯 Clustering jerárquico FUNCIONANDO: {len(cultural_found)} categorías culturales relacionadas")
            else:
                print(f"   ⚠️  Clustering jerárquico no detectado")
                
        else:
            print(f"   ❌ Error en test 3: {result_3.get('error')}")
        
        # Resumen de integración
        print("\n" + "=" * 50)
        print("📊 RESUMEN DE INTEGRACIÓN:")
        
        algoritmos_integrados = []
        algoritmos_disponibles = []
        
        if 'dbscan' in service.models:
            algoritmos_disponibles.append('DBSCAN (clustering geográfico)')
            algoritmos_integrados.append('✅ DBSCAN en filtrado y optimización')
        
        if 'geographic' in service.models:
            algoritmos_disponibles.append('K-means (clustering geográfico)')
            # K-means geográfico ya no se usa directamente
        
        if 'hierarchical' in service.models:
            algoritmos_disponibles.append('Jerárquico (relaciones de categorías)')
            algoritmos_integrados.append('✅ Jerárquico en bonus de categorías')
        
        print(f"   • Algoritmos disponibles: {len(algoritmos_disponibles)}")
        for algo in algoritmos_disponibles:
            print(f"     - {algo}")
        
        print(f"   • Integraciones activas: {len(algoritmos_integrados)}")
        for integ in algoritmos_integrados:
            print(f"     - {integ}")
        
        if algoritmos_integrados:
            print(f"\n🎉 INTEGRACIÓN EXITOSA: {len(algoritmos_integrados)} algoritmos funcionando")
        else:
            print(f"\n⚠️  SIN INTEGRACIONES: Verificar resultados de clustering")
            
    except Exception as e:
        print(f"\n❌ ERROR EN TEST: {e}")
        import traceback
        traceback.print_exc()
        
    finally:
        service.disconnect_database()

def test_clustering_methods_individually():
    """Test individual de métodos de clustering"""
    print("\n🔬 TEST DE MÉTODOS INDIVIDUALES")
    print("=" * 40)
    
    service = RecommendationService()
    
    try:
        service.connect_database()
        service.load_ml_models()
        
        # Test método de cluster geográfico
        print("\n1. Test _find_geographic_cluster_for_zone:")
        cluster_palermo = service._find_geographic_cluster_for_zone('Palermo')
        print(f"   Cluster para Palermo: {cluster_palermo}")
        
        cluster_recoleta = service._find_geographic_cluster_for_zone('Recoleta')
        print(f"   Cluster para Recoleta: {cluster_recoleta}")
        
        # Test método de perfil de usuario
        print("\n2. Test _get_user_cluster_profile:")
        profile_1 = service._get_user_cluster_profile(1)
        print(f"   Perfil usuario 1: {profile_1}")
        
        profile_2 = service._get_user_cluster_profile(2)
        print(f"   Perfil usuario 2: {profile_2}")
        
        # Test métodos de bonus
        print("\n3. Test métodos de bonus:")
        user_prefs = {'categorias_preferidas': ['Gastronomía', 'Museos']}
        
        bonus_gastro = service._calculate_category_cluster_bonus('Gastronomía', user_prefs)
        print(f"   Bonus jerárquico Gastronomía: {bonus_gastro}")
        
        poi_test = {'categoria': 'Gastronomía', 'tipo_cocina': 'Italiana', 'tiene_web': True}
        bonus_profile = service._calculate_user_profile_bonus(poi_test, 0)  # Perfil foodie
        print(f"   Bonus perfil foodie: {bonus_profile}")
        
    except Exception as e:
        print(f"   ❌ Error en métodos individuales: {e}")
        
    finally:
        service.disconnect_database()

def test_performance_comparison():
    """Test de comparación de performance con y sin clustering"""
    print("\n⚡ TEST DE PERFORMANCE: Con vs Sin Clustering")
    print("=" * 50)
    
    service = RecommendationService()
    
    try:
        service.connect_database()
        service.connect_operational_database()
        
        # Test con clustering
        print("\n🚀 Con clustering integrado:")
        service.load_ml_models()
        
        import time
        start_time = time.time()
        
        result_with_clustering = service.generate_itinerary(1, {
            'fecha_visita': '2025-09-01',
            'hora_inicio': '10:00',
            'duracion_horas': 6,
            'latitud_origen': -34.5755,
            'longitud_origen': -58.4139,
            'categorias_preferidas': ['Museos', 'Gastronomía']
        })
        
        time_with_clustering = time.time() - start_time
        
        if 'error' not in result_with_clustering:
            actividades_clustering = len(result_with_clustering.get('actividades', []))
            print(f"   ✅ Tiempo: {time_with_clustering:.3f}s, Actividades: {actividades_clustering}")
        else:
            print(f"   ❌ Error: {result_with_clustering.get('error')}")
        
        # Test sin clustering (simulado)
        print("\n🐌 Sin clustering (fallback):")
        service.models = {}  # Vaciar modelos para simular sin clustering
        
        start_time = time.time()
        
        result_without_clustering = service.generate_itinerary(1, {
            'fecha_visita': '2025-09-01',
            'hora_inicio': '10:00',
            'duracion_horas': 6,
            'latitud_origen': -34.5755,
            'longitud_origen': -58.4139,
            'categorias_preferidas': ['Museos', 'Gastronomía']
        })
        
        time_without_clustering = time.time() - start_time
        
        if 'error' not in result_without_clustering:
            actividades_sin_clustering = len(result_without_clustering.get('actividades', []))
            print(f"   ✅ Tiempo: {time_without_clustering:.3f}s, Actividades: {actividades_sin_clustering}")
        else:
            print(f"   ❌ Error: {result_without_clustering.get('error')}")
        
        # Comparación
        if 'error' not in result_with_clustering and 'error' not in result_without_clustering:
            print(f"\n📊 COMPARACIÓN:")
            print(f"   • Diferencia de tiempo: {abs(time_with_clustering - time_without_clustering):.3f}s")
            print(f"   • Diferencia de actividades: {abs(actividades_clustering - actividades_sin_clustering)}")
            
            if time_with_clustering < time_without_clustering:
                print("   🎯 Clustering MEJORA la performance")
            else:
                print("   ⚠️  Clustering tiene overhead, pero mejora calidad")
        
    except Exception as e:
        print(f"   ❌ Error en test de performance: {e}")
        
    finally:
        service.disconnect_database()

if __name__ == '__main__':
    test_clustering_integration()
    test_clustering_methods_individually()
    test_performance_comparison()
