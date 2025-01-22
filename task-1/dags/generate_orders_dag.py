"""
DAG: generate_orders_dag
Генерує випадкові замовлення кожні 10 хвилин, генерує 5 000 нових рядків з випадковими замовленнями
і вставляє їх в таблицю orders
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

from utils import (
    get_postgres_connection_params,
    create_orders_table,
    generate_random_orders,
    INSERT_ORDERS_SQL,
)

import psycopg2


default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
    'catchup': False
}

dag = DAG(
    dag_id='generate_orders_dag',
    default_args=default_args,
    description='Generate random orders every 10 minutes',
    schedule_interval='*/10 * * * *',
    max_active_runs=1,
    concurrency=1
)

def _generate_orders_task(**context):
    """
    1) Створюємо таблицю orders, якщо вона не існує
    2) Генеруємо 5 тис. випадкових замовлень
    3) Вставляємо їх в таблицю
    """
    conn_params = get_postgres_connection_params("POSTGRES_1_")

    with psycopg2.connect(**conn_params) as conn:
        with conn.cursor() as cur:
            create_orders_table(cur)
            rows_to_insert = generate_random_orders(num_orders=5000)
            cur.executemany(INSERT_ORDERS_SQL, rows_to_insert)

generate_orders_task = PythonOperator(
    task_id='generate_orders',
    python_callable=_generate_orders_task,
    dag=dag
)