"""
Data transformers for the ETL pipeline.
Cleaning, normalization and data preparation for the warehouse.
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from loguru import logger
from datetime import datetime


class BaseTransformer:
    """Base class for data transformers."""

    def __init__(self, name: str):
        self.name = name
        self.transformation_log = []
    
    def log_transformation(self, operation: str, details: str):
        """Logs applied transformations."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'operation': operation,
            'details': details
        }
        self.transformation_log.append(entry)
        logger.info(f"[{self.name}] {operation}: {details}")
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """Abstract method to transform data."""
        raise NotImplementedError("Subclasses must implement transform()")
    
    def clean_column_names(self, df: pd.DataFrame) -> pd.DataFrame:
        """Cleans and normalizes column names."""
        df.columns = (
            df.columns
            .str.lower()
            .str.strip()
            .str.replace(' ', '_')
            .str.replace(r'[^\w]', '', regex=True)
        )
        self.log_transformation('clean_column_names', f'Normalized columns: {list(df.columns)}')
        return df
    
    def remove_duplicates(self, df: pd.DataFrame, subset: Optional[List[str]] = None) -> pd.DataFrame:
        """Removes duplicate records."""
        original_count = len(df)
        df = df.drop_duplicates(subset=subset)
        removed = original_count - len(df)
        self.log_transformation('remove_duplicates', f'Removed {removed} duplicates')
        return df
    
    def handle_missing_values(self, df: pd.DataFrame, strategy: str = 'drop') -> pd.DataFrame:
        """Handles missing values according to specified strategy."""
        original_count = len(df)
        
        if strategy == 'drop':
            df = df.dropna()
        elif strategy == 'fill_zero':
            df = df.fillna(0)
        elif strategy == 'fill_mean':
            numeric_cols = df.select_dtypes(include=[np.number]).columns
            df[numeric_cols] = df[numeric_cols].fillna(df[numeric_cols].mean())
        elif strategy == 'fill_forward':
            df = df.fillna(method='ffill')
        
        affected = original_count - len(df) if strategy == 'drop' else df.isna().sum().sum()
        self.log_transformation('handle_missing', f'Strategy: {strategy}, Affected: {affected}')
        return df


class DespoblamientoTransformer(BaseTransformer):
    """Transformer for depopulation data."""

    def __init__(self):
        super().__init__('Despoblamiento')
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms depopulation data.
        - Normalizes column names
        - Calculates derived metrics
        - Categorizes depopulation levels
        """
        if df.empty:
            logger.warning("Depopulation DataFrame is empty")
            return df
        
        df = self.clean_column_names(df)
        
        # Rename columns for clarity
        column_mapping = {
            'porcen_desp': 'porcentaje_despoblamiento',
            'pob_tot': 'poblacion_total',
            'pob_hom': 'poblacion_hombres',
            'pob_muj': 'poblacion_mujeres',
            'asexos_tactividad': 'tasa_actividad_total',
            'asexos_templeo': 'tasa_empleo_total',
            'asexos_tparo': 'tasa_paro_total',
            'ipc_alim': 'ipc_alimentacion',
            'ipc_trans': 'ipc_transporte',
            'pib_prec': 'pib_precios_corrientes'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in df.columns:
                df = df.rename(columns={old_name: new_name})
        
        self.log_transformation('rename_columns', 'Columns renamed for clarity')

        # Calculate derived metrics
        if 'poblacion_total' in df.columns and 'poblacion_hombres' in df.columns:
            df['ratio_genero'] = df['poblacion_hombres'] / df['poblacion_mujeres']
            self.log_transformation('calculate_ratio', 'Calculated gender ratio')

        # Categorize depopulation level
        if 'porcentaje_despoblamiento' in df.columns:
            df['categoria_despoblamiento'] = pd.cut(
                df['porcentaje_despoblamiento'],
                bins=[0, 25, 50, 75, 100],
                labels=['Low', 'Medium', 'High', 'Very High']
            )
            self.log_transformation('categorize', 'Categorized depopulation level')

        # Add audit fields
        df['fecha_procesamiento'] = datetime.now()
        df['version_pipeline'] = '1.0.0'
        
        return df


class PoblacionTransformer(BaseTransformer):
    """Transformer for population data by municipality."""

    def __init__(self):
        super().__init__('Poblacion')
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms population data.
        - Normalizes structure
        - Extracts municipality codes
        - Pivots data by sex
        """
        if df.empty:
            logger.warning("Population DataFrame is empty")
            return df
        
        df = self.clean_column_names(df)
        
        # Extract municipality code and name
        if 'municipios' in df.columns:
            df['codigo_municipio'] = df['municipios'].str.extract(r'^(\d+)')
            df['nombre_municipio'] = df['municipios'].str.extract(r'\d+\s+(.+)$')
            self.log_transformation('extract_municipio', 'Extracted municipality code and name')

        # Convert period to integer
        if 'periodo' in df.columns:
            df['periodo'] = pd.to_numeric(df['periodo'], errors='coerce')
        
        # Convert total to numeric
        if 'total' in df.columns:
            df['total'] = pd.to_numeric(df['total'], errors='coerce')
        
        # Clean null values in total
        df = df.dropna(subset=['total'])
        self.log_transformation('clean_totals', 'Removed records without population value')

        # Add audit fields
        df['fecha_procesamiento'] = datetime.now()
        df['version_pipeline'] = '1.0.0'
        
        return df
    
    def create_population_summary(self, df: pd.DataFrame) -> pd.DataFrame:
        """Creates population summary by province and year."""
        summary = df.groupby(['codigo_provincia', 'nombre_provincia', 'periodo']).agg({
            'total': ['sum', 'mean', 'count']
        }).reset_index()
        
        summary.columns = ['codigo_provincia', 'nombre_provincia', 'periodo', 
                          'poblacion_total', 'poblacion_media_municipio', 'num_municipios']
        
        self.log_transformation('create_summary', 'Created population summary by province')
        return summary


class IndustriaTransformer(BaseTransformer):
    """Transformer for industry data."""

    def __init__(self):
        super().__init__('Industria')
    
    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Transforms industry data.
        - Normalizes structure
        - Standardizes province names
        - Calculates totals by sector
        """
        if df.empty:
            logger.warning("Industry DataFrame is empty")
            return df
        
        df = self.clean_column_names(df)
        
        # Province name to INE code mapping
        provincia_codes = {
            'Alava': 1, 'Albacete': 2, 'Alicante': 3, 'Almeria': 4, 'Avila': 5,
            'Badajoz': 6, 'Barcelona': 8, 'Bizkaia': 48, 'Burgos': 9, 'Caceres': 10,
            'Cadiz': 11, 'Cantabria': 39, 'Castellon': 12, 'Cordoba': 14, 'Coruña': 15,
            'CReal': 13, 'Cuenca': 16, 'Gipuzkoa': 20, 'Girona': 17, 'Granada': 18,
            'Guadalajara': 19, 'Huelva': 21, 'Huesca': 22, 'Jaen': 23, 'Lleida': 25,
            'Lugo': 27, 'Madrid': 28, 'Malaga': 29, 'Murcia': 30, 'Navarra': 31,
            'Ourense': 32, 'Palencia': 34, 'Pontevedra': 36, 'Rioja': 26, 'Salamanca': 37,
            'Segovia': 40, 'Sevilla': 41, 'Tarragona': 43, 'Teruel': 44, 'Toledo': 45,
            'Valencia': 46, 'Valladolid': 47, 'Zamora': 49, 'Zaragoza': 50
        }
        
        if 'provincia' in df.columns:
            df['codigo_provincia_ine'] = df['provincia'].map(provincia_codes)
            self.log_transformation('add_codes', 'Added province INE codes')

        # Add audit fields
        df['fecha_procesamiento'] = datetime.now()
        df['version_pipeline'] = '1.0.0'
        
        return df


class DataQualityChecker:
    """Data quality checker."""

    def __init__(self):
        self.quality_report = {}
    
    def check_completeness(self, df: pd.DataFrame, name: str) -> Dict:
        """Checks data completeness."""
        missing_pct = (df.isnull().sum() / len(df) * 100).to_dict()
        report = {
            'total_rows': len(df),
            'total_columns': len(df.columns),
            'missing_percentage': missing_pct,
            'complete_rows': len(df.dropna())
        }
        self.quality_report[f'{name}_completeness'] = report
        return report
    
    def check_uniqueness(self, df: pd.DataFrame, name: str, key_columns: List[str]) -> Dict:
        """Checks record uniqueness."""
        duplicates = df.duplicated(subset=key_columns).sum()
        report = {
            'key_columns': key_columns,
            'total_duplicates': duplicates,
            'duplicate_percentage': (duplicates / len(df) * 100) if len(df) > 0 else 0
        }
        self.quality_report[f'{name}_uniqueness'] = report
        return report
    
    def generate_report(self) -> Dict:
        """Generates complete quality report."""
        return self.quality_report


def transform_all(data: Dict[str, pd.DataFrame]) -> Dict[str, pd.DataFrame]:
    """
    Main function that transforms data from all sources.
    """
    logger.info("=" * 50)
    logger.info("STARTING DATA TRANSFORMATION")
    logger.info("=" * 50)
    
    transformers = {
        'despoblamiento': DespoblamientoTransformer(),
        'poblacion': PoblacionTransformer(),
        'industria': IndustriaTransformer()
    }
    
    transformed = {}
    quality_checker = DataQualityChecker()
    
    for name, df in data.items():
        if name in transformers and not df.empty:
            try:
                logger.info(f"\n--- Transforming: {name} ---")
                transformed[name] = transformers[name].transform(df)
                quality_checker.check_completeness(transformed[name], name)
            except Exception as e:
                logger.error(f"Error in transformation of {name}: {e}")
                transformed[name] = df
        else:
            transformed[name] = df
    
    # Log quality report
    quality_report = quality_checker.generate_report()
    logger.info(f"\nQuality Report: {quality_report}")

    logger.info("=" * 50)
    logger.info("TRANSFORMATION COMPLETED")
    logger.info("=" * 50)
    
    return transformed


if __name__ == "__main__":
    from src.etl.extractors import extract_all_sources
    import sys
    
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    # Extract data
    raw_data = extract_all_sources()
    
    # Transform data
    transformed_data = transform_all(raw_data)
    
    for name, df in transformed_data.items():
        print(f"\n{name} (transformed):")
        print(f"  - Rows: {len(df)}")
        print(f"  - Columns: {list(df.columns)[:5]}...")

