"""
DAG: convert_orders_to_eur_dag
Доставляти дані з таблиці orders в іншу локальну базу даних (postgres-2) на щогодинній основі.
Дані в таблиці orders_eur в postgres-2 приведені до єдиної валюти євро
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python_operator import PythonOperator
from airflow.utils.dates import days_ago

from utils import (
    fetch_exchange_rates,
    fetch_new_orders,
    convert_orders_to_eur,
    insert_into_orders_eur
)

default_args = {
    'owner': 'airflow',
    'start_date': days_ago(1),
    'catchup': False
}

dag = DAG(
    dag_id='convert_orders_to_eur_dag',
    default_args=default_args,
    description='Convert new orders to EUR and insert into postgres-2 every hour',
    schedule_interval='0 * * * *',
    max_active_runs=1,
    concurrency=1
)

def _convert_orders_to_eur_task(**context):
    """
    1) Викликаємо OpenExchangeRates API для отримання курсів валют
    2) Отримуємо нові замовлення з postgres-1 (фільтруємо по created_at >= last_run_time)
    3) Конвертуємо суму кожного замовлення в EUR
    4) Вставляємо дані в таблицю orders_eur в postgres-2
    """
    # Отримуємо час попереднього запуску DAG (Airflow макрос)
    last_run_time = context['prev_execution_date']
    if last_run_time is None:
        # Якщо це перший запуск - можна підставити якусь стартову дату
        last_run_time = days_ago(1)

    rates_data = fetch_exchange_rates()
    # Тут використовуємо нову версію fetch_new_orders з created_at
    new_orders = fetch_new_orders(last_run_time=last_run_time)
    converted_rows = convert_orders_to_eur(new_orders, rates_data)
    insert_into_orders_eur(converted_rows)

convert_orders_to_eur_task = PythonOperator(
    task_id='convert_orders_to_eur',
    python_callable=_convert_orders_to_eur_task,
    dag=dag
)