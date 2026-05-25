"""
Data extractors from original sources.
Module to extract data from CSV and Excel files.
"""
import pandas as pd
from pathlib import Path
from typing import List, Dict, Generator, Optional
from loguru import logger
import glob

from src.config import DATA_PATHS, settings


class BaseExtractor:
    """Base class for data extractors."""

    def __init__(self, source_path: Path):
        self.source_path = source_path
        logger.info(f"Initializing extractor for: {source_path}")

    def extract(self) -> pd.DataFrame:
        """Abstract method to extract data."""
        raise NotImplementedError("Subclasses must implement extract()")
    
    def validate(self, df: pd.DataFrame) -> bool:
        """Validates that the DataFrame is not empty and has correct structure."""
        if df.empty:
            logger.warning("Extracted DataFrame is empty")
            return False
        logger.info(f"Data extracted: {len(df)} rows, {len(df.columns)} columns")
        return True


class DespoblamientoExtractor(BaseExtractor):
    """Extractor for depopulation data."""

    def __init__(self):
        super().__init__(DATA_PATHS["despoblamiento"])
    
    def extract(self) -> pd.DataFrame:
        """Extracts all CSV files from depopulation folder."""
        main_file = self.source_path / "despob_pob_actividad_activos_ipc_pib_2023_clusters.csv"

        if main_file.exists():
            df = pd.read_csv(main_file, sep=';', encoding='utf-8')
            df['source_file'] = main_file.name
            logger.info(f"Extracted: {main_file.name} - {len(df)} rows")
            self.validate(df)
            return df

        logger.warning(f"Main file not found: {main_file}")
        return pd.DataFrame()


class PoblacionExtractor(BaseExtractor):
    """Extractor for population data by municipality and sex."""

    def __init__(self):
        super().__init__(DATA_PATHS["poblacion"])
    
    def extract(self) -> pd.DataFrame:
        """Extracts all CSV files from population folder."""
        all_data = []
        csv_files = list(self.source_path.glob("*.csv"))
        
        logger.info(f"Found {len(csv_files)} CSV files for population")

        for file_path in csv_files:
            try:
                df = pd.read_csv(file_path, sep=';', encoding='utf-8')
                df['source_file'] = file_path.name
                all_data.append(df)
                logger.debug(f"Extracted: {file_path.name} - {len(df)} rows")
            except Exception as e:
                logger.error(f"Error extracting {file_path.name}: {e}")

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            self.validate(combined_df)
            return combined_df
        
        return pd.DataFrame()
    
    def extract_batch(self, batch_size: int = 10) -> Generator[pd.DataFrame, None, None]:
        """Extracts data in batches for efficient processing."""
        csv_files = list(self.source_path.glob("*.csv"))
        
        for i in range(0, len(csv_files), batch_size):
            batch_files = csv_files[i:i + batch_size]
            batch_data = []
            
            for file_path in batch_files:
                try:
                    df = pd.read_csv(file_path, sep=';', encoding='utf-8')
                    df['source_file'] = file_path.name
                    batch_data.append(df)
                except Exception as e:
                    logger.error(f"Error extracting {file_path.name}: {e}")

            if batch_data:
                yield pd.concat(batch_data, ignore_index=True)


class IndustriaExtractor(BaseExtractor):
    """Extractor for industry data by province."""

    def __init__(self):
        super().__init__(DATA_PATHS["industria"])
    
    def extract(self) -> pd.DataFrame:
        """Extracts all Excel files from industry folder."""
        all_data = []
        excel_files = list(self.source_path.glob("*.xlsx"))
        
        logger.info(f"Found {len(excel_files)} Excel files for industry")

        for file_path in excel_files:
            try:
                df = pd.read_excel(file_path, engine='openpyxl')
                # Extract province name from filename
                provincia = file_path.stem.replace(" 2019", "")
                df['provincia'] = provincia
                df['anio'] = 2019
                df['source_file'] = file_path.name
                all_data.append(df)
                logger.debug(f"Extracted: {file_path.name} - {len(df)} rows")
            except Exception as e:
                logger.error(f"Error extracting {file_path.name}: {e}")

        if all_data:
            combined_df = pd.concat(all_data, ignore_index=True)
            self.validate(combined_df)
            return combined_df
        
        return pd.DataFrame()
    
    def get_provincias(self) -> List[str]:
        """Gets the list of available provinces."""
        excel_files = list(self.source_path.glob("*.xlsx"))
        provincias = [f.stem.replace(" 2019", "") for f in excel_files]
        return sorted(provincias)


def extract_all_sources() -> Dict[str, pd.DataFrame]:
    """
    Main function that extracts data from all sources.
    Returns a dictionary with DataFrames for each source.
    """
    logger.info("=" * 50)
    logger.info("STARTING DATA EXTRACTION")
    logger.info("=" * 50)
    
    extractors = {
        'despoblamiento': DespoblamientoExtractor(),
        'poblacion': PoblacionExtractor(),
        'industria': IndustriaExtractor()
    }
    
    data = {}
    for name, extractor in extractors.items():
        try:
            logger.info(f"\n--- Extracting: {name} ---")
            data[name] = extractor.extract()
        except Exception as e:
            logger.error(f"Error in extraction of {name}: {e}")
            data[name] = pd.DataFrame()
    
    logger.info("=" * 50)
    logger.info("EXTRACTION COMPLETED")
    logger.info("=" * 50)
    
    return data


if __name__ == "__main__":
    # Run test extraction
    from loguru import logger
    import sys
    
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    data = extract_all_sources()
    
    for name, df in data.items():
        print(f"\n{name}:")
        print(f"  - Rows: {len(df)}")
        print(f"  - Columns: {list(df.columns)[:5]}...")

