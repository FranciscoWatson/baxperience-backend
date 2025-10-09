#!/usr/bin/env python3
"""
NLP Service - Servicio de Procesamiento de Lenguaje Natural
============================================================

Servicio que escucha eventos de Kafka y procesa consultas en lenguaje natural
"""

import json
import logging
import threading
import time
from datetime import datetime
from typing import Dict, Any
from kafka import KafkaConsumer, KafkaProducer
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NLPServiceHandler(BaseHTTPRequestHandler):
    """Handler para las peticiones HTTP"""
    
    def do_GET(self):
        """Manejar peticiones GET"""
        if self.path == '/health':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "status": "healthy",
                "service": "nlp-service",
                "timestamp": datetime.now().isoformat(),
                "kafka_connected": True,
                "nlp_models_loaded": True
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        elif self.path == '/status':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            
            response = {
                "service": "nlp-service",
                "status": "running",
                "kafka_connected": True,
                "timestamp": datetime.now().isoformat()
            }
            
            self.wfile.write(json.dumps(response).encode())
            
        else:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not Found')
    
    def log_message(self, format, *args):
        """Sobrescribir logging para usar nuestro logger"""
        logger.info(f"HTTP: {format % args}")


class NLPService:
    """Servicio principal de NLP"""
    
    def __init__(self):
        self.consumer = None
        self.producer = None
        self.running = False
        self.kafka_bootstrap_servers = 'localhost:9092'
        self.http_server = None
        self.nlp_processor = None
        
    def start(self):
        """Iniciar el servicio"""
        logger.info("🚀 Iniciando NLP Service...")
        
        try:
            # Inicializar procesador NLP
            from nlp_processor import NLPProcessor
            self.nlp_processor = NLPProcessor()
            logger.info("✅ Procesador NLP inicializado")
            
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
            self.http_server = HTTPServer(('localhost', 5001), NLPServiceHandler)
            http_thread = threading.Thread(target=self._start_http_server)
            http_thread.daemon = True
            http_thread.start()
            
            logger.info("✅ NLP Service iniciado en puerto 5001")
            
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
                'nlp-requests',  # Tópico para solicitudes NLP
                bootstrap_servers=self.kafka_bootstrap_servers,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                group_id='nlp-service',
                auto_offset_reset='latest',
                enable_auto_commit=True
            )
            
            logger.info("✅ Listener de Kafka iniciado. Esperando solicitudes NLP...")
            
            # Escuchar eventos
            for message in self.consumer:
                if not self.running:
                    break
                    
                try:
                    event_data = message.value
                    logger.info(f"📥 Solicitud NLP recibida")
                    
                    # Procesar solicitud NLP
                    if event_data.get('event_type') == 'nlp_query':
                        self._process_nlp_query(event_data)
                        
                except Exception as e:
                    logger.error(f"❌ Error procesando solicitud: {e}")
                    
        except Exception as e:
            logger.error(f"❌ Error en listener de Kafka: {e}")
        finally:
            if self.consumer:
                self.consumer.close()
    
    def _process_nlp_query(self, event_data: Dict[str, Any]):
        """Procesar consulta NLP"""
        logger.info("🔍 Procesando consulta NLP...")
        
        try:
            # Extraer datos de la solicitud
            request_id = event_data.get('request_id', f"nlp_{int(datetime.now().timestamp())}")
            user_id = event_data.get('user_id')
            
            # El query está dentro de request_data
            request_data = event_data.get('request_data', {})
            query = request_data.get('query', '')
            
            logger.info(f"📋 Consulta NLP - Request ID: {request_id}, Usuario: {user_id}")
            logger.info(f"💬 Query: {query}")
            
            # Validar query
            if not query or not query.strip():
                error_msg = "Query vacío o inválido"
                logger.error(f"❌ {error_msg}")
                self._publish_nlp_error(request_id, error_msg)
                return
            
            # Procesar con el procesador NLP
            try:
                start_time = datetime.now()
                result = self.nlp_processor.process_query(query)
                end_time = datetime.now()
                
                processing_time = (end_time - start_time).total_seconds()
                
                logger.info(f"✅ Consulta procesada exitosamente: {result.get('confidence', 0):.2f} confianza")
                
                # Agregar metadata del procesamiento
                result['processing_metadata'] = {
                    'request_id': request_id,
                    'processing_time_seconds': processing_time,
                    'processed_at': end_time.isoformat(),
                    'service_version': '1.0.0'
                }
                
                # Publicar resultado exitoso
                self._publish_nlp_success(request_id, result)
                
            except Exception as e:
                error_msg = f"Error procesando consulta: {str(e)}"
                logger.error(f"❌ {error_msg}")
                import traceback
                logger.error(f"❌ Traceback: {traceback.format_exc()}")
                self._publish_nlp_error(request_id, error_msg)
                
        except Exception as e:
            logger.error(f"❌ Error procesando solicitud NLP: {e}")
            import traceback
            logger.error(f"❌ Traceback: {traceback.format_exc()}")
    
    def _publish_nlp_success(self, request_id: str, nlp_data: Dict[str, Any]):
        """Publicar resultado exitoso de NLP"""
        try:
            success_event = {
                "event_type": "nlp_processed",
                "status": "success",
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "data": nlp_data
            }
            
            future = self.producer.send('nlp-responses', key=request_id, value=success_event)
            future.get()
            logger.info(f"📤 Resultado NLP publicado - Request ID: {request_id}")
            
        except Exception as e:
            logger.error(f"❌ Error publicando resultado NLP: {e}")
    
    def _publish_nlp_error(self, request_id: str, error_message: str):
        """Publicar error de procesamiento NLP"""
        try:
            error_event = {
                "event_type": "nlp_error",
                "status": "error",
                "request_id": request_id,
                "timestamp": datetime.now().isoformat(),
                "error": {
                    "message": error_message,
                    "error_code": "NLP_PROCESSING_FAILED"
                }
            }
            
            future = self.producer.send('nlp-responses', key=request_id, value=error_event)
            future.get()
            logger.info(f"📤 Error NLP publicado - Request ID: {request_id}")
            
        except Exception as e:
            logger.error(f"❌ Error publicando error NLP: {e}")
    
    def stop(self):
        """Detener el servicio"""
        logger.info("🛑 Deteniendo NLP Service...")
        self.running = False
        
        if self.consumer:
            self.consumer.close()
        
        if self.producer:
            self.producer.close()
        
        if self.http_server:
            self.http_server.shutdown()
        
        logger.info("👋 NLP Service detenido")


def main():
    """Función principal"""
    service = NLPService()
    
    try:
        service.start()
        logger.info("🎉 Servicio NLP iniciado. Presiona Ctrl+C para detener...")
        
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

