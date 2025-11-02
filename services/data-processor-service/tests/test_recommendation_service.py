"""
Tests para RecommendationService
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from recommendation_service import RecommendationService


class TestRecommendationService:
    """Tests para el servicio de recomendaciones"""
    
    def test_recommendation_service_initialization(self):
        """Debe inicializarse correctamente"""
        service = RecommendationService()
        
        assert service.conn is None
        assert service.operational_conn is None
        assert service.models == {}
        assert service.scalers == {}
    
    @patch('recommendation_service.psycopg2')
    def test_connect_database_success(self, mock_psycopg2):
        """Debe conectarse a la BD correctamente"""
        mock_conn = Mock()
        mock_psycopg2.connect.return_value = mock_conn
        
        service = RecommendationService()
        service.connect_database()
        
        assert service.conn is not None
        mock_psycopg2.connect.assert_called_once()
    
    @patch('recommendation_service.psycopg2')
    def test_connect_database_failure(self, mock_psycopg2):
        """Debe manejar errores de conexión"""
        mock_psycopg2.connect.side_effect = Exception("Connection failed")
        
        service = RecommendationService()
        
        with pytest.raises(Exception):
            service.connect_database()
    
    def test_disconnect_database(self):
        """Debe desconectarse correctamente"""
        service = RecommendationService()
        mock_conn = Mock()
        service.conn = mock_conn
        
        service.disconnect_database()
        
        mock_conn.close.assert_called_once()
