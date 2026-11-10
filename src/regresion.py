"""
Módulo de Modelado Predictivo: Regresión de Tiempos de Entrega (DataSmart)
==========================================================================
Implementa la estimación de días de entrega ('dias_entrega') al momento
de la compra para pedidos del marketplace Olist bajo metodología CRISP-DM.

Objetivo de Negocio (PN-07 & PN-08):
- Predecir con rigor los días reales que tardará el pedido en llegar al cliente,
  utilizando ÚNICAMENTE variables disponibles al momento de la compra
  ('order_purchase_timestamp').
- Alertar proactivamente desviaciones logísticas respecto a la promesa comercial
  ('dias_prometidos') para mitigar insatisfacción y reseñas negativas.

Prevención Estricta de Fuga de Información (Data Leakage):
- Se excluyen como predictores:
  * Fecha de entrega real ('order_delivered_customer_date').
  * Variables de retraso observado ('dias_retraso_calendario', 'entrega_tardia').
  * Reseñas y calificaciones ('calificacion_media', 'cantidad_resenas').
  * Eventos operacionales posteriores a la compra (despacho, transporte, aprobación tardía).
  * Clusters RFM o PageRank calculados con toda la historia posterior.
- Partición cronológica estricta: corte en '2018-06-01'.
  * Train: pedidos comprados entre Sep 2016 y May 2018 (80,7% de la muestra).
  * Test: pedidos comprados entre Jun 2018 y Ago 2018 (19,3% de la muestra).
- Imputadores, escaladores y codificadores ajustados EXCLUSIVAMENTE con el conjunto de entrenamiento.

Modelos Comparados:
1. Baseline Ingenuo: Mediana de días de entrega calculada solo con entrenamiento.
2. Regresión Lineal Regularizada (Ridge): con regularización L2 (alpha=10.0).
3. Random Forest Regressor: ensamble no lineal con control de sobreajuste.

Ejecución:
    python src/regresion.py
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import RandomForestRegressor
from sklearn.impute import SimpleImputer
from sklearn.linear_model import Ridge
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("regresion")

ROOT_DIR = Path(__file__).resolve().parent.parent
PEDIDOS_PATH = ROOT_DIR / "data" / "processed" / "pedidos_procesados.csv"
ITEMS_PATH = ROOT_DIR / "data" / "processed" / "items_procesados.csv"
RESULTADOS_DIR = ROOT_DIR / "resultados"
GRAFICOS_DIR = RESULTADOS_DIR / "graficos"

FECHA_CORTE_TEST = "2018-06-01"


def preparar_dataset_regresion(
    ruta_pedidos: Path, ruta_items: Path
) -> pd.DataFrame:
    """Carga y consolida atributos conocidos al momento de la compra."""
    if not ruta_pedidos.is_file():
        raise FileNotFoundError(f"Falta archivo de pedidos: {ruta_pedidos}")
    if not ruta_items.is_file():
        raise FileNotFoundError(f"Falta archivo de ítems: {ruta_items}")

    logger.info("Cargando pedidos e ítems procesados...")
    p = pd.read_csv(
        ruta_pedidos,
        usecols=[
            "order_id",
            "order_status",
            "order_purchase_timestamp",
            "dias_entrega",
            "dias_prometidos",
            "cantidad_items",
            "cantidad_productos",
            "cantidad_vendedores",
            "valor_articulos",
            "valor_flete",
            "customer_state",
        ],
        parse_dates=["order_purchase_timestamp"],
        encoding="utf-8-sig",
    )

    # Filtrar pedidos entregados con objetivo válido y positivo
    ent = p[
        (p["order_status"] == "delivered")
        & (p["dias_entrega"].notna())
        & (p["dias_entrega"] > 0)
    ].copy()
    logger.info("Pedidos entregados con target válido: %d filas", len(ent))

    # Cargar y agregar ítems por order_id antes del join
    items = pd.read_csv(
        ruta_items,
        usecols=[
            "order_id",
            "product_weight_g",
            "volumen_cm3",
            "distancia_km",
            "ruta_interestatal",
            "seller_state",
        ],
        encoding="utf-8-sig",
    )

    items_agg = items.groupby("order_id").agg(
        peso_total_g=("product_weight_g", "sum"),
        volumen_total_cm3=("volumen_cm3", "sum"),
        distancia_media_km=("distancia_km", "mean"),
        distancia_max_km=("distancia_km", "max"),
        ruta_interestatal=(
            "ruta_interestatal",
            lambda s: bool(s.any()) if pd.Series.any(s.dropna()) else False,
        ),
        seller_state_principal=(
            "seller_state",
            lambda s: s.mode().iloc[0] if not s.empty else "UNKNOWN",
        ),
    ).reset_index()

    # Join 1-to-1 sobre order_id
    df = ent.merge(items_agg, on="order_id", how="left", validate="one_to_one")

    # Variables temporales al comprar
    df["hora_compra"] = df["order_purchase_timestamp"].dt.hour
    df["dia_semana_compra"] = df["order_purchase_timestamp"].dt.day_of_week
    df["mes_compra"] = df["order_purchase_timestamp"].dt.month
    df["ruta_interestatal_int"] = df["ruta_interestatal"].astype(int)

    logger.info("Dataset de regresión consolidado: %d pedidos.", len(df))
    return df


def entrenar_y_evaluar_regresion(
    df: pd.DataFrame, fecha_corte: str = FECHA_CORTE_TEST
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Realiza split cronológico, entrena modelos y genera predicciones y métricas."""
    num_cols = [
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
    ]
    cat_cols = ["customer_state", "seller_state_principal"]
    all_features = num_cols + cat_cols

    # Split cronológico estricto
    train_df = df[df["order_purchase_timestamp"] < fecha_corte].copy()
    test_df = df[df["order_purchase_timestamp"] >= fecha_corte].copy()

    X_train = train_df[all_features]
    y_train = train_df["dias_entrega"].values
    X_test = test_df[all_features]
    y_test = test_df["dias_entrega"].values

    train_inicio = train_df["order_purchase_timestamp"].min().strftime("%Y-%m-%d %H:%M:%S")
    train_fin = train_df["order_purchase_timestamp"].max().strftime("%Y-%m-%d %H:%M:%S")
    test_inicio = test_df["order_purchase_timestamp"].min().strftime("%Y-%m-%d %H:%M:%S")
    test_fin = test_df["order_purchase_timestamp"].max().strftime("%Y-%m-%d %H:%M:%S")

    logger.info(
        "Train: %d pedidos (%s -> %s)", len(train_df), train_inicio, train_fin
    )
    logger.info("Test:  %d pedidos (%s -> %s)", len(test_df), test_inicio, test_fin)

    evaluacion_rows = []
    predicciones_dict: dict[str, np.ndarray] = {}

    # 1. Baseline: Mediana histórica calculada solo en entrenamiento
    t0_base = time.time()
    mediana_train = float(np.median(y_train))
    t_fit_base = time.time() - t0_base

    t0_pred_base = time.time()
    pred_base = np.full_like(y_test, mediana_train)
    t_pred_base = time.time() - t0_pred_base

    mae_base = float(mean_absolute_error(y_test, pred_base))
    rmse_base = float(np.sqrt(mean_squared_error(y_test, pred_base)))
    r2_base = float(r2_score(y_test, pred_base))

    evaluacion_rows.append({
        "modelo": "baseline_mediana",
        "train_inicio": train_inicio,
        "train_fin": train_fin,
        "test_inicio": test_inicio,
        "test_fin": test_fin,
        "n_train": len(train_df),
        "n_test": len(test_df),
        "mae_dias": round(mae_base, 4),
        "rmse_dias": round(rmse_base, 4),
        "r2": round(r2_base, 4),
        "random_state": None,
        "parametros_json": json.dumps({"metodo": "mediana_train", "mediana_dias": round(mediana_train, 2)}),
        "tiempo_ajuste_s": round(t_fit_base, 4),
        "tiempo_prediccion_s": round(t_pred_base, 4),
    })
    predicciones_dict["baseline_mediana"] = pred_base

    # Preprocesador: Ajustado solo con Train
    preprocessor = ColumnTransformer(
        transformers=[
            (
                "num",
                Pipeline([
                    ("imputer", SimpleImputer(strategy="median")),
                    ("scaler", StandardScaler()),
                ]),
                num_cols,
            ),
            (
                "cat",
                OneHotEncoder(handle_unknown="ignore", sparse_output=False),
                cat_cols,
            ),
        ]
    )

    # 2. Ridge Regression
    logger.info("Entrenando Modelo Ridge (L2 regularizado)...")
    pipe_ridge = Pipeline([
        ("prep", preprocessor),
        ("model", Ridge(alpha=10.0, random_state=42)),
    ])
    t0_ridge = time.time()
    pipe_ridge.fit(X_train, y_train)
    t_fit_ridge = time.time() - t0_ridge

    t0_p_ridge = time.time()
    pred_ridge = pipe_ridge.predict(X_test)
    t_pred_ridge = time.time() - t0_p_ridge

    mae_ridge = float(mean_absolute_error(y_test, pred_ridge))
    rmse_ridge = float(np.sqrt(mean_squared_error(y_test, pred_ridge)))
    r2_ridge = float(r2_score(y_test, pred_ridge))

    evaluacion_rows.append({
        "modelo": "ridge",
        "train_inicio": train_inicio,
        "train_fin": train_fin,
        "test_inicio": test_inicio,
        "test_fin": test_fin,
        "n_train": len(train_df),
        "n_test": len(test_df),
        "mae_dias": round(mae_ridge, 4),
        "rmse_dias": round(rmse_ridge, 4),
        "r2": round(r2_ridge, 4),
        "random_state": 42,
        "parametros_json": json.dumps({"alpha": 10.0, "solver": "auto"}),
        "tiempo_ajuste_s": round(t_fit_ridge, 4),
        "tiempo_prediccion_s": round(t_pred_ridge, 4),
    })
    predicciones_dict["ridge"] = pred_ridge

    # 3. Random Forest Regressor
    logger.info("Entrenando Random Forest Regressor...")
    pipe_rf = Pipeline([
        ("prep", preprocessor),
        (
            "model",
            RandomForestRegressor(
                n_estimators=80,
                max_depth=14,
                min_samples_leaf=15,
                n_jobs=-1,
                random_state=42,
            ),
        ),
    ])
    t0_rf = time.time()
    pipe_rf.fit(X_train, y_train)
    t_fit_rf = time.time() - t0_rf

    t0_p_rf = time.time()
    pred_rf = pipe_rf.predict(X_test)
    t_pred_rf = time.time() - t0_p_rf

    mae_rf = float(mean_absolute_error(y_test, pred_rf))
    rmse_rf = float(np.sqrt(mean_squared_error(y_test, pred_rf)))
    r2_rf = float(r2_score(y_test, pred_rf))

    evaluacion_rows.append({
        "modelo": "random_forest",
        "train_inicio": train_inicio,
        "train_fin": train_fin,
        "test_inicio": test_inicio,
        "test_fin": test_fin,
        "n_train": len(train_df),
        "n_test": len(test_df),
        "mae_dias": round(mae_rf, 4),
        "rmse_dias": round(rmse_rf, 4),
        "r2": round(r2_rf, 4),
        "random_state": 42,
        "parametros_json": json.dumps({"n_estimators": 80, "max_depth": 14, "min_samples_leaf": 15}),
        "tiempo_ajuste_s": round(t_fit_rf, 4),
        "tiempo_prediccion_s": round(t_pred_rf, 4),
    })
    predicciones_dict["random_forest"] = pred_rf

    # Construir tabla de predicciones en test
    pred_rows = []
    test_orders = test_df["order_id"].values
    test_dates = test_df["order_purchase_timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S").values
    for mod_name, preds in predicciones_dict.items():
        for oid, ts, real, pred in zip(test_orders, test_dates, y_test, preds):
            pred_rows.append({
                "order_id": oid,
                "order_purchase_timestamp": ts,
                "modelo": mod_name,
                "dias_entrega_real": round(float(real), 2),
                "dias_entrega_predicha": round(float(pred), 2),
                "particion": "test",
            })

    df_predicciones = pd.DataFrame(pred_rows)
    df_evaluacion = pd.DataFrame(evaluacion_rows)

    metadata = {
        "tecnica": "Regresión Predictiva",
        "variable_objetivo": "dias_entrega",
        "unidad": "dias",
        "momento_prediccion": "order_purchase_timestamp (en el checkout)",
        "poblacion_total": len(df),
        "n_train": len(train_df),
        "n_test": len(test_df),
        "fecha_corte": fecha_corte,
        "train_inicio": train_inicio,
        "train_fin": train_fin,
        "test_inicio": test_inicio,
        "test_fin": test_fin,
        "mejor_modelo": df_evaluacion.sort_values("mae_dias").iloc[0]["modelo"],
        "mejor_mae_dias": float(df_evaluacion.sort_values("mae_dias").iloc[0]["mae_dias"]),
        "reduccion_mae_vs_baseline_pct": round(
            float((mae_base - mae_rf) / mae_base * 100), 2
        ),
    }

    return df_predicciones, df_evaluacion, metadata


def generar_graficos_regresion(
    df_predicciones: pd.DataFrame, graficos_dir: Path
) -> None:
    """Genera gráficos de real vs predicho y residuos para los modelos evaluados."""
    graficos_dir.mkdir(parents=True, exist_ok=True)
    rf_preds = df_predicciones[df_predicciones["modelo"] == "random_forest"]

    # 1. Gráfico Real vs Predicho (Random Forest)
    plt.figure(figsize=(9, 6), dpi=150)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # Muestra representativa de 2,000 pedidos para legibilidad visual
    sub = rf_preds.sample(n=min(2000, len(rf_preds)), random_state=42)

    plt.scatter(
        sub["dias_entrega_real"],
        sub["dias_entrega_predicha"],
        alpha=0.35,
        color="#3b82f6",
        edgecolors="none",
        s=25,
        label="Predicción Random Forest (Muestra Test)",
    )
    lim_max = 60
    plt.plot([0, lim_max], [0, lim_max], color="#ef4444", linestyle="--", linewidth=1.8, label="Línea Ideal (y = x)")

    plt.xlim(0, lim_max)
    plt.ylim(0, 40)
    plt.title("Regresión Logística: Días Reales vs Predichos (Random Forest)", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("Días de Entrega Reales (días)", fontsize=10, labelpad=8)
    plt.ylabel("Días de Entrega Estimados (días)", fontsize=10, labelpad=8)
    plt.legend(frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()
    ruta_real_vs_pred = graficos_dir / "regresion_real_vs_predicho.png"
    plt.savefig(ruta_real_vs_pred, dpi=150)
    plt.close()
    logger.info("Gráfico Real vs Predicho guardado en: %s", ruta_real_vs_pred)

    # 2. Gráfico de Distribución de Residuos
    plt.figure(figsize=(9, 5), dpi=150)
    residuos = rf_preds["dias_entrega_real"] - rf_preds["dias_entrega_predicha"]
    residuos_filtrados = residuos[(residuos >= -20) & (residuos <= 25)]

    plt.hist(residuos_filtrados, bins=45, color="#0ea5e9", edgecolor="white", alpha=0.85)
    plt.axvline(0, color="#ef4444", linestyle="--", linewidth=1.5, label="Error Cero (Insesgado)")
    plt.axvline(residuos.median(), color="#10b981", linestyle="-.", linewidth=1.5, label=f"Mediana Residuo ({residuos.median():.2f} d)")

    plt.title("Distribución de Errores de Predicción (Residuos = Real - Predicho)", fontsize=12, fontweight="bold", pad=12)
    plt.xlabel("Error de Predicción en Días (Residuo)", fontsize=10, labelpad=8)
    plt.ylabel("Frecuencia de Pedidos", fontsize=10, labelpad=8)
    plt.legend(frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()
    ruta_residuos = graficos_dir / "regresion_residuos.png"
    plt.savefig(ruta_residuos, dpi=150)
    plt.close()
    logger.info("Gráfico de residuos guardado en: %s", ruta_residuos)


def main() -> None:
    logger.info("Iniciando ejecución de Regresión Predictiva (DataSmart)...")
    df = preparar_dataset_regresion(PEDIDOS_PATH, ITEMS_PATH)
    df_predicciones, df_evaluacion, metadata = entrenar_y_evaluar_regresion(df)

    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)

    ruta_predicciones = RESULTADOS_DIR / "predicciones_entrega.csv"
    ruta_evaluacion = RESULTADOS_DIR / "evaluacion_regresion.csv"
    ruta_metadata = RESULTADOS_DIR / "regresion_metadata.json"

    df_predicciones.to_csv(ruta_predicciones, index=False, encoding="utf-8-sig")
    df_evaluacion.to_csv(ruta_evaluacion, index=False, encoding="utf-8-sig")
    ruta_metadata.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8-sig")

    generar_graficos_regresion(df_predicciones, GRAFICOS_DIR)

    logger.info("=" * 60)
    logger.info("RESUMEN DE EVALUACIÓN DE REGRESIÓN (DÍAS DE ENTREGA):")
    for _, row in df_evaluacion.iterrows():
        logger.info(
            "Modelo: %-18s | MAE: %6.4f d | RMSE: %6.4f d | R2: %7.4f",
            row["modelo"],
            row["mae_dias"],
            row["rmse_dias"],
            row["r2"],
        )
    logger.info(
        "Mejor modelo: %s (MAE: %.4f días | Mejora vs Baseline: %.2f%%)",
        metadata["mejor_modelo"],
        metadata["mejor_mae_dias"],
        metadata["reduccion_mae_vs_baseline_pct"],
    )
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
