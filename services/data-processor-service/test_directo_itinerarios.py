#!/usr/bin/env python3
"""
Test directo de funcionalidad de itinerarios
===========================================

Test que llama directamente a las funciones sin Kafka para verificar
que las categorías preferidas siempre vengan de BD y mostrar todas las actividades.
"""

import json
import logging
from datetime import datetime
from recommendation_service import generate_itinerary_request

# Configurar logging para ver detalles
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_direct_itinerary():
    """Test directo de generación de itinerarios"""
    
    print("=== TEST DIRECTO DE ITINERARIOS - SIN KAFKA ===\n")
    
    # Escenarios de prueba
    test_scenarios = [
        {
            'name': 'Usuario foodie - categorías de BD',
            'user_id': 1,  # Francisco - foodie urbano
            'request_data': {
                'fecha_visita': '2025-08-30',
                'hora_inicio': '10:00',
                'duracion_horas': 6,
                'latitud_origen': -34.6118,
                'longitud_origen': -58.3960,
                'zona_preferida': None,  # Usar de BD
            }
        },
        {
            'name': 'Usuario cultural - override zona pero NO categorías',
            'user_id': 2,  # María - cultural
            'request_data': {
                'fecha_visita': '2025-08-30',
                'hora_inicio': '14:00',
                'duracion_horas': 4,
                'latitud_origen': -34.5875,
                'longitud_origen': -58.3974,
                'zona_preferida': 'Recoleta',  # Override de zona
                # NO hay categorias_preferidas - siempre de BD
            }
        },
        {
            'name': 'Test con categorías en request (DEBE IGNORARSE)',
            'user_id': 1,  # Francisco - foodie urbano
            'request_data': {
                'fecha_visita': '2025-08-30',
                'hora_inicio': '09:00',
                'duracion_horas': 8,
                'latitud_origen': -34.6345,
                'longitud_origen': -58.3635,
                'categorias_preferidas': ['Solo Museos'],  # ESTO DEBE SER IGNORADO
                'zona_preferida': 'La Boca',
            }
        },
    ]
    
    for i, scenario in enumerate(test_scenarios, 1):
        print(f"{'='*80}")
        print(f"ESCENARIO {i}: {scenario['name']}")
        print(f"Usuario: {scenario['user_id']}")
        print(f"Request data enviado: {json.dumps(scenario['request_data'], indent=2)}")
        print(f"{'='*80}")
        
        try:
            # Generar itinerario directamente
            resultado = generate_itinerary_request(scenario['user_id'], scenario['request_data'])
            
            if 'error' in resultado:
                print(f"❌ ERROR: {resultado['error']}")
                if 'details' in resultado:
                    print(f"   Detalles: {resultado['details']}")
            else:
                print(f"✅ ITINERARIO GENERADO EXITOSAMENTE")
                
                # Mostrar preferencias usadas
                prefs = resultado.get('preferencias_usadas', {})
                print(f"\n📋 PREFERENCIAS UTILIZADAS:")
                print(f"   • Categorías preferidas (BD): {prefs.get('categorias_preferidas', [])}")
                print(f"   • Zona preferida: {prefs.get('zona_preferida', 'N/A')}")
                print(f"   • Tipo compañía: {prefs.get('tipo_compania', 'N/A')}")
                print(f"   • Duración preferida: {prefs.get('duracion_preferida', 'N/A')} horas")
                
                # Mostrar metadata
                metadata = resultado.get('metadata', {})
                print(f"\n📊 METADATA:")
                print(f"   • POIs analizados: {metadata.get('total_pois_analizados', 0)}")
                print(f"   • Eventos analizados: {metadata.get('total_eventos_analizados', 0)}")
                print(f"   • Eventos incluidos: {metadata.get('eventos_incluidos', 0)}")
                
                # Mostrar TODAS las actividades
                actividades = resultado.get('actividades', [])
                print(f"\n🎯 TODAS LAS ACTIVIDADES GENERADAS ({len(actividades)}):")
                
                if actividades:
                    for j, act in enumerate(actividades, 1):
                        horario = f"{act.get('horario_inicio', 'N/A')} - {act.get('horario_fin', 'N/A')}"
                        distancia = act.get('distancia_origen_km', 'N/A')
                        score = act.get('score_personalizado', 'N/A')
                        item_type = act.get('item_type', 'poi')
                        valoracion = act.get('valoracion_promedio', 0)
                        
                        print(f"   {j}. {act.get('nombre', 'Sin nombre')} ({act.get('categoria', 'Sin categoría')})")
                        print(f"      ⏰ {horario} | 📍 {act.get('barrio', 'Sin barrio')}")
                        print(f"      🎯 Score: {score} | 📏 Distancia: {distancia}km | 🏷️ Tipo: {item_type}")
                        if valoracion > 0:
                            print(f"      ⭐ Valoración: {valoracion}/5")
                        if act.get('es_gratuito'):
                            print(f"      💰 GRATUITO")
                        print("")
                else:
                    print("   ❌ No se generaron actividades")
                
                # Mostrar estadísticas
                stats = resultado.get('estadisticas', {})
                print(f"📈 ESTADÍSTICAS:")
                print(f"   • Total actividades: {stats.get('total_actividades', 0)}")
                print(f"   • Duración total: {stats.get('duracion_total_horas', 0):.1f} horas")
                print(f"   • Distancia total: {stats.get('distancia_total_km', 0)} km")
                print(f"   • Costo estimado: {stats.get('costo_estimado', 'N/A')}")
                print(f"   • Valoración promedio: {stats.get('valoracion_promedio', 0)}/5")
                
                # Mostrar distribución por categorías
                categorias_dist = stats.get('categorias', {})
                if categorias_dist:
                    print(f"   • Distribución por categorías:")
                    for cat, count in categorias_dist.items():
                        print(f"     - {cat}: {count} actividades")
        
        except Exception as e:
            print(f"❌ ERROR INESPERADO: {e}")
            import traceback
            print(f"Traceback: {traceback.format_exc()}")
        
        print(f"\n{'='*80}\n")
    
    print("🏁 Test directo completado!")

if __name__ == "__main__":
    test_direct_itinerary()
