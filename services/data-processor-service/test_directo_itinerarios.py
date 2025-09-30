#!/usr/bin/env python3
"""
Test directo de funcionalidad de itinerarios - 5 Zonas de CABA
============================================================

Test que prueba generación de itinerarios desde 5 puntos geográficos específicos
de Buenos Aires: Palermo, Recoleta, Belgrano, San Telmo y Puerto Madero.
Muestra información detallada sin logs de base de datos.
"""

import json
import logging
from datetime import datetime
from recommendation_service import generate_itinerary_request

# Configurar logging solo para errores críticos (sin logs de BD)
logging.basicConfig(level=logging.ERROR)

def test_direct_itinerary():
    """Test directo de generación de itinerarios desde 5 zonas específicas de CABA"""
    
    print("🏙️  TEST DE ITINERARIOS - 5 ZONAS PRINCIPALES DE BUENOS AIRES")
    print("=" * 80)
    print()
    
    # Coordenadas exactas de las 5 zonas de CABA
    test_locations = [
        {
            'name': 'PALERMO',
            'description': 'Zona trendy con parques, vida nocturna y gastronomía',
            'user_id': 1,  # Usuario foodie
            'coordinates': {
                'latitud_origen': -34.5875,   # Palermo Soho
                'longitud_origen': -58.4200
            },
            'request_data': {
                'fecha_visita': '2025-09-10',
                'hora_inicio': '10:00',
                'duracion_horas': 6,
                'zona_preferida': 'Palermo',
                'tipo_compania': 'amigos'
            }
        },
        {
            'name': 'RECOLETA',
            'description': 'Zona elegante con museos, cementerio y arquitectura europea',
            'user_id': 2,  # Usuario cultural
            'coordinates': {
                'latitud_origen': -34.5889,   # Plaza Francia
                'longitud_origen': -58.3922
            },
            'request_data': {
                'fecha_visita': '2025-09-10',
                'hora_inicio': '09:30',
                'duracion_horas': 7,
                'zona_preferida': 'Recoleta',
                'tipo_compania': 'pareja'
            }
        },
        {
            'name': 'BELGRANO',
            'description': 'Barrio residencial tranquilo con historia y comercios',
            'user_id': 4,  # Usuario mixto (eventos, gastronomía, museos)
            'coordinates': {
                'latitud_origen': -34.5524,   # Belgrano centro
                'longitud_origen': -58.4588
            },
            'request_data': {
                'fecha_visita': '2025-09-10',
                'hora_inicio': '11:00',
                'duracion_horas': 5,
                'zona_preferida': 'Belgrano',
                'tipo_compania': 'familia'
            }
        },
        {
            'name': 'SAN TELMO',
            'description': 'Barrio histórico con tango, antigüedades y arquitectura colonial',
            'user_id': 8,  # Usuario cultural (monumentos, lugares históricos, museos)
            'coordinates': {
                'latitud_origen': -34.6214,   # Plaza Dorrego
                'longitud_origen': -58.3731
            },
            'request_data': {
                'fecha_visita': '2025-09-10',
                'hora_inicio': '14:00',
                'duracion_horas': 4,
                'zona_preferida': 'San Telmo',
                'tipo_compania': 'solo'
            }
        },
        {
            'name': 'PUERTO MADERO',
            'description': 'Distrito financiero moderno con rascacielos y puerto',
            'user_id': 1,  # Usuario foodie (para aprovechar los restaurantes de PM)
            'coordinates': {
                'latitud_origen': -34.6118,   # Puente de la Mujer
                'longitud_origen': -58.3630
            },
            'request_data': {
                'fecha_visita': '2025-09-10',
                'hora_inicio': '12:00',
                'duracion_horas': 8,
                'zona_preferida': 'Puerto Madero',
                'tipo_compania': 'pareja'
            }
        },
        {
            'name': 'PUERTO MADERO',
            'description': 'Distrito financiero moderno con rascacielos y puerto',
            'user_id': 1,  # Usuario foodie (para aprovechar los restaurantes de PM)
            'coordinates': {
                'latitud_origen': -34.6118,   # Puente de la Mujer
                'longitud_origen': -58.3630
            },
            'request_data': {
                'fecha_visita': '2025-09-10',
                'hora_inicio': '12:00',
                'duracion_horas': 8,
                'zona_preferida': 'Palermo',
                'tipo_compania': 'pareja'
            }
        }
    ]
    
    for i, location in enumerate(test_locations, 1):
        print_zone_header(i, location)
        print_input_parameters(location)
        
        try:
            # Generar itinerario directamente
            resultado = generate_itinerary_request(
                location['user_id'], 
                {**location['request_data'], **location['coordinates']}
            )
            
            if 'error' in resultado:
                print_error_result(resultado)
            else:
                print_successful_result(resultado, location)
        
        except Exception as e:
            print_exception_result(e)
        
        print("\n" + "=" * 80 + "\n")
    
    print("🏁 TESTING COMPLETADO - 5 ZONAS DE CABA ANALIZADAS")


def print_zone_header(zone_num, location):
    """Imprime el header de la zona"""
    print(f"🌎 ZONA {zone_num}/5: {location['name']}")
    print(f"📍 {location['description']}")
    print(f"👤 Usuario ID: {location['user_id']}")
    print("-" * 50)


def print_input_parameters(location):
    """Imprime los parámetros de entrada detallados"""
    coords = location['coordinates']
    request = location['request_data']
    
    print("📥 PARÁMETROS DE ENTRADA:")
    print(f"   🗓️  Fecha visita: {request['fecha_visita']}")
    print(f"   ⏰ Hora inicio: {request['hora_inicio']}")
    print(f"   ⏳ Duración: {request['duracion_horas']} horas")
    print(f"   📍 Coordenadas origen: ({coords['latitud_origen']}, {coords['longitud_origen']})")
    print(f"   🏘️  Zona preferida: {request['zona_preferida']}")
    print(f"   👥 Tipo compañía: {request['tipo_compania']}")
    print()


def print_error_result(resultado):
    """Imprime resultado de error"""
    print("❌ ERROR EN GENERACIÓN:")
    print(f"   💥 Error: {resultado['error']}")
    if 'details' in resultado:
        print(f"   🔍 Detalles: {resultado['details']}")


def print_successful_result(resultado, location):
    """Imprime resultado exitoso con detalles completos"""
    print("✅ ITINERARIO GENERADO EXITOSAMENTE")
    print()
    
    # Preferencias utilizadas
    print_user_preferences(resultado)
    
    # Datos de filtrado y procesamiento
    print_processing_metadata(resultado)
    
    # Actividades generadas
    print_generated_activities(resultado)
    
    # Estadísticas finales
    print_final_statistics(resultado)


def print_user_preferences(resultado):
    """Imprime las preferencias del usuario utilizadas"""
    prefs = resultado.get('preferencias_usadas', {})
    print("� PREFERENCIAS DE USUARIO UTILIZADAS:")
    print(f"   🎯 Categorías preferidas (desde BD): {', '.join(prefs.get('categorias_preferidas', []))}")
    print(f"   🏘️  Zona preferida: {prefs.get('zona_preferida', 'N/A')}")
    print(f"   👥 Tipo compañía: {prefs.get('tipo_compania', 'N/A')}")
    print(f"   ⏳ Duración preferida: {prefs.get('duracion_preferida', 'N/A')} horas")
    if prefs.get('actividades_evitar'):
        print(f"   🚫 Actividades a evitar: {', '.join(prefs.get('actividades_evitar', []))}")
    print()


def print_processing_metadata(resultado):
    """Imprime metadata del procesamiento"""
    metadata = resultado.get('metadata', {})
    print("� PROCESAMIENTO REALIZADO:")
    print(f"   📊 POIs analizados: {metadata.get('total_pois_analizados', 0)}")
    print(f"   🎪 Eventos analizados: {metadata.get('total_eventos_analizados', 0)}")
    print(f"   ✅ Eventos incluidos: {metadata.get('eventos_incluidos', 0)}")
    print(f"   🧮 Algoritmo optimización: {metadata.get('algoritmo_optimizacion', 'N/A')}")
    if metadata.get('clustering_usado'):
        print(f"   🔬 Clustering usado: {metadata.get('clustering_usado')}")
    print()


def print_generated_activities(resultado):
    """Imprime todas las actividades generadas con detalles"""
    actividades = resultado.get('actividades', [])
    print(f"🎯 ACTIVIDADES GENERADAS ({len(actividades)}):")
    
    if not actividades:
        print("   ❌ No se generaron actividades")
        return
    
    for j, act in enumerate(actividades, 1):
        print_single_activity(j, act)
    print()


def print_single_activity(num, activity):
    """Imprime una sola actividad con todos sus detalles"""
    # Información básica
    nombre = activity.get('nombre', 'Sin nombre')
    categoria = activity.get('categoria', 'Sin categoría')
    barrio = activity.get('barrio', 'Sin barrio')
    
    # Horarios
    horario_inicio = activity.get('horario_inicio', 'N/A')
    horario_fin = activity.get('horario_fin', 'N/A')
    duracion = activity.get('duracion_minutos', 0)
    
    # Métricas
    score = activity.get('score_personalizado', 'N/A')
    distancia = activity.get('distancia_origen_km', 'N/A')
    valoracion = activity.get('valoracion_promedio', 0)
    
    # Características
    item_type = activity.get('item_type', 'poi')
    es_gratuito = activity.get('es_gratuito', False)
    tipo_actividad = activity.get('tipo_actividad', 'N/A')
    
    print(f"   {num}. 🏛️  {nombre}")
    print(f"      📂 Categoría: {categoria} | 🏷️  Tipo: {item_type.upper()}")
    print(f"      📍 Ubicación: {barrio}")
    print(f"      ⏰ Horario: {horario_inicio} - {horario_fin} ({duracion} min)")
    print(f"      🎯 Score personalizado: {score}")
    print(f"      📏 Distancia al origen: {distancia} km")
    
    if valoracion > 0:
        stars = "⭐" * int(valoracion)
        print(f"      {stars} Valoración: {valoracion}/5")
    
    if es_gratuito:
        print(f"      💰 ACTIVIDAD GRATUITA")
    
    if activity.get('tipo_cocina'):
        print(f"      🍽️  Tipo cocina: {activity.get('tipo_cocina')}")
    
    if activity.get('material'):
        print(f"      🏗️  Material: {activity.get('material')}")
    
    print(f"      🎭 Tipo actividad: {tipo_actividad}")
    print()


def print_final_statistics(resultado):
    """Imprime estadísticas finales del itinerario"""
    stats = resultado.get('estadisticas', {})
    print("📈 ESTADÍSTICAS DEL ITINERARIO:")
    print(f"   🎯 Total actividades: {stats.get('total_actividades', 0)}")
    print(f"   ⏱️  Duración total: {stats.get('duracion_total_horas', 0):.1f} horas")
    print(f"   🚗 Distancia total estimada: {stats.get('distancia_total_km', 0):.1f} km")
    print(f"   💰 Costo estimado: {stats.get('costo_estimado', 'N/A')}")
    
    if stats.get('valoracion_promedio', 0) > 0:
        stars = "⭐" * int(stats.get('valoracion_promedio', 0))
        print(f"   {stars} Valoración promedio: {stats.get('valoracion_promedio', 0):.1f}/5")
    
    # Distribución por categorías
    categorias_dist = stats.get('categorias', {})
    if categorias_dist:
        print(f"   📊 Distribución por categorías:")
        for cat, count in categorias_dist.items():
            print(f"      • {cat}: {count} actividad(es)")
    
    # Distribución por barrios
    barrios_dist = stats.get('barrios', {})
    if barrios_dist:
        print(f"   🗺️  Distribución por barrios:")
        for barrio, count in barrios_dist.items():
            print(f"      • {barrio}: {count} actividad(es)")


def print_exception_result(exception):
    """Imprime resultado de excepción"""
    print("❌ ERROR INESPERADO:")
    print(f"   💥 Excepción: {exception}")
    import traceback
    print(f"   🔍 Traceback: {traceback.format_exc()}")


if __name__ == "__main__":
    test_direct_itinerary()
