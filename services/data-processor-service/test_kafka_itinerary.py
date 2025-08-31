"""
Test para enviar eventos de solicitud de itinerario via Kafka
al Data Processor Service
"""

import json
import time
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ItineraryRequestTester:
    """Tester para solicitudes de itinerario via Kafka"""
    
    def __init__(self):
        self.producer = None
        self.consumer = None
        self.kafka_servers = 'localhost:9092'
        
    def connect(self):
        """Conectar a Kafka"""
        try:
            # Productor para enviar solicitudes
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            
            # Consumidor para recibir respuestas
            self.consumer = KafkaConsumer(
                'itinerary-responses',
                bootstrap_servers=self.kafka_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='itinerary-test-client',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            logger.info("✅ Conectado a Kafka")
            return True
            
        except Exception as e:
            logger.error(f"❌ Error conectando a Kafka: {e}")
            return False
    
    def send_itinerary_request(self, user_id: int, request_data: dict = None, request_id: str = None):
        """Enviar solicitud de itinerario"""
        if not self.producer:
            logger.error("❌ Productor no conectado")
            return None
        
        if not request_id:
            request_id = f"test_req_{int(datetime.now().timestamp())}"
        
        if not request_data:
            request_data = {}
        
        # Construir evento
        event = {
            "event_type": "itinerary_request",
            "request_id": request_id,
            "user_id": user_id,
            "request_data": request_data,
            "timestamp": datetime.now().isoformat(),
            "source": "test_client"
        }
        
        try:
            # Enviar evento
            future = self.producer.send('itinerary-requests', key=request_id, value=event)
            future.get(timeout=10)  # Esperar confirmación
            
            logger.info(f"📤 Solicitud enviada - Request ID: {request_id}, Usuario: {user_id}")
            return request_id
            
        except Exception as e:
            logger.error(f"❌ Error enviando solicitud: {e}")
            return None
    
    def wait_for_response(self, request_id: str, timeout: int = 30):
        """Esperar respuesta del servicio"""
        if not self.consumer:
            logger.error("❌ Consumidor no conectado")
            return None
        
        logger.info(f"⏳ Esperando respuesta para Request ID: {request_id} (timeout: {timeout}s)")
        
        start_time = time.time()
        
        try:
            for message in self.consumer:
                if time.time() - start_time > timeout:
                    logger.warning(f"⏰ Timeout esperando respuesta para {request_id}")
                    break
                
                response = message.value
                
                # Verificar si es la respuesta que esperamos
                if response.get('request_id') == request_id:
                    logger.info(f"📥 Respuesta recibida para {request_id}")
                    return response
                
                # Log de otras respuestas
                logger.debug(f"📥 Respuesta para otro request: {response.get('request_id')}")
        
        except Exception as e:
            logger.error(f"❌ Error esperando respuesta: {e}")
        
        return None
    
    def disconnect(self):
        """Desconectar de Kafka"""
        if self.producer:
            self.producer.close()
        if self.consumer:
            self.consumer.close()
        logger.info("👋 Desconectado de Kafka")

def test_itinerary_scenarios():
    """Test con diferentes escenarios de itinerarios"""
    
    print("=== TEST DE SOLICITUDES DE ITINERARIO VIA KAFKA ===\n")
    
    tester = ItineraryRequestTester()
    
    if not tester.connect():
        print("❌ No se pudo conectar a Kafka")
        return
    
    # Escenarios de prueba
    test_scenarios = [
        {
            'name': 'Usuario foodie con preferencias de BD',
            'user_id': 1,  # Francisco - foodie urbano
            'request_data': {
                'fecha_visita': '2025-08-30',
                'hora_inicio': '10:00',  # Inicio a las 10:00 am
                'duracion_horas': 6,
                'latitud_origen': -34.6118,
                'longitud_origen': -58.3960,
                'zona_preferida': None,  # Usar de BD: Puerto Madero
            }
        },
        {
            'name': 'Usuario cultural con override de zona',
            'user_id': 2,  # María - cultural
            'request_data': {
                'fecha_visita': '2025-08-30',
                'hora_inicio': '14:00',  # Inicio después del almuerzo
                'duracion_horas': 4,
                'latitud_origen': -34.5875,
                'longitud_origen': -58.3974,
                'zona_preferida': 'Recoleta',  # Override de zona
            }
        },
        {
            'name': 'Aventurera con coordenadas específicas',
            'user_id': 4,  # Lucía - aventurera
            'request_data': {
                'fecha_visita': '2025-08-30',
                'hora_inicio': '09:00',  # Inicio temprano
                'duracion_horas': 8,
                'latitud_origen': -34.6345,
                'longitud_origen': -58.3635,
                'zona_preferida': None,  # Usar de BD: La Boca
            }
        },
        {
            'name': 'Usuario que prefiere EVENTOS - debe priorizar eventos',
            'user_id': 7,  # Diego - Le gustan: Entretenimiento, Eventos, Gastronomía
            'request_data': {
                'fecha_visita': '2025-08-30',
                'hora_inicio': '11:00',
                'duracion_horas': 6,
                'latitud_origen': -34.6037,
                'longitud_origen': -58.3816,
                'zona_preferida': None,  # Usar de BD
            }
        },
        {
            'name': 'Usuario SIN gastronomía - NO debe incluir horarios de comida',
            'user_id': 8,  # Camila - Le gustan: Lugares Históricos, Monumentos, Museos (NO Gastronomía)
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
            'name': 'Usuario inexistente (test de error)',
            'user_id': 999,
            'request_data': {
                'fecha_visita': '2025-08-30',
                'hora_inicio': '11:30',  # Hora justo antes del almuerzo
                'duracion_horas': 4,
                'latitud_origen': -34.6037,
                'longitud_origen': -58.3816,
            }
        }
    ]
    
    try:
        for i, scenario in enumerate(test_scenarios, 1):
            print(f"{'='*60}")
            print(f"ESCENARIO {i}: {scenario['name']}")
            print(f"Usuario: {scenario['user_id']}")
            print(f"Request data: {scenario['request_data']}")
            print(f"{'='*60}")
            
            # Enviar solicitud
            request_id = tester.send_itinerary_request(
                scenario['user_id'], 
                scenario['request_data']
            )
            
            if request_id:
                # Esperar respuesta
                response = tester.wait_for_response(request_id, timeout=45)
                
                if response:
                    print(f"✅ RESPUESTA RECIBIDA:")
                    print(f"   • Status: {response.get('status')}")
                    print(f"   • Event Type: {response.get('event_type')}")
                    print(f"   • Timestamp: {response.get('timestamp')}")
                    
                    if response.get('status') == 'success':
                        data = response.get('data', {})
                        actividades = data.get('actividades', [])
                        prefs = data.get('preferencias_usadas', {})
                        
                        print(f"   • Itinerario ID: {data.get('itinerario_id')}")
                        print(f"   • Actividades: {len(actividades)}")
                        print(f"   • Zona usada: {prefs.get('zona_preferida')}")
                        print(f"   • Categorías preferidas (BD): {prefs.get('categorias_preferidas', [])}")
                        print(f"   • Tiempo de procesamiento: {data.get('processing_metadata', {}).get('processing_time_seconds', 'N/A')}s")
                        
                        if actividades:
                            print(f"   📋 TODAS LAS ACTIVIDADES GENERADAS:")
                            for j, act in enumerate(actividades, 1):
                                horario = f"{act.get('horario_inicio', 'N/A')} - {act.get('horario_fin', 'N/A')}"
                                distancia = act.get('distancia_origen_km', 'N/A')
                                score = act.get('score_personalizado', 'N/A')
                                item_type = act.get('item_type', 'poi')
                                print(f"     {j}. {act.get('nombre', 'Sin nombre')} ({act.get('categoria', 'Sin cat')})")
                                print(f"        ⏰ {horario} | 📍 {act.get('barrio', 'Sin barrio')} | 🎯 Score: {score}")
                                print(f"        📏 Distancia: {distancia}km | 🏷️ Tipo: {item_type}")
                                if act.get('valoracion_promedio', 0) > 0:
                                    print(f"        ⭐ Valoración: {act.get('valoracion_promedio')}/5")
                                print("")
                    
                    elif response.get('status') == 'error':
                        error = response.get('error', {})
                        print(f"   • Error: {error.get('message')}")
                        print(f"   • Sugerencias: {error.get('suggestions', [])}")
                
                else:
                    print(f"❌ No se recibió respuesta (timeout)")
            
            else:
                print(f"❌ No se pudo enviar la solicitud")
            
            print(f"\n{'='*60}\n")
            
            # Pausa entre escenarios
            if i < len(test_scenarios):
                time.sleep(2)
    
    finally:
        tester.disconnect()
    
    print("🏁 Test de solicitudes completado!")

if __name__ == "__main__":
    test_itinerary_scenarios()
