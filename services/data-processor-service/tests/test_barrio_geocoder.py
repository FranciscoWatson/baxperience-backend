"""
Tests para BarrioGeocoder
"""
import pytest
from unittest.mock import Mock, patch
from csv_processor import BarrioGeocoder


class TestBarrioGeocoder:
    """Tests para el geocodificador de barrios"""
    
    def test_geocoder_initialization(self):
        """Debe inicializarse correctamente"""
        geocoder = BarrioGeocoder()
        
        assert geocoder.cache == {}
        assert geocoder.session is not None
        assert geocoder.rate_limit_delay == 0.1
        assert geocoder.last_request_time == 0
    
    def test_get_barrio_returns_none_for_invalid_coordinates(self):
        """Debe retornar None para coordenadas inválidas"""
        geocoder = BarrioGeocoder()
        
        result = geocoder.get_barrio_by_coordinates(None, None)
        assert result is None
        
        result = geocoder.get_barrio_by_coordinates(-34.6037, None)
        assert result is None
    
    def test_cache_functionality(self):
        """Debe usar caché para coordenadas repetidas"""
        geocoder = BarrioGeocoder()
        lat, lng = -34.6037, -58.3816
        
        # Agregar a caché manualmente
        cache_key = f"{lat:.6f},{lng:.6f}"
        geocoder.cache[cache_key] = "Palermo"
        
        result = geocoder.get_barrio_by_coordinates(lat, lng)
        assert result == "Palermo"
