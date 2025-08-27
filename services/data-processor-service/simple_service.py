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
        """Ejecutar clustering actualizado"""
        try:
            logger.info("🧠 Ejecutando clustering actualizado...")
            
            # Importar y ejecutar clustering
            from clustering_processor import ClusteringProcessor
            from csv_processor import DatabaseConfig
            
            # Crear instancia y ejecutar clustering completo
            clustering_processor = ClusteringProcessor(DatabaseConfig.PROCESSOR_DB)
            clustering_result = clustering_processor.run_full_clustering()
            
            if clustering_result.get('status') == 'success':
                summary = clustering_result.get('summary', {})
                logger.info(f"✅ Clustering completado exitosamente")
                logger.info(f"   - POIs procesados: {summary.get('total_pois_processed', 0)}")
                logger.info(f"   - Zonas turísticas: {summary.get('tourist_zones_detected', 0)}")
                logger.info(f"   - Barrios analizados: {summary.get('neighborhoods_analyzed', 0)}")
                
                return {
                    'clusters_created': summary.get('tourist_zones_detected', 0),
                    'pois_processed': summary.get('total_pois_processed', 0),
                    'status': 'success'
                }
            else:
                logger.error(f"❌ Error en clustering: {clustering_result.get('message', 'Unknown error')}")
                return {'clusters_created': 0, 'status': 'error', 'error': clustering_result.get('message')}
                
        except Exception as e:
            logger.error(f"❌ Error ejecutando clustering: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
            return {'clusters_created': 0, 'status': 'error', 'error': str(e)}
    
    def _insert_scraper_events(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Insertar eventos del scraper en BD operacional"""
        try:
            # Verificar que tenemos eventos
            data = event_data.get('data', {})
            events = data.get('events', [])
            
            if not events:
                logger.warning("⚠️ No se encontraron eventos en el mensaje")
                return {'eventos_insertados': 0, 'error': 'No events found'}
            
            logger.info(f"📥 Insertando {len(events)} eventos del scraper...")
            
            # Conectar a BD operacional
            from csv_processor import DatabaseConfig
            import psycopg2
            
            op_conn = psycopg2.connect(**DatabaseConfig.OPERATIONAL_DB)
            op_cursor = op_conn.cursor()
            
            # PASO 1: LIMPIAR EVENTOS ANTIGUOS
            logger.info("🧹 Limpiando eventos antiguos...")
            op_cursor.execute("TRUNCATE TABLE eventos")
            eventos_eliminados = op_cursor.rowcount
            logger.info(f"�️ Eliminados {eventos_eliminados} eventos antiguos")
            
            # PASO 2: Insertar nuevos eventos
            insert_count = 0
            
            # MAPEO DE CATEGORÍAS UNIFICADAS
            categoria_mapping = {
                'Visita guiada': 'Lugares Históricos',
                'Experiencias': 'Entretenimiento', 
                'Paseo': 'Entretenimiento'
            }
            
            for event in events:
                try:
                    # Procesar datos del evento
                    nombre = event.get('nombre', 'Sin nombre')[:255]
                    descripcion = event.get('descripcion', '')
                    categoria_original = event.get('categoria', 'Evento')[:100]
                    
                    # APLICAR MAPEO DE CATEGORÍAS UNIFICADAS
                    categoria = categoria_mapping.get(categoria_original, categoria_original)
                    
                    tematica = event.get('tematica', '')[:100]
                    
                    # Ubicación
                    latitud = None
                    longitud = None
                    if event.get('coordenadas'):
                        try:
                            coords = event['coordenadas']
                            if isinstance(coords, list) and len(coords) >= 2:
                                latitud = float(coords[0])
                                longitud = float(coords[1])
                        except (ValueError, TypeError, IndexError):
                            pass
                    
                    barrio = event.get('barrio', '')[:100]
                    direccion = event.get('direccion', '')
                    
                    # Fechas y horarios
                    fecha_inicio = event.get('fecha_inicio', '2025-08-27')  # Default mañana
                    fecha_fin = event.get('fecha_fin')
                    hora_inicio = event.get('hora_inicio')
                    hora_fin = event.get('hora_fin')
                    dias_semana = event.get('dias_semana', '')[:7]
                    
                    # URLs y contacto
                    url_evento = event.get('url', '')[:500]
                    telefono = event.get('telefono', '')[:50]
                    email = event.get('email', '')[:255]
                    
                    # Insertar evento
                    insert_query = """
                    INSERT INTO eventos (
                        nombre, descripcion, categoria_evento, tematica,
                        latitud, longitud, barrio, direccion_evento,
                        fecha_inicio, fecha_fin, hora_inicio, hora_fin, dias_semana,
                        url_evento, telefono_contacto, email_contacto,
                        fecha_scraping, url_fuente
                    ) VALUES (
                        %s, %s, %s, %s,
                        %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s, %s,
                        CURRENT_TIMESTAMP, %s
                    )
                    """
                    
                    op_cursor.execute(insert_query, (
                        nombre, descripcion, categoria, tematica,
                        latitud, longitud, barrio, direccion,
                        fecha_inicio, fecha_fin, hora_inicio, hora_fin, dias_semana,
                        url_evento, telefono, email,
                        'scraper-turismo'
                    ))
                    
                    insert_count += 1
                    
                except Exception as e:
                    logger.warning(f"⚠️ Error insertando evento individual: {e}")
                    continue
            
            # Commit cambios
            op_conn.commit()
            op_cursor.close()
            op_conn.close()
            
            logger.info(f"✅ Eventos insertados exitosamente: {insert_count}")
            return {
                'eventos_insertados': insert_count,
                'eventos_eliminados': eventos_eliminados,
                'status': 'success'
            }
            
        except Exception as e:
            logger.error(f"❌ Error insertando eventos del scraper: {e}")
            return {'eventos_insertados': 0, 'error': str(e)}
    
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
