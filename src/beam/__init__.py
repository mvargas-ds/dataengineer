"""Apache Beam pipelines para transformación de datos."""
from .transform_for_vertex import (
    run_despoblamiento_pipeline,
    run_poblacion_pipeline
)

__all__ = ['run_despoblamiento_pipeline', 'run_poblacion_pipeline']

