-- вибираємо максимальну дату з таблиці purchases, яка буде використана як watermark для вибору нових даних
WITH last_timestamp AS (
    SELECT
        COALESCE(MAX(uploaded_at), '1900-01-01') AS watermark
    FROM purchases
),

-- вибираємо всі замовлення, транзакції та верифікацію з таблиць orders, transactions, verification
-- які рядки змінювати або вставляти в кінцеву таблицю purchases
-- для кожного замовлення вибираємо транзакції та верифікацію з максимальною датою
source_data AS (
    SELECT
        o.*,
        t.*,
        v.*,
        GREATEST(o.updated_at, t.updated_at, v.updated_at) AS max_updated_at
    FROM orders AS o
    JOIN transactions AS t ON o.id = t.order_id
    JOIN verification AS v ON t.id = v.transaction_id
    WHERE GREATEST(o.updated_at, t.updated_at, v.updated_at) > (SELECT watermark FROM last_timestamp)
      AND o.id IS NOT NULL
      AND t.order_id IS NOT NULL
      AND v.transaction_id IS NOT NULL
)

-- обираємо з таблиць orders, transactions, verification ті рядки, що мають бути зміненими або вставленими в кінцеву таблицю purchases
MERGE INTO purchases p
USING source_data s
ON p.order_id = s.order_id
WHEN MATCHED THEN
    UPDATE SET
        ...
        p.uploaded_at = CURRENT_TIMESTAMP  -- оновлюємо дату останнього завантаження
WHEN NOT MATCHED THEN
    INSERT (
        ...,
        uploaded_at
    )
    VALUES (
        ...,
        CURRENT_TIMESTAMP   -- вставляємо новий рядок з датою завантаження
    );
