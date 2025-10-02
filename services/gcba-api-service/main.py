"""
Servicio principal de GCBA API - EcoBici
Consulta la API del Gobierno de la Ciudad de Buenos Aires y actualiza la base de datos
"""
import logging
import os
import sys
from datetime import datetime
from dotenv import load_dotenv
from gcba_api.ecobici import EcobiciAPI
from gcba_api.database import EcobiciDatabase

# Cargar variables de entorno desde .env
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f'gcba_service_{datetime.now().strftime("%Y%m%d")}.log')
    ]
)
logger = logging.getLogger(__name__)


def update_ecobici_data():
    """
    Función principal que actualiza los datos de EcoBici en la base de datos
    
    Returns:
        dict: Resumen de la actualización
    """
    api = None
    db = None
    summary = {
        'success': False,
        'timestamp': datetime.now().isoformat(),
        'stations_updated': 0,
        'status_records_inserted': 0,
        'errors': []
    }
    
    try:
        # Inicializar API y base de datos
        logger.info("="*70)
        logger.info("INICIANDO ACTUALIZACIÓN DE DATOS DE ECOBICI")
        logger.info("="*70)
        
        api = EcobiciAPI()
        db = EcobiciDatabase()
        db.connect()
        
        # Obtener datos de la API
        logger.info("\n[1/4] Consultando API del GCBA...")
        raw_data = api.get_all_data()
        logger.info(f"✓ Datos obtenidos correctamente")
        
        # Formatear datos para la base de datos
        logger.info("\n[2/4] Procesando y formateando datos...")
        formatted_data = api.format_for_database(raw_data)
        
        metadata = formatted_data['metadata']
        logger.info(f"✓ Total estaciones: {metadata['total_stations']}")
        logger.info(f"✓ Total estados: {metadata['total_status']}")
        logger.info(f"✓ Última actualización (info): {datetime.fromtimestamp(metadata['last_updated_info'])}")
        logger.info(f"✓ Última actualización (status): {datetime.fromtimestamp(metadata['last_updated_status'])}")
        
        # Insertar/actualizar estaciones
        logger.info("\n[3/4] Actualizando estaciones en base de datos...")
        stations_count = db.upsert_stations(formatted_data['stations'])
        summary['stations_updated'] = stations_count
        
        # Insertar estados
        logger.info("\n[4/4] Insertando registros de estado...")
        status_count = db.insert_station_status(formatted_data['status'])
        summary['status_records_inserted'] = status_count
        
        # Obtener estadísticas actualizadas
        logger.info("\n" + "="*70)
        logger.info("ESTADÍSTICAS DE LA BASE DE DATOS")
        logger.info("="*70)
        stats = db.get_statistics()
        
        logger.info(f"\n📊 Resumen General:")
        logger.info(f"  • Total de estaciones: {stats['total_stations']}")
        logger.info(f"  • Total de registros históricos: {stats['total_status_records']}")
        logger.info(f"  • Estaciones con bicicletas disponibles: {stats['stations_with_bikes']}")
        logger.info(f"  • Total bicicletas mecánicas disponibles: {stats['total_bikes_available']}")
        logger.info(f"  • Total docks disponibles: {stats['total_docks_available']}")
        
        if stats['top_neighborhoods']:
            logger.info(f"\n🏘️  Top 5 Barrios con más estaciones:")
            for barrio, count in stats['top_neighborhoods']:
                logger.info(f"    {count:3d} estaciones - {barrio}")
        
        # Mostrar algunas estaciones con más bicicletas
        logger.info(f"\n🚲 Estaciones con más bicicletas disponibles:")
        latest = db.get_latest_status(limit=10)
        for i, row in enumerate(latest[:10], 1):
            # row es una tupla, ajustar índices según la vista latest_station_status
            station_id = row[0]
            name = row[1]
            bikes = row[8]  # num_bikes_mechanical
            docks = row[9]  # num_docks_available
            status_str = row[10]  # status
            logger.info(f"    {i:2d}. {name} ({station_id})")
            logger.info(f"        🚲 {bikes} bicis | 🅿️  {docks} docks | Status: {status_str}")
        
        summary['success'] = True
        
        logger.info("\n" + "="*70)
        logger.info("✅ ACTUALIZACIÓN COMPLETADA EXITOSAMENTE")
        logger.info("="*70)
        
    except Exception as e:
        error_msg = f"Error durante la actualización: {e}"
        logger.error(f"\n❌ {error_msg}")
        summary['errors'].append(error_msg)
        summary['success'] = False
        
    finally:
        # Cerrar conexiones
        if db:
            db.disconnect()
    
    return summary


def cleanup_old_data(days=7):
    """
    Limpia registros antiguos de la base de datos
    
    Args:
        days: Número de días a mantener (por defecto 7)
    """
    try:
        logger.info(f"\n🧹 Limpiando registros antiguos (>{days} días)...")
        db = EcobiciDatabase()
        db.connect()
        
        deleted = db.cleanup_old_records(days=days)
        logger.info(f"✓ Eliminados {deleted} registros antiguos")
        
        db.disconnect()
        
    except Exception as e:
        logger.error(f"❌ Error limpiando registros antiguos: {e}")


def main():
    """
    Función principal del servicio
    """
    try:
        # Verificar que existan las variables de entorno necesarias
        required_env_vars = [
            'GCBA_CLIENT_ID',
            'GCBA_CLIENT_SECRET',
            'ECOBICI_DB_HOST',
            'ECOBICI_DB_NAME',
            'ECOBICI_DB_USER',
            'ECOBICI_DB_PASSWORD'
        ]
        
        missing_vars = [var for var in required_env_vars if not os.getenv(var)]
        if missing_vars:
            logger.error(f"❌ Faltan variables de entorno: {', '.join(missing_vars)}")
            logger.info("\n💡 Tip: Asegúrate de tener un archivo .env con:")
            for var in required_env_vars:
                logger.info(f"   {var}=tu_valor")
            sys.exit(1)
        
        # Actualizar datos
        summary = update_ecobici_data()
        
        # Limpiar datos antiguos (opcional, descomenta si lo necesitas)
        # cleanup_old_data(days=7)
        
        # Retornar código de salida
        return 0 if summary['success'] else 1
        
    except KeyboardInterrupt:
        logger.info("\n\n⚠️  Proceso interrumpido por el usuario")
        return 130
    except Exception as e:
        logger.error(f"\n❌ Error fatal: {e}")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)

