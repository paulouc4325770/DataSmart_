"""
Pruebas unitarias para el módulo de Series Temporales (DataSmart).
"""

import unittest
from pathlib import Path
import pandas as pd
import numpy as np

from src.series_temporales import cargar_serie_ventas, evaluar_modelos_series

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "data" / "processed" / "pedidos_procesados.csv"
RESULTADOS_DIR = ROOT_DIR / "resultados"


class TestSeriesTemporales(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.serie = cargar_serie_ventas(DATA_PATH)
        cls.df_pronosticos, cls.df_evaluacion, cls.metadata = evaluar_modelos_series(cls.serie, n_test=12)

    def test_serie_completa_valida(self):
        """Verifica que la serie semanal no tenga nulos y contenga 84 semanas completas."""
        self.assertGreaterEqual(len(self.serie), 80)
        self.assertFalse(self.serie.isna().any(), "La serie no debe contener valores nulos.")
        self.assertEqual(self.serie.index.freqstr, "W-SUN", "La frecuencia debe ser semanal anclada en domingo.")

    def test_evaluacion_sin_data_leakage(self):
        """Verifica que la partición sea cronológica estricta sin solapamiento."""
        for _, row in self.df_evaluacion.iterrows():
            train_fin = pd.to_datetime(row["train_fin"])
            test_inicio = pd.to_datetime(row["test_inicio"])
            self.assertLess(train_fin, test_inicio, "El fin de train debe ser estrictamente anterior al inicio de test.")
            self.assertEqual(row["n_test"], 12)
            self.assertGreater(row["mae_brl"], 0.0)
            self.assertGreater(row["rmse_brl"], 0.0)

    def test_suavizamiento_supera_baseline(self):
        """Comprueba que el modelo exponencial reduzca el error respecto al baseline ingenuo."""
        mae_base = self.df_evaluacion.loc[self.df_evaluacion["modelo"] == "baseline_ultimo", "mae_brl"].values[0]
        mae_ses = self.df_evaluacion.loc[self.df_evaluacion["modelo"] == "suavizamiento_exponencial_simple", "mae_brl"].values[0]
        self.assertLess(mae_ses, mae_base, "El suavizamiento exponencial simple debe tener menor MAE que el baseline.")

    def test_archivos_exportados_existen(self):
        """Verifica la existencia y contenido de los CSV y JSON de resultados."""
        self.assertTrue((RESULTADOS_DIR / "pronosticos_ventas.csv").is_file())
        self.assertTrue((RESULTADOS_DIR / "evaluacion_series.csv").is_file())
        self.assertTrue((RESULTADOS_DIR / "series_temporales_metadata.json").is_file())
        self.assertTrue((RESULTADOS_DIR / "graficos" / "series_temporales_prediccion.png").is_file())


if __name__ == "__main__":
    unittest.main()
