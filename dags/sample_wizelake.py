# Import packages
from airflow import DAG
from airflow.contrib.operators.bigquery_operator import BigQueryOperator
from airflow.operators.dummy_operator import DummyOperator
from datetime import datetime
from airflow.contrib.operators.gcs_to_bq import GoogleCloudStorageToBigQueryOperator
from airflow.contrib.operators.bigquery_check_operator import BigQueryCheckOperator
from airflow.operators.python_operator import PythonOperator
from airflow.contrib.operators.file_to_gcs import FileToGoogleCloudStorageOperator
from scripts.wizelake_bamboo_ingest_v2 import process_bamboo_report
import os
# from airflow.hooks.base_hook import BaseHook
# from airflow.contrib.operators.slack_webhook_operator import SlackWebhookOperator
#import utils.slack_notification as slack
REPORT_ID = 109
# Define default arguments
default_args = {
    'owner': 'Bizops',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    #'on_failure_callback': slack.task_fail_slack_alert
}
# Dag variables
project_id = os.environ['PROJECT_ID']
staging_dataset = os.environ['BAMBOO_STAGING_DATASET']
wzlk_views_dataset = os.environ['BAMBOO_VIEWS_DATASET']
gs_bucket = os.environ['PROJECT_ID']
# Define dag
with DAG( dag_id='bamboo-datalake-pipeline',
    start_date= datetime(2021, 6, 9),
    schedule_interval='0 0,4,8,12,16,20 * * *',
    concurrency=5,
    max_active_runs=1,
    default_args=default_args) as dag:
    start_pipeline = DummyOperator(
        task_id= 'start_pipeline'
    )
    # Get bamboo report 
    extract_employees = PythonOperator(
        task_id='extract_employees', 
        python_callable=process_bamboo_report, 
        op_args=[REPORT_ID]
    )
    # Load local data to GCS
    load_csv_to_gcs = FileToGoogleCloudStorageOperator(
        task_id= 'load_csv_to_gcs',
        bucket= gs_bucket,
        src= "{{ task_instance.xcom_pull(task_ids='extract_employees')[2] }}",
        dst= "{{ task_instance.xcom_pull(task_ids='extract_employees')[3] }}"
    )
    load_schema_to_gcs = FileToGoogleCloudStorageOperator(
        task_id= 'load_schema_to_gcs',
        bucket= gs_bucket,
        src= "{{ task_instance.xcom_pull(task_ids='extract_employees')[0] }}",
        dst= "{{ task_instance.xcom_pull(task_ids='extract_employees')[1] }}"
    )
    # Load data from GCS to BQ
    load_employees_to_gbq = GoogleCloudStorageToBigQueryOperator(
        task_id = 'load_employees_to_gbq',
        bucket = gs_bucket,
        source_objects = ["{{ task_instance.xcom_pull(task_ids='extract_employees')[3] }}"],
        destination_project_dataset_table = f'{project_id}:{staging_dataset}.employees',
        schema_object = "{{ task_instance.xcom_pull(task_ids=\'extract_employees\')[1] }}", 
        write_disposition='WRITE_TRUNCATE',
        source_format = 'csv',
        field_delimiter=',',
        skip_leading_rows = 1
    )
    # Check loaded data not null
    check_employees_table = BigQueryCheckOperator(
        task_id = 'check_employees_table',
        use_legacy_sql=False,
        sql = f'SELECT count(*) FROM `{project_id}.{staging_dataset}.employees`'
    )
    # Transform and load views
    create_employees_view = BigQueryOperator(
        task_id = 'create_employee_view',
        use_legacy_sql = False,
        params = {
            'project_id': project_id,
            'staging_dataset': staging_dataset,
            'dwh_dataset': wzlk_views_dataset
        },
        sql = './sql/EMPLOYEES_WZLK.sql'
    )
    # Check view
    check_employees_view = BigQueryCheckOperator(
        task_id = 'check_employee_view',
        use_legacy_sql=False,
        params = {
            'project_id': project_id,
            'staging_dataset': staging_dataset,
            'dwh_dataset': wzlk_views_dataset
        },
        sql = f'SELECT count(*) FROM `{project_id}.{wzlk_views_dataset}.employee`'
    )
    finish_pipeline = DummyOperator(
        task_id = 'finish_pipeline'
    )
    # Define task dependencies
    start_pipeline >> extract_employees >> [load_csv_to_gcs, load_schema_to_gcs] >> load_employees_to_gbq >> check_employees_table
    check_employees_table >> create_employees_view >> check_employees_view >> finish_pipeline