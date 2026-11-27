"""Monitoreo académico retrospectivo: métricas, registro y PSI de train/test.

No es un servicio en tiempo real. Compara las particiones cronológicas del
dataset histórico y registra ejecuciones locales para auditoría y enseñanza.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path

import numpy as np
import pandas as pd

from clasificacion_resenas import ROOT, cargar_resenas_zip, preparar_resenas, sha256


EPSILON = 1e-6


def calcular_psi(distribucion_referencia, distribucion_actual, epsilon=EPSILON) -> float:
    """PSI para dos vectores de proporciones con bins alineados."""
    referencia = np.asarray(distribucion_referencia, dtype=float)
    actual = np.asarray(distribucion_actual, dtype=float)
    if referencia.ndim != 1 or actual.ndim != 1 or len(referencia) != len(actual) or not len(referencia):
        raise ValueError('PSI requiere vectores unidimensionales de igual longitud no vacíos.')
    if (referencia < 0).any() or (actual < 0).any() or referencia.sum() <= 0 or actual.sum() <= 0:
        raise ValueError('Las distribuciones PSI deben tener masa positiva y no negativa.')
    p = referencia / referencia.sum()
    q = actual / actual.sum()
    p = np.clip(p, epsilon, None)
    q = np.clip(q, epsilon, None)
    p = p / p.sum()
    q = q / q.sum()
    return float(np.sum((q - p) * np.log(q / p)))


def estado_psi(valor: float) -> str:
    if valor < 0.1:
        return 'estable_referencia_academica'
    if valor < 0.25:
        return 'cambio_moderado_revision'
    return 'cambio_alto_revisar_reentrenamiento'


def _psi_continuo(referencia: pd.Series, actual: pd.Series, nombre: str) -> dict:
    ref = pd.to_numeric(referencia, errors='coerce').dropna().to_numpy(dtype=float)
    cur = pd.to_numeric(actual, errors='coerce').dropna().to_numpy(dtype=float)
    if not len(ref) or not len(cur):
        raise ValueError(f'No hay observaciones válidas para calcular drift de {nombre}.')
    quantiles = np.unique(np.quantile(ref, np.linspace(0, 1, 11)))
    if len(quantiles) < 2:
        edges = np.array([-np.inf, np.inf])
    else:
        edges = np.concatenate(([-np.inf], quantiles[1:-1], [np.inf]))
        edges = np.unique(edges)
    ref_counts, _ = np.histogram(ref, bins=edges)
    cur_counts, _ = np.histogram(cur, bins=edges)
    psi = calcular_psi(ref_counts, cur_counts)
    return {
        'variable': nombre, 'tipo_variable': 'continua', 'psi': psi,
        'n_referencia': len(ref), 'n_actual': len(cur), 'estado': estado_psi(psi),
        'bins': int(len(edges) - 1), 'criterio': 'Bordes de deciles calculados solo sobre train.',
    }


def _psi_categorico(referencia: pd.Series, actual: pd.Series, nombre: str) -> dict:
    ref = referencia.astype('string').fillna('<nulo>')
    cur = actual.astype('string').fillna('<nulo>')
    categorias = sorted(set(ref) | set(cur))
    ref_counts = ref.value_counts().reindex(categorias, fill_value=0).to_numpy()
    cur_counts = cur.value_counts().reindex(categorias, fill_value=0).to_numpy()
    psi = calcular_psi(ref_counts, cur_counts)
    return {
        'variable': nombre, 'tipo_variable': 'categorica', 'psi': psi,
        'n_referencia': len(ref), 'n_actual': len(cur), 'estado': estado_psi(psi),
        'bins': len(categorias), 'criterio': 'Categorías observadas en train o test.',
    }


def construir_informe_drift(train: pd.DataFrame, test: pd.DataFrame) -> pd.DataFrame:
    if train.empty or test.empty:
        raise ValueError('Train y test deben contener datos para comparar drift.')
    train = train.copy()
    test = test.copy()
    for frame in (train, test):
        frame['longitud_caracteres'] = frame['texto_limpio'].str.len()
        frame['cantidad_tokens'] = frame['texto_limpio'].str.split().str.len()
    filas = [
        _psi_continuo(train[col], test[col], col)
        for col in ('longitud_caracteres', 'cantidad_tokens')
    ]
    filas.append(_psi_categorico(train['sentimiento_score'], test['sentimiento_score'], 'sentimiento_score_proxy'))
    return pd.DataFrame(filas)


def _append_csv(path: Path, filas: pd.DataFrame, unique_by: str | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_file():
        anterior = pd.read_csv(path, encoding='utf-8-sig')
        filas = pd.concat([anterior, filas], ignore_index=True)
    if unique_by and unique_by in filas:
        filas = filas.drop_duplicates(subset=[unique_by], keep='first')
    filas.to_csv(path, index=False, encoding='utf-8-sig')


def ejecutar(root: Path = ROOT) -> dict:
    resultados = root / 'resultados'
    data_dir = root / 'data/processed/modelos'
    modelo_path = data_dir / 'clasificador_resenas.joblib'
    zip_path = root / 'data/raw/archive.zip'
    clasificacion_path = resultados / 'clasificacion_metadata.json'
    metricas_path = resultados / 'evaluacion_clasificacion.csv'
    for path in (modelo_path, zip_path, clasificacion_path, metricas_path):
        if not path.is_file():
            raise FileNotFoundError(f'Falta {path.relative_to(root)}; ejecutar primero src/clasificacion_resenas.py.')
    metadata_clasif = json.loads(clasificacion_path.read_text(encoding='utf-8-sig'))
    resenas = cargar_resenas_zip(zip_path)
    datos, _ = preparar_resenas(resenas)
    corte = pd.Timestamp(metadata_clasif['fecha_corte_test'])
    train = datos.loc[datos['fecha_resena'] < corte]
    test = datos.loc[datos['fecha_resena'] >= corte]
    drift = construir_informe_drift(train, test)
    run_id = datetime.now(timezone.utc).isoformat()
    version = metadata_clasif.get('sha256_modelo') or sha256(modelo_path)
    evaluacion = pd.read_csv(metricas_path, encoding='utf-8-sig')
    metricas_rows = []
    for _, fila in evaluacion.iterrows():
        for metrica in ('accuracy', 'precision_macro', 'recall_macro', 'f1_macro', 'roc_auc_ovr_macro', 'pr_auc_macro_ovr'):
            valor = pd.to_numeric(fila.get(metrica), errors='coerce')
            if pd.notna(valor):
                metricas_rows.append({
                    'run_id': run_id, 'model_version': version,
                    'modelo': fila.get('modelo'), 'metrica': metrica, 'valor': float(valor),
                    'particion': 'test_cronologico', 'n_evaluacion': int(fila['n_test']),
                    'origen': 'evaluacion_clasificacion.csv',
                })
    metrics_path = resultados / 'monitoring_metrics.csv'
    _append_csv(metrics_path, pd.DataFrame(metricas_rows))
    drift_path = resultados / 'data_drift_report.csv'
    drift.assign(run_id=run_id, model_version=version,
                 comparacion='train_test_mismo_dataset_historico').to_csv(
        drift_path, index=False, encoding='utf-8-sig',
    )

    history_path = resultados / 'model_history.csv'
    history_row = pd.DataFrame([{
        'model_version': version, 'registrado_en_utc': run_id,
        'modelo': 'logistic_regression_tfidf', 'artefacto': str(modelo_path.relative_to(root)),
        'sha256_artefacto': sha256(modelo_path), 'sha256_datos': metadata_clasif.get('sha256_origen'),
        'n_train': metadata_clasif['n_train'], 'n_test': metadata_clasif['n_test'],
        'particion': 'cronologica_por_review_creation_date',
    }])
    _append_csv(history_path, history_row, unique_by='model_version')
    historial = pd.read_csv(history_path, encoding='utf-8-sig').fillna('')
    registro = {
        'modo': 'retrospectivo_academico', 'tiempo_real': False,
        'version_activa': version, 'versiones': historial.to_dict(orient='records'),
        'ultima_ejecucion_utc': run_id,
        'criterio_revision': 'PSI < 0.1 referencia estable; 0.1–0.25 revisión; >= 0.25 evaluar reentrenamiento manual.',
        'limitaciones': [
            'El drift compara train y test históricos del mismo dataset; no monitorea datos entrantes.',
            'PSI es un indicador de cambio de distribución, no evidencia por sí solo de degradación predictiva.',
            'Las recomendaciones requieren revisión humana y validación del modelo candidato.',
        ],
    }
    (resultados / 'model_registry.json').write_text(
        json.dumps(registro, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
    )
    audit_path = resultados / 'audit_log.csv'
    _append_csv(audit_path, pd.DataFrame([{
        'run_id': run_id, 'event': 'monitoring_retroactivo', 'status': 'ok',
        'model_version': version, 'fuente': str(zip_path.relative_to(root)),
        'metricas': str(metrics_path.relative_to(root)), 'drift': str(drift_path.relative_to(root)),
    }]))
    print(f'Monitoreo retrospectivo: {len(drift)} variables; versión {version[:12]}; drift sin afirmación de tiempo real.')
    return registro


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        ejecutar(args.root.resolve())
    except (OSError, ValueError, KeyError) as error:
        parser.exit(1, f'Error de monitoreo: {error}\n')


if __name__ == '__main__':
    main()
