"""NLP descriptivo de reseñas Olist: idioma heurístico, TF-IDF y léxico polar.

La polaridad léxica se calcula desde el comentario; las clases de review_score
se reportan aparte como referencia, nunca como predicción textual.
"""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from itertools import combinations
import json
from pathlib import Path
import re
from zipfile import BadZipFile

import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer

from clasificacion_resenas import ARCHIVO_RESENAS, ROOT, cargar_resenas_zip, limpiar_comentario, sha256


STOP_PT = {
    'a', 'ao', 'aos', 'as', 'com', 'como', 'da', 'das', 'de', 'do', 'dos', 'e',
    'ela', 'ele', 'em', 'essa', 'esse', 'esta', 'este', 'eu', 'foi', 'for', 'isso',
    'mais', 'mas', 'me', 'muito', 'na', 'nas', 'nao', 'no', 'nos', 'o', 'os', 'ou',
    'para', 'pela', 'pelas', 'pelo', 'pelos', 'por', 'que', 'se', 'sem', 'um', 'uma',
    'voce', 'ja', 'quando', 'produto', 'pedido', 'entrega', 'chegou',
}
POSITIVAS = {
    'adorei', 'amei', 'atencioso', 'boa', 'bom', 'bonito', 'eficiente', 'excelente',
    'feliz', 'gostei', 'otimo', 'perfeito', 'recomendo', 'satisfeito', 'qualidade',
    'rapido', 'maravilhoso', 'lindo', 'funciona', 'vale',
}
NEGATIVAS = {
    'atrasado', 'atraso', 'cancelado', 'decepcionado', 'defeito', 'demora', 'demorou',
    'errado', 'falha', 'faltou', 'horrivel', 'insatisfeito', 'nao', 'nunca', 'pessimo',
    'problema', 'quebrado', 'ruim', 'terrivel',
}
TOKEN = re.compile(r'[^\W_]+', re.UNICODE)
SALIDA = ['negativo_lexico', 'neutral_lexico', 'positivo_lexico']


def identificar_idioma_heuristico(texto: str) -> str:
    tokens = set(TOKEN.findall(texto))
    coincidencias = len(tokens & STOP_PT)
    return 'portugues_probable' if coincidencias >= 2 else 'idioma_incierto'


def sentimiento_lexico(texto: str) -> tuple[str, int, int, int]:
    tokens = TOKEN.findall(texto)
    positivos = sum(token in POSITIVAS for token in tokens)
    negativos = sum(token in NEGATIVAS for token in tokens)
    clase = 'positivo_lexico' if positivos > negativos else 'negativo_lexico' if negativos > positivos else 'neutral_lexico'
    return clase, positivos, negativos, positivos - negativos


def analizar_resenas(resenas: pd.DataFrame, top_n: int = 30) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    requeridas = {'review_score', 'review_comment_message'}
    faltan = sorted(requeridas - set(resenas.columns))
    if faltan:
        raise ValueError(f'Faltan columnas requeridas para NLP: {faltan}')
    if top_n < 1 or top_n > 100:
        raise ValueError('top_n debe estar entre 1 y 100.')
    datos = resenas[['review_score', 'review_comment_message']].copy()
    datos['texto_limpio'] = datos['review_comment_message'].map(limpiar_comentario)
    no_vacios = datos.loc[datos['texto_limpio'].str.len().gt(0)].copy().reset_index(drop=True)
    if no_vacios.empty:
        raise ValueError('No hay comentarios de reseñas no vacíos para analizar.')
    no_vacios['review_score_num'] = pd.to_numeric(no_vacios['review_score'], errors='coerce')
    no_vacios['sentimiento_score'] = no_vacios['review_score_num'].map(
        {1: 'negativo_score', 2: 'negativo_score', 3: 'neutral_score', 4: 'positivo_score', 5: 'positivo_score'}
    )
    polaridades = no_vacios['texto_limpio'].map(sentimiento_lexico)
    no_vacios[['sentimiento_lexico', 'conteo_positivo_lexico', 'conteo_negativo_lexico', 'polaridad_lexica']] = pd.DataFrame(
        polaridades.tolist(), index=no_vacios.index,
    )
    no_vacios['idioma_heuristico'] = no_vacios['texto_limpio'].map(identificar_idioma_heuristico)

    distribuciones = []
    for columna, origen, clases in [
        ('sentimiento_score', 'derivado_de_review_score', ['negativo_score', 'neutral_score', 'positivo_score']),
        ('sentimiento_lexico', 'calculado_desde_texto_lexico', SALIDA),
        ('idioma_heuristico', 'heuristica_de_vocabulario', ['portugues_probable', 'idioma_incierto']),
    ]:
        conteos = no_vacios[columna].value_counts(dropna=False)
        denominator = int(conteos.sum())
        for clase in clases:
            cantidad = int(conteos.get(clase, 0))
            distribuciones.append({
                'origen_etiqueta': origen, 'clase': clase, 'cantidad': cantidad,
                'porcentaje': 100 * cantidad / denominator if denominator else 0,
            })
    sentimientos = pd.DataFrame(distribuciones)

    vectorizador = TfidfVectorizer(
        strip_accents='unicode', lowercase=False, ngram_range=(1, 2),
        min_df=3, max_features=30000, stop_words=sorted(STOP_PT), sublinear_tf=True,
    )
    matriz = vectorizador.fit_transform(no_vacios['texto_limpio'])
    terminos = np.asarray(vectorizador.get_feature_names_out())
    filas_terminos = []
    for clase in ['negativo_score', 'neutral_score', 'positivo_score']:
        mascara = no_vacios['sentimiento_score'].eq(clase).to_numpy()
        if not mascara.any():
            continue
        promedio = np.asarray(matriz[mascara].mean(axis=0)).ravel()
        cantidad = min(top_n, len(promedio))
        mejores = np.argsort(-promedio, kind='stable')[:cantidad]
        filas_terminos.extend({
            'referencia_sentimiento_score': clase,
            'termino': str(terminos[indice]),
            'tfidf_medio': float(promedio[indice]),
            'n_documentos_referencia': int(mascara.sum()),
        } for indice in mejores if promedio[indice] > 0)
    tabla_terminos = pd.DataFrame(filas_terminos, columns=[
        'referencia_sentimiento_score', 'termino', 'tfidf_medio', 'n_documentos_referencia',
    ])

    coocurrencias = Counter()
    for texto in no_vacios['texto_limpio']:
        tokens = sorted({token for token in TOKEN.findall(texto) if token not in STOP_PT and len(token) > 1})
        for par in combinations(tokens[:20], 2):
            coocurrencias[par] += 1
    tabla_coocurrencias = pd.DataFrame([
        {'termino_1': a, 'termino_2': b, 'documentos_coocurrencia': n}
        for (a, b), n in coocurrencias.most_common(200)
    ], columns=['termino_1', 'termino_2', 'documentos_coocurrencia'])

    metadata = {
        'tecnica': 'NLP descriptivo de reseñas Olist',
        'resenas_entrada': len(resenas), 'resenas_con_texto_util': len(no_vacios),
        'resenas_texto_vacio_o_nulo': int(len(datos) - len(no_vacios)),
        'distribucion_idioma_heuristico': no_vacios['idioma_heuristico'].value_counts().to_dict(),
        'representacion': {'tipo': 'TF-IDF', 'ngram_range': [1, 2], 'min_df': 3, 'max_features': 30000,
                           'stopwords': 'lista portuguesa incluida en el módulo'},
        'sentimiento_score': 'Etiquetas de referencia: 1-2 negativo, 3 neutral, 4-5 positivo.',
        'sentimiento_lexico': {
            'metodo': 'Diferencia de conteos de vocabulario portugués positivo y negativo; empate=neutral.',
            'positivo': sorted(POSITIVAS), 'negativo': sorted(NEGATIVAS),
        },
        'idioma': 'Heurística de palabras funcionales portuguesas; no es un detector estadístico de idioma.',
        'limitaciones': [
            'El léxico no modela negación, ironía ni contexto y su vocabulario es limitado.',
            'El TF-IDF describe términos por etiquetas de puntuación; no demuestra causalidad ni tópicos latentes.',
            'Sentimiento calculado desde texto y sentimiento derivado de review_score son medidas distintas.',
        ],
    }
    return tabla_terminos, tabla_coocurrencias, sentimientos, metadata


def ejecutar(ruta_zip: Path, output_root: Path, top_n: int = 30) -> dict:
    resenas = cargar_resenas_zip(ruta_zip)
    terminos, coocurrencias, sentimientos, metadata = analizar_resenas(resenas, top_n)
    resultados = output_root / 'resultados'
    resultados.mkdir(parents=True, exist_ok=True)
    terminos.to_csv(resultados / 'nlp_terminos_frecuentes.csv', index=False, encoding='utf-8-sig')
    coocurrencias.to_csv(resultados / 'nlp_coocurrencias.csv', index=False, encoding='utf-8-sig')
    sentimientos.to_csv(resultados / 'nlp_sentimientos.csv', index=False, encoding='utf-8-sig')
    metadata.update({
        'ejecutado_en_utc': datetime.now(timezone.utc).isoformat(),
        'archivo_origen': str(ruta_zip), 'archivo_csv': ARCHIVO_RESENAS,
        'sha256_origen': sha256(ruta_zip), 'top_n_terminos_por_clase': top_n,
    })
    (resultados / 'nlp_metadata.json').write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8',
    )
    print(f"NLP: {metadata['resenas_con_texto_util']} reseñas con texto útil; TF-IDF={len(terminos)} términos; pares={len(coocurrencias)}")
    return metadata


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, default=ROOT / 'data/raw/archive.zip')
    parser.add_argument('--output-root', type=Path, default=ROOT)
    parser.add_argument('--top-n', type=int, default=30)
    args = parser.parse_args(argv)
    try:
        ejecutar(args.zip.resolve(), args.output_root.resolve(), args.top_n)
    except (OSError, ValueError, BadZipFile) as error:
        parser.exit(1, f'Error de NLP: {error}\n')


if __name__ == '__main__':
    main()
