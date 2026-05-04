"""Test and setup Snowflake connection."""
import snowflake.connector
from dotenv import load_dotenv
import os

load_dotenv()

account = 'fj69748.sa-east-1.aws'
user = os.getenv('SNOWFLAKE_USER')
password = os.getenv('SNOWFLAKE_PASSWORD')
database = os.getenv('SNOWFLAKE_DATABASE')
warehouse = os.getenv('SNOWFLAKE_WAREHOUSE')
role = os.getenv('SNOWFLAKE_ROLE')

print('=' * 50)
print('SNOWFLAKE SETUP')
print('=' * 50)

conn = snowflake.connector.connect(
    account=account,
    user=user,
    password=password,
    login_timeout=30
)
cursor = conn.cursor()

cursor.execute('SELECT CURRENT_VERSION(), CURRENT_ACCOUNT(), CURRENT_REGION()')
result = cursor.fetchone()
print(f'Connected to Snowflake!')
print(f'  Version: {result[0]}')
print(f'  Account: {result[1]}')
print(f'  Region: {result[2]}')
print()

print('Setting up resources...')
cursor.execute(f'USE ROLE {role}')
print(f'  Role {role}: OK')

cursor.execute(f"CREATE WAREHOUSE IF NOT EXISTS {warehouse} WITH WAREHOUSE_SIZE = 'XSMALL' AUTO_SUSPEND = 60 AUTO_RESUME = TRUE")
cursor.execute(f'USE WAREHOUSE {warehouse}')
print(f'  Warehouse {warehouse}: OK')

cursor.execute(f'CREATE DATABASE IF NOT EXISTS {database}')
cursor.execute(f'USE DATABASE {database}')
print(f'  Database {database}: OK')

cursor.execute('CREATE SCHEMA IF NOT EXISTS PUBLIC')
cursor.execute('USE SCHEMA PUBLIC')
print(f'  Schema PUBLIC: OK')

conn.close()
print()
print('=' * 50)
print('SNOWFLAKE IS READY!')
print('=' * 50)
print()
print('You can now run:')
print('  python -m src.pipeline.main --target snowflake')

