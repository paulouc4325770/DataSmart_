"""
Pruebas unitarias para la consolidación multimodelo de DataSmart.
"""

import unittest
from pathlib import Path
import json
import pandas as pd

from src.consolidar_evaluacion import consolidar_evaluacion

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = ROOT_DIR / "resultados"


class TestConsolidarEvaluacion(unittest.TestCase):
    def test_consolidacion_incluye_familias_con_artefactos_disponibles(self):
        """Consolida las familias base y las extensiones cuyos artefactos existen."""
        df = consolidar_evaluacion()
        familias = set(df["tecnica"].unique())
        esperadas = {
            "Reglas de Asociación",
            "Clustering RFM",
            "Grafos y Redes Complejas",
            "Series Temporales",
            "Regresión Predictiva",
        }
        opcionales = {
            "evaluacion_clustering_dbscan.csv": "Clustering RFM DBSCAN",
            "evaluacion_clasificacion.csv": "Clasificación de reseñas",
            "nlp_sentimientos.csv": "NLP de reseñas",
            "importancia_variables.csv": "Explicabilidad",
            "monitoring_metrics.csv": "Monitoreo retrospectivo",
        }
        esperadas.update(familia for archivo, familia in opcionales.items() if (RESULTADOS_DIR / archivo).is_file())
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
            "ejecutado_en_utc",
            "fuente",
            "estado",
            "ubicacion_resultados",
            "version",
        ]
        self.assertEqual(list(df.columns), columnas_esperadas)

    def test_grafos_concuerdan_con_metadatos_y_metricas_actuales(self):
        df = consolidar_evaluacion()
        meta = json.loads((RESULTADOS_DIR / "grafos_metadata.json").read_text(encoding="utf-8-sig"))
        metricas = pd.read_csv(RESULTADOS_DIR / "grafo_metricas.csv", encoding="utf-8-sig")
        grafo = df[df["tecnica"] == "Grafos y Redes Complejas"].set_index("metrica")
        self.assertEqual(grafo.loc["total_nodos", "valor"], meta["nodos"])
        self.assertEqual(grafo.loc["total_aristas", "valor"], meta["aristas"])
        self.assertAlmostEqual(grafo.loc["max_pagerank", "valor"], metricas["pagerank"].max(), places=6)

    def test_asociacion_conserva_poblacion_y_parametros_de_ejecucion(self):
        df = consolidar_evaluacion()
        fila = df[(df["tecnica"] == "Reglas de Asociación") & (df["metrica"] == "reglas_generadas")].iloc[0]
        comp = pd.read_csv(RESULTADOS_DIR / "comparacion_asociacion.csv", encoding="utf-8-sig").iloc[0]
        parametros = json.loads(fila["parametros_json"])
        self.assertEqual(fila["poblacion"], comp["poblacion"])
        self.assertEqual(parametros["min_pedidos"], comp["min_pedidos"])

    def test_familias_nuevas_conservan_metricas_reales_y_trazabilidad(self):
        df = consolidar_evaluacion()
        clasificacion = df[df["tecnica"] == "Clasificación de reseñas"]
        nlp = df[df["tecnica"] == "NLP de reseñas"]
        monitoreo = df[df["tecnica"] == "Monitoreo retrospectivo"]
        self.assertIn("f1_macro", set(clasificacion["metrica"]))
        self.assertTrue((clasificacion["estado"] == "ok").all())
        self.assertIn("porcentaje_positivo_lexico", set(nlp["metrica"]))
        self.assertIn("psi_longitud_caracteres", set(monitoreo["metrica"]))
        self.assertTrue((monitoreo["particion"] == "test_cronologico").any())


if __name__ == "__main__":
    unittest.main()
