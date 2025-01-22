import os
import random
import string
import uuid
import requests
import psycopg2
from datetime import datetime, timedelta
from typing import List, Tuple

# Функція для отримання параметрів підключення до бази даних
def get_postgres_connection_params(db_prefix: str) -> dict:
    """
    Отримати параметри підключення до PostgresSQL з змінних середовища.
    """
    return {
        'dbname': os.environ.get(f"{db_prefix}DB"),
        'user': os.environ.get(f"{db_prefix}USER"),
        'password': os.environ.get(f"{db_prefix}PASSWORD"),
        'host': os.environ.get(f"{db_prefix}HOST"),
        'port': os.environ.get(f"{db_prefix}PORT"),
    }

# Запит для створення таблиці orders
CREATE_TABLE_ORDERS_SQL = """
CREATE TABLE IF NOT EXISTS orders (
    order_id UUID PRIMARY KEY,
    customer_email VARCHAR(255),
    order_date TIMESTAMP,
    amount NUMERIC(10, 2),
    currency VARCHAR(10)
);
"""

# Запит для вставки даних в таблицю orders
INSERT_ORDERS_SQL = """
INSERT INTO orders (
    order_id,
    customer_email,
    order_date,
    amount,
    currency
)
VALUES (%s, %s, %s, %s, %s);
"""
# Запит для створення таблиці orders_eur
CREATE_TABLE_ORDERS_EUR_SQL = """
CREATE TABLE IF NOT EXISTS orders_eur (
    order_id UUID PRIMARY KEY,
    customer_email VARCHAR(255),
    order_date TIMESTAMP,
    original_amount NUMERIC(10, 2),
    original_currency VARCHAR(10),
    amount_eur NUMERIC(10, 2)
);
"""

# Запит для вставки даних в таблицю orders_eur
INSERT_ORDERS_EUR_SQL = """
INSERT INTO orders_eur (
    order_id,
    customer_email,
    order_date,
    original_amount,
    original_currency,
    amount_eur
)
VALUES (%s, %s, %s, %s, %s, %s)
ON CONFLICT (order_id) DO NOTHING;
"""

# Запит для вибору нових замовлень
SELECT_NEW_ORDERS_SQL = """
SELECT order_id, customer_email, order_date, amount, currency
FROM orders
WHERE order_date >= %s
"""

# Функція для отримання можливих валют з OpenExchangeRates API
def get_possible_currencies() -> List[str]:
    """
    Fetch available currencies from the exchange rates API.
    """
    rates_data = fetch_exchange_rates()
    return list(rates_data.get('rates', {}).keys())

# Функція для створення таблиці orders
def create_orders_table(cursor) -> None:
    """
    Create the 'orders' table if it doesn't exist.
    """
    cursor.execute(CREATE_TABLE_ORDERS_SQL)

# Функція для генерації випадкових замовлень
def generate_random_orders(num_orders: int = 5000) -> List[Tuple[str, str, datetime, float, str]]:
    """
    Генерує список випадкових замовлень, кожен з яких є кортежем:
    (order_id, customer_email, order_date, amount, currency).
    """
    now = datetime.now()
    seven_days_ago = now - timedelta(days=7)
    rows_to_insert = []

    # отримуємо можливі валюти
    possible_currencies = get_possible_currencies()
    if not possible_currencies:
        raise ValueError("No currencies available from the API")
    
    for _ in range(num_orders):
        order_id = str(uuid.uuid4())
        name_part = ''.join(random.choices(string.ascii_lowercase, k=7))
        domain_part = ''.join(random.choices(string.ascii_lowercase, k=5))
        email = f"{name_part}@{domain_part}.com"

        # замовлення випадково вибираються в межах останніх 7 днів
        random_date = seven_days_ago + (now - seven_days_ago) * random.random()

        amount = round(random.uniform(10, 5000), 2)

        currency = random.choice(possible_currencies)
        rows_to_insert.append((order_id, email, random_date, amount, currency))

    return rows_to_insert

# Функція для отримання курсів валют
def fetch_exchange_rates() -> dict:
    """
    Отримати курси валют з API OpenExchangeRates.
    """
    api_key = os.environ.get('OPENEXCHANGE_API_KEY')
    base_url = os.environ.get('OPENEXCHANGE_BASE_URL', 'https://openexchangerates.org/api/latest.json')
    response = requests.get(base_url, params={"app_id": api_key})
    response.raise_for_status()
    return response.json()

# Функція для отримання нових замовлень
def fetch_new_orders(hours_back: int = 1) -> List[Tuple]:
    """
    Конектимося до postgres-1, отримуємо нові замовлення з останню годину за замовчуванням,
    та повертаємо список кортежів:
    (order_id, customer_email, order_date, amount, currency).
    """
    conn_params_src = get_postgres_connection_params("POSTGRES_1_")
    last_hour_dt = datetime.now() - timedelta(hours=hours_back)

    with psycopg2.connect(**conn_params_src) as conn:
        with conn.cursor() as cur:
            cur.execute(SELECT_NEW_ORDERS_SQL, (last_hour_dt,))
            return cur.fetchall()

# Функція для конвертації суми кожного замовлення в EUR
def convert_orders_to_eur(orders: List[Tuple], rates_data: dict) -> List[Tuple]:
    """
    Конвертуємо суму кожного замовлення в EUR.
    Вхідні значення (order_id, email, order_date, amount, currency).
    Вихідні значення (order_id, email, order_date, original_amount, original_currency, amount_eur).
    """
    eur_rate = rates_data['rates'].get('EUR')
    converted_rows = []

    for (order_id, email, order_date, amount, currency) in orders:
        # перевіряємо, чи валюта вже є EUR
        if currency == 'EUR':
            amount_eur = float(amount)
        # перевіряємо, чи валюта взагалі є в доступних курсах валют    
        else:
            currency_rate = rates_data['rates'].get(currency)
            if not currency_rate or not eur_rate:
                continue
            # конвертуємо суму в EUR
            amount_eur = float(amount) * (eur_rate / currency_rate)

        converted_rows.append((
            order_id,
            email,
            order_date,
            amount,
            currency,
            round(amount_eur, 2)
        ))

    return converted_rows

# Функція для вставки даних в таблицю orders_eur
def insert_into_orders_eur(converted_rows: List[Tuple]) -> None:
    """
    Створюємо таблицю orders_eur в postgres-2 та додаємо в неї дані.
    """
    conn_params_dst = get_postgres_connection_params("POSTGRES_2_")

    with psycopg2.connect(**conn_params_dst) as conn:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_ORDERS_EUR_SQL)
            cur.executemany(INSERT_ORDERS_EUR_SQL, converted_rows)