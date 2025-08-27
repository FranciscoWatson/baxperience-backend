#!/usr/bin/env python3
"""
Test directo del servicio de recomendaciones
===========================================

Test para verificar las mejoras en la lógica de clustering sin usar Kafka
"""

import sys
import logging
from datetime import datetime

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_recommendation_service():
    """Test directo del servicio de recomendaciones"""
    
    print("=== TEST DIRECTO DEL SERVICIO DE RECOMENDACIONES ===\n")
    
    try:
        # Importar el servicio
        from recommendation_service import RecommendationService
        
        # Crear instancia del servicio
        service = RecommendationService()
        service.connect_database()
        service.connect_operational_database()
        
        print("✅ Servicio de recomendaciones inicializado")
        
        # Test 1: Usuario foodie con preferencias de BD
        print("\n" + "="*60)
        print("TEST 1: Usuario foodie (ID: 1) - 6 horas desde 10:00")
        print("="*60)
        
        user_id = 1
        request_data = {
            'fecha_visita': '2025-08-30',  # Actualizado a 2025
            'hora_inicio': '10:00',
            'duracion_horas': 6,
            'categorias_preferidas': None,  # Usar de BD
            'zona_preferida': None,  # Usar de BD: Puerto Madero
            'presupuesto': None  # Usar de BD: alto
        }
        
        start_time = datetime.now()
        resultado = service.generate_itinerary(user_id, request_data)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        if 'error' in resultado:
            print(f"❌ Error: {resultado['error']}")
        else:
            actividades = resultado.get('actividades', [])
            eventos = [act for act in actividades if act.get('item_type') == 'evento']
            
            print(f"✅ Itinerario generado exitosamente")
            print(f"   • Itinerario ID: {resultado.get('itinerario_id')}")
            print(f"   • Actividades totales: {len(actividades)}")
            print(f"   • Eventos incluidos: {len(eventos)}")
            print(f"   • Tiempo de procesamiento: {processing_time:.3f}s")
            print(f"   • Zona usada: {resultado.get('preferencias_usadas', {}).get('zona_preferida')}")
            print(f"   • Presupuesto: {resultado.get('preferencias_usadas', {}).get('presupuesto')}")
            
            if actividades:
                print(f"   • Actividades generadas:")
                for i, act in enumerate(actividades, 1):
                    tipo = "EVENTO" if act.get('item_type') == 'evento' else "POI"
                    print(f"     {i}. {act.get('nombre')} ({act.get('categoria')}, {act.get('barrio')}) [{tipo}]")
                    if act.get('horario_inicio'):
                        print(f"        Horario: {act.get('horario_inicio')} - {act.get('horario_fin')}")
        
        # Test 2: Usuario cultural con override
        print("\n" + "="*60)
        print("TEST 2: Usuario cultural (ID: 2) - 4 horas desde 14:00")
        print("="*60)
        
        user_id = 2
        request_data = {
            'fecha_visita': '2025-08-30',  # Actualizado a 2025
            'hora_inicio': '14:00',
            'duracion_horas': 4,
            'categorias_preferidas': ['Museos'],
            'zona_preferida': 'Recoleta',
            'presupuesto': 'medio'
        }
        
        start_time = datetime.now()
        resultado = service.generate_itinerary(user_id, request_data)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        if 'error' in resultado:
            print(f"❌ Error: {resultado['error']}")
        else:
            actividades = resultado.get('actividades', [])
            eventos = [act for act in actividades if act.get('item_type') == 'evento']
            
            print(f"✅ Itinerario generado exitosamente")
            print(f"   • Itinerario ID: {resultado.get('itinerario_id')}")
            print(f"   • Actividades totales: {len(actividades)}")
            print(f"   • Eventos incluidos: {len(eventos)}")
            print(f"   • Tiempo de procesamiento: {processing_time:.3f}s")
            
            if actividades:
                print(f"   • Actividades generadas:")
                for i, act in enumerate(actividades, 1):
                    tipo = "EVENTO" if act.get('item_type') == 'evento' else "POI"
                    print(f"     {i}. {act.get('nombre')} ({act.get('categoria')}, {act.get('barrio')}) [{tipo}]")
                    if act.get('horario_inicio'):
                        print(f"        Horario: {act.get('horario_inicio')} - {act.get('horario_fin')}")
        
        # Test 3: Usuario aventurero con presupuesto bajo
        print("\n" + "="*60)
        print("TEST 3: Usuario aventurero (ID: 4) - 8 horas desde 09:00")
        print("="*60)
        
        user_id = 4
        request_data = {
            'fecha_visita': '2025-08-30',  # Actualizado a 2025
            'hora_inicio': '09:00',
            'duracion_horas': 8,
            'zona_preferida': None,  # Usar de BD: La Boca
            'presupuesto': 'bajo'
        }
        
        start_time = datetime.now()
        resultado = service.generate_itinerary(user_id, request_data)
        end_time = datetime.now()
        
        processing_time = (end_time - start_time).total_seconds()
        
        if 'error' in resultado:
            print(f"❌ Error: {resultado['error']}")
        else:
            actividades = resultado.get('actividades', [])
            eventos = [act for act in actividades if act.get('item_type') == 'evento']
            
            print(f"✅ Itinerario generado exitosamente")
            print(f"   • Itinerario ID: {resultado.get('itinerario_id')}")
            print(f"   • Actividades totales: {len(actividades)}")
            print(f"   • Eventos incluidos: {len(eventos)}")
            print(f"   • Tiempo de procesamiento: {processing_time:.3f}s")
            
            if actividades:
                print(f"   • Actividades generadas:")
                for i, act in enumerate(actividades, 1):
                    tipo = "EVENTO" if act.get('item_type') == 'evento' else "POI"
                    print(f"     {i}. {act.get('nombre')} ({act.get('categoria')}, {act.get('barrio')}) [{tipo}]")
                    if act.get('horario_inicio'):
                        print(f"        Horario: {act.get('horario_inicio')} - {act.get('horario_fin')}")
        
        # Limpiar conexiones
        service.disconnect_database()
        
        print("\n" + "="*60)
        print("🏁 Test directo completado!")
        print("="*60)
        
    except Exception as e:
        logger.error(f"❌ Error en test directo: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_recommendation_service()
