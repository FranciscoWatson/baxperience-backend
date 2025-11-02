"""
Tests para DataProcessorOrchestrator
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from main import DataProcessorOrchestrator


class TestDataProcessorOrchestrator:
    """Tests para el orquestador principal"""
    
    def test_orchestrator_initialization(self):
        """Debe inicializarse correctamente"""
        orchestrator = DataProcessorOrchestrator()
        
        assert orchestrator.start_time is None
        assert orchestrator.results == {}
    
    def test_print_banner(self, capsys):
        """Debe mostrar banner correctamente"""
        orchestrator = DataProcessorOrchestrator()
        orchestrator.print_banner()
        
        captured = capsys.readouterr()
        assert 'BAXperience Data Processor' in captured.out
        assert 'Museos' in captured.out
    
    @patch('main.CSVProcessor')
    def test_run_csv_processing_success(self, mock_csv_processor):
        """Debe procesar CSVs exitosamente"""
        # Setup mock
        mock_processor_instance = Mock()
        mock_processor_instance.process_all_csvs.return_value = {
            'museos': 50,
            'gastronomia': 100
        }
        mock_csv_processor.return_value = mock_processor_instance
        
        orchestrator = DataProcessorOrchestrator()
        result = orchestrator.run_csv_processing()
        
        assert result is True
        assert 'csv_processing' in orchestrator.results
        assert orchestrator.results['csv_processing']['museos'] == 50
    
    @patch('main.CSVProcessor')
    def test_run_csv_processing_failure(self, mock_csv_processor):
        """Debe manejar errores en procesamiento de CSVs"""
        mock_csv_processor.side_effect = Exception("Database error")
        
        orchestrator = DataProcessorOrchestrator()
        result = orchestrator.run_csv_processing()
        
        assert result is False
    
    @patch('main.ETLProcessor')
    def test_run_etl_processing_success(self, mock_etl_processor):
        """Debe ejecutar ETL exitosamente"""
        mock_etl_instance = Mock()
        mock_etl_instance.run_full_etl.return_value = {
            'pois': 150,
            'categorias': 5
        }
        mock_etl_processor.return_value = mock_etl_instance
        
        orchestrator = DataProcessorOrchestrator()
        result = orchestrator.run_etl_processing()
        
        assert result is True
        assert 'etl_processing' in orchestrator.results
    
    @patch('main.ClusteringProcessor')
    def test_run_clustering_success(self, mock_clustering):
        """Debe ejecutar clustering exitosamente"""
        mock_clustering_instance = Mock()
        mock_clustering_instance.run_full_clustering.return_value = {
            'status': 'completed',
            'summary': {
                'total_pois_processed': 150,
                'algorithms_executed': 3,
                'successful_algorithms': ['kmeans', 'dbscan'],
                'tourist_zones_detected': 5,
                'neighborhoods_analyzed': 10
            }
        }
        mock_clustering.return_value = mock_clustering_instance
        
        orchestrator = DataProcessorOrchestrator()
        result = orchestrator.run_clustering()
        
        assert result is True
        assert orchestrator.results['clustering']['status'] == 'completed'
        assert orchestrator.results['clustering']['pois_processed'] == 150
    
    @patch('main.ClusteringProcessor')
    def test_run_clustering_failure(self, mock_clustering):
        """Debe manejar errores en clustering"""
        mock_clustering_instance = Mock()
        mock_clustering_instance.run_full_clustering.return_value = {
            'status': 'error',
            'message': 'Clustering failed'
        }
        mock_clustering.return_value = mock_clustering_instance
        
        orchestrator = DataProcessorOrchestrator()
        result = orchestrator.run_clustering()
        
        assert result is False
        assert orchestrator.results['clustering']['status'] == 'failed'
