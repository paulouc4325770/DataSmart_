"""Clasificación textual de reseñas Olist con etiquetas derivadas de review_score.

Las etiquetas son una aproximación basada en la puntuación, no anotaciones humanas
independientes de sentimiento. El modelo usa únicamente el comentario textual y se
evalúa con una partición cronológica por fecha de creación de la reseña.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import html
import json
from pathlib import Path
import re
import unicodedata
from zipfile import BadZipFile, ZipFile

from joblib import dump
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import (
    accuracy_score, average_precision_score, classification_report,
    confusion_matrix, f1_score, precision_score, recall_score, roc_auc_score,
)
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import label_binarize


ROOT = Path(__file__).resolve().parents[1]
ARCHIVO_RESENAS = 'olist_order_reviews_dataset.csv'
CLASES = ('negativo', 'neutral', 'positivo')
MAPA_PUNTUACION = {1: 'negativo', 2: 'negativo', 3: 'neutral', 4: 'positivo', 5: 'positivo'}
RE_HTML = re.compile(r'<[^>]+>')
RE_URL = re.compile(r'https?://\S+|www\.\S+', re.IGNORECASE)
RE_NO_TEXTO = re.compile(r'[^\w\s]', re.UNICODE)


def sha256(ruta: Path) -> str:
    digest = hashlib.sha256()
    with ruta.open('rb') as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b''):
            digest.update(bloque)
    return digest.hexdigest()


def cargar_resenas_zip(ruta_zip: Path) -> pd.DataFrame:
    if not ruta_zip.is_file():
        raise FileNotFoundError(f'No se encontró el archivo Olist: {ruta_zip}')
    try:
        with ZipFile(ruta_zip) as archivo:
            if ARCHIVO_RESENAS not in archivo.namelist():
                raise ValueError(f'El ZIP no contiene {ARCHIVO_RESENAS}.')
            with archivo.open(ARCHIVO_RESENAS) as entrada:
                return pd.read_csv(entrada, encoding='utf-8-sig')
    except BadZipFile as error:
        raise ValueError(f'El archivo de entrada no es un ZIP válido: {ruta_zip}') from error


def limpiar_comentario(texto) -> str:
    if texto is None or pd.isna(texto):
        return ''
    texto = html.unescape(str(texto)).lower()
    texto = ''.join(char for char in unicodedata.normalize('NFKD', texto)
                    if not unicodedata.combining(char))
    texto = RE_HTML.sub(' ', texto)
    texto = RE_URL.sub(' ', texto)
    texto = RE_NO_TEXTO.sub(' ', texto)
    return ' '.join(texto.split())


def preparar_resenas(resenas: pd.DataFrame) -> tuple[pd.DataFrame, dict]:
    requeridas = {'review_id', 'order_id', 'review_score', 'review_comment_message', 'review_creation_date'}
    faltantes = sorted(requeridas - set(resenas.columns))
    if faltantes:
        raise ValueError(f'Faltan columnas requeridas en reseñas: {faltantes}')
    datos = resenas.copy()
    datos['_source_row'] = np.arange(len(datos), dtype=np.int64)
    datos['review_score_num'] = pd.to_numeric(datos['review_score'], errors='coerce')
    datos['fecha_resena'] = pd.to_datetime(datos['review_creation_date'], errors='coerce')
    datos['texto_limpio'] = datos['review_comment_message'].map(limpiar_comentario)
    score_valido = datos['review_score_num'].isin(MAPA_PUNTUACION)
    texto_valido = datos['texto_limpio'].str.len().gt(0)
    fecha_valida = datos['fecha_resena'].notna()
    elegibles = datos.loc[score_valido & texto_valido & fecha_valida].copy()
    if elegibles.empty:
        raise ValueError('No hay reseñas con texto, puntuación válida y fecha de creación válida.')
    elegibles['sentimiento_score'] = elegibles['review_score_num'].astype(int).map(MAPA_PUNTUACION)
    elegibles = elegibles.sort_values(['fecha_resena', 'review_id'], kind='mergesort').reset_index(drop=True)
    resumen = {
        'resenas_entrada': len(datos),
        'resenas_con_texto_no_vacio': int(texto_valido.sum()),
        'resenas_score_valido': int(score_valido.sum()),
        'resenas_fecha_valida': int(fecha_valida.sum()),
        'resenas_elegibles': len(elegibles),
        'resenas_excluidas': len(datos) - len(elegibles),
        'distribucion_etiquetas_score': {
            nombre: int((elegibles['sentimiento_score'] == nombre).sum()) for nombre in CLASES
        },
    }
    return elegibles, resumen


def evaluar_clasificador(resenas: pd.DataFrame, test_fraction: float = 0.2) -> tuple[pd.DataFrame, pd.DataFrame, dict, Pipeline]:
    if not 0.1 <= test_fraction <= 0.4:
        raise ValueError('test_fraction debe estar entre 0.1 y 0.4.')
    datos, poblacion = preparar_resenas(resenas)
    if len(datos) < 30:
        raise ValueError('Se requieren al menos 30 reseñas elegibles para evaluación.')
    indice_corte = max(1, min(len(datos) - 1, int(np.floor(len(datos) * (1 - test_fraction)))))
    fecha_corte = datos.iloc[indice_corte]['fecha_resena']
    train = datos.loc[datos['fecha_resena'] < fecha_corte]
    test = datos.loc[datos['fecha_resena'] >= fecha_corte]
    if train.empty or test.empty:
        raise ValueError('El corte cronológico dejó una partición vacía; revisar fechas.')
    for nombre in CLASES:
        if nombre not in set(train['sentimiento_score']) or nombre not in set(test['sentimiento_score']):
            raise ValueError(f'La clase {nombre!r} no está presente en train y test cronológicos.')

    modelo = Pipeline([
        ('tfidf', TfidfVectorizer(
            strip_accents='unicode', lowercase=False, ngram_range=(1, 2),
            min_df=2, max_features=50000, sublinear_tf=True, dtype=np.float64,
        )),
        ('clasificador', LogisticRegression(
            max_iter=1000, class_weight='balanced', random_state=42, solver='lbfgs',
        )),
    ])
    modelo.fit(train['texto_limpio'], train['sentimiento_score'])
    predicho = modelo.predict(test['texto_limpio'])
    probabilidades = modelo.predict_proba(test['texto_limpio'])
    clases_modelo = list(modelo.named_steps['clasificador'].classes_)
    y_binario = label_binarize(test['sentimiento_score'], classes=clases_modelo)
    try:
        roc_auc = float(roc_auc_score(test['sentimiento_score'], probabilidades,
                                      labels=clases_modelo, multi_class='ovr', average='macro'))
    except ValueError:
        roc_auc = None
    try:
        pr_auc = float(average_precision_score(y_binario, probabilidades, average='macro'))
    except ValueError:
        pr_auc = None
    metricas = {
        'accuracy': float(accuracy_score(test['sentimiento_score'], predicho)),
        'precision_macro': float(precision_score(test['sentimiento_score'], predicho, labels=CLASES, average='macro', zero_division=0)),
        'recall_macro': float(recall_score(test['sentimiento_score'], predicho, labels=CLASES, average='macro', zero_division=0)),
        'f1_macro': float(f1_score(test['sentimiento_score'], predicho, labels=CLASES, average='macro', zero_division=0)),
        'roc_auc_ovr_macro': roc_auc,
        'pr_auc_macro_ovr': pr_auc,
        'matriz_confusion': confusion_matrix(test['sentimiento_score'], predicho, labels=CLASES).tolist(),
        'orden_clases_matriz': list(CLASES),
        'reporte_por_clase': classification_report(test['sentimiento_score'], predicho, labels=CLASES,
                                                   output_dict=True, zero_division=0),
    }
    prob_por_clase = {clase: probabilidades[:, indice] for indice, clase in enumerate(clases_modelo)}
    predicciones = pd.DataFrame({
        'source_row': test['_source_row'].to_numpy(),
        'review_id': test['review_id'].astype('string').fillna(''),
        'fecha_resena': test['fecha_resena'].dt.strftime('%Y-%m-%d'),
        'etiqueta_score_real': test['sentimiento_score'].to_numpy(),
        'etiqueta_texto_predicha': predicho,
        'prob_negativo': prob_por_clase['negativo'],
        'prob_neutral': prob_por_clase['neutral'],
        'prob_positivo': prob_por_clase['positivo'],
        'particion': 'test_cronologico',
    })
    metadata = {
        'tecnica': 'Clasificación de sentimiento textual supervisada',
        'objetivo': 'Clase derivada de review_score; no es anotación humana independiente.',
        'etiquetas': {'1-2': 'negativo', '3': 'neutral', '4-5': 'positivo'},
        'predictores': ['review_comment_message (texto limpio)'],
        'variables_excluidas': ['review_score', 'review_id', 'order_id', 'fechas y estados post-evento'],
        'particion': 'Cronológica por review_creation_date; el tiempo se usa solo para separar, no como predictor.',
        'fecha_corte_test': fecha_corte.date().isoformat(),
        'train_inicio': train['fecha_resena'].min().date().isoformat(),
        'train_fin': train['fecha_resena'].max().date().isoformat(),
        'test_inicio': test['fecha_resena'].min().date().isoformat(),
        'test_fin': test['fecha_resena'].max().date().isoformat(),
        'n_train': len(train), 'n_test': len(test),
        'conteos_train': {c: int((train['sentimiento_score'] == c).sum()) for c in CLASES},
        'conteos_test': {c: int((test['sentimiento_score'] == c).sum()) for c in CLASES},
        'vectorizador': {'tipo': 'TF-IDF', 'ngram_range': [1, 2], 'min_df': 2, 'max_features': 50000, 'strip_accents': 'unicode'},
        'modelo': {'tipo': 'LogisticRegression', 'class_weight': 'balanced', 'max_iter': 1000, 'solver': 'lbfgs', 'random_state': 42},
        'poblacion': poblacion,
        'metricas': metricas,
        'limitaciones': [
            'La puntuación funciona como proxy de polaridad; no garantiza sentimiento semántico independiente.',
            'Solo se modelan reseñas con comentario no vacío, score y fecha válidos.',
            'La evaluación es retrospectiva y no estima satisfacción al momento del checkout.',
        ],
    }
    evaluacion = pd.DataFrame([{
        'modelo': 'logistic_regression_tfidf', 'accuracy': metricas['accuracy'],
        'precision_macro': metricas['precision_macro'], 'recall_macro': metricas['recall_macro'],
        'f1_macro': metricas['f1_macro'], 'roc_auc_ovr_macro': metricas['roc_auc_ovr_macro'],
        'pr_auc_macro_ovr': metricas['pr_auc_macro_ovr'], 'n_train': len(train), 'n_test': len(test),
        'fecha_corte_test': fecha_corte.date().isoformat(),
        'matriz_confusion_json': json.dumps(metricas['matriz_confusion']),
    }])
    return evaluacion, predicciones, metadata, modelo


def ejecutar(ruta_zip: Path, output_root: Path) -> dict:
    resenas = cargar_resenas_zip(ruta_zip)
    evaluacion, predicciones, metadata, modelo = evaluar_clasificador(resenas)
    resultados = output_root / 'resultados'
    resultados.mkdir(parents=True, exist_ok=True)
    evaluacion.to_csv(resultados / 'evaluacion_clasificacion.csv', index=False, encoding='utf-8-sig')
    predicciones.to_csv(resultados / 'predicciones_clasificacion.csv', index=False, encoding='utf-8-sig')
    metadata['ejecutado_en_utc'] = datetime.now(timezone.utc).isoformat()
    metadata['archivo_origen'] = str(ruta_zip)
    metadata['sha256_origen'] = sha256(ruta_zip)
    model_path = output_root / 'data/processed/modelos/clasificador_resenas.joblib'
    model_path.parent.mkdir(parents=True, exist_ok=True)
    dump(modelo, model_path)
    metadata['artefacto_modelo'] = str(model_path.relative_to(output_root))
    metadata['sha256_modelo'] = sha256(model_path)
    (resultados / 'clasificacion_metadata.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
    )
    print(f"Clasificación: n_train={metadata['n_train']}, n_test={metadata['n_test']}, F1 macro={metadata['metricas']['f1_macro']:.4f}")
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, default=ROOT / 'data/raw/archive.zip')
    parser.add_argument('--output-root', type=Path, default=ROOT)
    args = parser.parse_args(argv)
    try:
        ejecutar(args.zip.resolve(), args.output_root.resolve())
    except (OSError, ValueError, BadZipFile) as error:
        parser.exit(1, f'Error de clasificación de reseñas: {error}\n')


if __name__ == '__main__':
    main()
