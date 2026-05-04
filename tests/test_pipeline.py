"""
Tests unitarios para el pipeline de Data Engineering.
"""
import pytest
import pandas as pd
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# Agregar el path del proyecto
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestExtractors:
    """Tests para los extractores de datos."""
    
    def test_despoblamiento_extractor_init(self):
        """Test inicialización del extractor de despoblamiento."""
        from src.etl.extractors import DespoblamientoExtractor
        
        extractor = DespoblamientoExtractor()
        assert extractor.source_path is not None
    
    def test_poblacion_extractor_init(self):
        """Test inicialización del extractor de población."""
        from src.etl.extractors import PoblacionExtractor
        
        extractor = PoblacionExtractor()
        assert extractor.source_path is not None
    
    def test_industria_extractor_init(self):
        """Test inicialización del extractor de industria."""
        from src.etl.extractors import IndustriaExtractor
        
        extractor = IndustriaExtractor()
        assert extractor.source_path is not None
    
    def test_base_extractor_validate_non_empty(self):
        """Test validación de DataFrame no vacío."""
        from src.etl.extractors import BaseExtractor
        
        extractor = BaseExtractor(Path("."))
        df = pd.DataFrame({'a': [1, 2, 3]})
        
        assert extractor.validate(df) is True
    
    def test_base_extractor_validate_empty(self):
        """Test validación de DataFrame vacío."""
        from src.etl.extractors import BaseExtractor
        
        extractor = BaseExtractor(Path("."))
        df = pd.DataFrame()
        
        assert extractor.validate(df) is False


class TestTransformers:
    """Tests para los transformadores de datos."""
    
    def test_base_transformer_clean_column_names(self):
        """Test limpieza de nombres de columnas."""
        from src.etl.transformers import BaseTransformer
        
        class TestTransformer(BaseTransformer):
            def transform(self, df):
                return df
        
        transformer = TestTransformer("test")
        df = pd.DataFrame({'Column Name': [1], 'Another-Column': [2]})
        
        result = transformer.clean_column_names(df)
        
        assert 'column_name' in result.columns
        assert 'anothercolumn' in result.columns
    
    def test_base_transformer_remove_duplicates(self):
        """Test eliminación de duplicados."""
        from src.etl.transformers import BaseTransformer
        
        class TestTransformer(BaseTransformer):
            def transform(self, df):
                return df
        
        transformer = TestTransformer("test")
        df = pd.DataFrame({'a': [1, 1, 2], 'b': [3, 3, 4]})
        
        result = transformer.remove_duplicates(df)
        
        assert len(result) == 2
    
    def test_despoblamiento_transformer_creates_categories(self):
        """Test categorización de nivel de despoblamiento."""
        from src.etl.transformers import DespoblamientoTransformer
        
        transformer = DespoblamientoTransformer()
        df = pd.DataFrame({
            'porcen_desp': [10, 40, 60, 90],
            'pob_tot': [1000, 2000, 3000, 4000],
            'pob_hom': [500, 1000, 1500, 2000],
            'pob_muj': [500, 1000, 1500, 2000]
        })
        
        result = transformer.transform(df)
        
        assert 'categoria_despoblamiento' in result.columns
    
    def test_poblacion_transformer_extracts_municipio_code(self):
        """Test extracción de código de municipio."""
        from src.etl.transformers import PoblacionTransformer
        
        transformer = PoblacionTransformer()
        df = pd.DataFrame({
            'municipios': ['01051 Agurain/Salvatierra'],
            'total': [5000]
        })
        
        result = transformer.transform(df)
        
        assert 'codigo_municipio' in result.columns


class TestLoaders:
    """Tests para los cargadores de datos."""
    
    def test_duckdb_loader_init(self, tmp_path):
        """Test inicialización del loader de DuckDB."""
        from src.etl.loaders import DuckDBLoader
        
        db_path = str(tmp_path / "test.duckdb")
        loader = DuckDBLoader(db_path)
        
        assert loader.db_path == db_path
        loader.close()
    
    def test_duckdb_loader_load(self, tmp_path):
        """Test carga de datos a DuckDB."""
        from src.etl.loaders import DuckDBLoader
        
        db_path = str(tmp_path / "test.duckdb")
        loader = DuckDBLoader(db_path)
        loader.create_schema()
        
        df = pd.DataFrame({'a': [1, 2, 3], 'b': ['x', 'y', 'z']})
        result = loader.load(df, 'test_table')
        
        assert result is True
        
        # Verificar datos cargados
        loaded_df = loader.query("SELECT * FROM warehouse.test_table")
        assert len(loaded_df) == 3
        
        loader.close()
    
    def test_file_loader_save_parquet(self, tmp_path):
        """Test guardado en formato Parquet."""
        from src.etl.loaders import FileLoader
        
        loader = FileLoader(tmp_path)
        df = pd.DataFrame({'a': [1, 2, 3]})
        
        result = loader.load(df, 'test', format='parquet')
        
        assert result is True
        assert any(f.suffix == '.parquet' for f in tmp_path.iterdir())
    
    def test_file_loader_save_csv(self, tmp_path):
        """Test guardado en formato CSV."""
        from src.etl.loaders import FileLoader
        
        loader = FileLoader(tmp_path)
        df = pd.DataFrame({'a': [1, 2, 3]})
        
        result = loader.load(df, 'test', format='csv')
        
        assert result is True
        assert any(f.suffix == '.csv' for f in tmp_path.iterdir())


class TestDataQuality:
    """Tests para verificación de calidad de datos."""
    
    def test_quality_checker_completeness(self):
        """Test verificación de completitud."""
        from src.etl.transformers import DataQualityChecker
        
        checker = DataQualityChecker()
        df = pd.DataFrame({
            'a': [1, 2, None],
            'b': [4, 5, 6]
        })
        
        report = checker.check_completeness(df, 'test')
        
        assert report['total_rows'] == 3
        assert 'missing_percentage' in report
    
    def test_quality_checker_uniqueness(self):
        """Test verificación de unicidad."""
        from src.etl.transformers import DataQualityChecker
        
        checker = DataQualityChecker()
        df = pd.DataFrame({
            'id': [1, 1, 2],
            'value': ['a', 'b', 'c']
        })
        
        report = checker.check_uniqueness(df, 'test', ['id'])
        
        assert report['total_duplicates'] == 1


class TestPipeline:
    """Tests para el pipeline principal."""
    
    def test_pipeline_initialization(self):
        """Test inicialización del pipeline."""
        from src.pipeline.main import DataPipeline
        
        pipeline = DataPipeline(target='duckdb')
        
        assert pipeline.target == 'duckdb'
        assert pipeline.metrics is not None
    
    @patch('src.pipeline.main.extract_all_sources')
    @patch('src.pipeline.main.transform_all')
    @patch('src.pipeline.main.load_to_warehouse')
    def test_pipeline_run(self, mock_load, mock_transform, mock_extract):
        """Test ejecución del pipeline con mocks."""
        from src.pipeline.main import DataPipeline
        
        # Configurar mocks
        mock_extract.return_value = {'test': pd.DataFrame({'a': [1, 2, 3]})}
        mock_transform.return_value = {'test': pd.DataFrame({'a': [1, 2, 3]})}
        mock_load.return_value = {'test': True}
        
        pipeline = DataPipeline(target='duckdb')
        result = pipeline.run()
        
        assert result is True
        assert mock_extract.called
        assert mock_transform.called
        assert mock_load.called


class TestConfig:
    """Tests para la configuración."""
    
    def test_settings_loads(self):
        """Test carga de configuración."""
        from src.config import settings
        
        assert settings is not None
        assert settings.pipeline is not None
    
    def test_data_paths_defined(self):
        """Test rutas de datos definidas."""
        from src.config import DATA_PATHS
        
        assert 'despoblamiento' in DATA_PATHS
        assert 'industria' in DATA_PATHS
        assert 'poblacion' in DATA_PATHS


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

