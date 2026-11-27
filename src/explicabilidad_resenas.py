"""Explicaciones globales y locales del Logistic Regression TF-IDF entrenado.

Las contribuciones locales son la descomposición exacta de términos al logit
lineal de la clase predicha; no son valores SHAP ni cambios directos de probabilidad.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import load

from clasificacion_resenas import ROOT, cargar_resenas_zip, limpiar_comentario


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open('rb') as archivo:
        for bloque in iter(lambda: archivo.read(1 << 20), b''):
            digest.update(bloque)
    return digest.hexdigest()


def validar_pipeline(modelo):
    if not hasattr(modelo, 'named_steps') or 'tfidf' not in modelo.named_steps or 'clasificador' not in modelo.named_steps:
        raise ValueError('El artefacto no es el Pipeline TF-IDF + LogisticRegression esperado.')
    vectorizador = modelo.named_steps['tfidf']
    clasificador = modelo.named_steps['clasificador']
    if not hasattr(clasificador, 'coef_'):
        raise ValueError('El clasificador no expone coeficientes para explicar.')
    return vectorizador, clasificador


def importancia_global(modelo, top_n=30) -> pd.DataFrame:
    vectorizador, clasificador = validar_pipeline(modelo)
    nombres = vectorizador.get_feature_names_out()
    filas = []
    for indice, clase in enumerate(clasificador.classes_):
        coeficientes = clasificador.coef_[indice]
        orden = np.argsort(-np.abs(coeficientes), kind='stable')[:top_n]
        filas.extend({
            'clase': str(clase), 'termino': str(nombres[j]),
            'coeficiente_logit': float(coeficientes[j]),
            'magnitud_coeficiente': float(abs(coeficientes[j])),
            'direccion': 'a_favor_de_clase' if coeficientes[j] >= 0 else 'en_contra_de_clase',
            'rango_global': rango + 1,
        } for rango, j in enumerate(orden))
    return pd.DataFrame(filas)


def explicaciones_locales(modelo, predicciones: pd.DataFrame, textos: list[str], muestra=50, top_n=5) -> pd.DataFrame:
    vectorizador, clasificador = validar_pipeline(modelo)
    if len(predicciones) != len(textos):
        raise ValueError('Las predicciones y los textos deben tener igual longitud.')
    if not len(predicciones):
        return pd.DataFrame(columns=[
            'review_id', 'clase_real', 'clase_predicha', 'probabilidad_predicha',
            'termino', 'tfidf', 'coeficiente_logit', 'contribucion_logit', 'direccion',
        ])
    predicciones = predicciones.reset_index(drop=True)
    seleccion = predicciones.sample(n=min(muestra, len(predicciones)), random_state=42)
    indices = seleccion.index.to_numpy()
    seleccion = seleccion.reset_index(drop=True)
    textos_muestra = [textos[i] for i in indices]
    matriz = vectorizador.transform(textos_muestra).tocsr()
    probabilidades = modelo.predict_proba(textos_muestra)
    clases = list(clasificador.classes_)
    clase_predicha = modelo.predict(textos_muestra)
    nombres = vectorizador.get_feature_names_out()
    filas = []
    for fila in range(matriz.shape[0]):
        clase = str(clase_predicha[fila])
        clase_indice = clases.index(clase)
        inicio, fin = matriz.indptr[fila], matriz.indptr[fila + 1]
        indices_feature = matriz.indices[inicio:fin]
        valores_tfidf = matriz.data[inicio:fin]
        contribuciones = valores_tfidf * clasificador.coef_[clase_indice][indices_feature]
        if not len(contribuciones):
            continue
        ordenes = [
            np.argsort(-contribuciones, kind='stable')[:top_n],
            np.argsort(contribuciones, kind='stable')[:top_n],
        ]
        for direccion, orden in [('a_favor', ordenes[0]), ('en_contra', ordenes[1])]:
            for rango, posicion in enumerate(orden):
                contribucion = float(contribuciones[posicion])
                if (direccion == 'a_favor' and contribucion <= 0) or (direccion == 'en_contra' and contribucion >= 0):
                    continue
                feature_id = int(indices_feature[posicion])
                filas.append({
                    'review_id': str(seleccion.iloc[fila].get('review_id', '')),
                    'fecha_resena': str(seleccion.iloc[fila].get('fecha_resena', '')),
                    'clase_real': str(seleccion.iloc[fila].get('etiqueta_score_real', '')),
                    'clase_predicha': clase,
                    'probabilidad_predicha': float(probabilidades[fila, clase_indice]),
                    'termino': str(nombres[feature_id]),
                    'tfidf': float(valores_tfidf[posicion]),
                    'coeficiente_logit': float(clasificador.coef_[clase_indice, feature_id]),
                    'contribucion_logit': contribucion,
                    'direccion': direccion,
                    'rango_direccion': rango + 1,
                })
    return pd.DataFrame(filas)


def ejecutar(root: Path = ROOT, muestra: int = 50, top_n: int = 30) -> dict:
    resultados = root / 'resultados'
    ruta_modelo = root / 'data/processed/modelos/clasificador_resenas.joblib'
    ruta_predicciones = resultados / 'predicciones_clasificacion.csv'
    ruta_zip = root / 'data/raw/archive.zip'
    if not ruta_modelo.is_file() or not ruta_predicciones.is_file():
        raise FileNotFoundError('Ejecuta primero src/clasificacion_resenas.py para generar modelo y predicciones de test.')
    modelo = load(ruta_modelo)
    resenas = cargar_resenas_zip(ruta_zip)
    predicciones = pd.read_csv(ruta_predicciones, encoding='utf-8-sig')
    if 'source_row' not in predicciones:
        raise ValueError('predicciones_clasificacion.csv no contiene source_row; regenerar clasificación con la versión actual.')
    indices = pd.to_numeric(predicciones['source_row'], errors='coerce')
    if indices.isna().any() or (indices < 0).any() or (indices >= len(resenas)).any():
        raise ValueError('source_row de predicciones no corresponde al ZIP de entrada.')
    textos = [limpiar_comentario(resenas.iloc[int(i)]['review_comment_message']) for i in indices]
    globales = importancia_global(modelo, top_n)
    locales = explicaciones_locales(modelo, predicciones, textos, muestra=muestra)
    globales.to_csv(resultados / 'importancia_variables.csv', index=False, encoding='utf-8-sig')
    locales.to_csv(resultados / 'explicaciones_locales.csv', index=False, encoding='utf-8-sig')
    metadata = {
        'tecnica': 'Explicabilidad lineal de LogisticRegression TF-IDF',
        'modelo': str(ruta_modelo.relative_to(root)), 'sha256_modelo': sha256(ruta_modelo),
        'sha256_entrada': sha256(ruta_zip), 'metodo_global': 'Magnitud y signo de coeficientes TF-IDF por clase.',
        'metodo_local': 'Contribución exacta TF-IDF * coeficiente al logit de la clase predicha.',
        'predicciones_test_disponibles': len(predicciones), 'predicciones_explicadas': min(muestra, len(predicciones)),
        'terminos_globales_por_clase': top_n, 'terminos_locales_por_direccion': 5,
        'ejecutado_en_utc': datetime.now(timezone.utc).isoformat(),
        'limitaciones': [
            'No se calcula SHAP; la explicación local está en escala de logit, no en puntos de probabilidad.',
            'Coeficientes reflejan asociación del modelo y no causalidad.',
            'El target corresponde a categorías derivadas de review_score, no a anotaciones humanas independientes.',
        ],
    }
    (resultados / 'explicabilidad_metadata.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
    )
    print(f'Explicabilidad: {len(globales)} coeficientes globales y {len(locales)} contribuciones locales.')
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--muestra', type=int, default=50)
    parser.add_argument('--top-n', type=int, default=30)
    args = parser.parse_args(argv)
    if args.muestra < 1 or args.top_n < 1 or args.top_n > 100:
        parser.error('--muestra debe ser positiva y --top-n debe estar entre 1 y 100.')
    try:
        ejecutar(args.root.resolve(), args.muestra, args.top_n)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error de explicabilidad: {error}\n')


if __name__ == '__main__':
    main()
