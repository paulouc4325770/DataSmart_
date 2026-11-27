"""Pruebas unitarias para el módulo de segmentación y clustering RFM."""

from pathlib import Path
import sys
import unittest
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from clustering import (
    construir_rfm,
    transformar_rfm,
    evaluar_modelos,
    evaluar_dbscan,
    ejecutar_dbscan_solo,
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

    def test_dbscan_es_reproducible_y_reporta_ruido_sin_extrapolar(self):
        rng = np.random.default_rng(13)
        puntos = np.vstack([
            rng.normal(0, .04, size=(40, 3)),
            rng.normal(4, .04, size=(40, 3)),
            rng.uniform(-3, 7, size=(20, 3)),
        ])
        clientes = pd.DataFrame({
            'customer_unique_id': [f'c{i}' for i in range(len(puntos))],
            'recencia': puntos[:, 0], 'frecuencia': puntos[:, 1], 'monto': puntos[:, 2],
        })
        a = evaluar_dbscan(clientes, puntos, muestra=80, eps=.3, min_samples=5)
        b = evaluar_dbscan(clientes, puntos, muestra=80, eps=.3, min_samples=5)
        self.assertEqual(a[2], b[2])
        self.assertEqual(len(a[0]), 80)
        self.assertEqual(int(a[1]['cantidad_clientes'].sum()), 80)
        self.assertGreater(a[2]['n_clusters_sin_ruido'], 1)
        self.assertGreater(a[2]['n_ruido'], 0)

    def test_cli_dbscan_solo_no_escribe_sobre_las_salidas_kmeans(self):
        rng = np.random.default_rng(22)
        n = 120
        pedidos = pd.DataFrame({
            'order_id': [f'ord_{i}' for i in range(n)],
            'customer_unique_id': [f'cust_{i}' for i in range(n)],
            'order_status': ['delivered'] * n,
            'order_purchase_timestamp': [f'2018-01-{(i % 28) + 1:02d} 12:00:00' for i in range(n)],
            'valor_articulos': rng.uniform(10, 500, size=n),
        })
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            pedidos_path = tmp / 'pedidos.csv'
            pedidos.to_csv(pedidos_path, index=False)
            ejecutar_dbscan_solo(pedidos_path, tmp, muestra=100)
            outputs = tmp / 'resultados'
            self.assertTrue((outputs / 'perfiles_clusters_dbscan.csv').is_file())
            self.assertTrue((outputs / 'clustering_dbscan_metadata.json').is_file())
            self.assertFalse((outputs / 'perfiles_clusters.csv').exists())


if __name__ == "__main__":
    unittest.main()
