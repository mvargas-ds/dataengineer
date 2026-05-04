"""
Módulo ETL - Extract, Transform, Load
Pipeline de datos para el Data Warehouse.
"""
from .extractors import (
    DespoblamientoExtractor,
    PoblacionExtractor,
    IndustriaExtractor,
    extract_all_sources
)
from .transformers import (
    DespoblamientoTransformer,
    PoblacionTransformer,
    IndustriaTransformer,
    transform_all,
    DataQualityChecker
)
from .loaders import (
    DuckDBLoader,
    SnowflakeLoader,
    GCSLoader,
    FileLoader,
    load_to_warehouse
)

__all__ = [
    # Extractors
    'DespoblamientoExtractor',
    'PoblacionExtractor', 
    'IndustriaExtractor',
    'extract_all_sources',
    # Transformers
    'DespoblamientoTransformer',
    'PoblacionTransformer',
    'IndustriaTransformer',
    'transform_all',
    'DataQualityChecker',
    # Loaders
    'DuckDBLoader',
    'SnowflakeLoader',
    'GCSLoader',
    'FileLoader',
    'load_to_warehouse'
]

