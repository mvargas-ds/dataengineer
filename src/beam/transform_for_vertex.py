"""
Apache Beam Pipeline para transformación de datos en GCP.

Este script es similar al mencionado en el proyecto ePlan:
- Transforma datos en formato específico para Vertex AI Datastore
- Se ejecuta en Google Cloud Dataflow
- Puede orquestarse desde Airflow

Uso local:
    python -m src.beam.transform_for_vertex --input gs://bucket/data --output gs://bucket/output

Uso en Dataflow:
    python -m src.beam.transform_for_vertex \
        --input gs://bucket/data \
        --output gs://bucket/output \
        --runner DataflowRunner \
        --project your-project \
        --region us-central1 \
        --temp_location gs://bucket/temp
"""
import apache_beam as beam
from apache_beam.options.pipeline_options import PipelineOptions, SetupOptions
from apache_beam.io import ReadFromText, WriteToText
from apache_beam.io.gcp.bigquery import WriteToBigQuery, BigQueryDisposition
import argparse
import json
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional


class ParseCSVRow(beam.DoFn):
    """Parsea filas CSV a diccionarios."""
    
    def __init__(self, headers: List[str], delimiter: str = ';'):
        self.headers = headers
        self.delimiter = delimiter
    
    def process(self, row: str):
        try:
            values = row.split(self.delimiter)
            if len(values) == len(self.headers):
                record = dict(zip(self.headers, values))
                yield record
        except Exception as e:
            logging.error(f"Error parsing row: {e}")


class TransformDespoblamiento(beam.DoFn):
    """Transforma datos de despoblamiento para Vertex AI."""
    
    def process(self, record: Dict) -> List[Dict]:
        try:
            # Crear documento estructurado para Vertex AI Datastore
            document = {
                'id': f"desp_{record.get('codigo_provincia', 'unknown')}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                'structData': {
                    'tipo': 'despoblamiento',
                    'porcentaje_despoblamiento': float(record.get('porcen_desp', 0)),
                    'poblacion_total': int(record.get('pob_tot', 0)),
                    'poblacion_hombres': int(record.get('pob_hom', 0)),
                    'poblacion_mujeres': int(record.get('pob_muj', 0)),
                    'tasa_actividad': float(record.get('asexos_tactividad', 0)),
                    'tasa_empleo': float(record.get('asexos_templeo', 0)),
                    'tasa_paro': float(record.get('asexos_tparo', 0)),
                    'pib_total': float(record.get('pib_prec', 0)),
                    'metadata': {
                        'source': 'ine_spain',
                        'processed_at': datetime.now().isoformat(),
                        'version': '1.0.0'
                    }
                },
                'content': self._generate_content(record)
            }
            yield document
        except Exception as e:
            logging.error(f"Error transforming record: {e}")
    
    def _generate_content(self, record: Dict) -> str:
        """Genera contenido textual para embeddings de IA."""
        return f"""
        Datos de despoblamiento provincial en España.
        Porcentaje de despoblamiento: {record.get('porcen_desp', 'N/A')}%
        Población total: {record.get('pob_tot', 'N/A')} habitantes.
        Distribución por género: {record.get('pob_hom', 'N/A')} hombres, {record.get('pob_muj', 'N/A')} mujeres.
        Indicadores laborales: Tasa de actividad {record.get('asexos_tactividad', 'N/A')}%, 
        Tasa de empleo {record.get('asexos_templeo', 'N/A')}%, 
        Tasa de paro {record.get('asexos_tparo', 'N/A')}%.
        PIB provincial: {record.get('pib_prec', 'N/A')} euros.
        """


class TransformPoblacion(beam.DoFn):
    """Transforma datos de población para Vertex AI."""
    
    def process(self, record: Dict) -> List[Dict]:
        try:
            document = {
                'id': f"pob_{record.get('codigo_provincia', '')}_{record.get('Municipios', '').replace(' ', '_')}_{record.get('Periodo', '')}",
                'structData': {
                    'tipo': 'poblacion_municipal',
                    'codigo_provincia': int(record.get('codigo_provincia', 0)),
                    'nombre_provincia': record.get('nombre_provincia', ''),
                    'municipio': record.get('Municipios', ''),
                    'sexo': record.get('Sexo', ''),
                    'periodo': int(record.get('Periodo', 0)),
                    'total': int(record.get('Total', 0) or 0),
                    'metadata': {
                        'source': 'ine_spain',
                        'processed_at': datetime.now().isoformat(),
                        'version': '1.0.0'
                    }
                },
                'content': self._generate_content(record)
            }
            yield document
        except Exception as e:
            logging.error(f"Error transforming record: {e}")
    
    def _generate_content(self, record: Dict) -> str:
        return f"""
        Datos de población municipal de España.
        Provincia: {record.get('nombre_provincia', 'N/A')}.
        Municipio: {record.get('Municipios', 'N/A')}.
        Año: {record.get('Periodo', 'N/A')}.
        Categoría: {record.get('Sexo', 'N/A')}.
        Población: {record.get('Total', 'N/A')} habitantes.
        """


class FormatAsJSONL(beam.DoFn):
    """Formatea documentos como JSONL para Vertex AI Datastore."""
    
    def process(self, document: Dict) -> List[str]:
        try:
            jsonl_line = json.dumps(document, ensure_ascii=False)
            yield jsonl_line
        except Exception as e:
            logging.error(f"Error formatting JSON: {e}")


class ValidateDocument(beam.DoFn):
    """Valida la estructura del documento."""
    
    def process(self, document: Dict):
        required_fields = ['id', 'structData']
        
        if all(field in document for field in required_fields):
            yield beam.pvalue.TaggedOutput('valid', document)
        else:
            yield beam.pvalue.TaggedOutput('invalid', document)


def run_despoblamiento_pipeline(input_path: str, output_path: str, pipeline_options: PipelineOptions):
    """Pipeline para transformar datos de despoblamiento."""
    
    headers = [
        'porcen_desp', 'pob_tot', 'pob_hom', 'pob_muj',
        'asexos_tactividad', 'asexos_templeo', 'asexos_tparo',
        'hombres_tactividad', 'hombres_templeo', 'hombres_tparo',
        'mujeres_tactividad', 'mujeres_templeo', 'mujeres_tparo',
        'activos_agricultura', 'activos_construccion', 'activos_industria', 'activos_servicios',
        'ipc_alim', 'ipc_bebi', 'ipc_vest', 'ipc_vivi', 'ipc_hoga',
        'ipc_sani', 'ipc_trans', 'ipc_comu', 'ipc_ocio', 'ipc_ense',
        'ipc_resta', 'ipc_otros', 'pib_prec', 'pib_agri', 'pib_indu',
        'pib_ind_manu', 'pib_constr', 'pib_comer', 'pib_act_fin',
        'pib_admin', 'pib_valor_brut', 'pib_imp_netos'
    ]
    
    with beam.Pipeline(options=pipeline_options) as p:
        # Leer datos
        raw_data = (
            p 
            | 'Read CSV' >> ReadFromText(f"{input_path}/despoblamiento/*.csv", skip_header_lines=1)
        )
        
        # Parsear y transformar
        parsed = (
            raw_data
            | 'Parse CSV' >> beam.ParDo(ParseCSVRow(headers, ';'))
            | 'Transform for Vertex' >> beam.ParDo(TransformDespoblamiento())
        )
        
        # Validar
        validated = parsed | 'Validate' >> beam.ParDo(ValidateDocument()).with_outputs('valid', 'invalid')
        
        # Escribir documentos válidos
        (
            validated.valid
            | 'Format JSONL' >> beam.ParDo(FormatAsJSONL())
            | 'Write Output' >> WriteToText(
                f"{output_path}/despoblamiento/data",
                file_name_suffix='.jsonl',
                num_shards=1
            )
        )
        
        # Registrar documentos inválidos
        (
            validated.invalid
            | 'Format Invalid' >> beam.ParDo(FormatAsJSONL())
            | 'Write Invalid' >> WriteToText(
                f"{output_path}/despoblamiento/errors",
                file_name_suffix='.jsonl'
            )
        )


def run_poblacion_pipeline(input_path: str, output_path: str, pipeline_options: PipelineOptions):
    """Pipeline para transformar datos de población."""
    
    headers = ['codigo_provincia', 'nombre_provincia', 'Municipios', 'Sexo', 'Periodo', 'Total']
    
    with beam.Pipeline(options=pipeline_options) as p:
        # Leer todos los archivos CSV de población
        raw_data = (
            p
            | 'Read CSV' >> ReadFromText(f"{input_path}/pob_x_munic_y_sexo/*.csv", skip_header_lines=1)
        )
        
        # Parsear y transformar
        parsed = (
            raw_data
            | 'Parse CSV' >> beam.ParDo(ParseCSVRow(headers, ';'))
            | 'Transform for Vertex' >> beam.ParDo(TransformPoblacion())
        )
        
        # Escribir salida
        (
            parsed
            | 'Format JSONL' >> beam.ParDo(FormatAsJSONL())
            | 'Write Output' >> WriteToText(
                f"{output_path}/poblacion/data",
                file_name_suffix='.jsonl',
                num_shards=4  # Más shards por volumen de datos
            )
        )


def main():
    """Punto de entrada principal del script Beam."""
    parser = argparse.ArgumentParser(description='Transform data for Vertex AI Datastore')
    
    parser.add_argument(
        '--input',
        required=True,
        help='Input path (local or GCS)'
    )
    parser.add_argument(
        '--output',
        required=True,
        help='Output path (local or GCS)'
    )
    parser.add_argument(
        '--dataset',
        choices=['despoblamiento', 'poblacion', 'all'],
        default='all',
        help='Dataset to process'
    )
    
    known_args, pipeline_args = parser.parse_known_args()
    
    pipeline_options = PipelineOptions(pipeline_args)
    pipeline_options.view_as(SetupOptions).save_main_session = True
    
    logging.info(f"Starting Beam pipeline: {known_args.dataset}")
    logging.info(f"Input: {known_args.input}")
    logging.info(f"Output: {known_args.output}")
    
    if known_args.dataset in ['despoblamiento', 'all']:
        logging.info("Processing despoblamiento data...")
        run_despoblamiento_pipeline(known_args.input, known_args.output, pipeline_options)
    
    if known_args.dataset in ['poblacion', 'all']:
        logging.info("Processing poblacion data...")
        run_poblacion_pipeline(known_args.input, known_args.output, pipeline_options)
    
    logging.info("Beam pipeline completed!")


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.INFO)
    main()

