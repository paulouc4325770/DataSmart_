"""Pruebas del clasificador de sentimiento supervisado sobre reseñas."""

from datetime import datetime, timedelta
import sys
from pathlib import Path
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from clasificacion_resenas import evaluar_clasificador, limpiar_comentario, preparar_resenas


def resenas_sinteticas(n=90):
    filas = []
    frases = {
        'negativo': 'produto ruim atraso e problema',
        'neutral': 'produto normal entrega comum',
        'positivo': 'produto otimo entrega excelente',
    }
    puntuaciones = {'negativo': 1, 'neutral': 3, 'positivo': 5}
    etiquetas = list(frases)
    inicio = datetime(2020, 1, 1)
    for i in range(n):
        etiqueta = etiquetas[i % len(etiquetas)]
        filas.append({
            'review_id': f'r{i}', 'order_id': f'o{i}', 'review_score': puntuaciones[etiqueta],
            'review_comment_message': frases[etiqueta] + f' palavra{i % 4}',
            'review_creation_date': (inicio + timedelta(days=i)).isoformat(),
        })
    return pd.DataFrame(filas)


class TestClasificacionResenas(unittest.TestCase):
    def test_limpieza_textual_y_etiqueta_basada_en_score(self):
        self.assertEqual(limpiar_comentario('<b>\u00d3TIMO!</b> https://exemplo.com'), 'otimo')
        preparadas, poblacion = preparar_resenas(resenas_sinteticas())
        self.assertEqual(set(preparadas['sentimiento_score']), {'negativo', 'neutral', 'positivo'})
        self.assertEqual(poblacion['resenas_elegibles'], 90)

    def test_entrenamiento_cronologico_no_usa_score_ni_fecha_como_predictor(self):
        evaluacion, predicciones, metadata, _ = evaluar_clasificador(resenas_sinteticas())
        self.assertGreater(metadata['n_train'], 0)
        self.assertGreater(metadata['n_test'], 0)
        self.assertLess(metadata['train_fin'], metadata['test_inicio'])
        self.assertIn('review_score', metadata['variables_excluidas'])
        self.assertEqual(evaluacion.iloc[0]['n_test'], metadata['n_test'])
        self.assertIn('f1_macro', evaluacion.columns)
        self.assertIn('roc_auc_ovr_macro', evaluacion.columns)
        self.assertNotIn('review_comment_message', predicciones.columns)
        self.assertEqual(set(predicciones['particion']), {'test_cronologico'})

    def test_rechaza_esquema_incompleto_y_clase_ausente(self):
        with self.assertRaises(ValueError):
            preparar_resenas(pd.DataFrame({'review_score': [5]}))
        solo_dos_clases = resenas_sinteticas()
        solo_dos_clases['review_score'] = solo_dos_clases['review_score'].replace(3, 5)
        with self.assertRaises(ValueError):
            evaluar_clasificador(solo_dos_clases)


if __name__ == '__main__':
    unittest.main()
