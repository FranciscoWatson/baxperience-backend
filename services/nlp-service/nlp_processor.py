"""
NLP Processor - Procesamiento de Lenguaje Natural
================================================

Módulo que procesa consultas en lenguaje natural y extrae entidades
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from unidecode import unidecode
import psycopg2
from psycopg2.extras import RealDictCursor
from rapidfuzz import fuzz, process
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

logger = logging.getLogger(__name__)


class NLPProcessor:
    """
    Procesador NLP para consultas de usuarios
    Soporta español e inglés sin APIs pagas
    """
    
    def __init__(self):
        """Inicializar procesador NLP"""
        # Configuración de base de datos
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'port': int(os.getenv('DB_PORT', 5432)),
            'database': os.getenv('DB_NAME', 'baxperience_operational'),
            'user': os.getenv('DB_USER', 'postgres'),
            'password': os.getenv('DB_PASSWORD', '')
        }
        
        # Cargar modelos NLP si están disponibles
        self.nlp_es = None
        self.nlp_en = None
        self._load_spacy_models()
        
        # Cargar entidades de la base de datos
        self.categories = {}
        self.subcategories = {}
        self.barrios = []
        self._load_database_entities()
        
        # Inicializar patrones de intención
        self._initialize_intent_patterns()
    
    def _load_spacy_models(self):
        """Cargar modelos spaCy (opcional)"""
        try:
            import spacy
            self.nlp_es = spacy.load("es_core_news_md")
            logger.info("✅ Modelo español de spaCy cargado")
        except:
            logger.warning("⚠️ Modelo español de spaCy no disponible")
            self.nlp_es = None
        
        try:
            import spacy
            self.nlp_en = spacy.load("en_core_web_md")
            logger.info("✅ Modelo inglés de spaCy cargado")
        except:
            logger.warning("⚠️ Modelo inglés de spaCy no disponible")
            self.nlp_en = None
    
    def _load_database_entities(self):
        """Cargar categorías, subcategorías y barrios desde la base de datos"""
        try:
            conn = psycopg2.connect(**self.db_config)
            cur = conn.cursor(cursor_factory=RealDictCursor)
            
            # Cargar categorías
            cur.execute("SELECT id, nombre FROM categorias")
            for row in cur.fetchall():
                self.categories[row['id']] = {
                    'name': row['nombre'],
                    'name_lower': row['nombre'].lower(),
                    'name_normalized': unidecode(row['nombre'].lower())
                }
            
            # Cargar subcategorías
            cur.execute("SELECT id, categoria_id, nombre FROM subcategorias")
            for row in cur.fetchall():
                self.subcategories[row['id']] = {
                    'name': row['nombre'],
                    'name_lower': row['nombre'].lower(),
                    'name_normalized': unidecode(row['nombre'].lower()),
                    'categoria_id': row['categoria_id']
                }
            
            # Cargar barrios únicos
            cur.execute("SELECT DISTINCT barrio FROM pois WHERE barrio IS NOT NULL ORDER BY barrio")
            self.barrios = [row['barrio'] for row in cur.fetchall()]
            
            conn.close()
            
            logger.info(f"✅ Cargadas {len(self.categories)} categorías, {len(self.subcategories)} subcategorías, {len(self.barrios)} barrios")
            
        except Exception as e:
            logger.error(f"❌ Error cargando entidades de la BD: {e}")
            # Establecer valores por defecto
            self._set_default_entities()
    
    def _set_default_entities(self):
        """Establecer entidades por defecto si la BD no está disponible"""
        self.categories = {
            1: {'name': 'Museos', 'name_lower': 'museos', 'name_normalized': 'museos'},
            2: {'name': 'Gastronomía', 'name_lower': 'gastronomía', 'name_normalized': 'gastronomia'},
            3: {'name': 'Monumentos', 'name_lower': 'monumentos', 'name_normalized': 'monumentos'},
            4: {'name': 'Lugares Históricos', 'name_lower': 'lugares históricos', 'name_normalized': 'lugares historicos'},
            5: {'name': 'Entretenimiento', 'name_lower': 'entretenimiento', 'name_normalized': 'entretenimiento'},
            6: {'name': 'Eventos', 'name_lower': 'eventos', 'name_normalized': 'eventos'}
        }
        self.barrios = ['Palermo', 'Recoleta', 'San Telmo', 'Puerto Madero', 'Belgrano']
    
    def _initialize_intent_patterns(self):
        """Definir patrones de regex para detección de intención"""
        # Patrones de intención: BUSCAR
        self.search_patterns_es = [
            r'\b(quiero|busco|necesito|estoy buscando|me gustaria|quisiera)\b',
            r'\b(donde|dónde)\b.*\b(puedo|podría|hay|encuentro)\b',
            r'\b(recomendame|recomiendame|recomienda|sugiere|sugerí)\b',
            r'\b(conocer|visitar|ir a|ver)\b'
        ]
        
        self.search_patterns_en = [
            r'\b(want|need|looking for|would like|i\'d like)\b',
            r'\b(where)\b.*\b(can|could|is|are)\b',
            r'\b(recommend|suggest|show me)\b',
            r'\b(visit|see|go to|explore)\b'
        ]
        
        # Palabras clave por categoría
        self.food_keywords_es = [
            'comer', 'comida', 'restaurante', 'almorzar', 'cenar', 'desayunar',
            'parrilla', 'asado', 'pizza', 'café', 'bar', 'cerveza', 'vino',
            'cocina', 'gastronomía', 'gastronómico', 'carne', 'bife'
        ]
        
        self.food_keywords_en = [
            'eat', 'food', 'restaurant', 'lunch', 'dinner', 'breakfast',
            'grill', 'bbq', 'pizza', 'cafe', 'coffee', 'bar', 'beer', 'wine',
            'cuisine', 'gastronomy', 'steak', 'meat'
        ]
        
        self.culture_keywords_es = [
            'museo', 'arte', 'cultura', 'historia', 'monumento', 'histórico',
            'exhibición', 'exposición', 'galería', 'patrimonio'
        ]
        
        self.culture_keywords_en = [
            'museum', 'art', 'culture', 'history', 'monument', 'historic',
            'exhibition', 'gallery', 'heritage'
        ]
        
        self.entertainment_keywords_es = [
            'cine', 'teatro', 'show', 'concierto', 'evento', 'espectáculo',
            'diversión', 'entretenimiento', 'música'
        ]
        
        self.entertainment_keywords_en = [
            'cinema', 'movie', 'theater', 'show', 'concert', 'event',
            'entertainment', 'fun', 'music'
        ]
    
    def detect_language(self, text: str) -> str:
        """Detectar idioma del texto (español o inglés)"""
        spanish_indicators = ['quiero', 'busco', 'donde', 'dónde', 'comer', 'el', 'la', 'un', 'una', 'en']
        english_indicators = ['want', 'looking', 'where', 'eat', 'the', 'a', 'an', 'in', 'at']
        
        text_lower = text.lower()
        spanish_count = sum(1 for word in spanish_indicators if word in text_lower)
        english_count = sum(1 for word in english_indicators if word in text_lower)
        
        return 'es' if spanish_count >= english_count else 'en'
    
    def extract_intent(self, text: str, language: str) -> Tuple[str, float]:
        """Extraer intención del texto"""
        text_lower = text.lower()
        
        patterns = self.search_patterns_es if language == 'es' else self.search_patterns_en
        
        for pattern in patterns:
            if re.search(pattern, text_lower):
                return ('SEARCH', 0.85)
        
        return ('SEARCH', 0.6)
    
    def extract_category(self, text: str, language: str) -> Optional[Dict]:
        """Extraer categoría del texto"""
        text_lower = text.lower()
        text_normalized = unidecode(text_lower)
        
        # Verificar palabras clave de comida
        food_keywords = self.food_keywords_es if language == 'es' else self.food_keywords_en
        if any(keyword in text_lower for keyword in food_keywords):
            for cat_id, cat in self.categories.items():
                if 'gastrono' in cat['name_normalized'] or 'gastro' in cat['name_normalized']:
                    return {
                        'id': cat_id,
                        'name': cat['name'],
                        'confidence': 0.9,
                        'matched_text': 'food-related keywords'
                    }
        
        # Verificar palabras clave de cultura
        culture_keywords = self.culture_keywords_es if language == 'es' else self.culture_keywords_en
        if any(keyword in text_lower for keyword in culture_keywords):
            for cat_id, cat in self.categories.items():
                if 'museo' in cat['name_normalized'] or 'monumento' in cat['name_normalized'] or 'historico' in cat['name_normalized']:
                    return {
                        'id': cat_id,
                        'name': cat['name'],
                        'confidence': 0.85,
                        'matched_text': 'culture keywords'
                    }
        
        # Verificar palabras clave de entretenimiento
        entertainment_keywords = self.entertainment_keywords_es if language == 'es' else self.entertainment_keywords_en
        if any(keyword in text_lower for keyword in entertainment_keywords):
            for cat_id, cat in self.categories.items():
                if 'entret' in cat['name_normalized'] or 'evento' in cat['name_normalized']:
                    return {
                        'id': cat_id,
                        'name': cat['name'],
                        'confidence': 0.8,
                        'matched_text': 'entertainment keywords'
                    }
        
        # Matching difuso contra nombres de categorías
        category_names = [cat['name_normalized'] for cat in self.categories.values()]
        match = process.extractOne(
            text_normalized, 
            category_names,
            scorer=fuzz.partial_ratio,
            score_cutoff=60
        )
        
        if match:
            matched_name, score, _ = match
            for cat_id, cat in self.categories.items():
                if cat['name_normalized'] == matched_name:
                    return {
                        'id': cat_id,
                        'name': cat['name'],
                        'confidence': score / 100,
                        'matched_text': cat['name']
                    }
        
        return None
    
    def extract_subcategory(self, text: str, category_id: Optional[int]) -> Optional[Dict]:
        """Extraer subcategoría del texto"""
        text_lower = text.lower()
        text_normalized = unidecode(text_lower)
        
        # Filtrar subcategorías por categoría si se proporciona
        relevant_subcats = self.subcategories
        if category_id:
            relevant_subcats = {
                sub_id: sub for sub_id, sub in self.subcategories.items()
                if sub['categoria_id'] == category_id
            }
        
        # Palabras clave específicas para gastronomía
        gastro_keywords = {
            'parrilla': 'Parrilla',
            'asado': 'Parrilla',
            'carne': 'Parrilla',
            'pizza': 'Pizzería',
            'café': 'Café',
            'coffee': 'Café',
            'bar': 'Bar',
            'restaurante': 'Restaurante',
            'restaurant': 'Restaurante'
        }
        
        for keyword, subcat_name in gastro_keywords.items():
            if keyword in text_lower:
                for sub_id, sub in relevant_subcats.items():
                    if subcat_name.lower() in sub['name_lower']:
                        return {
                            'id': sub_id,
                            'name': sub['name'],
                            'confidence': 0.9,
                            'matched_text': keyword
                        }
        
        # Matching difuso
        subcat_names = [sub['name_normalized'] for sub in relevant_subcats.values()]
        if subcat_names:
            match = process.extractOne(
                text_normalized,
                subcat_names,
                scorer=fuzz.partial_ratio,
                score_cutoff=65
            )
            
            if match:
                matched_name, score, _ = match
                for sub_id, sub in relevant_subcats.items():
                    if sub['name_normalized'] == matched_name:
                        return {
                            'id': sub_id,
                            'name': sub['name'],
                            'confidence': score / 100,
                            'matched_text': sub['name']
                        }
        
        return None
    
    def extract_zone(self, text: str) -> Optional[Dict]:
        """Extraer barrio/zona del texto"""
        text_lower = text.lower()
        text_normalized = unidecode(text_lower)
        
        if self.barrios:
            match = process.extractOne(
                text_normalized,
                [unidecode(barrio.lower()) for barrio in self.barrios],
                scorer=fuzz.partial_ratio,
                score_cutoff=75
            )
            
            if match:
                _, score, idx = match
                return {
                    'name': self.barrios[idx],
                    'confidence': score / 100,
                    'matched_text': self.barrios[idx]
                }
        
        return None
    
    def extract_cuisine_type(self, text: str) -> Optional[str]:
        """Extraer tipo de cocina del texto"""
        text_lower = text.lower()
        
        cuisine_keywords = {
            'argentina': ['argentina', 'argentino', 'criollo', 'asado', 'parrilla', 'carne'],
            'italiana': ['italiana', 'italiano', 'pizza', 'pasta'],
            'mexicana': ['mexicana', 'mexicano', 'tacos'],
            'japonesa': ['japonesa', 'japonés', 'sushi', 'ramen'],
            'china': ['china', 'chino'],
            'peruana': ['peruana', 'peruano', 'ceviche'],
            'española': ['española', 'español', 'tapas'],
            'francesa': ['francesa', 'francés'],
            'vegetariana': ['vegetariana', 'vegetariano', 'vegano', 'vegan']
        }
        
        for cuisine, keywords in cuisine_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                return cuisine
        
        return None
    
    def process_query(self, query: str) -> Dict:
        """
        Procesar una consulta en lenguaje natural
        
        Args:
            query: Consulta del usuario
        
        Returns:
            Diccionario con intención, entidades y confianza
        """
        # Detectar idioma
        language = self.detect_language(query)
        
        # Extraer intención
        intent, intent_confidence = self.extract_intent(query, language)
        
        # Extraer entidades
        category = self.extract_category(query, language)
        subcategory = None
        if category:
            subcategory = self.extract_subcategory(query, category['id'])
        else:
            subcategory = self.extract_subcategory(query, None)
        
        zone = self.extract_zone(query)
        cuisine_type = self.extract_cuisine_type(query)
        
        # Usar spaCy para extracción adicional si está disponible
        entities_spacy = []
        nlp = self.nlp_es if language == 'es' else self.nlp_en
        if nlp:
            try:
                doc = nlp(query)
                entities_spacy = [
                    {
                        'text': ent.text,
                        'label': ent.label_,
                        'start': ent.start_char,
                        'end': ent.end_char
                    }
                    for ent in doc.ents
                ]
            except:
                pass
        
        # Calcular confianza general
        confidences = [intent_confidence]
        if category:
            confidences.append(category['confidence'])
        if subcategory:
            confidences.append(subcategory['confidence'])
        if zone:
            confidences.append(zone['confidence'])
        
        overall_confidence = sum(confidences) / len(confidences)
        
        # Construir respuesta
        response = {
            'query': query,
            'language': language,
            'intent': {
                'name': intent,
                'confidence': round(intent_confidence, 2)
            },
            'entities': {
                'category': category,
                'subcategory': subcategory,
                'zone': zone,
                'cuisine_type': cuisine_type,
                'spacy_entities': entities_spacy
            },
            'confidence': round(overall_confidence, 2),
            'processed': True,
            'suggestions': self._generate_suggestions(category, subcategory, zone, cuisine_type)
        }
        
        return response
    
    def _generate_suggestions(self, category, subcategory, zone, cuisine_type) -> Dict:
        """Generar sugerencias para la llamada API"""
        suggestions = {
            'categorias': [],
            'zona': None,
            'tipo_cocina': None
        }
        
        if category:
            suggestions['categorias'].append(category['name'])
        
        if zone:
            suggestions['zona'] = zone['name']
        
        if cuisine_type:
            suggestions['tipo_cocina'] = cuisine_type
        
        return suggestions

