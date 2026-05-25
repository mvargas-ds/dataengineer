"""
Data loaders for the ETL pipeline.
Loads transformed data to different destinations:
- DuckDB (local/development)
- Snowflake (production)
- GCP Cloud Storage + Vertex AI Datastore
"""
import pandas as pd
import duckdb
from pathlib import Path
from typing import Dict, Optional, List
from loguru import logger
from datetime import datetime
import json
import os

from src.config import settings, TABLE_SCHEMAS


class BaseLoader:
    """Base class for data loaders."""

    def __init__(self, name: str):
        self.name = name
        self.load_log = []
    
    def log_load(self, table: str, rows: int, status: str):
        """Logs load operations."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'table': table,
            'rows_loaded': rows,
            'status': status
        }
        self.load_log.append(entry)
        logger.info(f"[{self.name}] Loaded {table}: {rows} rows - {status}")

    def load(self, df: pd.DataFrame, table_name: str) -> bool:
        """Abstract method to load data."""
        raise NotImplementedError("Subclasses must implement load()")


class DuckDBLoader(BaseLoader):
    """
    Loader for DuckDB (local Data Warehouse).
    Ideal for development and testing.
    """
    
    def __init__(self, db_path: Optional[str] = None):
        super().__init__('DuckDB')
        self.db_path = db_path or settings.pipeline.local_db_path
        
        # Create directory if it doesn't exist
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = duckdb.connect(self.db_path)
        logger.info(f"Connected to DuckDB: {self.db_path}")

    def create_schema(self):
        """Creates the table schema in DuckDB."""
        # For simple DuckDB, we use tables without schema prefix
        logger.info("DuckDB initialized - using tables in main schema")

    def load(self, df: pd.DataFrame, table_name: str, mode: str = 'replace') -> bool:
        """
        Loads a DataFrame into a DuckDB table.

        Args:
            df: DataFrame to load
            table_name: Target table name
            mode: 'replace' (replace) or 'append' (add)
        """
        try:
            # Use simple table name (without schema prefix)
            if mode == 'replace':
                # Drop table if exists
                self.conn.execute(f"DROP TABLE IF EXISTS {table_name}")
            
            # Register DataFrame and create table
            self.conn.register('temp_df', df)
            
            if mode == 'replace':
                self.conn.execute(f"CREATE TABLE {table_name} AS SELECT * FROM temp_df")
            else:
                self.conn.execute(f"INSERT INTO {table_name} SELECT * FROM temp_df")
            
            self.conn.unregister('temp_df')
            
            # Verify load
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            self.log_load(table_name, count, 'SUCCESS')
            
            return True
            
        except Exception as e:
            logger.error(f"Error loading {table_name}: {e}")
            self.log_load(table_name, 0, f'FAILED: {str(e)}')
            return False
    
    def query(self, sql: str) -> pd.DataFrame:
        """Executes a query and returns DataFrame."""
        return self.conn.execute(sql).fetchdf()
    
    def get_table_info(self, table_name: str) -> Dict:
        """Gets information about a table."""
        try:
            count = self.conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]
            columns = self.conn.execute(f"DESCRIBE {table_name}").fetchdf()
            return {
                'table': table_name,
                'row_count': count,
                'columns': columns.to_dict('records')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def close(self):
        """Closes the connection."""
        self.conn.close()
        logger.info("DuckDB connection closed")


class SnowflakeLoader(BaseLoader):
    """
    Loader for Snowflake (cloud Data Warehouse).
    For production environment.
    """
    
    def __init__(self):
        super().__init__('Snowflake')
        self.conn = None
        self._connect()
    
    def _connect(self):
        """Establishes connection with Snowflake."""
        try:
            import snowflake.connector
            from dotenv import load_dotenv
            import os
            
            load_dotenv()
            
            # Get credentials from environment (more reliable)
            account = os.getenv('SNOWFLAKE_ACCOUNT', settings.snowflake.account)
            user = os.getenv('SNOWFLAKE_USER', settings.snowflake.user)
            password = os.getenv('SNOWFLAKE_PASSWORD', settings.snowflake.password)
            warehouse = os.getenv('SNOWFLAKE_WAREHOUSE', settings.snowflake.warehouse)
            database = os.getenv('SNOWFLAKE_DATABASE', settings.snowflake.database)
            schema = os.getenv('SNOWFLAKE_SCHEMA', settings.snowflake.schema_name)
            role = os.getenv('SNOWFLAKE_ROLE', settings.snowflake.role)
            
            self.conn = snowflake.connector.connect(
                account=account,
                user=user,
                password=password,
                login_timeout=30
            )
            
            # Setup warehouse, database, schema
            cursor = self.conn.cursor()
            cursor.execute(f'USE ROLE {role}')
            cursor.execute(f'USE WAREHOUSE {warehouse}')
            cursor.execute(f'USE DATABASE {database}')
            cursor.execute(f'USE SCHEMA {schema}')
            cursor.close()
            
            logger.info(f"Connected to Snowflake: {account}")
        except Exception as e:
            logger.warning(f"Could not connect to Snowflake: {e}")
            self.conn = None
    
    def load(self, df: pd.DataFrame, table_name: str, mode: str = 'replace') -> bool:
        """Loads data to Snowflake using INSERT statements (compatible with trial accounts)."""
        if not self.conn:
            logger.error("No connection to Snowflake")
            return False
        
        try:
            cursor = self.conn.cursor()
            
            # Prepare DataFrame
            df = df.copy().reset_index(drop=True)
            df.columns = df.columns.str.upper().str.replace(' ', '_').str.replace('.', '_')
            
            # Convert datetime columns to string for Snowflake compatibility
            for col in df.columns:
                if df[col].dtype == 'datetime64[ns]' or 'datetime' in str(df[col].dtype):
                    df[col] = df[col].astype(str).replace('NaT', None)
            
            # Drop table if replace mode
            if mode == 'replace':
                cursor.execute(f"DROP TABLE IF EXISTS {table_name.upper()}")
            
            # Create table with inferred schema
            col_types = []
            for col in df.columns:
                dtype = df[col].dtype
                if 'int' in str(dtype):
                    col_types.append(f'"{col}" INTEGER')
                elif 'float' in str(dtype):
                    col_types.append(f'"{col}" FLOAT')
                elif 'bool' in str(dtype):
                    col_types.append(f'"{col}" BOOLEAN')
                else:
                    col_types.append(f'"{col}" VARCHAR(16777216)')
            
            create_sql = f"CREATE TABLE IF NOT EXISTS {table_name.upper()} ({', '.join(col_types)})"
            cursor.execute(create_sql)
            
            # Insert in batches using executemany
            batch_size = 1000
            total_rows = len(df)
            
            # Prepare insert statement
            cols = ', '.join([f'"{c}"' for c in df.columns])
            placeholders = ', '.join(['%s'] * len(df.columns))
            insert_sql = f"INSERT INTO {table_name.upper()} ({cols}) VALUES ({placeholders})"
            
            rows_inserted = 0
            for i in range(0, total_rows, batch_size):
                batch = df.iloc[i:i+batch_size]
                # Convert to list of tuples, handling NaN and special values
                data = []
                for row in batch.values:
                    cleaned_row = []
                    for x in row:
                        if pd.isna(x):
                            cleaned_row.append(None)
                        elif isinstance(x, (pd.Timestamp, datetime)):
                            cleaned_row.append(str(x))
                        else:
                            cleaned_row.append(x)
                    data.append(tuple(cleaned_row))
                
                cursor.executemany(insert_sql, data)
                rows_inserted += len(data)
                
                if rows_inserted % 10000 == 0:
                    logger.info(f"  Inserted {rows_inserted}/{total_rows} rows...")

            self.conn.commit()
            cursor.close()
            
            self.log_load(table_name, rows_inserted, 'SUCCESS')
            return True
                
        except Exception as e:
            logger.error(f"Error loading to Snowflake: {e}")
            self.log_load(table_name, 0, f'FAILED: {str(e)}')
            return False
    
    def close(self):
        """Closes the connection."""
        if self.conn:
            self.conn.close()
            logger.info("Snowflake connection closed")


class GCSLoader(BaseLoader):
    """
    Loader for Google Cloud Storage.
    Prepares data for Vertex AI Datastore.
    """
    
    def __init__(self):
        super().__init__('GCS')
        self.client = None
        self._connect()
    
    def _connect(self):
        """Establishes connection with GCS."""
        try:
            from google.cloud import storage
            
            self.client = storage.Client(project=settings.gcp.project_id)
            self.bucket = self.client.bucket(settings.gcp.bucket_name)
            logger.info(f"Connected to GCS bucket: {settings.gcp.bucket_name}")
        except Exception as e:
            logger.warning(f"Could not connect to GCS: {e}")
            self.client = None
    
    def load(self, df: pd.DataFrame, table_name: str, format: str = 'jsonl') -> bool:
        """
        Loads data to GCS in Vertex AI format.

        Args:
            df: DataFrame to load
            table_name: File/dataset name
            format: 'jsonl' for Vertex AI Datastore, 'parquet' for analytics
        """
        if not self.client:
            logger.error("No connection to GCS")
            return False
        
        try:
            blob_name = f"data/{table_name}/{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            if format == 'jsonl':
                # JSONL format for Vertex AI Datastore
                blob_name += '.jsonl'
                content = df.to_json(orient='records', lines=True)
            elif format == 'parquet':
                blob_name += '.parquet'
                content = df.to_parquet()
            else:
                blob_name += '.csv'
                content = df.to_csv(index=False)
            
            blob = self.bucket.blob(blob_name)
            blob.upload_from_string(content)
            
            self.log_load(table_name, len(df), f'SUCCESS - {blob_name}')
            return True
            
        except Exception as e:
            logger.error(f"Error loading to GCS: {e}")
            self.log_load(table_name, 0, f'FAILED: {str(e)}')
            return False
    
    def prepare_for_vertex_datastore(self, df: pd.DataFrame, id_column: str) -> List[Dict]:
        """
        Prepares data in Vertex AI Datastore format.
        Each document must have a unique ID and structured content.
        """
        documents = []
        for _, row in df.iterrows():
            doc = {
                'id': str(row[id_column]) if id_column in row else str(_),
                'structData': row.to_dict(),
                'jsonData': json.dumps(row.to_dict())
            }
            documents.append(doc)
        return documents


class FileLoader(BaseLoader):
    """
    Loader for processed local files.
    Saves data in CSV, Parquet, JSON formats.
    """
    
    def __init__(self, output_path: Optional[Path] = None):
        super().__init__('File')
        self.output_path = output_path or settings.pipeline.output_path
        self.output_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Output path: {self.output_path}")
    
    def load(self, df: pd.DataFrame, table_name: str, format: str = 'parquet') -> bool:
        """
        Saves DataFrame to local file.

        Args:
            df: DataFrame to save
            table_name: File name
            format: 'parquet', 'csv', 'json'
        """
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            
            if format == 'parquet':
                file_path = self.output_path / f"{table_name}_{timestamp}.parquet"
                df.to_parquet(file_path, index=False)
            elif format == 'csv':
                file_path = self.output_path / f"{table_name}_{timestamp}.csv"
                df.to_csv(file_path, index=False)
            elif format == 'json':
                file_path = self.output_path / f"{table_name}_{timestamp}.json"
                df.to_json(file_path, orient='records', indent=2)
            else:
                raise ValueError(f"Unsupported format: {format}")

            self.log_load(table_name, len(df), f'SUCCESS - {file_path}')
            return True
            
        except Exception as e:
            logger.error(f"Error saving file: {e}")
            self.log_load(table_name, 0, f'FAILED: {str(e)}')
            return False


def load_to_warehouse(data: Dict[str, pd.DataFrame], target: str = 'duckdb') -> Dict[str, bool]:
    """
    Main function that loads all data to the warehouse.

    Args:
        data: Dictionary with transformed DataFrames
        target: 'duckdb', 'snowflake', 'gcs', 'file'
    """
    logger.info("=" * 50)
    logger.info(f"STARTING DATA LOAD TO {target.upper()}")
    logger.info("=" * 50)
    
    # Select loader based on target
    if target == 'duckdb':
        loader = DuckDBLoader()
        loader.create_schema()
    elif target == 'snowflake':
        loader = SnowflakeLoader()
    elif target == 'gcs':
        loader = GCSLoader()
    elif target == 'file':
        loader = FileLoader()
    else:
        raise ValueError(f"Unsupported target: {target}")

    results = {}
    
    for name, df in data.items():
        if not df.empty:
            logger.info(f"\n--- Loading: {name} ---")
            results[name] = loader.load(df, f"fact_{name}")
        else:
            logger.warning(f"DataFrame {name} is empty, skipping load")
            results[name] = False
    
    # Close connection
    if hasattr(loader, 'close'):
        loader.close()
    
    logger.info("=" * 50)
    logger.info("LOAD COMPLETED")
    logger.info(f"Results: {results}")
    logger.info("=" * 50)
    
    return results


if __name__ == "__main__":
    from src.etl.extractors import extract_all_sources
    from src.etl.transformers import transform_all
    import sys
    
    logger.remove()
    logger.add(sys.stdout, level="DEBUG")
    
    # Complete test pipeline
    print("\n1. Extracting data...")
    raw_data = extract_all_sources()
    
    print("\n2. Transforming data...")
    transformed_data = transform_all(raw_data)
    
    print("\n3. Loading to DuckDB...")
    results = load_to_warehouse(transformed_data, target='duckdb')
    
    # Verify loaded data
    print("\n4. Verifying data...")
    loader = DuckDBLoader()
    for table_name in results.keys():
        info = loader.get_table_info(f"fact_{table_name}")
        print(f"  {table_name}: {info}")
    loader.close()