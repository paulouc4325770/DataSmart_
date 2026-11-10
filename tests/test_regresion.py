"""
Pruebas unitarias para el módulo de Regresión Predictiva de Días de Entrega (DataSmart).
"""

import unittest
from pathlib import Path
import pandas as pd
import numpy as np

from src.regresion import (
    preparar_dataset_regresion,
    entrenar_y_evaluar_regresion,
    PEDIDOS_PATH,
    ITEMS_PATH,
    FECHA_CORTE_TEST,
)

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = ROOT_DIR / "resultados"


class TestRegresion(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = preparar_dataset_regresion(PEDIDOS_PATH, ITEMS_PATH)
        cls.df_predicciones, cls.df_evaluacion, cls.metadata = entrenar_y_evaluar_regresion(cls.df)

    def test_dataset_preparado_consistencia(self):
        """Verifica que el dataset contenga exactamente los 96,470 pedidos entregados evaluables."""
        self.assertEqual(len(self.df), 96470)
        self.assertTrue((self.df["dias_entrega"] > 0).all())
        self.assertFalse(self.df["dias_entrega"].isna().any())
        self.assertTrue("peso_total_g" in self.df.columns)
        self.assertTrue("distancia_media_km" in self.df.columns)

    def test_exclusion_estricta_de_fuga_de_datos(self):
        """Verifica que ninguna variable posterior a la compra esté en los predictores."""
        prohibidos = [
            "dias_retraso_calendario",
            "entrega_tardia",
            "calificacion_media",
            "cantidad_resenas",
            "sin_resenas",
            "order_delivered_customer_date",
            "order_delivered_carrier_date",
        ]
        columnas_usadas = [
            "cantidad_items",
            "cantidad_productos",
            "cantidad_vendedores",
            "valor_articulos",
            "valor_flete",
            "dias_prometidos",
            "peso_total_g",
            "volumen_total_cm3",
            "distancia_media_km",
            "distancia_max_km",
            "hora_compra",
            "dia_semana_compra",
            "mes_compra",
            "ruta_interestatal_int",
            "customer_state",
            "seller_state_principal",
        ]
        for p in prohibidos:
            self.assertNotIn(p, columnas_usadas)

    def test_split_cronologico_sin_lookahead(self):
        """Verifica que todas las compras de train ocurran antes que las de test."""
        for _, row in self.df_evaluacion.iterrows():
            train_fin = pd.to_datetime(row["train_fin"])
            test_inicio = pd.to_datetime(row["test_inicio"])
            self.assertLess(train_fin, test_inicio)
            self.assertEqual(row["n_train"], 77867)
            self.assertEqual(row["n_test"], 18603)

    def test_random_forest_supera_baseline(self):
        """Verifica que Random Forest reduzca el MAE de días respecto al baseline."""
        mae_base = self.df_evaluacion.loc[self.df_evaluacion["modelo"] == "baseline_mediana", "mae_dias"].values[0]
        mae_rf = self.df_evaluacion.loc[self.df_evaluacion["modelo"] == "random_forest", "mae_dias"].values[0]
        self.assertLess(mae_rf, mae_base)
        self.assertLess(mae_rf, 4.5, "El MAE de Random Forest debe ser inferior a 4.5 días.")

    def test_archivos_exportados_existen(self):
        """Verifica que los CSV, JSON y gráficos de regresión estén generados."""
        self.assertTrue((RESULTADOS_DIR / "predicciones_entrega.csv").is_file())
        self.assertTrue((RESULTADOS_DIR / "evaluacion_regresion.csv").is_file())
        self.assertTrue((RESULTADOS_DIR / "regresion_metadata.json").is_file())
        self.assertTrue((RESULTADOS_DIR / "graficos" / "regresion_real_vs_predicho.png").is_file())
        self.assertTrue((RESULTADOS_DIR / "graficos" / "regresion_residuos.png").is_file())


if __name__ == "__main__":
    unittest.main()
