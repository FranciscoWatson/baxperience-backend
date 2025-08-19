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
        """Ejecutar algoritmos de clustering (placeholder para futuro)"""
        logger.info("Preparando clustering...")
        
        # TODO: Implementar algoritmos de clustering
        logger.info("Clustering no implementado aun - coming soon!")
        
        self.results['clustering'] = {'status': 'pending'}
        return True
        
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
            print(f"   Estado: {clustering_results.get('status', 'unknown')}")
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
                
        if mode == 'full' and success:
            if not self.run_clustering():
                success = False
                
        return success

def main():
    """Función principal"""
    parser = argparse.ArgumentParser(description='BAXperience Data Processor')
    parser.add_argument(
        '--mode', 
        choices=['csv', 'etl', 'full'], 
        default='full',
        help='Modo de ejecución: csv (solo CSVs), etl (solo ETL), full (completo)'
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
