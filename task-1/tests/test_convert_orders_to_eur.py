import unittest
from datetime import datetime
from dags.utils import convert_orders_to_eur

class TestConvertOrdersToEUR(unittest.TestCase):
    def setUp(self):
        self.rates_data = {
            "rates": {
                "EUR": 1.0,
                "USD": 1.1,
                "GBP": 0.9
            }
        }
        
    # функція для перевірки конвертації суми кожного замовлення в EUR
    def test_convert_orders_to_eur_all_eur(self):
        orders = [
            ("1", "customer@example.com", datetime(2023, 1, 1, 12, 0), 100.0, "EUR"),
            ("2", "customer@example.com", datetime(2023, 1, 1, 13, 0), 200.0, "EUR"),
        ]
        converted = convert_orders_to_eur(orders, self.rates_data)
        expected = [
            ("1", "customer@example.com", datetime(2023, 1, 1, 12, 0), 100.0, "EUR", 100.0),
            ("2", "customer@example.com", datetime(2023, 1, 1, 13, 0), 200.0, "EUR", 200.0),
        ]
        self.assertEqual(converted, expected)

    # функція для перевірки конвертації суми кожного замовлення в EUR
    def test_convert_orders_to_eur_mixed_currencies(self):
        orders = [
            ("1", "customer@example.com", datetime(2023, 1, 1, 12, 0), 100.0, "USD"),
            ("2", "customer@example.com", datetime(2023, 1, 1, 13, 0), 200.0, "GBP"),
        ]
        converted = convert_orders_to_eur(orders, self.rates_data)
        expected = [
            ("1", "customer@example.com", datetime(2023, 1, 1, 12, 0), 100.0, "USD", 90.91),
            ("2", "customer@example.com", datetime(2023, 1, 1, 13, 0), 200.0, "GBP", 222.22),
        ]
        for c, e in zip(converted, expected):
            self.assertEqual(c[:5], e[:5])
            self.assertAlmostEqual(c[5], e[5], places=2)

    # функція для перевірки конвертації суми кожного замовлення в EUR
    def test_convert_orders_to_eur_unknown_currency(self):
        orders = [
            ("1", "customer@example.com", datetime(2023, 1, 1, 12, 0), 100.0, "XYZ"),
        ]
        converted = convert_orders_to_eur(orders, self.rates_data)
        self.assertEqual(converted, [])

    # функція для перевірки конвертації суми кожного замовлення в EUR
    def test_convert_orders_to_eur_missing_rates(self):
        rates_data = {"rates": {"EUR": 1.0}}
        orders = [
            ("1", "customer@example.com", datetime(2023, 1, 1, 12, 0), 100.0, "USD"),
        ]
        converted = convert_orders_to_eur(orders, rates_data)
        self.assertEqual(converted, [])

if __name__ == "__main__":
    unittest.main()
