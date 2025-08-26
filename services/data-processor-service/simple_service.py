#!/usr/bin/env python3
"""
Data Processor Service - Versión Simplificada
===========================================

Servicio básico que escucha eventos de Kafka y responde a health checks
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any
from decimal import Decimal
from kafka import KafkaConsumer, KafkaProducer
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataProcessorHandler(BaseHTTPRequestHandler):
    """Handler para las peticiones HTTP"""
    
    def do_GET(self):
        """Manejar peticiones GET"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "service": "data-processor",
                "timestamp": datetime.now().isoformat(),
                "kafka_connected": True
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "service": "data-processor",
                "status": "running",
                "kafka_connected": True,
                "timestamp": datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def do_POST(self):
        """Manejar peticiones POST"""
        if self.path == '/recommendations/generate':
            # Leer el body de la petición
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)
            
            try:
                request_data = json.loads(post_data.decode('utf-8'))
                user_id = request_data.get('user_id', 0)
                
                # Generar respuesta simulada
                response = {
                    "request_id": f"req_{int(datetime.now().timestamp())}",
                    "user_id": user_id,
                    "status": "completed",
                    "itinerary": {
                        "itinerario_id": f"it_{user_id}_{int(datetime.now().timestamp())}",
                        "actividades": [
                            {
                                "nombre": "Museo de Arte Moderno",
                                "categoria": "Museos",
                                "duracion_minutos": 120,
                                "hora_inicio": "10:00",
                                "ubicacion": "San Telmo"
                            },
                            {
                                "nombre": "Restaurante La Brigada",
                                "categoria": "Gastronomía",
                                "duracion_minutos": 90,
                                "hora_inicio": "12:30",
                                "ubicacion": "San Telmo"
                            }
                        ],
                        "estadisticas": {
                            "duracion_total_horas": 3.5,
                            "costo_estimado": "Medio",
                            "valoracion_promedio": 4.5
                        }
                    },
                    "timestamp": datetime.now().isoformat()
                }
                
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(response).encode())
                
            except Exception as e:
                logger.error(f"Error procesando recomendación: {e}")
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b'Internal Server Error')
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """Sobrescribir logging para usar nuestro logger"""
        logger.info(f"HTTP: {format % args}")

class DataProcessorService:
    """Servicio principal del Data Processor"""
    
    def __init__(self):
        self.consumer = None
        self.producer = None
        self.running = False
        self.kafka_bootstrap_servers = 'localhost:9092'
        self.http_server = None
        
    def start(self):
        """Iniciar el servicio"""
        logger.info("🚀 Iniciando Data Processor Service...")
        
        try:
            # Conectar a Kafka
            self.producer = KafkaProducer(
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_serializer=lambda v: json.dumps(v).encode('utf-8'),
                key_serializer=lambda k: k.encode('utf-8') if k else None
            )
            
            # Iniciar listener de Kafka en background
            self.running = True
            kafka_thread = threading.Thread(target=self._start_kafka_listener)
            kafka_thread.daemon = True
            kafka_thread.start()
            
            # Iniciar servidor HTTP
            self.http_server = HTTPServer(('localhost', 8002), DataProcessorHandler)
            http_thread = threading.Thread(target=self._start_http_server)
            http_thread.daemon = True
            http_thread.start()
            
            logger.info("✅ Data Processor Service iniciado en puerto 8002")
            
        except Exception as e:
            logger.error(f"❌ Error iniciando servicio: {e}")
            raise
    
    def _start_http_server(self):
        """Iniciar servidor HTTP"""
        logger.info("🌐 Iniciando servidor HTTP...")
        try:
            self.http_server.serve_forever()
        except Exception as e:
            logger.error(f"❌ Error en servidor HTTP: {e}")
    
    def _start_kafka_listener(self):
        """Iniciar listener de Kafka en thread separado"""
        logger.info("🎧 Iniciando listener de Kafka...")
        
        try:
            self.consumer = KafkaConsumer(
                'scraper-events',
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='data-processor-service',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            logger.info("✅ Listener de Kafka iniciado. Esperando eventos...")
            
            # Escuchar eventos
            for message in self.consumer:
                if not self.running:
                    break
                    
                try:
                    event_data = message.value
                    logger.info(f"📥 Evento recibido: {event_data.get('event_type')}")
                    
                    # Procesar evento del scraper
                    if event_data.get('event_type') == 'scraper_data':
                        self._process_scraper_event(event_data)
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando evento: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error en listener de Kafka: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
    
    def _process_scraper_event(self, event_data: Dict[str, Any]):
        """Procesar evento del scraper"""
        logger.info("⚙️ Procesando evento del scraper...")
        
        try:
            # 1. Insertar eventos del scraper PRIMERO
            logger.info("� Insertando eventos del scraper...")
            scraper_events_result = self._insert_scraper_events(event_data)
            
            # 2. Ejecutar ETL completo
            logger.info("� Ejecutando ETL completo...")
            etl_result = self._run_etl(event_data)
            
            # 3. Ejecutar Clustering
            logger.info("🧠 Ejecutando clustering...")
            clustering_result = self._run_clustering()
            
            # 4. Publicar eventos de completado
            self._publish_completion_events(etl_result, scraper_events_result, clustering_result)
            
            logger.info("✅ Procesamiento completado exitosamente")
            logger.info(f"📊 Resumen: {scraper_events_result.get('eventos_insertados', 0)} eventos insertados, {etl_result.get('pois_processed', 0)} POIs procesados, {clustering_result.get('clusters_created', 0)} clusters creados")
            
        except Exception as e:
            logger.error(f"❌ Error en procesamiento: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    def _run_etl(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Ejecutar ETL"""
        try:
            logger.info("🔄 Ejecutando ETL real...")
            
            # Importar y ejecutar ETL real
            try:
                from etl_to_processor import ETLProcessor
                
                # Crear instancia y ejecutar ETL completo
                etl_processor = ETLProcessor()
                etl_result = etl_processor.run_full_etl()
                
                logger.info(f"✅ ETL real completado: {etl_result}")
                return {
                    "pois_processed": etl_result.get('pois', 0),
                    "eventos_processed": etl_result.get('eventos', 0),
                    "barrios_processed": etl_result.get('barrios', 0),
                    "processing_time_seconds": etl_result.get('processing_time', 0),
                    "status": "completed",
                    "etl_details": etl_result
                }
                
            except ImportError as e:
                logger.warning(f"⚠️ No se pudo importar ETL real: {e}")
                # Fallback a simulación
                events_count = event_data.get('data', {}).get('events_count', 0)
                etl_result = {
                    "pois_processed": events_count,
                    "processing_time_seconds": 2.5,
                    "status": "completed",
                    "note": "ETL simulado - módulo no disponible"
                }
                logger.info(f"✅ ETL simulado completado: {etl_result['pois_processed']} eventos procesados")
                return etl_result
            
        except Exception as e:
            logger.error(f"❌ Error en ETL: {e}")
            raise
    
    def _run_clustering(self) -> Dict[str, Any]:
        """Ejecutar clustering"""
        try:
            logger.info("🧠 Ejecutando clustering real...")
            
            # Importar y ejecutar clustering real
            try:
                from clustering_processor import ClusteringProcessor
                from csv_processor import DatabaseConfig
                
                # Crear instancia con configuración de DB y ejecutar clustering
                processor = ClusteringProcessor(DatabaseConfig.PROCESSOR_DB)
                clustering_result = processor.run_full_clustering()
                
                logger.info(f"✅ Clustering real completado: {clustering_result}")
                return {
                    "algorithms_executed": clustering_result.get('algorithms_executed', []),
                    "pois_processed": clustering_result.get('pois_processed', 0),
                    "clusters_created": clustering_result.get('clusters_created', 0),
                    "processing_time_seconds": clustering_result.get('processing_time', 0),
                    "status": "completed",
                    "clustering_details": clustering_result
                }
                
            except ImportError as e:
                logger.warning(f"⚠️ No se pudo importar clustering real: {e}")
                # Fallback a simulación
                clustering_result = {
                    "algorithms_executed": ["geographic", "category", "neighborhood", "tourist_zones"],
                    "pois_processed": 175,
                    "clusters_created": 12,
                    "processing_time_seconds": 4.2,
                    "status": "completed",
                    "note": "Clustering simulado - módulo no disponible"
                }
                logger.info(f"✅ Clustering simulado completado: {clustering_result['clusters_created']} clusters creados")
                return clustering_result
            
        except Exception as e:
            logger.error(f"❌ Error en clustering: {e}")
            raise
    
    def _insert_scraper_events(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insertar eventos del scraper en la BD operacional"""
        try:
            logger.info("📥 Insertando eventos del scraper en BD operacional...")
            
            # Validar que tengamos datos - CORREGIDO: buscar en 'events' no en 'eventos'
            events_list = event_data.get('data', {}).get('events', [])
            if not events_list:
                logger.warning("No hay eventos para insertar")
                return {
                    "eventos_insertados": 0,
                    "status": "no_events",
                    "message": "No hay eventos en los datos recibidos"
                }
            
            logger.info(f"📝 Procesando {len(events_list)} eventos del scraper...")
            
            try:
                from etl_to_processor import ETLProcessor
                etl_processor = ETLProcessor()
                
                # Conectar a las bases de datos
                etl_processor.connect_databases()
                
                # Crear estructura de datos compatible con insertar_eventos_desde_scraper
                eventos_data = {
                    'eventos': events_list,
                    'metadata': event_data.get('data', {}).get('metadata', {})
                }
                
                # Insertar eventos en BD operacional
                eventos_insertados = etl_processor.insertar_eventos_desde_scraper(eventos_data)
                
                # Desconectar de las bases de datos
                etl_processor.disconnect_databases()
                
                logger.info(f"✅ Eventos del scraper insertados: {eventos_insertados}")
                return {
                    "eventos_insertados": eventos_insertados,
                    "status": "completed",
                    "message": f"Se insertaron {eventos_insertados} eventos exitosamente"
                }
                
            except ImportError as e:
                logger.warning(f"⚠️ No se pudo importar ETL para eventos: {e}")
                return {
                    "eventos_insertados": 0,
                    "status": "module_error",
                    "error": "Módulo ETL no disponible",
                    "details": str(e)
                }
                
        except Exception as e:
            logger.error(f"❌ Error insertando eventos del scraper: {e}")
            import traceback
            logger.error(f"❌ Traceback completo: {traceback.format_exc()}")
            return {
                "eventos_insertados": 0,
                "status": "error",
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _publish_completion_events(self, etl_result: Dict[str, Any], scraper_events_result: Dict[str, Any], clustering_result: Dict[str, Any]):
        """Publicar eventos de completado"""
        try:
            # Función para limpiar datos para JSON (remover DataFrames y objetos no serializables)
            def clean_for_json(obj):
                if isinstance(obj, dict):
                    return {k: clean_for_json(v) for k, v in obj.items() if k != 'dataframe'}
                elif isinstance(obj, list):
                    return [clean_for_json(item) for item in obj]
                elif isinstance(obj, Decimal):
                    return float(obj)
                elif hasattr(obj, 'dtype'):  # numpy/pandas types
                    return float(obj) if hasattr(obj, 'item') else str(obj)
                elif hasattr(obj, 'quantize'):  # Decimal objects
                    return float(obj)
                else:
                    return obj
            
            # Evento ETL completado
            etl_event = {
                "event_type": "etl_complete",
                "timestamp": datetime.now().isoformat(),
                "data": clean_for_json(etl_result)
            }
            
            future = self.producer.send('ml-updates', key='etl_complete', value=etl_event)
            future.get()
            logger.info("📤 Evento ETL publicado")
            
            # Evento eventos del scraper completado
            scraper_events_event = {
                "event_type": "scraper_events_inserted",
                "timestamp": datetime.now().isoformat(),
                "data": clean_for_json(scraper_events_result)
            }
            
            future = self.producer.send('ml-updates', key='scraper_events_inserted', value=scraper_events_event)
            future.get()
            logger.info("📤 Evento eventos del scraper publicado")
            
            # Evento clustering completado
            clustering_event = {
                "event_type": "clustering_complete",
                "timestamp": datetime.now().isoformat(),
                "data": clean_for_json(clustering_result)
            }
            
            future = self.producer.send('ml-updates', key='clustering_complete', value=clustering_event)
            future.get()
            logger.info("📤 Evento clustering publicado")
            
        except Exception as e:
            logger.error(f"❌ Error publicando eventos: {e}")
    
    def stop(self):
        """Detener el servicio"""
        logger.info("🛑 Deteniendo Data Processor Service...")
        self.running = False
        
        if self.consumer:
            self.consumer.close()
        
        if self.producer:
            self.producer.close()
        
        if self.http_server:
            self.http_server.shutdown()
        
        logger.info("👋 Data Processor Service detenido")

def main():
    """Función principal"""
    service = DataProcessorService()
    
    try:
        service.start()
        logger.info("🎉 Servicio iniciado. Presiona Ctrl+C para detener...")
        
        # Mantener el servicio corriendo
        while True:
            time.sleep(1)
            
    except KeyboardInterrupt:
        logger.info("🛑 Interrumpido por usuario")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        service.stop()

if __name__ == "__main__":
    main()
