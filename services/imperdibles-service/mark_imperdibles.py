import json
import psycopg2
from psycopg2.extras import RealDictCursor
import os
import unicodedata
import math

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

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calcula la distancia en metros entre dos puntos usando la fórmula de Haversine
    Más preciso que solo comparar diferencias de coordenadas
    """
    lat1, lon1, lat2, lon2 = map(float, [lat1, lon1, lat2, lon2])
    
    # Radio de la Tierra en metros
    R = 6371000
    
    # Convertir a radianes
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)
    
    # Fórmula de Haversine
    a = math.sin(delta_lat/2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon/2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    
    distance = R * c
    return distance

def normalizar_texto(texto):
    """
    Normaliza el texto removiendo acentos, caracteres especiales 
    y convirtiendo a minúsculas para comparaciones más flexibles
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
    # Remover comillas, guiones y caracteres especiales, reemplazar por espacios
    texto = texto.replace('"', '').replace(',', ' ').replace('-', ' ').replace('(', ' ').replace(')', ' ')
    # Normalizar espacios múltiples
    texto = ' '.join(texto.split())
    return texto.strip()

def extraer_palabras_clave(texto_normalizado):
    """
    Extrae las palabras clave más importantes del texto
    excluyendo palabras comunes (stopwords)
    """
    palabras_comunes = {
        'de', 'la', 'el', 'los', 'las', 'y', 'en', 'del', 'al', 'a',
        'un', 'una', 'por', 'con', 'para', 'museo', 'centro', 'casa',
        'sala', 'estadio', 'teatro', 'plaza', 'parque', 'calle'
    }
    palabras = texto_normalizado.split()
    return [p for p in palabras if p not in palabras_comunes and len(p) > 2]

def calcular_score_nombre(nombre_poi_norm, nombre_imp_norm):
    """
    Calcula un score de coincidencia entre 0 y 1 basado en:
    1. Contención directa (score alto)
    2. Palabras clave compartidas (score proporcional)
    3. Orden de palabras (bonus)
    """
    # 1. Contención completa o casi completa
    if nombre_imp_norm in nombre_poi_norm:
        return 1.0
    if nombre_poi_norm in nombre_imp_norm:
        return 0.95
    
    # 2. Palabras clave compartidas
    palabras_poi = extraer_palabras_clave(nombre_poi_norm)
    palabras_imp = extraer_palabras_clave(nombre_imp_norm)
    
    if len(palabras_imp) == 0:
        return 0
    
    # Calcular intersección
    palabras_poi_set = set(palabras_poi)
    palabras_imp_set = set(palabras_imp)
    palabras_comunes = palabras_poi_set.intersection(palabras_imp_set)
    
    # Score base: proporción de palabras del imperdible que están en el POI
    score = len(palabras_comunes) / len(palabras_imp_set)
    
    # 3. Bonus por orden de palabras (si las palabras están en orden)
    if score > 0 and len(palabras_comunes) >= 2:
        # Verificar si las palabras comunes aparecen en el mismo orden
        indices_poi = [i for i, p in enumerate(palabras_poi) if p in palabras_comunes]
        indices_imp = [i for i, p in enumerate(palabras_imp) if p in palabras_comunes]
        
        if indices_poi == indices_imp:
            score = min(1.0, score * 1.2)  # Bonus del 20%
    
    return score

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
    print("="*70)
    print("INICIANDO PROCESO DE MARCADO DE IMPERDIBLES")
    print("="*70)
    
    # Cargar imperdibles del JSON
    imperdibles = cargar_imperdibles()
    print(f"\n✓ Cargados {len(imperdibles)} imperdibles del JSON")
    
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
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        print(f"✓ Conectado a la base de datos: {DB_CONFIG['database']}")
        
        # Obtener POIs
        pois = obtener_pois(conn)
        print(f"✓ Obtenidos {len(pois)} POIs de la base de datos\n")
        
        # Constantes para el matching
        DISTANCIA_MAXIMA = 500  # metros
        SCORE_MINIMO = 0.4  # Score mínimo de nombre para considerar un match
        
        marcados = 0
        encontrados = {}  # Diccionario para guardar matches con sus scores
        
        print("-"*70)
        print("BUSCANDO MATCHES...")
        print("-"*70)
        
        # Para cada imperdible, encontrar el mejor match
        for i, imp in enumerate(imperdibles_normalizados, 1):
            mejores_candidatos = []
            
            print(f"\n[{i}/{len(imperdibles_normalizados)}] Buscando: {imp['nombre_original']}")
            
            # Buscar todos los POIs que estén cerca y tengan nombre similar
            for poi in pois:
                # Calcular distancia real
                distancia = haversine_distance(
                    poi['latitud'], poi['longitud'],
                    imp['latitud'], imp['longitud']
                )
                
                # Solo considerar POIs dentro del rango de distancia
                if distancia <= DISTANCIA_MAXIMA:
                    poi_nombre_norm = normalizar_texto(poi['nombre'])
                    score_nombre = calcular_score_nombre(poi_nombre_norm, imp['nombre_normalizado'])
                    
                    # Solo considerar si el score es razonable
                    if score_nombre >= SCORE_MINIMO:
                        mejores_candidatos.append({
                            'poi': poi,
                            'score_nombre': score_nombre,
                            'distancia': distancia,
                            # Score combinado: 70% nombre, 30% distancia inversa
                            'score_total': score_nombre * 0.7 + (1 - distancia/DISTANCIA_MAXIMA) * 0.3
                        })
            
            # Si hay candidatos, elegir el mejor por score total
            if mejores_candidatos:
                # Ordenar por score total descendente
                mejores_candidatos.sort(key=lambda x: x['score_total'], reverse=True)
                mejor = mejores_candidatos[0]
                poi = mejor['poi']
                
                # Mostrar información del match
                print(f"  → MATCH ENCONTRADO:")
                print(f"     POI: {poi['nombre']}")
                print(f"     Score nombre: {mejor['score_nombre']:.2f}")
                print(f"     Distancia: {mejor['distancia']:.1f}m")
                print(f"     Score total: {mejor['score_total']:.2f}")
                
                # Guardar el match
                encontrados[i-1] = {
                    'imperdible': imp['nombre_original'],
                    'poi': poi,
                    'score': mejor['score_total'],
                    'distancia': mejor['distancia']
                }
                
                # Marcar si no estaba marcado
                if not poi['is_imperdible']:
                    marcar_imperdible(conn, poi['id'])
                    marcados += 1
                    print(f"     ✓ MARCADO como imperdible (ID: {poi['id']})")
                else:
                    print(f"     ⚠ Ya estaba marcado (ID: {poi['id']})")
                
                # Mostrar otros candidatos si los hay
                if len(mejores_candidatos) > 1:
                    print(f"     Otros candidatos encontrados ({len(mejores_candidatos)-1}):")
                    for candidato in mejores_candidatos[1:3]:  # Mostrar máximo 2 más
                        print(f"       • {candidato['poi']['nombre']} "
                              f"(score: {candidato['score_total']:.2f}, "
                              f"dist: {candidato['distancia']:.1f}m)")
            else:
                print(f"  ✗ NO SE ENCONTRÓ MATCH")
                print(f"     (revisá las coordenadas o el nombre en la BD)")
        
        # Confirmar cambios
        conn.commit()
        
        # RESUMEN FINAL
        print("\n" + "="*70)
        print("RESUMEN DEL PROCESO")
        print("="*70)
        print(f"\n✓ POIs marcados como imperdibles: {marcados}")
        print(f"✓ Matches encontrados: {len(encontrados)}/{len(imperdibles)}")
        print(f"✓ Ya marcados previamente: {len(encontrados) - marcados}")
        
        # Mostrar imperdibles no encontrados
        no_encontrados = []
        for i in range(len(imperdibles_normalizados)):
            if i not in encontrados:
                no_encontrados.append(imperdibles_normalizados[i]['nombre_original'])
        
        if no_encontrados:
            print(f"\n⚠️  IMPERDIBLES NO ENCONTRADOS ({len(no_encontrados)}/{len(imperdibles)}):")
            print("-"*70)
            for nombre in no_encontrados:
                imp_data = next(imp for imp in imperdibles_normalizados if imp['nombre_original'] == nombre)
                print(f"  • {nombre}")
                print(f"    Coordenadas: ({imp_data['latitud']}, {imp_data['longitud']})")
            print("\n💡 Sugerencias:")
            print("   - Verificá que estos POIs existan en la base de datos")
            print("   - Revisá las coordenadas en el JSON")
            print("   - Revisá que los nombres coincidan (al menos parcialmente)")
        else:
            print(f"\n✅ ¡ÉXITO! Todos los {len(imperdibles)} imperdibles fueron encontrados!")
        
        print("\n" + "="*70)
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        if conn:
            conn.rollback()
            print("✓ Rollback ejecutado")
    finally:
        if conn:
            conn.close()
            print("✓ Conexión cerrada")

if __name__ == "__main__":
    main()
