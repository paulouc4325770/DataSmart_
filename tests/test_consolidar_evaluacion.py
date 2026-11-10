"""
Pruebas unitarias para la consolidación multimodelo de DataSmart.
"""

import unittest
from pathlib import Path
import pandas as pd

from src.consolidar_evaluacion import consolidar_evaluacion

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = ROOT_DIR / "resultados"


class TestConsolidarEvaluacion(unittest.TestCase):
    def test_consolidacion_cinco_familias(self):
        """Verifica que se consoliden las 5 familias de minería de datos."""
        df = consolidar_evaluacion()
        familias = set(df["tecnica"].unique())
        esperadas = {
            "Reglas de Asociación",
            "Clustering RFM",
            "Grafos y Redes Complejas",
            "Series Temporales",
            "Regresión Predictiva",
        }
        self.assertEqual(familias, esperadas)
        self.assertGreaterEqual(len(df), 30)

    def test_columnas_contrato(self):
        """Verifica que las columnas coincidan con el contrato de entrega."""
        df = consolidar_evaluacion()
        columnas_esperadas = [
            "tecnica",
            "modelo",
            "metrica",
            "valor",
            "unidad",
            "poblacion",
            "particion",
            "n_evaluacion",
            "parametros_json",
            "tiempo_s",
        ]
        self.assertEqual(list(df.columns), columnas_esperadas)


if __name__ == "__main__":
    unittest.main()
