"""
Consolidación de Métricas y Evaluación Comparativa Multimodelo (DataSmart)
========================================================================
Consolida en `resultados/evaluacion_comparativa.csv` las métricas de evaluación
de las cinco familias de minería de datos del proyecto DataSmart:
1. Reglas de Asociación (Apriori vs FP-Growth) — Paulo
2. Segmentación RFM / Clustering (K-Means k=2..6) — Anderson
3. Redes Complejas / Grafos (Bipartita Vendedor-Producto) — Anderson
4. Series Temporales (Baseline vs Suavizamiento Exponencial) — Brandon
5. Regresión Predictiva de Entrega (Baseline vs Ridge vs Random Forest) — Brandon

Estructura del contrato:
    tecnica,modelo,metrica,valor,unidad,poblacion,particion,n_evaluacion,parametros_json,tiempo_s

Ejecución:
    python src/consolidar_evaluacion.py
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
import pandas as pd

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("consolidar_evaluacion")

ROOT_DIR = Path(__file__).resolve().parent.parent
RESULTADOS_DIR = ROOT_DIR / "resultados"


def consolidar_evaluacion() -> pd.DataFrame:
    filas = []

    # 1. Reglas de Asociación (Apriori vs FP-Growth)
    comp_asoc_path = RESULTADOS_DIR / "comparacion_asociacion.csv"
    if comp_asoc_path.is_file():
        df_asoc = pd.read_csv(comp_asoc_path, encoding="utf-8-sig")
        for _, r in df_asoc.iterrows():
            alg = str(r["algoritmo"]).lower()
            t_s = float(r["tiempo_mediana_s"])
            n_reglas = int(r["reglas"])
            n_conj = int(r["conjuntos_frecuentes"])

            filas.append({
                "tecnica": "Reglas de Asociación",
                "modelo": alg,
                "metrica": "reglas_generadas",
                "valor": float(n_reglas),
                "unidad": "reglas",
                "poblacion": "cestas_multicategoria",
                "particion": "completa",
                "n_evaluacion": n_reglas,
                "parametros_json": json.dumps({"min_support": 0.0001, "min_confidence": 0.05, "min_lift": 1.0}),
                "tiempo_s": round(t_s, 4),
            })
            filas.append({
                "tecnica": "Reglas de Asociación",
                "modelo": alg,
                "metrica": "conjuntos_frecuentes",
                "valor": float(n_conj),
                "unidad": "itemsets",
                "poblacion": "cestas_multicategoria",
                "particion": "completa",
                "n_evaluacion": n_conj,
                "parametros_json": json.dumps({"min_support": 0.0001}),
                "tiempo_s": round(t_s, 4),
            })

    # 2. Clustering K-Means (k=2 a 6)
    eval_clust_path = RESULTADOS_DIR / "evaluacion_clustering.csv"
    if eval_clust_path.is_file():
        df_clust = pd.read_csv(eval_clust_path, encoding="utf-8-sig")
        for _, r in df_clust.iterrows():
            k_val = int(r["k"])
            sil = float(r["silhouette"])
            db = float(r["davies_bouldin"])
            inercia = float(r["inercia"])

            filas.append({
                "tecnica": "Clustering RFM",
                "modelo": f"kmeans_k{k_val}",
                "metrica": "silhouette_score",
                "valor": round(sil, 6),
                "unidad": "coeficiente [-1, 1]",
                "poblacion": "compradores_unicos_entregados",
                "particion": "muestra_evaluacion",
                "n_evaluacion": 93358,
                "parametros_json": json.dumps({"k": k_val, "random_state": 42}),
                "tiempo_s": None,
            })
            filas.append({
                "tecnica": "Clustering RFM",
                "modelo": f"kmeans_k{k_val}",
                "metrica": "davies_bouldin_index",
                "valor": round(db, 6),
                "unidad": "indice [0, inf)",
                "poblacion": "compradores_unicos_entregados",
                "particion": "muestra_evaluacion",
                "n_evaluacion": 93358,
                "parametros_json": json.dumps({"k": k_val, "random_state": 42}),
                "tiempo_s": None,
            })
            filas.append({
                "tecnica": "Clustering RFM",
                "modelo": f"kmeans_k{k_val}",
                "metrica": "inercia_wcss",
                "valor": round(inercia, 2),
                "unidad": "suma_cuadrados_wcss",
                "poblacion": "compradores_unicos_entregados",
                "particion": "muestra_evaluacion",
                "n_evaluacion": 93358,
                "parametros_json": json.dumps({"k": k_val, "random_state": 42}),
                "tiempo_s": None,
            })

    # 3. Grafos (Red Bipartita Vendedor-Producto)
    grafos_meta_path = RESULTADOS_DIR / "grafos_metadata.json"
    if grafos_meta_path.is_file():
        meta_g = json.loads(grafos_meta_path.read_text(encoding="utf-8-sig"))
        filas.append({
            "tecnica": "Grafos y Redes Complejas",
            "modelo": "red_vendedor_producto_bipartita",
            "metrica": "total_nodos",
            "valor": float(meta_g.get("total_nodos", 35186)),
            "unidad": "nodos",
            "poblacion": "vendedores_y_productos_entregados",
            "particion": "grafo_completo",
            "n_evaluacion": int(meta_g.get("total_nodos", 35186)),
            "parametros_json": json.dumps({"tipo": "bipartito_no_dirigido", "peso": "cantidad_items"}),
            "tiempo_s": None,
        })
        filas.append({
            "tecnica": "Grafos y Redes Complejas",
            "modelo": "red_vendedor_producto_bipartita",
            "metrica": "total_aristas",
            "valor": float(meta_g.get("total_aristas", 33659)),
            "unidad": "aristas",
            "poblacion": "vendedores_y_productos_entregados",
            "particion": "grafo_completo",
            "n_evaluacion": int(meta_g.get("total_aristas", 33659)),
            "parametros_json": json.dumps({"peso_total_items": int(meta_g.get("total_items_acumulados", 110197))}),
            "tiempo_s": None,
        })
        filas.append({
            "tecnica": "Grafos y Redes Complejas",
            "modelo": "pagerank_ponderado",
            "metrica": "max_pagerank",
            "valor": round(float(meta_g.get("vendedor_top_pagerank", {}).get("pagerank", 0.005084)), 6),
            "unidad": "probabilidad_pagerank",
            "poblacion": "vendedores_y_productos_entregados",
            "particion": "grafo_completo",
            "n_evaluacion": int(meta_g.get("total_nodos", 35186)),
            "parametros_json": json.dumps({"alpha": 0.85, "weight": "peso"}),
            "tiempo_s": None,
        })

    # 4. Series Temporales (Ventas Semanales BRL)
    eval_series_path = RESULTADOS_DIR / "evaluacion_series.csv"
    if eval_series_path.is_file():
        df_series = pd.read_csv(eval_series_path, encoding="utf-8-sig")
        for _, r in df_series.iterrows():
            mod = str(r["modelo"])
            mae = float(r["mae_brl"])
            rmse = float(r["rmse_brl"])
            t_s = float(r["tiempo_ajuste_s"]) + float(r["tiempo_prediccion_s"])
            n_eval = int(r["n_test"])

            filas.append({
                "tecnica": "Series Temporales",
                "modelo": mod,
                "metrica": "mae_brl",
                "valor": round(mae, 2),
                "unidad": "BRL/semana",
                "poblacion": "ventas_semanales_entregadas",
                "particion": "test_cronologico",
                "n_evaluacion": n_eval,
                "parametros_json": r["parametros_json"],
                "tiempo_s": round(t_s, 4),
            })
            filas.append({
                "tecnica": "Series Temporales",
                "modelo": mod,
                "metrica": "rmse_brl",
                "valor": round(rmse, 2),
                "unidad": "BRL/semana",
                "poblacion": "ventas_semanales_entregadas",
                "particion": "test_cronologico",
                "n_evaluacion": n_eval,
                "parametros_json": r["parametros_json"],
                "tiempo_s": round(t_s, 4),
            })

    # 5. Regresión Predictiva de Días de Entrega
    eval_reg_path = RESULTADOS_DIR / "evaluacion_regresion.csv"
    if eval_reg_path.is_file():
        df_reg = pd.read_csv(eval_reg_path, encoding="utf-8-sig")
        for _, r in df_reg.iterrows():
            mod = str(r["modelo"])
            mae = float(r["mae_dias"])
            rmse = float(r["rmse_dias"])
            r2_val = float(r["r2"])
            t_s = float(r["tiempo_ajuste_s"]) + float(r["tiempo_prediccion_s"])
            n_eval = int(r["n_test"])

            filas.append({
                "tecnica": "Regresión Predictiva",
                "modelo": mod,
                "metrica": "mae_dias",
                "valor": round(mae, 4),
                "unidad": "días",
                "poblacion": "pedidos_entregados_evaluables",
                "particion": "test_cronologico",
                "n_evaluacion": n_eval,
                "parametros_json": r["parametros_json"],
                "tiempo_s": round(t_s, 4),
            })
            filas.append({
                "tecnica": "Regresión Predictiva",
                "modelo": mod,
                "metrica": "rmse_dias",
                "valor": round(rmse, 4),
                "unidad": "días",
                "poblacion": "pedidos_entregados_evaluables",
                "particion": "test_cronologico",
                "n_evaluacion": n_eval,
                "parametros_json": r["parametros_json"],
                "tiempo_s": round(t_s, 4),
            })
            filas.append({
                "tecnica": "Regresión Predictiva",
                "modelo": mod,
                "metrica": "r2_score",
                "valor": round(r2_val, 4),
                "unidad": "adimensional [-inf, 1]",
                "poblacion": "pedidos_entregados_evaluables",
                "particion": "test_cronologico",
                "n_evaluacion": n_eval,
                "parametros_json": r["parametros_json"],
                "tiempo_s": round(t_s, 4),
            })

    df_consolidado = pd.DataFrame(filas)
    return df_consolidado


def main() -> None:
    logger.info("Iniciando consolidación multimodelo...")
    df_consolidado = consolidar_evaluacion()
    salida_csv = RESULTADOS_DIR / "evaluacion_comparativa.csv"
    salida_json = RESULTADOS_DIR / "evaluacion_comparativa_resumen.json"

    df_consolidado.to_csv(salida_csv, index=False, encoding="utf-8-sig")

    resumen = {
        "total_registros_evaluacion": len(df_consolidado),
        "familias_tecnicas": df_consolidado["tecnica"].unique().tolist(),
        "modelos_evaluados": df_consolidado["modelo"].unique().tolist(),
        "metricas_consolidadas": df_consolidado["metrica"].unique().tolist(),
    }
    salida_json.write_text(json.dumps(resumen, indent=2, ensure_ascii=False), encoding="utf-8-sig")

    logger.info("Consolidación guardada en: %s (%d filas)", salida_csv, len(df_consolidado))
    logger.info("Familias incluidas: %s", ", ".join(resumen["familias_tecnicas"]))


if __name__ == "__main__":
    main()
