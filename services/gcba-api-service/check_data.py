"""Script para verificar los datos en la base de datos"""
import psycopg2
import os
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('ECOBICI_DB_HOST', 'localhost'),
    'port': os.getenv('ECOBICI_DB_PORT', '5432'),
    'database': os.getenv('ECOBICI_DB_NAME', 'eco_bicis'),
    'user': os.getenv('ECOBICI_DB_USER', 'postgres'),
    'password': os.getenv('ECOBICI_DB_PASSWORD', 'admin')
}

try:
    conn = psycopg2.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    print("="*70)
    print("VERIFICACION DE DATOS EN BASE DE DATOS")
    print("="*70)
    
    # Contar estaciones
    cursor.execute("SELECT COUNT(*) FROM stations")
    total_stations = cursor.fetchone()[0]
    print(f"\nTotal de estaciones: {total_stations}")
    
    # Contar registros de estado
    cursor.execute("SELECT COUNT(*) FROM station_status")
    total_status = cursor.fetchone()[0]
    print(f"Total de registros de estado: {total_status}")
    
    # Estaciones con bicicletas disponibles
    cursor.execute("""
        SELECT COUNT(*) FROM latest_station_status 
        WHERE num_bikes_mechanical > 0
    """)
    stations_with_bikes = cursor.fetchone()[0]
    print(f"Estaciones con bicicletas: {stations_with_bikes}")
    
    # Total de bicicletas disponibles
    cursor.execute("""
        SELECT COALESCE(SUM(num_bikes_mechanical), 0) FROM latest_station_status
    """)
    total_bikes = cursor.fetchone()[0]
    print(f"Total bicicletas mecanicas disponibles: {total_bikes}")
    
    # Top 10 estaciones con mas bicicletas
    print(f"\nTop 10 estaciones con mas bicicletas:")
    cursor.execute("""
        SELECT name, num_bikes_mechanical, num_docks_available, status
        FROM latest_station_status
        WHERE num_bikes_mechanical > 0
        ORDER BY num_bikes_mechanical DESC
        LIMIT 10
    """)
    
    for i, (name, bikes, docks, status) in enumerate(cursor.fetchall(), 1):
        print(f"  {i:2d}. {name[:40]:<40} | {bikes:2d} bicis | {docks:2d} docks | {status}")
    
    # Top 5 barrios
    print(f"\nTop 5 barrios con mas estaciones:")
    cursor.execute("""
        SELECT barrio, total_stations 
        FROM stations_by_group 
        ORDER BY total_stations DESC 
        LIMIT 5
    """)
    
    for barrio, count in cursor.fetchall():
        print(f"  - {barrio}: {count} estaciones")
    
    cursor.close()
    conn.close()
    
    print("\n" + "="*70)
    if total_stations > 0 and total_status > 0:
        print("BASE DE DATOS POBLADA EXITOSAMENTE")
    else:
        print("ATENCION: Faltan datos en la base de datos")
    print("="*70)
    
except Exception as e:
    print(f"Error: {e}")

