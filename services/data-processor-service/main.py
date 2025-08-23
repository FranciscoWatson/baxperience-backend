"""
BAXperience Data Processor - Main Entry Point
=============================================

Orquestador principal que ejecuta todo el pipeline de procesamiento de datos:

1. Procesar CSVs → BD Operacional
2. ETL: BD Operacional → BD Data Processor
3. (Futuro) Ejecutar algoritmos de clustering

Uso:
    python main.py --mode=csv          # Solo procesar CSVs
    python main.py --mode=etl          # Solo ejecutar ETL
    python main.py --mode=full         # Pipeline completo (default)

Autor: BAXperience Team
"""

import argparse
import sys
import time
from datetime import datetime
import logging

from csv_processor import CSVProcessor
from etl_to_processor import ETLProcessor
from clustering_processor import ClusteringProcessor
# from clustering_etl_original import ClusteringETLOriginal  # Archivo eliminado

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_processor_main.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class DataProcessorOrchestrator:
    """Orquestador principal del procesamiento de datos"""
    
    def __init__(self):
        self.start_time = None
        self.results = {}
        
    def print_banner(self):
        """Mostrar banner inicial"""
        banner = """
===============================================================
                    BAXperience Data Processor                
                                                              
      Museos | Gastronomia | Monumentos | Entretenimiento    
                                                              
              Transformando datos en experiencias             
===============================================================
        """
        print(banner)
        
    def run_csv_processing(self) -> bool:
        """Ejecutar procesamiento de CSVs"""
        logger.info("Iniciando procesamiento de CSVs...")
        
        try:
            processor = CSVProcessor()
            csv_results = processor.process_all_csvs()
            
            self.results['csv_processing'] = csv_results
            total_pois = sum(csv_results.values())
            
            logger.info(f"Procesamiento de CSVs completado: {total_pois} POIs cargados")
            return True
            
        except Exception as e:
            logger.error(f"Error en procesamiento de CSVs: {e}")
            return False
            
    def run_etl_processing(self) -> bool:
        """Ejecutar ETL a BD Data Processor"""
        logger.info("Iniciando ETL a BD Data Processor...")
        
        try:
            etl = ETLProcessor()
            etl_results = etl.run_full_etl()
            
            self.results['etl_processing'] = etl_results
            
            logger.info("ETL completado exitosamente")
            return True
            
        except Exception as e:
            logger.error(f"Error en ETL: {e}")
            return False
            
    def run_clustering(self) -> bool:
        """Ejecutar algoritmos de clustering según ETL original"""
        logger.info("Iniciando algoritmos de clustering ETL original...")
        
        try:
            # Usar la misma configuración que el ETL
            from csv_processor import DatabaseConfig
            proc_db_config = DatabaseConfig.PROCESSOR_DB
            
            # Ejecutar clustering original (ya implementado)
            clustering = ClusteringProcessor(proc_db_config)
            clustering_results = clustering.run_full_clustering()
            
            if clustering_results.get('status') == 'error':
                logger.error(f"Error en clustering ETL: {clustering_results.get('message')}")
                self.results['clustering'] = {'status': 'failed', 'error': clustering_results.get('message')}
                return False
            
            # Extraer métricas del resumen
            summary = clustering_results.get('summary', {})
            
            self.results['clustering'] = {
                'status': 'completed',
                'pois_processed': summary.get('total_pois_processed', 0),
                'algorithms_executed': summary.get('algorithms_executed', 0),
                'successful_algorithms': summary.get('successful_algorithms', []),
                'tourist_zones': summary.get('tourist_zones_detected', 0),
                'neighborhoods': summary.get('neighborhoods_analyzed', 0)
            }
            
            logger.info(f"Clustering completado: {summary.get('total_pois_processed', 0)} POIs procesados")
            logger.info(f"Zonas turísticas detectadas: {summary.get('tourist_zones_detected', 0)}")
            return True
            
        except Exception as e:
            logger.error(f"Error en clustering ETL: {e}")
            self.results['clustering'] = {'status': 'failed', 'error': str(e)}
            return False
    
    def run_recommendations(self) -> bool:
        """Ejecutar sistema de recomendaciones"""
        logger.info("Iniciando sistema de recomendaciones...")
        
        try:
            from recommendation_service import generate_itinerary_request
            
            # Simular request de usuario
            user_id = 123
            request_data = {
                'categorias_preferidas': ['Museos', 'Gastronomía'],
                'zona_preferida': 'Palermo',
                'duracion_preferida': 8,
                'presupuesto': 'medio',
                'tipo_compania': 'pareja'
            }
            
            # Generar itinerario de prueba
            result = generate_itinerary_request(user_id, request_data)
            
            if 'error' in result:
                logger.error(f"Error en recomendaciones: {result['error']}")
                self.results['recommendations'] = {'status': 'failed', 'error': result['error']}
                return False
            
            # Extraer métricas
            self.results['recommendations'] = {
                'status': 'completed',
                'itinerario_id': result.get('itinerario_id', 'N/A'),
                'actividades_generadas': len(result.get('actividades', [])),
                'duracion_horas': result.get('estadisticas', {}).get('duracion_total_horas', 0),
                'costo_estimado': result.get('estadisticas', {}).get('costo_estimado', 'N/A'),
                'pois_analizados': result.get('metadata', {}).get('total_pois_analizados', 0)
            }
            
            logger.info(f"Recomendaciones completadas: {len(result.get('actividades', []))} actividades generadas")
            return True
            
        except Exception as e:
            logger.error(f"Error en recomendaciones: {e}")
            self.results['recommendations'] = {'status': 'failed', 'error': str(e)}
            return False
        
    def print_summary(self):
        """Mostrar resumen de resultados"""
        end_time = time.time()
        duration = end_time - self.start_time
        
        print("\n" + "="*70)
        print(f"{'RESUMEN DE EJECUCIÓN':^70}")
        print("="*70)
        print(f"Duracion total: {duration:.2f} segundos")
        print(f"Finalizado: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        if 'csv_processing' in self.results:
            print("PROCESAMIENTO DE CSVs:")
            csv_results = self.results['csv_processing']
            for categoria, count in csv_results.items():
                print(f"   {categoria.title():20}: {count:4} POIs")
            print(f"   {'TOTAL':20}: {sum(csv_results.values()):4} POIs")
            print()
            
        if 'etl_processing' in self.results:
            print("ETL A DATA PROCESSOR:")
            etl_results = self.results['etl_processing']
            for proceso, count in etl_results.items():
                print(f"   {proceso.title():20}: {count:4} registros")
            print()
            
        if 'clustering' in self.results:
            print("CLUSTERING:")
            clustering_results = self.results['clustering']
            status = clustering_results.get('status', 'unknown')
            print(f"   Estado: {status}")
            
            if status == 'completed':
                print(f"   POIs procesados: {clustering_results.get('pois_processed', 0)}")
                print(f"   Algoritmos ejecutados: {clustering_results.get('algorithms_executed', 0)}")
                algorithms = clustering_results.get('successful_algorithms', [])
                print(f"   Algoritmos exitosos: {', '.join(algorithms) if algorithms else 'Ninguno'}")
                print(f"   Zonas turísticas: {clustering_results.get('tourist_zones', 0)}")
                print(f"   Barrios analizados: {clustering_results.get('neighborhoods', 0)}")
            elif status == 'failed':
                print(f"   Error: {clustering_results.get('error', 'Desconocido')}")
            print()
            
        if 'recommendations' in self.results:
            print("SISTEMA DE RECOMENDACIONES:")
            rec_results = self.results['recommendations']
            status = rec_results.get('status', 'unknown')
            print(f"   Estado: {status}")
            
            if status == 'completed':
                print(f"   Itinerario ID: {rec_results.get('itinerario_id', 'N/A')}")
                print(f"   Actividades generadas: {rec_results.get('actividades_generadas', 0)}")
                print(f"   Duración: {rec_results.get('duracion_horas', 0):.1f} horas")
                print(f"   Costo estimado: {rec_results.get('costo_estimado', 'N/A')}")
                print(f"   POIs analizados: {rec_results.get('pois_analizados', 0)}")
            elif status == 'failed':
                print(f"   Error: {rec_results.get('error', 'Desconocido')}")
            print()
            
        print("="*70)
        
    def run_pipeline(self, mode: str = 'full') -> bool:
        """Ejecutar pipeline según el modo especificado"""
        self.start_time = time.time()
        success = True
        
        logger.info(f"Iniciando pipeline en modo: {mode}")
        
        if mode in ['csv', 'full']:
            if not self.run_csv_processing():
                success = False
                
        if mode in ['etl', 'full'] and success:
            if not self.run_etl_processing():
                success = False
                
        if mode in ['clustering', 'full'] and success:
            if not self.run_clustering():
                success = False
                
        if mode in ['recommendations', 'full'] and success:
            if not self.run_recommendations():
                success = False
                
        return success

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='BAXperience Data Processor')
    parser.add_argument(
        '--mode', 
        choices=['csv', 'etl', 'clustering', 'recommendations', 'full'], 
        default='full',
        help='Modo de ejecución: csv (solo CSVs), etl (solo ETL), clustering (solo clustering), recommendations (solo recomendaciones), full (completo)'
    )
    parser.add_argument(
        '--verbose', 
        action='store_true',
        help='Habilitar logging detallado'
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        
    orchestrator = DataProcessorOrchestrator()
    orchestrator.print_banner()
    
    try:
        success = orchestrator.run_pipeline(args.mode)
        orchestrator.print_summary()
        
        if success:
            print("Pipeline ejecutado exitosamente!")
            sys.exit(0)
        else:
            print("Pipeline fallo. Ver logs para detalles.")
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\nPipeline interrumpido por el usuario")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Error critico: {e}")
        print(f"Error critico: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
