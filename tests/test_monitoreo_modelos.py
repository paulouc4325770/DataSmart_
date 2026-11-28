"""Pruebas para PSI y el alcance retrospectivo de monitoreo."""

from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from monitoreo_modelos import _append_csv, calcular_psi, construir_informe_drift, estado_psi


class TestMonitoreoModelos(unittest.TestCase):
    def test_psi_cero_para_distribuciones_iguales_y_posible_desplazamiento(self):
        self.assertAlmostEqual(calcular_psi([5, 5], [5, 5]), 0.0, places=12)
        desplazamiento = calcular_psi([90, 10], [20, 80])
        self.assertGreater(desplazamiento, 0.25)
        self.assertEqual(estado_psi(desplazamiento), 'cambio_alto_revisar_reentrenamiento')

    def test_informe_drift_compara_train_y_test_con_mismo_esquema(self):
        train = pd.DataFrame({
            'texto_limpio': ['bom produto'] * 30 + ['atraso ruim'] * 10,
            'sentimiento_score': ['positivo'] * 30 + ['negativo'] * 10,
        })
        test = pd.DataFrame({
            'texto_limpio': ['bom produto'] * 10 + ['atraso ruim'] * 30,
            'sentimiento_score': ['positivo'] * 10 + ['negativo'] * 30,
        })
        reporte = construir_informe_drift(train, test)
        self.assertEqual(set(reporte['variable']), {'longitud_caracteres', 'cantidad_tokens', 'sentimiento_score_proxy'})
        self.assertTrue((reporte['n_referencia'] == 40).all())
        self.assertTrue((reporte['n_actual'] == 40).all())
        self.assertTrue(reporte['estado'].str.len().gt(0).all())

    def test_psi_rechaza_entradas_invalidas(self):
        with self.assertRaises(ValueError):
            calcular_psi([], [])
        with self.assertRaises(ValueError):
            calcular_psi([1, 2], [1])

    def test_historial_append_conserva_ejecuciones_y_deduplica_version(self):
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / 'model_history.csv'
            _append_csv(path, pd.DataFrame([{'model_version': 'v1', 'metric': 1}]), unique_by='model_version')
            _append_csv(path, pd.DataFrame([{'model_version': 'v2', 'metric': 2}]), unique_by='model_version')
            _append_csv(path, pd.DataFrame([{'model_version': 'v1', 'metric': 3}]), unique_by='model_version')
            history = pd.read_csv(path)
        self.assertEqual(list(history['model_version']), ['v1', 'v2'])
        self.assertEqual(list(history['metric']), [1, 2])


if __name__ == '__main__':
    unittest.main()
