"""Pruebas unitarias para el módulo de análisis de redes y grafos vendedor-producto."""

from pathlib import Path
import sys
import unittest

import networkx as nx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from grafos import construir_grafo, calcular_metricas


class TestGrafos(unittest.TestCase):
    def setUp(self):
        # Datos sintéticos de ítems vendidos
        self.df_items = pd.DataFrame({
            "seller_id": ["s1", "s1", "s1", "s2", "s2", "s3"],
            "product_id": ["p1", "p1", "p2", "p2", "p3", "p4"],
            "order_item_id": [1, 2, 1, 1, 1, 1],
            "price": [50.0, 50.0, 30.0, 30.0, 70.0, 100.0],
            "order_id": ["o1", "o1", "o2", "o3", "o4", "o5"],
            "order_status": ["delivered"] * 6,
        })

    def test_construir_grafo(self):
        G, aristas, pob = construir_grafo(self.df_items)
        self.assertEqual(G.number_of_nodes(), 7)
        self.assertEqual(G.number_of_edges(), 5)
        self.assertTrue(nx.is_bipartite(G))
        self.assertEqual(G["v:s1"]["p:p1"]["peso"], 2)

    def test_calcular_metricas(self):
        G, _, _ = construir_grafo(self.df_items)
        metricas_df, resumen_comp = calcular_metricas(G)

        self.assertEqual(len(metricas_df), 7)
        self.assertIn("pagerank", metricas_df.columns)
        self.assertIn("grado_ponderado", metricas_df.columns)
        self.assertEqual(len(resumen_comp), 2)


if __name__ == "__main__":
    unittest.main()
