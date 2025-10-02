"""
Módulo para interactuar con la API de EcoBici del Gobierno de la Ciudad de Buenos Aires
"""
import requests
import os
from datetime import datetime
import logging
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

logger = logging.getLogger(__name__)

class EcobiciAPI:
    """Cliente para la API de EcoBici GBFS (General Bikeshare Feed Specification)"""
    
    BASE_URL = "https://apitransporte.buenosaires.gob.ar/ecobici/gbfs"
    
    def __init__(self, client_id=None, client_secret=None):
        """
        Inicializa el cliente de la API
        
        Args:
            client_id: Client ID de la API del GCBA (si no se provee, se lee de env)
            client_secret: Client Secret de la API del GCBA (si no se provee, se lee de env)
        """
        self.client_id = client_id or os.getenv('GCBA_CLIENT_ID')
        self.client_secret = client_secret or os.getenv('GCBA_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            raise ValueError(
                "Se requieren GCBA_CLIENT_ID y GCBA_CLIENT_SECRET. "
                "Deben estar en las variables de entorno o pasarse al constructor."
            )
        
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'BAXperience/1.0 (Tourism Platform)'
        })
    
    def _make_request(self, endpoint):
        """
        Realiza una petición GET a la API
        
        Args:
            endpoint: Endpoint de la API (sin el base URL)
            
        Returns:
            dict: Respuesta JSON de la API
        """
        url = f"{self.BASE_URL}/{endpoint}"
        params = {
            'client_id': self.client_id,
            'client_secret': self.client_secret
        }
        
        try:
            logger.info(f"Consultando API: {endpoint}")
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            logger.info(f"✓ Respuesta recibida de {endpoint}")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"✗ Error consultando {endpoint}: {e}")
            raise
    
    def get_station_information(self):
        """
        Obtiene información estática de todas las estaciones
        
        Returns:
            dict: Información de estaciones en formato GBFS
        """
        return self._make_request('stationInformation')
    
    def get_station_status(self):
        """
        Obtiene el estado en tiempo real de todas las estaciones
        
        Returns:
            dict: Estado actual de las estaciones
        """
        return self._make_request('stationStatus')
    
    def get_all_data(self):
        """
        Obtiene toda la información (estática + tiempo real) de las estaciones
        
        Returns:
            dict: Diccionario con 'information' y 'status'
        """
        information = self.get_station_information()
        status = self.get_station_status()
        
        return {
            'information': information,
            'status': status,
            'fetched_at': datetime.now().isoformat()
        }
    
    def format_for_database(self, raw_data):
        """
        Formatea los datos crudos para inserción en base de datos
        
        Args:
            raw_data: Datos crudos de get_all_data()
            
        Returns:
            dict: Datos formateados con 'stations' y 'status'
        """
        stations = []
        station_statuses = []
        
        # Procesar información de estaciones
        info_data = raw_data['information'].get('data', {})
        for station in info_data.get('stations', []):
            # Extraer grupos/barrios
            groups = station.get('groups', [])
            
            station_data = {
                'station_id': station.get('station_id'),
                'name': station.get('name', '').strip(),
                'physical_configuration': station.get('physical_configuration'),
                'lat': station.get('lat'),
                'lon': station.get('lon'),
                'address': station.get('address', '').strip(),
                'cross_street': station.get('cross_street', '').strip() if station.get('cross_street') else None,
                'post_code': station.get('post_code', '').strip(),
                'capacity': station.get('capacity', 0),
                'is_charging_station': station.get('is_charging_station', False),
                'groups': groups if groups else [],
                'nearby_distance': station.get('nearby_distance', 1000)
            }
            stations.append(station_data)
        
        # Procesar estado de estaciones
        status_data = raw_data['status'].get('data', {})
        for status in status_data.get('stations', []):
            # Extraer solo bicicletas mecánicas (ignorar ebikes)
            bikes_types = status.get('num_bikes_available_types', {})
            num_bikes_mechanical = bikes_types.get('mechanical', 0)
            
            status_data_dict = {
                'station_id': status.get('station_id'),
                'num_bikes_mechanical': num_bikes_mechanical,
                'num_bikes_disabled': status.get('num_bikes_disabled', 0),
                'num_docks_available': status.get('num_docks_available', 0),
                'num_docks_disabled': status.get('num_docks_disabled', 0),
                'last_reported': status.get('last_reported'),
                'is_charging_station': status.get('is_charging_station', False),
                'status': status.get('status', 'UNKNOWN'),
                'is_installed': status.get('is_installed', 1),
                'is_renting': status.get('is_renting', 1),
                'is_returning': status.get('is_returning', 1),
                'traffic': status.get('traffic')
            }
            station_statuses.append(status_data_dict)
        
        logger.info(f"✓ Formateados {len(stations)} estaciones y {len(station_statuses)} estados")
        
        return {
            'stations': stations,
            'status': station_statuses,
            'metadata': {
                'total_stations': len(stations),
                'total_status': len(station_statuses),
                'fetched_at': raw_data['fetched_at'],
                'last_updated_info': raw_data['information'].get('last_updated'),
                'last_updated_status': raw_data['status'].get('last_updated')
            }
        }


def test_api():
    """Función de prueba para verificar conectividad con la API"""
    try:
        api = EcobiciAPI()
        print("\n[TEST] Probando conexión con API de EcoBici...")
        
        # Probar información de estaciones
        info = api.get_station_information()
        stations = info.get('data', {}).get('stations', [])
        print(f"✓ Información de estaciones: {len(stations)} estaciones encontradas")
        
        if stations:
            example = stations[0]
            print(f"\nEjemplo de estación:")
            print(f"  ID: {example.get('station_id')}")
            print(f"  Nombre: {example.get('name')}")
            print(f"  Ubicación: {example.get('address')}")
            print(f"  Capacidad: {example.get('capacity')} bicicletas")
            print(f"  Barrio(s): {example.get('groups')}")
        
        # Probar estado de estaciones
        status = api.get_station_status()
        statuses = status.get('data', {}).get('stations', [])
        print(f"\n✓ Estado de estaciones: {len(statuses)} estados encontrados")
        
        if statuses:
            example_status = statuses[0]
            bikes_types = example_status.get('num_bikes_available_types', {})
            print(f"\nEjemplo de estado:")
            print(f"  Station ID: {example_status.get('station_id')}")
            print(f"  Bicis mecánicas disponibles: {bikes_types.get('mechanical', 0)}")
            print(f"  Docks disponibles: {example_status.get('num_docks_available')}")
            print(f"  Estado: {example_status.get('status')}")
        
        print("\n✓ TEST EXITOSO - API funcionando correctamente")
        return True
        
    except Exception as e:
        print(f"\n✗ TEST FALLIDO: {e}")
        return False


if __name__ == "__main__":
    # Ejecutar test si se corre directamente
    test_api()

