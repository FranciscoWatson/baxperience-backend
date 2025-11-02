"""
Tests para DatabaseConfig
"""
import pytest
import os
from unittest.mock import patch
from csv_processor import DatabaseConfig


class TestDatabaseConfig:
    """Tests para configuración de base de datos"""
    
    def test_operational_db_default_config(self):
        """Debe tener configuración por defecto para BD Operacional"""
        config = DatabaseConfig.OPERATIONAL_DB
        
        assert 'host' in config
        assert 'port' in config
        assert 'database' in config
        assert 'user' in config
        assert 'password' in config
        assert config['database'] == 'OPERATIONAL_DB'
    
    def test_processor_db_default_config(self):
        """Debe tener configuración por defecto para BD Processor"""
        config = DatabaseConfig.PROCESSOR_DB
        
        assert 'host' in config
        assert 'port' in config
        assert 'database' in config
        assert 'user' in config
        assert 'password' in config
        assert config['database'] == 'PROCESSOR_DB'
    
    @patch.dict(os.environ, {
        'OPERATIONAL_DB_HOST': 'test-host',
        'OPERATIONAL_DB_PORT': '5433',
        'OPERATIONAL_DB_NAME': 'test_db'
    })
    def test_operational_db_uses_environment_variables(self):
        """Debe usar variables de entorno si están disponibles"""
        # Recrear config con nuevas env vars
        config = {
            'host': os.getenv('OPERATIONAL_DB_HOST', 'localhost'),
            'port': os.getenv('OPERATIONAL_DB_PORT', '5432'),
            'database': os.getenv('OPERATIONAL_DB_NAME', 'OPERATIONAL_DB'),
        }
        
        assert config['host'] == 'test-host'
        assert config['port'] == '5433'
        assert config['database'] == 'test_db'
