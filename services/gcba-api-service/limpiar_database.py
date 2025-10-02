"""
Script para limpiar completamente la base de datos de EcoBici
ATENCION: Este script ELIMINA TODAS las tablas, vistas y datos
"""
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

DB_CONFIG = {
    'host': os.getenv('ECOBICI_DB_HOST', 'localhost'),
    'port': os.getenv('ECOBICI_DB_PORT', '5432'),
    'database': os.getenv('ECOBICI_DB_NAME', 'eco_bicis'),
    'user': os.getenv('ECOBICI_DB_USER', 'postgres'),
    'password': os.getenv('ECOBICI_DB_PASSWORD', 'admin')
}

def limpiar_solo_datos():
    """Elimina todos los registros pero mantiene las tablas"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("Eliminando todos los datos...")
        
        # Eliminar datos de las tablas (en orden correcto por FK)
        cursor.execute("DELETE FROM station_status;")
        print("  - Eliminados registros de station_status")
        
        cursor.execute("DELETE FROM stations;")
        print("  - Eliminados registros de stations")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\nOK Datos eliminados exitosamente (tablas intactas)")
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def limpiar_todo():
    """Elimina todas las tablas, vistas y funciones"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("Eliminando TODA la estructura de la base de datos...")
        
        # Eliminar vistas
        print("\n1. Eliminando vistas...")
        cursor.execute("DROP VIEW IF EXISTS latest_station_status CASCADE;")
        print("  - Vista latest_station_status eliminada")
        
        cursor.execute("DROP VIEW IF EXISTS top_stations_with_bikes CASCADE;")
        print("  - Vista top_stations_with_bikes eliminada")
        
        cursor.execute("DROP VIEW IF EXISTS stations_by_group CASCADE;")
        print("  - Vista stations_by_group eliminada")
        
        # Eliminar funciones
        print("\n2. Eliminando funciones...")
        cursor.execute("DROP FUNCTION IF EXISTS cleanup_old_status_records() CASCADE;")
        print("  - Funcion cleanup_old_status_records eliminada")
        
        # Eliminar tablas
        print("\n3. Eliminando tablas...")
        cursor.execute("DROP TABLE IF EXISTS station_status CASCADE;")
        print("  - Tabla station_status eliminada")
        
        cursor.execute("DROP TABLE IF EXISTS stations CASCADE;")
        print("  - Tabla stations eliminada")
        
        conn.commit()
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print("OK TODA la base de datos fue limpiada completamente")
        print("="*70)
        print("\nPara recrear la estructura ejecuta:")
        print("  python create_database.py")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def eliminar_base_datos():
    """Elimina la base de datos completa"""
    try:
        # Conectar a la base por defecto (postgres)
        conn = psycopg2.connect(
            host=DB_CONFIG['host'],
            port=DB_CONFIG['port'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database='postgres'
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Terminar todas las conexiones a la BD
        db_name = DB_CONFIG['database']
        cursor.execute(f"""
            SELECT pg_terminate_backend(pg_stat_activity.pid)
            FROM pg_stat_activity
            WHERE pg_stat_activity.datname = '{db_name}'
            AND pid <> pg_backend_pid();
        """)
        
        print(f"Eliminando base de datos '{db_name}'...")
        cursor.execute(f"DROP DATABASE IF EXISTS {db_name};")
        
        cursor.close()
        conn.close()
        
        print("\n" + "="*70)
        print(f"OK Base de datos '{db_name}' ELIMINADA COMPLETAMENTE")
        print("="*70)
        print("\nPara recrear todo desde cero ejecuta:")
        print("  python create_database.py")
        print("  python main.py")
        
        return True
        
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def main():
    print("="*70)
    print("LIMPIEZA DE BASE DE DATOS ECOBICI")
    print("="*70)
    print("\nOpciones:")
    print("  1. Limpiar SOLO los datos (mantiene tablas y estructura)")
    print("  2. Limpiar TODO (elimina tablas, vistas, funciones)")
    print("  3. ELIMINAR la base de datos completa")
    print("  4. Cancelar")
    
    try:
        opcion = input("\nSelecciona una opcion (1-4): ").strip()
        
        if opcion == '1':
            print("\n" + "="*70)
            confirmacion = input("CONFIRMA: Eliminar todos los datos? (escribe 'SI' para confirmar): ")
            if confirmacion == 'SI':
                limpiar_solo_datos()
            else:
                print("Cancelado")
                
        elif opcion == '2':
            print("\n" + "="*70)
            confirmacion = input("CONFIRMA: Eliminar TODAS las tablas y estructura? (escribe 'SI' para confirmar): ")
            if confirmacion == 'SI':
                limpiar_todo()
            else:
                print("Cancelado")
                
        elif opcion == '3':
            print("\n" + "="*70)
            print("ATENCION: Esto eliminara la base de datos COMPLETA!")
            confirmacion = input("CONFIRMA: Eliminar base de datos completa? (escribe 'ELIMINAR' para confirmar): ")
            if confirmacion == 'ELIMINAR':
                eliminar_base_datos()
            else:
                print("Cancelado")
                
        elif opcion == '4':
            print("Operacion cancelada")
            
        else:
            print("Opcion invalida")
            
    except KeyboardInterrupt:
        print("\n\nOperacion cancelada por el usuario")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())

