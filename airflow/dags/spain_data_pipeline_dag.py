"""
Airflow DAG for the Data Engineering Pipeline.

This DAG orchestrates the complete ETL flow:
1. Data extraction from local sources
2. Data transformation and cleaning
3. Load to DuckDB (local) or Snowflake (production)

Similar to the described project:
- Extracts data from sources
- Transforms using Python/Pandas
- Loads to warehouse (Snowflake)
- Prepares for Vertex AI Datastore
"""
from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.empty import EmptyOperator
from airflow.utils.task_group import TaskGroup
from airflow.models import Variable
import sys
import os

# Add project path
sys.path.insert(0, '/opt/airflow/dags/dataengineer')

# DAG configuration
default_args = {
    'owner': 'data-engineering',
    'depends_on_past': False,
    'email': ['marielabvargas@gmail.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(hours=2),
}

# Airflow Variables (configure in UI or CLI)
TARGET_WAREHOUSE = Variable.get('target_warehouse', default_var='duckdb')
ENABLE_GCP_EXPORT = Variable.get('enable_gcp_export', default_var='false') == 'true'


def extract_despoblamiento(**context):
    """Task: Extract depopulation data."""
    from src.etl.extractors import DespoblamientoExtractor
    
    extractor = DespoblamientoExtractor()
    df = extractor.extract()
    
    # Save to XCom for next task
    context['ti'].xcom_push(key='despoblamiento_rows', value=len(df))
    
    # Save temporarily
    temp_path = '/tmp/despoblamiento_raw.parquet'
    df.to_parquet(temp_path)
    
    return temp_path


def extract_poblacion(**context):
    """Task: Extract population data."""
    from src.etl.extractors import PoblacionExtractor
    
    extractor = PoblacionExtractor()
    df = extractor.extract()
    
    context['ti'].xcom_push(key='poblacion_rows', value=len(df))
    
    temp_path = '/tmp/poblacion_raw.parquet'
    df.to_parquet(temp_path)
    
    return temp_path


def extract_industria(**context):
    """Task: Extract industry data."""
    from src.etl.extractors import IndustriaExtractor
    
    extractor = IndustriaExtractor()
    df = extractor.extract()
    
    context['ti'].xcom_push(key='industria_rows', value=len(df))
    
    temp_path = '/tmp/industria_raw.parquet'
    df.to_parquet(temp_path)
    
    return temp_path


def transform_despoblamiento(**context):
    """Task: Transform depopulation data."""
    import pandas as pd
    from src.etl.transformers import DespoblamientoTransformer
    
    input_path = context['ti'].xcom_pull(task_ids='extraction.extract_despoblamiento')
    df = pd.read_parquet(input_path)
    
    transformer = DespoblamientoTransformer()
    transformed_df = transformer.transform(df)
    
    output_path = '/tmp/despoblamiento_transformed.parquet'
    transformed_df.to_parquet(output_path)
    
    return output_path


def transform_poblacion(**context):
    """Task: Transform population data."""
    import pandas as pd
    from src.etl.transformers import PoblacionTransformer
    
    input_path = context['ti'].xcom_pull(task_ids='extraction.extract_poblacion')
    df = pd.read_parquet(input_path)
    
    transformer = PoblacionTransformer()
    transformed_df = transformer.transform(df)
    
    output_path = '/tmp/poblacion_transformed.parquet'
    transformed_df.to_parquet(output_path)
    
    return output_path


def transform_industria(**context):
    """Task: Transform industry data."""
    import pandas as pd
    from src.etl.transformers import IndustriaTransformer
    
    input_path = context['ti'].xcom_pull(task_ids='extraction.extract_industria')
    df = pd.read_parquet(input_path)
    
    transformer = IndustriaTransformer()
    transformed_df = transformer.transform(df)
    
    output_path = '/tmp/industria_transformed.parquet'
    transformed_df.to_parquet(output_path)
    
    return output_path

def load_to_warehouse(**context):
    """Task: Load all data to warehouse."""
    import pandas as pd
    from src.etl.loaders import load_to_warehouse as load_func
    
    # Get transformed data paths
    despoblamiento_path = context['ti'].xcom_pull(task_ids='transformation.transform_despoblamiento')
    poblacion_path = context['ti'].xcom_pull(task_ids='transformation.transform_poblacion')
    industria_path = context['ti'].xcom_pull(task_ids='transformation.transform_industria')
    
    # Load DataFrames
    data = {
        'despoblamiento': pd.read_parquet(despoblamiento_path),
        'poblacion': pd.read_parquet(poblacion_path),
        'industria': pd.read_parquet(industria_path)
    }
    
    # Load to configured warehouse
    results = load_func(data, target=TARGET_WAREHOUSE)
    
    context['ti'].xcom_push(key='load_results', value=results)
    
    return results

def quality_check(**context):
    """Task: Verify loaded data quality."""
    from src.etl.transformers import DataQualityChecker
    from src.etl.loaders import DuckDBLoader
    
    loader = DuckDBLoader()
    checker = DataQualityChecker()
    
    tables = ['fact_despoblamiento', 'fact_poblacion', 'fact_industria']
    
    quality_report = {}
    for table in tables:
        info = loader.get_table_info(table)
        quality_report[table] = info
    
    loader.close()
    
    context['ti'].xcom_push(key='quality_report', value=quality_report)
    
    return quality_report


def send_notification(**context):
    """Task: Send completion notification."""
    load_results = context['ti'].xcom_pull(task_ids='loading.load_to_warehouse', key='load_results')
    quality_report = context['ti'].xcom_pull(task_ids='quality_checks.quality_check', key='quality_report')
    
    message = f"""
    Data Engineering Pipeline Completed
    ====================================
    
    Load Results:
    {load_results}
    
    Quality Report:
    {quality_report}
    
    Timestamp: {datetime.now().isoformat()}
    """
    
    print(message)
    # Could integrate with Slack, Teams, email, etc.

    return message


# DAG definition
with DAG(
    dag_id='spain_data_engineering_pipeline',
    default_args=default_args,
    description='ETL Pipeline for Spain data (depopulation, population, industry)',
    # schedule_interval='0 2 * * *',  # Airflow is programmed to run at 2 AM daily
    schedule_interval = timedelta(minutes=20),    # For testing: execute every 20 minutes
    start_date=datetime(2024, 1, 1),
    catchup=False,
    tags=['etl', 'spain', 'data-engineering'],
    doc_md=__doc__
) as dag:
    
    # Start task
    start = EmptyOperator(task_id='start')
    
    # Extraction task group
    with TaskGroup(group_id='extraction') as extraction_group:
        extract_desp = PythonOperator(
            task_id='extract_despoblamiento',
            python_callable=extract_despoblamiento,
            provide_context=True
        )
        
        extract_pob = PythonOperator(
            task_id='extract_poblacion',
            python_callable=extract_poblacion,
            provide_context=True
        )
        
        extract_ind = PythonOperator(
            task_id='extract_industria',
            python_callable=extract_industria,
            provide_context=True
        )
    
    # Transformation task group
    with TaskGroup(group_id='transformation') as transformation_group:
        transform_desp = PythonOperator(
            task_id='transform_despoblamiento',
            python_callable=transform_despoblamiento,
            provide_context=True
        )
        
        transform_pob = PythonOperator(
            task_id='transform_poblacion',
            python_callable=transform_poblacion,
            provide_context=True
        )
        
        transform_ind = PythonOperator(
            task_id='transform_industria',
            python_callable=transform_industria,
            provide_context=True
        )
    
    # Loading task group
    with TaskGroup(group_id='loading') as loading_group:
        load_warehouse = PythonOperator(
            task_id='load_to_warehouse',
            python_callable=load_to_warehouse,
            provide_context=True
        )
        
        export_gcp = PythonOperator(
            task_id='export_to_gcp',
            python_callable=export_to_gcp,
            provide_context=True
        )
        
        load_warehouse >> export_gcp
    
    # Quality checks task group
    with TaskGroup(group_id='quality_checks') as quality_group:
        check_quality = PythonOperator(
            task_id='quality_check',
            python_callable=quality_check,
            provide_context=True
        )
    
    # Notification task
    notify = PythonOperator(
        task_id='send_notification',
        python_callable=send_notification,
        provide_context=True,
        trigger_rule='all_done'  # Execute even if there are failures
    )
    
    # End task
    end = EmptyOperator(task_id='end')
    
    # Define DAG dependencies
    # Flow: start -> extraction -> transformation -> loading -> quality -> notify -> end
    start >> extraction_group
    
    # Extractions can run in parallel
    # Then transformations depend on their respective extractions
    extract_desp >> transform_desp
    extract_pob >> transform_pob
    extract_ind >> transform_ind
    
    # Loading depends on all transformations
    [transform_desp, transform_pob, transform_ind] >> loading_group
    
    # Quality checks after loading
    loading_group >> quality_group
    
    # Notification at the end
    quality_group >> notify >> end

