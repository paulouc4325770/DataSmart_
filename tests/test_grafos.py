"""Pruebas unitarias para el módulo de análisis de redes y grafos vendedor-producto."""

from pathlib import Path
import sys
import unittest

import networkx as nx
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from grafos import (
    construir_grafo_bipartito, calcular_metricas_red, extraer_subgrafo_legible,
)


class TestGrafos(unittest.TestCase):
    def setUp(self):
        # Datos sintéticos de ítems vendidos
        self.df_items = pd.DataFrame({
            'seller_id': ['s1', 's1', 's1', 's2', 's2', 's3'],
            'product_id': ['p1', 'p1', 'p2', 'p2', 'p3', 'p4'],
            'order_item_id': [1, 2, 1, 1, 1, 1],
            'price': [50.0, 50.0, 30.0, 30.0, 70.0, 100.0],
            'seller_city': ['Sao Paulo', 'Sao Paulo', 'Sao Paulo', 'Curitiba', 'Curitiba', 'Rio'],
            'seller_state': ['SP', 'SP', 'SP', 'PR', 'PR', 'RJ'],
            'categoria_presentacion': ['Informatica', 'Informatica', 'Informatica', 'Informatica', 'Hogar', 'Salud'],
            'order_status': ['delivered'] * 6,
        })

    def test_construir_grafo_bipartito(self):
        G, aristas, dict_s, dict_p = construir_grafo_bipartito(self.df_items)
        # Nodos: s1, s2, s3 (3 vendedores) + p1, p2, p3, p4 (4 productos) = 7
        self.assertEqual(G.number_of_nodes(), 7)
        # Aristas: (s1, p1 peso=2), (s1, p2 peso=1), (s2, p2 peso=1), (s2, p3 peso=1), (s3, p4 peso=1) = 5
        self.assertEqual(G.number_of_edges(), 5)
        self.assertTrue(nx.is_bipartite(G))
        self.assertEqual(G['s1']['p1']['weight'], 2)
        self.assertEqual(G['s1']['p1']['monto'], 100.0)

    def test_calcular_metricas_red(self):
        G, _, _, _ = construir_grafo_bipartito(self.df_items)
        metricas_df, componentes, pagerank = calcular_metricas_red(G)
        
        self.assertEqual(len(metricas_df), 7)
        self.assertIn('pagerank', metricas_df.columns)
        self.assertIn('grado_ponderado', metricas_df.columns)
        self.assertIn('componente_id', metricas_df.columns)
        
        # s3 <-> p4 es un componente desconectado del resto (s1, s2, p1, p2, p3)
        self.assertEqual(len(componentes), 2)
        # Grado ponderado de s1 es 2 (p1) + 1 (p2) = 3
        s1_row = metricas_df.loc[metricas_df['nodo'] == 's1'].iloc[0]
        self.assertEqual(s1_row['grado_ponderado'], 3)
        self.assertEqual(s1_row['grado'], 2)

    def test_extraer_subgrafo_legible(self):
        G, _, _, _ = construir_grafo_bipartito(self.df_items)
        metricas_df, _, _ = calcular_metricas_red(G)
        subG, sub_dict = extraer_subgrafo_legible(G, metricas_df, max_vendedores=2, max_productos_por_vendedor=2)
        
        self.assertGreater(len(sub_dict['nodes']), 0)
        self.assertGreater(len(sub_dict['links']), 0)
        self.assertIn('criterio_seleccion', sub_dict)


if __name__ == '__main__':
    unittest.main()
