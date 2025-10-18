import json
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import unicodedata

# Cargar variables de entorno manualmente
def load_env():
    env_vars = {}
    try:
        with open('.env', 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
    except:
        try:
            with open('.env', 'r', encoding='latin-1') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#') and '=' in line:
                        key, value = line.split('=', 1)
                        env_vars[key.strip()] = value.strip()
        except Exception as e:
            print(f"Error leyendo .env: {e}")
    return env_vars

env_vars = load_env()

# Configuración de la base de datos
DB_CONFIG = {
    'host': env_vars.get('OPERATIONAL_DB_HOST', 'localhost'),
    'port': env_vars.get('OPERATIONAL_DB_PORT', '5432'),
    'database': env_vars.get('OPERATIONAL_DB_NAME', 'OPERATIONAL_DB'),
    'user': env_vars.get('OPERATIONAL_DB_USER', 'postgres'),
    'password': env_vars.get('OPERATIONAL_DB_PASSWORD', 'admin')
}

def normalizar_texto(texto):
    """
    Normaliza el texto removiendo acentos y convirtiendo a minúsculas
    para hacer comparaciones más flexibles
    """
    if not texto:
        return ""
    # Convertir a minúsculas
    texto = texto.lower()
    # Remover acentos
    texto = ''.join(
        c for c in unicodedata.normalize('NFD', texto)
        if unicodedata.category(c) != 'Mn'
    )
    # Remover comillas y caracteres especiales
    texto = texto.replace('"', '').replace(',', ' ').replace('-', ' ')
    return texto.strip()

def extraer_palabras_clave(texto_normalizado):
    """
    Extrae las palabras clave más importantes del texto
    excluyendo palabras comunes
    """
    palabras_comunes = {'de', 'la', 'el', 'los', 'las', 'y', 'en', 'del', 'al'}
    palabras = texto_normalizado.split()
    return [p for p in palabras if p not in palabras_comunes and len(p) > 2]

def calcular_score_nombre(nombre_poi_norm, nombre_imp_norm):
    """
    Calcula un score de coincidencia entre 0 y 1
    Mayor score = mejor coincidencia
    """
    # Contención directa: score alto
    if nombre_imp_norm in nombre_poi_norm or nombre_poi_norm in nombre_imp_norm:
        return 0.9
    
    # Palabras clave compartidas
    palabras_poi = set(extraer_palabras_clave(nombre_poi_norm))
    palabras_imp = set(extraer_palabras_clave(nombre_imp_norm))
    
    if len(palabras_imp) == 0:
        return 0
    
    palabras_comunes = palabras_poi.intersection(palabras_imp)
    score = len(palabras_comunes) / len(palabras_imp)
    
    return score

def coordenadas_cercanas(lat1, lon1, lat2, lon2, tolerancia=0.005):
    """
    Verifica si dos coordenadas están cerca (dentro de la tolerancia)
    tolerancia de 0.005 es aproximadamente 555 metros
    """
    lat1 = float(lat1)
    lon1 = float(lon1)
    lat2 = float(lat2)
    lon2 = float(lon2)
    return abs(lat1 - lat2) < tolerancia and abs(lon1 - lon2) < tolerancia

def cargar_imperdibles():
    """Carga el JSON de imperdibles"""
    with open('imperdibles.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    return data['imperdibles']

def obtener_pois(conn):
    """Obtiene todos los POIs de la base de datos"""
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute("""
            SELECT id, nombre, latitud, longitud, is_imperdible
            FROM pois
        """)
        return cur.fetchall()

def marcar_imperdible(conn, poi_id):
    """Marca un POI como imperdible"""
    with conn.cursor() as cur:
        cur.execute("""
            UPDATE pois
            SET is_imperdible = TRUE
            WHERE id = %s
        """, (poi_id,))

def main():
    print("Iniciando proceso de marcado de imperdibles...")
    
    # Cargar imperdibles del JSON
    imperdibles = cargar_imperdibles()
    print(f"Cargados {len(imperdibles)} imperdibles del JSON")
    
    # Normalizar nombres de imperdibles
    imperdibles_normalizados = []
    for imp in imperdibles:
        imperdibles_normalizados.append({
            'nombre_original': imp['nombre'],
            'nombre_normalizado': normalizar_texto(imp['nombre']),
            'latitud': imp['latitud'],
            'longitud': imp['longitud']
        })
    
    # Conectar a la base de datos
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print("Conectado a la base de datos")
        
        # Obtener POIs
        pois = obtener_pois(conn)
        print(f"Obtenidos {len(pois)} POIs de la base de datos")
        
        marcados = 0
        encontrados = set()
        
        # Para cada imperdible, encontrar el mejor match
        for i, imp in enumerate(imperdibles_normalizados):
            mejores_candidatos = []
            
            # Buscar todos los POIs que estén cerca
            for poi in pois:
                coords_coinciden = coordenadas_cercanas(
                    poi['latitud'], poi['longitud'],
                    imp['latitud'], imp['longitud']
                )
                
                if coords_coinciden:
                    poi_nombre_norm = normalizar_texto(poi['nombre'])
                    score = calcular_score_nombre(poi_nombre_norm, imp['nombre_normalizado'])
                    
                    # Solo considerar si tiene al menos 1 palabra clave en común
                    if score > 0:
                        mejores_candidatos.append({
                            'poi': poi,
                            'score': score
                        })
            
            # Si hay candidatos, elegir el mejor
            if mejores_candidatos:
                # Ordenar por score descendente
                mejores_candidatos.sort(key=lambda x: x['score'], reverse=True)
                mejor = mejores_candidatos[0]
                poi = mejor['poi']
                
                encontrados.add(i)
                if not poi['is_imperdible']:
                    marcar_imperdible(conn, poi['id'])
                    marcados += 1
                    print(f"✓ Marcado: {poi['nombre']} (ID: {poi['id']}, score: {mejor['score']:.2f}) - coincide con '{imp['nombre_original']}'")
                else:
                    print(f"  Ya marcado: {poi['nombre']} (ID: {poi['id']})")
        
        # Confirmar cambios
        conn.commit()
        print(f"\n{'='*60}")
        print(f"Proceso completado: {marcados} POIs marcados como imperdibles")
        print(f"{'='*60}")
        
        # Mostrar imperdibles no encontrados
        no_encontrados = []
        for i, imp in enumerate(imperdibles_normalizados):
            if i not in encontrados:
                no_encontrados.append(imp['nombre_original'])
        
        if no_encontrados:
            print(f"\n⚠️  IMPERDIBLES NO ENCONTRADOS ({len(no_encontrados)}/{len(imperdibles)}):")
            print("="*60)
            for nombre in no_encontrados:
                print(f"  • {nombre}")
        else:
            print(f"\n✅ Todos los {len(imperdibles)} imperdibles fueron encontrados!")
        
    except Exception as e:
        print(f"Error: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
            print("Conexión cerrada")

if __name__ == "__main__":
    main()
