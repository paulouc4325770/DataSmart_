"""Pruebas unitarias para el módulo de segmentación y clustering RFM."""

from pathlib import Path
import sys
import unittest
from tempfile import TemporaryDirectory

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from clustering import (
    construir_rfm, preparar_variables_clustering, evaluar_k_clusters,
    generar_perfiles_clusters, NOMBRES_SEGMENTOS_K4,
)


class TestClustering(unittest.TestCase):
    def setUp(self):
        # Dataset de prueba controlado
        self.df_pedidos = pd.DataFrame({
            'order_id': ['ord_1', 'ord_2', 'ord_3', 'ord_4', 'ord_5'],
            'customer_unique_id': ['cust_A', 'cust_A', 'cust_B', 'cust_C', 'cust_D'],
            'order_purchase_timestamp': pd.to_datetime([
                '2018-08-01 10:00:00',
                '2018-08-15 12:00:00',  # cust_A compra 2 veces
                '2018-08-10 09:00:00',  # cust_B
                '2018-05-01 15:00:00',  # cust_C antigua
                '2018-08-20 18:00:00',  # cust_D reciente
            ]),
            'valor_articulos': [100.0, 150.0, 50.0, 300.0, 45.0],
            'es_entregado': [True, True, True, True, True],
        })
        self.ref_date = pd.to_datetime('2018-08-21 18:00:00')

    def test_construir_rfm(self):
        rfm, ref = construir_rfm(self.df_pedidos, fecha_referencia=self.ref_date)
        self.assertEqual(len(rfm), 4)  # 4 clientes únicos
        
        # cust_A tiene 2 pedidos y monto 250
        cust_a = rfm.loc[rfm['customer_unique_id'] == 'cust_A'].iloc[0]
        self.assertEqual(cust_a['frecuencia'], 2)
        self.assertEqual(cust_a['monto_brl'], 250.0)
        # Última compra de cust_A fue el 2018-08-15 12:00:00
        # ref = 2018-08-21 18:00:00 -> 6 días y 6 horas = 6.25 días
        self.assertAlmostEqual(cust_a['recencia_dias'], 6.25, places=2)

    def test_preparar_variables_clustering(self):
        rfm, _ = construir_rfm(self.df_pedidos, fecha_referencia=self.ref_date)
        X_scaled, scaler = preparar_variables_clustering(rfm)
        self.assertEqual(X_scaled.shape, (4, 3))
        # Medias cercanas a 0 y desv aprox 1 tras StandardScaler
        self.assertAlmostEqual(X_scaled[:, 0].mean(), 0.0, places=5)
        self.assertAlmostEqual(X_scaled[:, 1].mean(), 0.0, places=5)
        self.assertAlmostEqual(X_scaled[:, 2].mean(), 0.0, places=5)

    def test_evaluar_k_clusters(self):
        # Crear datos sintéticos suficientes para k=2 y k=3
        np.random.seed(42)
        X_dummy = np.random.randn(50, 3)
        eval_df, modelos = evaluar_k_clusters(X_dummy, k_range=range(2, 4), semilla=42, muestra_silhouette=50)
        
        self.assertEqual(len(eval_df), 2)
        self.assertIn('silhouette', eval_df.columns)
        self.assertIn('davies_bouldin', eval_df.columns)
        self.assertIn('inercia', eval_df.columns)
        self.assertIn(2, modelos)
        self.assertIn(3, modelos)

    def test_generar_perfiles_clusters(self):
        rfm, _ = construir_rfm(self.df_pedidos, fecha_referencia=self.ref_date)
        labels = np.array([0, 1, 2, 3])
        rfm_etq, perfiles = generar_perfiles_clusters(rfm, labels, k=4)
        
        self.assertEqual(len(perfiles), 4)
        self.assertIn('segmento', perfiles.columns)
        self.assertIn('accion_comercial', perfiles.columns)
        self.assertEqual(perfiles['clientes'].sum(), 4)


if __name__ == '__main__':
    unittest.main()
