from scraper.turismo import scrap_turismo, formatear_para_data_processor
import json
from datetime import datetime
import os
import logging

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    """
    Función principal del scraper service - Genera JSON para el data processor
    """
    print("[scraper-service] Iniciando scraping de turismo...")
    
    # Ejecutar scraping
    eventos_raw = scrap_turismo()
    
    if eventos_raw:
        # Formatear para el data processor
        datos_json = formatear_para_data_processor(eventos_raw)
        
        # Guardar JSON para el data processor
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        archivo_json = f"eventos_turismo_{timestamp}.json"
        
        with open(archivo_json, 'w', encoding='utf-8') as f:
            json.dump(datos_json, f, ensure_ascii=False, indent=2)
        
        # Mostrar resumen en consola
        print(f"\n[scraper-service] SCRAPING COMPLETADO")
        print(f" Archivo JSON generado: {archivo_json}")
        print(f" Resumen de datos:")
        print(f"  • Total eventos: {datos_json['metadata']['total_eventos']}")
        print(f"  • Con coordenadas: {sum(1 for e in datos_json['eventos'] if e['latitud'] is not None)}")
        print(f"  • Organizadores únicos: {len(set(e['organizador'] for e in datos_json['eventos'] if e['organizador']))}")
        print(f"  • Barrios únicos: {len(set(e['barrio'] for e in datos_json['eventos'] if e['barrio']))}")
        
        # Mostrar ejemplo de evento
        if datos_json['eventos']:
            ejemplo = datos_json['eventos'][0]
            print(f"\n Ejemplo de evento:")
            print(f"  Nombre: {ejemplo['nombre']}")
            print(f"  Ubicación: {ejemplo['direccion_evento']} ({ejemplo['barrio']})")
            print(f"  Coordenadas: {ejemplo['latitud']}, {ejemplo['longitud']}")
            print(f"  Organizador: {ejemplo['organizador']}")
            print(f"  Días: {ejemplo['dias_semana']} | Precio: {ejemplo['categoria_precio']}")
        
        print(f"\n JSON listo para data processor en: {archivo_json}")
        
        # Enviar evento a Kafka automáticamente
        try:
            send_to_kafka(datos_json, archivo_json)
            print(f"✅ Evento enviado a Kafka automáticamente")
        except Exception as e:
            print(f"⚠️ Error enviando a Kafka: {e}")
            print(f"   Los datos están disponibles en: {archivo_json}")
        
        return datos_json
        
    else:
        print("[scraper-service]  No se pudieron obtener eventos")
        return None

def send_to_kafka(datos_json, archivo_json):
    """
    Enviar datos del scraper a Kafka automáticamente
    """
    try:
        from kafka import KafkaProducer
        
        # Conectar a Kafka
        producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            key_serializer=lambda k: k.encode('utf-8') if k else None
        )
        
        # Preparar evento para Kafka
        scraper_event = {
            "event_type": "scraper_data",
            "timestamp": datetime.now().isoformat(),
            "data": {
                "events_count": datos_json['metadata']['total_eventos'],
                "events": datos_json['eventos'][:3],  # Solo los primeros 3 para el log
                "source_file": archivo_json,
                "scraping_timestamp": datetime.now().isoformat(),
                "metadata": {
                    "total_eventos": datos_json['metadata']['total_eventos'],
                    "con_coordenadas": sum(1 for e in datos_json['eventos'] if e['latitud'] is not None),
                    "organizadores_unicos": len(set(e['organizador'] for e in datos_json['eventos'] if e['organizador'])),
                    "barrios_unicos": len(set(e['barrio'] for e in datos_json['eventos'] if e['barrio']))
                }
            }
        }
        
        # Enviar a Kafka
        future = producer.send(
            'scraper-events',
            key='scraper_data',
            value=scraper_event
        )
        future.get()  # Esperar confirmación
        
        producer.close()
        
        print(f"📤 Evento enviado a Kafka: {scraper_event['data']['events_count']} eventos")
        
    except ImportError:
        print("⚠️ kafka-python no está instalado. Instalando...")
        os.system("pip install kafka-python")
        # Reintentar después de instalar
        send_to_kafka(datos_json, archivo_json)
    except Exception as e:
        print(f"❌ Error enviando a Kafka: {e}")
        raise

if __name__ == "__main__":
    main()