"""
Test para NLP Service usando Kafka
"""

import json
import time
from datetime import datetime
from kafka import KafkaProducer, KafkaConsumer

KAFKA_BOOTSTRAP_SERVERS = 'localhost:9092'

def test_nlp_query(query: str):
    """Enviar una consulta NLP a través de Kafka y esperar respuesta"""
    
    print(f"\n🔍 Enviando consulta: '{query}'")
    
    # Crear producer
    producer = KafkaProducer(
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_serializer=lambda v: json.dumps(v).encode('utf-8'),
        key_serializer=lambda k: k.encode('utf-8') if k else None
    )
    
    # Crear consumer para respuestas
    consumer = KafkaConsumer(
        'nlp-responses',
        bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
        value_deserializer=lambda m: json.loads(m.decode('utf-8')),
        auto_offset_reset='latest',
        enable_auto_commit=False,
        consumer_timeout_ms=15000  # 15 segundos timeout
    )
    
    # Generar request ID
    request_id = f"test_nlp_{int(datetime.now().timestamp())}"
    
    # Enviar solicitud
    message = {
        "event_type": "nlp_query",
        "request_id": request_id,
        "user_id": 123,
        "query": query,
        "timestamp": datetime.now().isoformat()
    }
    
    future = producer.send('nlp-requests', key=request_id, value=message)
    future.get(timeout=5)
    print(f"📤 Solicitud enviada - Request ID: {request_id}")
    
    # Esperar respuesta
    print("⏳ Esperando respuesta del servicio NLP...")
    
    for message in consumer:
        event_data = message.value
        
        if event_data.get('request_id') == request_id:
            print(f"\n✅ Respuesta recibida:")
            print(json.dumps(event_data, indent=2, ensure_ascii=False))
            break
    
    producer.close()
    consumer.close()


def main():
    """Ejecutar tests"""
    print("="*70)
    print("TEST DE NLP SERVICE - VÍA KAFKA")
    print("="*70)
    
    # Consultas de prueba en español
    spanish_queries = [
        "quiero comer en un restaurante de carne",
        "busco una parrilla en Palermo",
        "dónde puedo almorzar algo argentino",
        "recomiendame un museo de arte",
        "busco un bar en San Telmo"
    ]
    
    # Consultas de prueba en inglés
    english_queries = [
        "I want to eat at a steakhouse",
        "looking for a restaurant in Recoleta",
        "where can I find museums"
    ]
    
    print("\n📝 PRUEBAS EN ESPAÑOL:")
    print("-"*70)
    for query in spanish_queries[:2]:  # Solo 2 queries para no saturar
        try:
            test_nlp_query(query)
            time.sleep(2)  # Esperar entre consultas
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n📝 PRUEBAS EN INGLÉS:")
    print("-"*70)
    for query in english_queries[:1]:  # Solo 1 query
        try:
            test_nlp_query(query)
            time.sleep(2)
        except Exception as e:
            print(f"❌ Error: {e}")
    
    print("\n" + "="*70)
    print("TESTS COMPLETADOS")
    print("="*70)


if __name__ == "__main__":
    main()

