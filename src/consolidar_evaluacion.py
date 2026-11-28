"""
Consolidación de Métricas y Evaluación Comparativa Multimodelo (DataSmart)
========================================================================
Consolida en `resultados/evaluacion_comparativa.csv` las métricas de los
artefactos disponibles: asociación (Apriori/FP-Growth/ECLAT), K-Means, DBSCAN
muestral, grafos, series, regresión, clasificación, NLP descriptivo,
explicabilidad y monitoreo retrospectivo.

Estructura del contrato:
    tecnica,modelo,metrica,valor,unidad,poblacion,particion,n_evaluacion,
    parametros_json,tiempo_s,ejecutado_en_utc,fuente,estado,ubicacion_resultados,version

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
                "poblacion": str(r.get("poblacion", "no_especificada")),
                "particion": "completa",
                "n_evaluacion": n_reglas,
                "parametros_json": json.dumps({
                    "min_pedidos": r.get("min_pedidos"),
                    "min_soporte": r.get("min_soporte"),
                    "min_confianza": r.get("min_confianza"),
                    "max_len": r.get("max_len"),
                    "poblacion": r.get("poblacion"),
                }),
                "tiempo_s": round(t_s, 4),
            })
            filas.append({
                "tecnica": "Reglas de Asociación",
                "modelo": alg,
                "metrica": "conjuntos_frecuentes",
                "valor": float(n_conj),
                "unidad": "itemsets",
                "poblacion": str(r.get("poblacion", "no_especificada")),
                "particion": "completa",
                "n_evaluacion": n_conj,
                "parametros_json": json.dumps({
                    "min_pedidos": r.get("min_pedidos"),
                    "min_soporte": r.get("min_soporte"),
                    "poblacion": r.get("poblacion"),
                }),
                "tiempo_s": round(t_s, 4),
            })

    # 2. Clustering K-Means (k=2 a 6).
    eval_clust_path = RESULTADOS_DIR / "evaluacion_clustering.csv"
    if eval_clust_path.is_file():
        df_clust = pd.read_csv(eval_clust_path, encoding="utf-8-sig")
        for _, r in df_clust.iterrows():
            k_val = int(r["k"])
            parametros = json.dumps({
                "k": k_val, "random_state": int(r.get("random_state", 42)),
                "n_init": int(r.get("n_init", 10)), "escala": r.get("escala"),
                "muestra_silhouette": int(r.get("muestra_silhouette", 0)),
            })
            for metrica, campo, unidad, decimales in [
                ("silhouette_score", "silhouette", "coeficiente [-1, 1]", 6),
                ("davies_bouldin_index", "davies_bouldin", "índice [0, inf)", 6),
                ("inercia_wcss", "inercia", "suma_cuadrados_wcss", 2),
            ]:
                filas.append({
                    "tecnica": "Clustering RFM", "modelo": f"kmeans_k{k_val}",
                    "metrica": metrica, "valor": round(float(r[campo]), decimales), "unidad": unidad,
                    "poblacion": "compradores_unicos_entregados", "particion": "ajuste_completo_y_muestra_silhouette",
                    "n_evaluacion": int(r.get("clientes_ajuste", 0)),
                    "parametros_json": parametros, "tiempo_s": None,
                })

    # 2b. DBSCAN, evaluado únicamente sobre la muestra fija declarada.
    dbscan_path = RESULTADOS_DIR / "evaluacion_clustering_dbscan.csv"
    if dbscan_path.is_file():
        df_dbscan = pd.read_csv(dbscan_path, encoding="utf-8-sig")
        if not df_dbscan.empty:
            r_db = df_dbscan.iloc[0]
            parametros = json.dumps({
                "eps": float(r_db["eps"]), "min_samples": int(r_db["min_samples"]),
                "metric": r_db["metric"], "semilla_muestra": int(r_db["semilla_muestra"]),
                "metodo_muestra": r_db["metodo_muestra"],
            }, ensure_ascii=False)
            for metrica, unidad in [
                ("n_clusters_sin_ruido", "clusters"),
                ("porcentaje_ruido", "% de muestra"),
                ("silhouette_sin_ruido", "coeficiente [-1, 1]"),
                ("davies_bouldin_sin_ruido", "índice [0, inf)"),
            ]:
                valor = pd.to_numeric(r_db.get(metrica), errors="coerce")
                if pd.notna(valor):
                    filas.append({
                        "tecnica": "Clustering RFM DBSCAN", "modelo": "dbscan_muestra_fija",
                        "metrica": metrica, "valor": float(valor), "unidad": unidad,
                        "poblacion": "compradores_unicos_muestra_dbscan", "particion": "muestra_fija",
                        "n_evaluacion": int(r_db["n_muestra"]), "parametros_json": parametros, "tiempo_s": None,
                    })

    # 3. Grafos (Red Bipartita Vendedor-Producto)
    grafos_meta_path = RESULTADOS_DIR / "grafos_metadata.json"
    if grafos_meta_path.is_file():
        meta_g = json.loads(grafos_meta_path.read_text(encoding="utf-8-sig"))
        total_nodos = int(meta_g.get("nodos", meta_g.get("total_nodos", 0)))
        total_aristas = int(meta_g.get("aristas", meta_g.get("total_aristas", 0)))
        peso_total = int(meta_g.get("peso_total", meta_g.get("total_items_acumulados", 0)))
        metricas_path = RESULTADOS_DIR / "grafo_metricas.csv"
        max_pagerank = None
        if metricas_path.is_file():
            metricas_grafo = pd.read_csv(metricas_path, usecols=["pagerank"], encoding="utf-8-sig")
            if not metricas_grafo.empty:
                max_pagerank = float(metricas_grafo["pagerank"].max())
        if max_pagerank is None:
            top = meta_g.get("vendedor_top_pagerank")
            if isinstance(top, dict):
                max_pagerank = top.get("pagerank")
            else:
                top_legacy = meta_g.get("top_vendedores_pagerank", [])
                max_pagerank = top_legacy[0].get("pagerank") if top_legacy else None
        filas.append({
            "tecnica": "Grafos y Redes Complejas",
            "modelo": "red_vendedor_producto_bipartita",
            "metrica": "total_nodos",
            "valor": float(total_nodos),
            "unidad": "nodos",
            "poblacion": "vendedores_y_productos_entregados",
            "particion": "grafo_completo",
            "n_evaluacion": total_nodos,
            "parametros_json": json.dumps({"tipo": "bipartito_no_dirigido", "peso": "cantidad_items"}),
            "tiempo_s": None,
        })
        filas.append({
            "tecnica": "Grafos y Redes Complejas",
            "modelo": "red_vendedor_producto_bipartita",
            "metrica": "total_aristas",
            "valor": float(total_aristas),
            "unidad": "aristas",
            "poblacion": "vendedores_y_productos_entregados",
            "particion": "grafo_completo",
            "n_evaluacion": total_aristas,
            "parametros_json": json.dumps({"peso_total_items": peso_total}),
            "tiempo_s": None,
        })
        filas.append({
            "tecnica": "Grafos y Redes Complejas",
            "modelo": "pagerank_ponderado",
            "metrica": "max_pagerank",
            "valor": None if max_pagerank is None else round(float(max_pagerank), 6),
            "unidad": "probabilidad_pagerank",
            "poblacion": "vendedores_y_productos_entregados",
            "particion": "grafo_completo",
            "n_evaluacion": total_nodos,
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

    # 6. Clasificación (review_score como proxy de polaridad textual).
    clas_path = RESULTADOS_DIR / "evaluacion_clasificacion.csv"
    if clas_path.is_file():
        df_clas = pd.read_csv(clas_path, encoding="utf-8-sig")
        for _, r in df_clas.iterrows():
            for metrica in ("accuracy", "precision_macro", "recall_macro", "f1_macro", "roc_auc_ovr_macro", "pr_auc_macro_ovr"):
                valor = pd.to_numeric(r.get(metrica), errors="coerce")
                if pd.notna(valor):
                    filas.append({
                        "tecnica": "Clasificación de reseñas", "modelo": str(r["modelo"]),
                        "metrica": metrica, "valor": float(valor), "unidad": "coeficiente [0, 1]",
                        "poblacion": "resenas_con_texto_y_score_valido", "particion": "test_cronologico",
                        "n_evaluacion": int(r["n_test"]),
                        "parametros_json": json.dumps({"fecha_corte_test": r.get("fecha_corte_test")}),
                        "tiempo_s": None,
                    })

    # 7. NLP descriptivo: score proxy y polaridad léxica se conservan separados.
    nlp_sent_path = RESULTADOS_DIR / "nlp_sentimientos.csv"
    if nlp_sent_path.is_file():
        df_sent = pd.read_csv(nlp_sent_path, encoding="utf-8-sig")
        for _, r in df_sent.iterrows():
            filas.append({
                "tecnica": "NLP de reseñas", "modelo": str(r["origen_etiqueta"]),
                "metrica": f"porcentaje_{r['clase']}", "valor": float(r["porcentaje"]),
                "unidad": "% de reseñas con texto", "poblacion": "resenas_con_texto_util",
                "particion": "descriptiva", "n_evaluacion": int(r["cantidad"]),
                "parametros_json": json.dumps({"clase": r["clase"]}), "tiempo_s": None,
            })

    # 8. Explicabilidad: contar artefactos realmente generados por el modelo entrenado.
    global_path = RESULTADOS_DIR / "importancia_variables.csv"
    local_path = RESULTADOS_DIR / "explicaciones_locales.csv"
    if global_path.is_file():
        importancia = pd.read_csv(global_path, encoding="utf-8-sig")
        filas.append({
            "tecnica": "Explicabilidad", "modelo": "logistic_regression_tfidf",
            "metrica": "coeficientes_globales_exportados", "valor": float(len(importancia)),
            "unidad": "coeficientes", "poblacion": "vocabulario_tfidf_por_clase",
            "particion": "modelo_entrenado", "n_evaluacion": len(importancia),
            "parametros_json": json.dumps({"metodo": "coeficiente_logit"}), "tiempo_s": None,
        })
    if local_path.is_file():
        explicaciones = pd.read_csv(local_path, encoding="utf-8-sig")
        filas.append({
            "tecnica": "Explicabilidad", "modelo": "logistic_regression_tfidf",
            "metrica": "contribuciones_locales_exportadas", "valor": float(len(explicaciones)),
            "unidad": "contribuciones", "poblacion": "muestra_predicciones_test",
            "particion": "test_cronologico",
            "n_evaluacion": int(explicaciones["review_id"].nunique()) if len(explicaciones) else 0,
            "parametros_json": json.dumps({"metodo": "tfidf_por_coeficiente_en_escala_logit"}), "tiempo_s": None,
        })

    # 9. Monitoreo retrospectivo: métricas y PSI train/test, nunca tiempo real.
    monitor_path = RESULTADOS_DIR / "monitoring_metrics.csv"
    if monitor_path.is_file():
        df_monitor = pd.read_csv(monitor_path, encoding="utf-8-sig")
        for _, r in df_monitor.iterrows():
            filas.append({
                "tecnica": "Monitoreo retrospectivo", "modelo": str(r["model_version"]),
                "metrica": str(r["metrica"]), "valor": float(r["valor"]),
                "unidad": "coeficiente [0, 1]", "poblacion": "resenas_test_historico",
                "particion": str(r["particion"]), "n_evaluacion": int(r["n_evaluacion"]),
                "parametros_json": json.dumps({"run_id": r["run_id"], "origen": r["origen"]}), "tiempo_s": None,
            })
    drift_path = RESULTADOS_DIR / "data_drift_report.csv"
    if drift_path.is_file():
        df_drift = pd.read_csv(drift_path, encoding="utf-8-sig")
        for _, r in df_drift.iterrows():
            filas.append({
                "tecnica": "Monitoreo retrospectivo", "modelo": str(r["model_version"]),
                "metrica": f"psi_{r['variable']}", "valor": float(r["psi"]), "unidad": "PSI",
                "poblacion": "train_vs_test_historicos", "particion": "comparacion_retroactiva",
                "n_evaluacion": int(r["n_actual"]),
                "parametros_json": json.dumps({"estado": r["estado"], "run_id": r["run_id"]}), "tiempo_s": None,
            })

    df_consolidado = pd.DataFrame(filas)
    contratos = {
        "Reglas de Asociación": ("asociacion_metadata.json", "comparacion_asociacion.csv"),
        "Clustering RFM": ("clustering_metadata.json", "evaluacion_clustering.csv"),
        "Clustering RFM DBSCAN": ("clustering_dbscan_metadata.json", "evaluacion_clustering_dbscan.csv"),
        "Grafos y Redes Complejas": ("grafos_metadata.json", "grafo_metricas.csv"),
        "Series Temporales": ("series_temporales_metadata.json", "evaluacion_series.csv"),
        "Regresión Predictiva": ("regresion_metadata.json", "evaluacion_regresion.csv"),
        "Clasificación de reseñas": ("clasificacion_metadata.json", "evaluacion_clasificacion.csv"),
        "NLP de reseñas": ("nlp_metadata.json", "nlp_sentimientos.csv"),
        "Explicabilidad": ("explicabilidad_metadata.json", "importancia_variables.csv"),
        "Monitoreo retrospectivo": ("model_registry.json", "monitoring_metrics.csv"),
    }
    filas_enriquecidas = []
    for tecnica, grupo in df_consolidado.groupby("tecnica", sort=False):
        meta_name, artefacto = contratos.get(tecnica, (None, None))
        meta_path = RESULTADOS_DIR / meta_name if meta_name else None
        meta = json.loads(meta_path.read_text(encoding="utf-8-sig")) if meta_path and meta_path.is_file() else {}
        fuente = (meta.get("items_csv") or meta.get("fuente") or meta.get("archivo_origen")
                  or meta.get("archivo_csv") or "")
        if not fuente and tecnica == "Monitoreo retrospectivo":
            fuente = "data/raw/archive.zip (comparación train/test histórica)"
        elif not fuente and tecnica == "Series Temporales":
            fuente = "data/processed/pedidos_procesados.csv"
        elif not fuente and tecnica == "Regresión Predictiva":
            fuente = "data/processed/pedidos_procesados.csv + items_procesados.csv"
        ejecutado = meta.get("ejecutado_en_utc") or meta.get("ultima_ejecucion_utc")
        version = (meta.get("sha256_modelo") or meta.get("sha256_entrada") or meta.get("sha256_origen")
                   or meta.get("version_activa") or "")
        grupo = grupo.copy()
        grupo["ejecutado_en_utc"] = ejecutado
        grupo["fuente"] = fuente
        grupo["estado"] = "ok" if artefacto and (RESULTADOS_DIR / artefacto).is_file() else "sin_resultados"
        grupo["ubicacion_resultados"] = f"resultados/{artefacto}" if artefacto else ""
        grupo["version"] = version
        filas_enriquecidas.append(grupo)
    df_consolidado = pd.concat(filas_enriquecidas, ignore_index=True) if filas_enriquecidas else df_consolidado
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
