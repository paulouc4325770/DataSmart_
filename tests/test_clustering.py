"""Pruebas unitarias para el módulo de segmentación y clustering RFM."""

from pathlib import Path
import sys
import unittest

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from clustering import (
    construir_rfm,
    transformar_rfm,
    evaluar_modelos,
    perfilar_clusters,
)


class TestClustering(unittest.TestCase):
    def setUp(self):
        # Dataset de prueba controlado
        self.df_pedidos = pd.DataFrame({
            "order_id": ["ord_1", "ord_2", "ord_3", "ord_4", "ord_5", "ord_6", "ord_7"],
            "customer_unique_id": ["cust_A", "cust_A", "cust_B", "cust_C", "cust_D", "cust_E", "cust_F"],
            "order_purchase_timestamp": [
                "2018-08-01 10:00:00",
                "2018-08-15 12:00:00",
                "2018-08-10 09:00:00",
                "2018-05-01 15:00:00",
                "2018-08-20 18:00:00",
                "2018-07-20 18:00:00",
                "2018-06-20 18:00:00",
            ],
            "valor_articulos": [100.0, 150.0, 50.0, 300.0, 45.0, 80.0, 120.0],
            "order_status": ["delivered"] * 7,
        })
        self.ref_date = "2018-08-22"

    def test_construir_rfm(self):
        rfm, resumen = construir_rfm(self.df_pedidos, fecha_referencia=self.ref_date)
        self.assertEqual(len(rfm), 6)  # 6 clientes únicos
        cust_a = rfm.loc[rfm["customer_unique_id"] == "cust_A"].iloc[0]
        self.assertEqual(cust_a["frecuencia"], 2)
        self.assertEqual(cust_a["monto"], 250.0)
        self.assertGreater(cust_a["recencia"], 0)

    def test_transformar_rfm(self):
        rfm, _ = construir_rfm(self.df_pedidos, fecha_referencia=self.ref_date)
        escaladas, dist, trans, scaler = transformar_rfm(rfm)
        self.assertEqual(escaladas.shape[0], len(rfm))
        self.assertEqual(escaladas.shape[1], 3)
        self.assertAlmostEqual(float(escaladas.mean()), 0.0, places=1)


if __name__ == "__main__":
    unittest.main()
