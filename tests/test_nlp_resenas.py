"""Pruebas para NLP de reseñas y la separación de sus dos tipos de sentimiento."""

import sys
from pathlib import Path
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from nlp_resenas import analizar_resenas, identificar_idioma_heuristico, sentimiento_lexico


class TestNLPResenas(unittest.TestCase):
    def setUp(self):
        filas = []
        for i in range(60):
            grupo = i % 3
            puntuacion = [1, 3, 5][grupo]
            texto = [
                'produto ruim com defeito atraso',
                'produto normal chegou no prazo',
                'produto otimo excelente recomendo',
            ][grupo]
            filas.append({'review_score': puntuacion, 'review_comment_message': f'{texto} item{i % 4}'})
        self.df = pd.DataFrame(filas)

    def test_tfidf_sentimiento_y_puntuacion_se_exportan_como_origenes_distintos(self):
        terminos, pares, sentimientos, metadata = analizar_resenas(self.df, top_n=5)
        self.assertFalse(terminos.empty)
        self.assertIn('termino', terminos.columns)
        self.assertTrue(set(sentimientos['origen_etiqueta']) == {
            'derivado_de_review_score', 'calculado_desde_texto_lexico', 'heuristica_de_vocabulario',
        })
        self.assertTrue({'positivo_lexico', 'negativo_lexico', 'neutral_lexico'} <= set(sentimientos['clase']))
        self.assertEqual(metadata['resenas_con_texto_util'], 60)
        self.assertIn('no modela negación', ' '.join(metadata['limitaciones']))

    def test_lexico_e_idioma_se_basam_en_texto_y_se_declaran_heuristicos(self):
        clase, positivos, negativos, score = sentimiento_lexico('produto otimo excelente')
        self.assertEqual(clase, 'positivo_lexico')
        self.assertEqual((positivos, negativos, score), (2, 0, 2))
        self.assertEqual(identificar_idioma_heuristico('produto com entrega muito boa'), 'portugues_probable')
        self.assertEqual(identificar_idioma_heuristico('great product and fast'), 'idioma_incierto')

    def test_rechaza_entrada_sin_columnas_o_comentarios(self):
        with self.assertRaises(ValueError):
            analizar_resenas(pd.DataFrame({'review_score': [5]}))
        with self.assertRaises(ValueError):
            analizar_resenas(pd.DataFrame({'review_score': [5], 'review_comment_message': ['  ']}))


if __name__ == '__main__':
    unittest.main()
