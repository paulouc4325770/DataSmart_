"""Pruebas de explicación global/local para el modelo TF-IDF lineal."""

import sys
from pathlib import Path
import unittest
from datetime import datetime, timedelta

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from clasificacion_resenas import limpiar_comentario
from clasificacion_resenas import evaluar_clasificador
from explicabilidad_resenas import explicaciones_locales, importancia_global


def resenas_sinteticas(n=90):
    frases = {'negativo': ('produto ruim atraso problema', 1),
              'neutral': ('produto normal entrega comum', 3),
              'positivo': ('produto otimo entrega excelente', 5)}
    inicio = datetime(2020, 1, 1)
    filas = []
    nombres = list(frases)
    for i in range(n):
        texto, score = frases[nombres[i % 3]]
        filas.append({'review_id': f'r{i}', 'order_id': f'o{i}', 'review_score': score,
                      'review_comment_message': f'{texto} palavra{i % 4}',
                      'review_creation_date': (inicio + timedelta(days=i)).isoformat()})
    return pd.DataFrame(filas)


class TestExplicabilidadResenas(unittest.TestCase):
    def test_coeficientes_globales_y_contribuciones_locales_se_asocian_al_modelo(self):
        resenas = resenas_sinteticas()
        _, predicciones, _, modelo = evaluar_clasificador(resenas)
        globales = importancia_global(modelo, top_n=5)
        textos = [limpiar_comentario(resenas.iloc[int(indice)]['review_comment_message'])
                  for indice in predicciones['source_row']]
        locales = explicaciones_locales(modelo, predicciones, textos, muestra=10, top_n=2)
        self.assertEqual(set(globales['clase']), set(modelo.classes_))
        self.assertTrue({'termino', 'coeficiente_logit', 'magnitud_coeficiente'} <= set(globales.columns))
        self.assertEqual(locales['review_id'].nunique(), 10)
        self.assertTrue(set(locales['direccion']) <= {'a_favor', 'en_contra'})
        self.assertTrue((locales['contribucion_logit'] != 0).all())

    def test_rechaza_un_modelo_sin_pipeline_tfidf(self):
        with self.assertRaises(ValueError):
            importancia_global(object(), top_n=5)


if __name__ == '__main__':
    unittest.main()
