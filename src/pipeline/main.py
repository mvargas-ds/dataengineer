"""
Main Data Engineering Pipeline.
Orchestrates the complete flow: Extraction -> Transformation -> Load.

This script can be executed:
1. Directly: python -m src.pipeline.main
2. From Docker: docker run dataengineer-pipeline
3. From Airflow: As a DAG task
"""
import click
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional
from loguru import logger

# Add root directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.etl import extract_all_sources, transform_all, load_to_warehouse
from src.config import settings


def setup_logging(log_level: str = "INFO", log_file: Optional[str] = None):
    """Configures the logging system."""
    logger.remove()
    
    # Console format
    console_format = (
        "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
        "<level>{message}</level>"
    )
    
    logger.add(sys.stdout, format=console_format, level=log_level, colorize=True)
    
    # Log file if specified
    if log_file:
        file_format = "{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {message}"
        logger.add(log_file, format=file_format, level=log_level, rotation="100 MB")


class DataPipeline:
    """
    Main data pipeline.
    Coordinates ETL phases and handles errors.
    """
    
    def __init__(self, targets: list = None):
        self.targets = targets or ['duckdb']
        # Handle 'all' target
        if 'all' in self.targets:
            self.targets = ['duckdb', 'snowflake']
        self.start_time = None
        self.end_time = None
        self.metrics = {
            'extraction': {},
            'transformation': {},
            'loading': {}
        }
    
    def run(self) -> bool:
        """
        Executes the complete pipeline.

        Returns:
            bool: True if the pipeline executed successfully
        """
        self.start_time = datetime.now()
        logger.info("=" * 60)
        logger.info("DATA ENGINEERING PIPELINE STARTED")
        logger.info(f"Timestamp: {self.start_time}")
        logger.info(f"Targets: {', '.join(self.targets)}")
        logger.info("=" * 60)
        
        try:
            # Phase 1: Extraction
            logger.info("\n" + "=" * 40)
            logger.info("PHASE 1: DATA EXTRACTION")
            logger.info("=" * 40)
            
            raw_data = extract_all_sources()
            
            self.metrics['extraction'] = {
                name: len(df) for name, df in raw_data.items()
            }
            logger.info(f"Extraction metrics: {self.metrics['extraction']}")

            # Phase 2: Transformation
            logger.info("\n" + "=" * 40)
            logger.info("PHASE 2: DATA TRANSFORMATION")
            logger.info("=" * 40)
            
            transformed_data = transform_all(raw_data)
            
            self.metrics['transformation'] = {
                name: len(df) for name, df in transformed_data.items()
            }
            logger.info(f"Transformation metrics: {self.metrics['transformation']}")

            # Phase 3: Load to ALL targets
            logger.info("\n" + "=" * 40)
            logger.info("PHASE 3: DATA LOADING")
            logger.info("=" * 40)
            
            all_load_results = {}
            for target in self.targets:
                logger.info(f"\n--- Loading to: {target.upper()} ---")
                load_results = load_to_warehouse(transformed_data, target=target)
                all_load_results[target] = load_results
            
            self.metrics['loading'] = all_load_results
            logger.info(f"Load results: {self.metrics['loading']}")

            # Summary
            self.end_time = datetime.now()
            duration = (self.end_time - self.start_time).total_seconds()
            
            logger.info("\n" + "=" * 60)
            logger.info("PIPELINE COMPLETED SUCCESSFULLY")
            logger.info(f"Total duration: {duration:.2f} seconds")
            logger.info(f"Targets: {', '.join(self.targets)}")
            logger.info(f"Final metrics: {self.metrics}")
            logger.info("=" * 60)
            
            return True
            
        except Exception as e:
            self.end_time = datetime.now()
            logger.error(f"PIPELINE ERROR: {e}")
            logger.exception(e)
            return False
    
    def run_extraction_only(self):
        """Executes only the extraction phase."""
        logger.info("Executing EXTRACTION only")
        return extract_all_sources()
    
    def run_transformation_only(self, data):
        """Executes only the transformation phase."""
        logger.info("Executing TRANSFORMATION only")
        return transform_all(data)
    
    def run_loading_only(self, data):
        """Executes only the loading phase to all targets."""
        logger.info("Executing LOADING only")
        results = {}
        for target in self.targets:
            results[target] = load_to_warehouse(data, target=target)
        return results


@click.command()
@click.option('--target', '-t', default=['duckdb'], multiple=True,
              type=click.Choice(['duckdb', 'snowflake', 'gcs', 'file', 'all']),
              help='Data destination (can specify multiple: -t duckdb -t snowflake)')
@click.option('--log-level', '-l', default='INFO',
              type=click.Choice(['DEBUG', 'INFO', 'WARNING', 'ERROR']),
              help='Logging level')
@click.option('--log-file', '-f', default=None,
              help='File to save logs')
@click.option('--phase', '-p', default='all',
              type=click.Choice(['all', 'extract', 'transform', 'load']),
              help='Pipeline phase to execute')
def main(target: tuple, log_level: str, log_file: Optional[str], phase: str):
    """
    Data Engineering Pipeline for Spain data.

    Extracts depopulation, population and industry data,
    transforms them and loads them into a Data Warehouse.

    Usage example:
        python -m src.pipeline.main --target duckdb --log-level INFO
    """
    setup_logging(log_level, log_file)
    
    # Convert tuple to list
    targets = list(target) if target else ['duckdb']
    
    pipeline = DataPipeline(targets=targets)
    
    if phase == 'all':
        success = pipeline.run()
    elif phase == 'extract':
        data = pipeline.run_extraction_only()
        success = bool(data)
    elif phase == 'transform':
        raw_data = pipeline.run_extraction_only()
        transformed = pipeline.run_transformation_only(raw_data)
        success = bool(transformed)
    elif phase == 'load':
        raw_data = pipeline.run_extraction_only()
        transformed = pipeline.run_transformation_only(raw_data)
        success = pipeline.run_loading_only(transformed)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

