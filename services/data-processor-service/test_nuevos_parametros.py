#!/usr/bin/env python3
"""
Test rápido para los nuevos parámetros del sistema de itinerarios
==================================================================

Este script demuestra cómo usar los nuevos parámetros:
- latitud_origen y longitud_origen (obligatorios)
- zona_preferida (opcional)
- Sin presupuesto

Uso:
    python test_nuevos_parametros.py
"""

import json
from datetime import datetime
from recommendation_service import generate_itinerary_request

def test_nuevos_parametros():
    """Test con los nuevos parámetros"""
    
    print("=== TEST NUEVOS PARÁMETROS SISTEMA ITINERARIOS ===\n")
    
    # Caso 1: Con coordenadas de Puerto Madero y zona preferida override
    print("🧪 Test 1: Coordenadas Puerto Madero + zona preferida Recoleta")
    user_id = 1
    request_data = {
        'fecha_visita': '2025-08-30',
        'hora_inicio': '10:00',
        'duracion_horas': 6,
        'latitud_origen': -34.6118,    # Puerto Madero (obligatorio)
        'longitud_origen': -58.3960,   # Puerto Madero (obligatorio)
        'zona_preferida': 'Recoleta', # Override zona preferida
        'categorias_preferidas': ['Museos', 'Gastronomía']
    }
    
    print(f"Request data: {json.dumps(request_data, indent=2)}")
    
    try:
        resultado = generate_itinerary_request(user_id, request_data)
        
        if 'error' in resultado:
            print(f"❌ Error: {resultado['error']}")
        else:
            print("✅ Itinerario generado exitosamente!")
            print(f"   • ID: {resultado.get('itinerario_id')}")
            print(f"   • Actividades: {len(resultado.get('actividades', []))}")
            print(f"   • Zona usada: {resultado.get('preferencias_usadas', {}).get('zona_preferida')}")
            
            # Mostrar primeras actividades con distancias
            actividades = resultado.get('actividades', [])
            if actividades:
                print(f"   • Primeras actividades:")
                for i, act in enumerate(actividades[:3], 1):
                    distancia = act.get('distancia_origen_km', 'N/A')
                    print(f"     {i}. {act.get('nombre')} ({act.get('categoria')}) - {distancia}km del origen")
    
    except Exception as e:
        print(f"❌ Error en test: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Caso 2: Sin coordenadas (debería fallar)
    print("🧪 Test 2: Sin coordenadas de origen (error esperado)")
    request_data_sin_coords = {
        'fecha_visita': '2025-08-30',
        'hora_inicio': '14:00',
        'duracion_horas': 4
        # Faltan latitud_origen y longitud_origen
    }
    
    try:
        resultado = generate_itinerary_request(user_id, request_data_sin_coords)
        
        if 'error' in resultado:
            print(f"✅ Error esperado: {resultado['error']}")
        else:
            print("❌ Debería haber fallado sin coordenadas")
    
    except Exception as e:
        print(f"❌ Error inesperado: {e}")
    
    print("\n" + "="*60 + "\n")
    
    # Caso 3: Con coordenadas de La Boca sin zona preferida
    print("🧪 Test 3: Coordenadas La Boca + zona de BD")
    request_data_la_boca = {
        'fecha_visita': '2025-08-30',
        'hora_inicio': '09:00',
        'duracion_horas': 8,
        'latitud_origen': -34.6345,    # La Boca
        'longitud_origen': -58.3635,   # La Boca
        'zona_preferida': None,       # Usar zona de BD del usuario
    }
    
    print(f"Request data: {json.dumps(request_data_la_boca, indent=2)}")
    
    try:
        resultado = generate_itinerary_request(4, request_data_la_boca)  # Usuario 4 = Lucía
        
        if 'error' in resultado:
            print(f"❌ Error: {resultado['error']}")
        else:
            print("✅ Itinerario generado exitosamente!")
            print(f"   • ID: {resultado.get('itinerario_id')}")
            print(f"   • Actividades: {len(resultado.get('actividades', []))}")
            print(f"   • Zona usada (de BD): {resultado.get('preferencias_usadas', {}).get('zona_preferida')}")
    
    except Exception as e:
        print(f"❌ Error en test: {e}")
    
    print("\n🏁 Tests de nuevos parámetros completados!")

if __name__ == "__main__":
    test_nuevos_parametros()
