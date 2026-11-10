"""
Módulo de Modelado Predictivo: Series Temporales de Ventas (DataSmart)
====================================================================
Implementa el pronóstico de ventas semanales del marketplace Olist
siguiendo la metodología CRISP-DM (Fase de Modelado y Evaluación).

Objetivo de Negocio (PN-03 & PN-04):
- Proyectar el volumen transaccional en moneda local (BRL) para planificar
  capacidad operativa, logística y campañas comerciales.
- Establecer una línea base (Baseline ingenuo) y contrastarla con Suavizamiento
  Exponencial (Holt-Winters / Exponential Smoothing).

Buenas Prácticas Metodológicas:
1. Población: pedidos entregados ('delivered') con fecha de compra verificada.
2. Variable: 'valor_articulos' (excluye flete y recargos operativos).
3. Agregación temporal: frecuencia semanal ('W-SUN') sobre periodos completos.
   Se excluyen los meses aislados de 2016 y la última semana censurada de agosto 2018.
4. Partición cronológica estricta: entrenamiento sobre las primeras 72 semanas y
   evaluación fuera de muestra sobre las últimas 12 semanas (sin 'shuffle').
5. Métricas: MAE (BRL) y RMSE (BRL).

Ejecución:
    python src/series_temporales.py
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
from sklearn.metrics import mean_absolute_error, mean_squared_error
from statsmodels.tsa.holtwinters import SimpleExpSmoothing, Holt

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("series_temporales")

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT_DIR / "data" / "processed" / "pedidos_procesados.csv"
RESULTADOS_DIR = ROOT_DIR / "resultados"
GRAFICOS_DIR = RESULTADOS_DIR / "graficos"


def cargar_serie_ventas(ruta_pedidos: Path) -> pd.Series:
    """Carga pedidos procesados y construye la serie semanal de ventas BRL."""
    if not ruta_pedidos.is_file():
        raise FileNotFoundError(f"No se encontró el dataset procesado: {ruta_pedidos}")

    df = pd.read_csv(
        ruta_pedidos,
        usecols=["order_id", "order_status", "order_purchase_timestamp", "valor_articulos"],
        parse_dates=["order_purchase_timestamp"],
        encoding="utf-8-sig",
    )

    # 1. Filtro estricto: pedidos entregados con valor no nulo
    ent = df[(df["order_status"] == "delivered") & (df["valor_articulos"].notna())].copy()
    logger.info("Total de pedidos entregados con valor conocido: %d", len(ent))

    # 2. Delimitación de ventana regular completa:
    # 2016 tuvo actividad fragmentaria y la última semana de agosto 2018 sufre censura por derecha.
    # Ventana completa: del lunes 2017-01-09 al domingo 2018-08-19.
    fecha_inicio = "2017-01-09"
    fecha_fin = "2018-08-19 23:59:59"

    ventana = ent[
        (ent["order_purchase_timestamp"] >= fecha_inicio)
        & (ent["order_purchase_timestamp"] <= fecha_fin)
    ].copy()

    # 3. Resample semanal anclado en domingo ('W-SUN')
    serie = (
        ventana.set_index("order_purchase_timestamp")
        .resample("W-SUN")["valor_articulos"]
        .sum(min_count=1)
    )

    logger.info(
        "Serie semanal construida: %d semanas desde %s hasta %s (Total BRL: %.2f)",
        len(serie),
        serie.index.min().strftime("%Y-%m-%d"),
        serie.index.max().strftime("%Y-%m-%d"),
        serie.sum(),
    )
    return serie


def evaluar_modelos_series(serie: pd.Series, n_test: int = 12) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Entrena y evalúa los modelos de series temporales con partición cronológica."""
    if len(serie) <= n_test:
        raise ValueError(f"Longitud de serie ({len(serie)}) insuficiente para test ({n_test}).")

    train = serie.iloc[:-n_test]
    test = serie.iloc[-n_test:]

    train_inicio = train.index.min().strftime("%Y-%m-%d")
    train_fin = train.index.max().strftime("%Y-%m-%d")
    test_inicio = test.index.min().strftime("%Y-%m-%d")
    test_fin = test.index.max().strftime("%Y-%m-%d")

    logger.info("Train: %d semanas (%s a %s)", len(train), train_inicio, train_fin)
    logger.info("Test:  %d semanas (%s a %s)", len(test), test_inicio, test_fin)

    pronosticos_rows = []
    evaluacion_rows = []

    # -------------------------------------------------------------
    # 1. Baseline ingenuo: último valor observado (persistencia flat)
    # -------------------------------------------------------------
    t0_base = time.time()
    ultimo_valor_train = float(train.iloc[-1])
    t_fit_base = time.time() - t0_base

    t0_pred_base = time.time()
    pred_base = pd.Series(ultimo_valor_train, index=test.index)
    t_pred_base = time.time() - t0_pred_base

    mae_base = float(mean_absolute_error(test, pred_base))
    rmse_base = float(np.sqrt(mean_squared_error(test, pred_base)))

    evaluacion_rows.append({
        "modelo": "baseline_ultimo",
        "frecuencia": "W-SUN",
        "train_inicio": train_inicio,
        "train_fin": train_fin,
        "test_inicio": test_inicio,
        "test_fin": test_fin,
        "n_train": len(train),
        "n_test": len(test),
        "mae_brl": round(mae_base, 2),
        "rmse_brl": round(rmse_base, 2),
        "parametros_json": json.dumps({"metodo": "naive_last_value", "ultimo_valor": round(ultimo_valor_train, 2)}),
        "tiempo_ajuste_s": round(t_fit_base, 4),
        "tiempo_prediccion_s": round(t_pred_base, 4),
    })

    for fecha, real, pred in zip(test.index, test.values, pred_base.values):
        pronosticos_rows.append({
            "fecha": fecha.strftime("%Y-%m-%d"),
            "modelo": "baseline_ultimo",
            "venta_real": round(float(real), 2),
            "venta_predicha": round(float(pred), 2),
            "particion": "test",
            "frecuencia": "W-SUN",
        })

    # -------------------------------------------------------------
    # 2. Suavizamiento Exponencial Simple (SES)
    # -------------------------------------------------------------
    t0_ses = time.time()
    model_ses = SimpleExpSmoothing(train, initialization_method="estimated").fit()
    t_fit_ses = time.time() - t0_ses

    t0_pred_ses = time.time()
    pred_ses = model_ses.forecast(n_test)
    t_pred_ses = time.time() - t0_pred_ses

    mae_ses = float(mean_absolute_error(test, pred_ses))
    rmse_ses = float(np.sqrt(mean_squared_error(test, pred_ses)))

    evaluacion_rows.append({
        "modelo": "suavizamiento_exponencial_simple",
        "frecuencia": "W-SUN",
        "train_inicio": train_inicio,
        "train_fin": train_fin,
        "test_inicio": test_inicio,
        "test_fin": test_fin,
        "n_train": len(train),
        "n_test": len(test),
        "mae_brl": round(mae_ses, 2),
        "rmse_brl": round(rmse_ses, 2),
        "parametros_json": json.dumps({"alpha": round(float(model_ses.params.get("smoothing_level", 0.0)), 4)}),
        "tiempo_ajuste_s": round(t_fit_ses, 4),
        "tiempo_prediccion_s": round(t_pred_ses, 4),
    })

    for fecha, real, pred in zip(test.index, test.values, pred_ses.values):
        pronosticos_rows.append({
            "fecha": fecha.strftime("%Y-%m-%d"),
            "modelo": "suavizamiento_exponencial_simple",
            "venta_real": round(float(real), 2),
            "venta_predicha": round(float(pred), 2),
            "particion": "test",
            "frecuencia": "W-SUN",
        })

    # -------------------------------------------------------------
    # 3. Suavizamiento Exponencial Holt (Tendencia Lineal)
    # -------------------------------------------------------------
    t0_holt = time.time()
    model_holt = Holt(train, initialization_method="estimated", damped_trend=True).fit()
    t_fit_holt = time.time() - t0_holt

    t0_pred_holt = time.time()
    pred_holt = model_holt.forecast(n_test)
    t_pred_holt = time.time() - t0_pred_holt

    mae_holt = float(mean_absolute_error(test, pred_holt))
    rmse_holt = float(np.sqrt(mean_squared_error(test, pred_holt)))

    evaluacion_rows.append({
        "modelo": "suavizamiento_exponencial_holt",
        "frecuencia": "W-SUN",
        "train_inicio": train_inicio,
        "train_fin": train_fin,
        "test_inicio": test_inicio,
        "test_fin": test_fin,
        "n_train": len(train),
        "n_test": len(test),
        "mae_brl": round(mae_holt, 2),
        "rmse_brl": round(rmse_holt, 2),
        "parametros_json": json.dumps({
            "alpha": round(float(model_holt.params.get("smoothing_level", 0.0)), 4),
            "beta": round(float(model_holt.params.get("smoothing_trend", 0.0)), 4),
            "damping_trend": round(float(model_holt.params.get("damping_trend", 0.0)), 4),
        }),
        "tiempo_ajuste_s": round(t_fit_holt, 4),
        "tiempo_prediccion_s": round(t_pred_holt, 4),
    })

    for fecha, real, pred in zip(test.index, test.values, pred_holt.values):
        pronosticos_rows.append({
            "fecha": fecha.strftime("%Y-%m-%d"),
            "modelo": "suavizamiento_exponencial_holt",
            "venta_real": round(float(real), 2),
            "venta_predicha": round(float(pred), 2),
            "particion": "test",
            "frecuencia": "W-SUN",
        })

    df_pronosticos = pd.DataFrame(pronosticos_rows)
    df_evaluacion = pd.DataFrame(evaluacion_rows)

    metadata = {
        "tecnica": "Series Temporales",
        "frecuencia": "W-SUN",
        "total_semanas": len(serie),
        "train_semanas": len(train),
        "test_semanas": len(test),
        "train_inicio": train_inicio,
        "train_fin": train_fin,
        "test_inicio": test_inicio,
        "test_fin": test_fin,
        "mejor_modelo": df_evaluacion.sort_values("mae_brl").iloc[0]["modelo"],
        "mejor_mae_brl": float(df_evaluacion.sort_values("mae_brl").iloc[0]["mae_brl"]),
        "reduccion_mae_vs_baseline_pct": round(
            float((mae_base - min(mae_ses, mae_holt)) / mae_base * 100), 2
        ),
    }

    return df_pronosticos, df_evaluacion, metadata


def generar_grafico_series(serie: pd.Series, df_pronosticos: pd.DataFrame, ruta_salida: Path) -> None:
    """Genera gráfico comparativo de valores reales vs predichos con estilo académico."""
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)
    test_fechas = pd.to_datetime(df_pronosticos[df_pronosticos["modelo"] == "baseline_ultimo"]["fecha"])
    real_test = df_pronosticos[df_pronosticos["modelo"] == "baseline_ultimo"]["venta_real"].values

    plt.figure(figsize=(12, 6), dpi=150)
    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

    # Serie histórica completa
    plt.plot(
        serie.index,
        serie.values / 1e3,
        label="Ventas Reales Históricas (k BRL)",
        color="#1e293b",
        linewidth=1.8,
        alpha=0.85,
    )

    # Predicciones sobre periodo test
    pred_base = df_pronosticos[df_pronosticos["modelo"] == "baseline_ultimo"]["venta_predicha"].values / 1e3
    pred_ses = df_pronosticos[df_pronosticos["modelo"] == "suavizamiento_exponencial_simple"]["venta_predicha"].values / 1e3
    pred_holt = df_pronosticos[df_pronosticos["modelo"] == "suavizamiento_exponencial_holt"]["venta_predicha"].values / 1e3

    plt.plot(test_fechas, pred_base, label="Baseline (Último Valor)", color="#ef4444", linestyle="--", linewidth=2.0)
    plt.plot(test_fechas, pred_ses, label="Suavizamiento Exponencial Simple", color="#3b82f6", linestyle="-.", linewidth=2.2)
    plt.plot(test_fechas, pred_holt, label="Suavizamiento Holt (Tendencia Amortiguada)", color="#10b981", linewidth=2.4)

    # Sombra del periodo test
    plt.axvspan(test_fechas.min(), test_fechas.max(), color="#f1f5f9", alpha=0.6, label="Periodo de Test (Fuera de Muestra)")

    plt.title("Pronóstico de Ventas Semanales en Olist: Serie Real vs Modelos Predictivos", fontsize=13, fontweight="bold", pad=12)
    plt.xlabel("Fecha de Compra (Semana W-SUN)", fontsize=10, labelpad=8)
    plt.ylabel("Ventas Semanales (Miles de BRL)", fontsize=10, labelpad=8)
    plt.legend(loc="upper left", frameon=True, facecolor="white", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(ruta_salida, dpi=150)
    plt.close()
    logger.info("Gráfico de series temporales guardado en: %s", ruta_salida)


def main() -> None:
    logger.info("Iniciando ejecución de Series Temporales (DataSmart)...")
    serie = cargar_serie_ventas(DATA_PATH)
    df_pronosticos, df_evaluacion, metadata = evaluar_modelos_series(serie, n_test=12)

    RESULTADOS_DIR.mkdir(parents=True, exist_ok=True)
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)

    ruta_pronosticos = RESULTADOS_DIR / "pronosticos_ventas.csv"
    ruta_evaluacion = RESULTADOS_DIR / "evaluacion_series.csv"
    ruta_metadata = RESULTADOS_DIR / "series_temporales_metadata.json"
    ruta_grafico = GRAFICOS_DIR / "series_temporales_prediccion.png"

    df_pronosticos.to_csv(ruta_pronosticos, index=False, encoding="utf-8-sig")
    df_evaluacion.to_csv(ruta_evaluacion, index=False, encoding="utf-8-sig")
    ruta_metadata.write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8-sig")

    generar_grafico_series(serie, df_pronosticos, ruta_grafico)

    logger.info("=" * 60)
    logger.info("RESUMEN DE EVALUACIÓN DE SERIES TEMPORALES:")
    for _, row in df_evaluacion.iterrows():
        logger.info(
            "Modelo: %-32s | MAE: %10.2f BRL | RMSE: %10.2f BRL",
            row["modelo"],
            row["mae_brl"],
            row["rmse_brl"],
        )
    logger.info("Mejor modelo: %s (Reducción MAE vs Baseline: %.2f%%)", metadata["mejor_modelo"], metadata["reduccion_mae_vs_baseline_pct"])
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
