"""Reglas de asociación entre categorías de Olist: Apriori y FP-Growth.

Ejecutar desde la raíz del proyecto:

    python src/asociacion.py

Requiere haber ejecutado antes ``python src/preparar_datos.py``.

Población de referencia
-----------------------
Pedidos *entregados* con al menos un ítem de categoría conocida. Cada pedido
(``order_id``) es una cesta de categorías distintas. La etiqueta «Sin categoría»
no se usa como ítem. Las cestas unitarias (una sola categoría) permanecen en el
denominador del soporte; los pedidos vacíos y los que solo tienen categorías
desconocidas se informan, pero quedan fuera del universo.

Ambos algoritmos se implementan aquí sin dependencias externas, reciben las mismas
cestas y los mismos parámetros, y se verifica que obtengan los mismos resultados.

Análisis complementario (``--poblacion multicategoria``)
--------------------------------------------------------
Repite el análisis solo con las cestas de 2 o más categorías. Responde: entre los
pedidos que sí combinan categorías, ¿qué combinaciones son más frecuentes de lo
esperable? Las métricas tienen otra población de referencia y se guardan en archivos
con el sufijo ``_multicategoria``; no reemplazan al análisis principal.

``p_valor`` es la probabilidad, bajo independencia de las dos categorías dentro de la
población de referencia, de observar al menos ``n_pedidos`` cestas con ambas
(distribución hipergeométrica, cola superior). Es descriptivo: con muchos pares
evaluados conviene corregir por comparaciones múltiples.
"""

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
from functools import lru_cache
from itertools import combinations
import json
import math
from pathlib import Path
import platform
import statistics
import time

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SEPARADOR_ITEMS = ' + '
UMBRALES_DIAGNOSTICO = [1, 2, 3, 5, 10, 20, 50, 100]
COLUMNAS_ITEMS = ['order_id', 'order_status', 'categoria_presentacion', 'sin_categoria']
COLUMNAS_PEDIDOS = ['order_id', 'es_entregado', 'sin_items']
COLUMNAS_REGLAS = [
    'regla_id', 'antecedente', 'consecuente', 'soporte', 'confianza', 'lift', 'conviccion',
    'p_valor', 'n_pedidos', 'n_pedidos_antecedente', 'n_pedidos_consecuente',
    'soporte_antecedente', 'soporte_consecuente', 'asociacion_positiva',
    'total_cestas', 'poblacion_referencia',
]


# ---------------------------------------------------------------------------
# Cestas
# ---------------------------------------------------------------------------

def leer_csv(ruta, columnas, nombre):
    """Lee solo las columnas necesarias, como texto, y valida que existan."""
    if not Path(ruta).is_file():
        raise FileNotFoundError(
            f'No existe {ruta}. Ejecutar primero: python src/preparar_datos.py'
        )
    encabezado = pd.read_csv(ruta, nrows=0, encoding='utf-8-sig').columns
    faltan = [c for c in columnas if c not in encabezado]
    if faltan:
        raise ValueError(f'{nombre} no contiene las columnas requeridas: {faltan}')
    return pd.read_csv(ruta, usecols=columnas, dtype='string', encoding='utf-8-sig')


def construir_cestas(items, pedidos=None):
    """Construye una cesta de categorías distintas por pedido entregado.

    Devuelve ``(cestas, composicion)``. ``cestas`` es un diccionario
    ``order_id -> tupla ordenada de categorías`` solo con pedidos del universo
    (al menos una categoría conocida). ``composicion`` describe la población.
    """
    entregados = items[items['order_status'].eq('delivered').fillna(False)]
    n_items_por_pedido = entregados.groupby('order_id').size()
    pedidos_con_items = set(n_items_por_pedido.index)

    desconocida = entregados['sin_categoria'].eq('True').fillna(False) \
        | entregados['categoria_presentacion'].isna()
    conocidas = entregados.loc[~desconocida, ['order_id', 'categoria_presentacion']]
    conocidas = conocidas.drop_duplicates()
    por_pedido = conocidas.groupby('order_id')['categoria_presentacion'].agg(
        lambda s: tuple(sorted(str(c) for c in s))
    )
    cestas = {str(oid): cesta for oid, cesta in sorted(por_pedido.items())}

    n_con_items = len(pedidos_con_items)
    n_sin_categoria_conocida = n_con_items - len(cestas)
    n_unitarias = sum(1 for c in cestas.values() if len(c) == 1)
    n_multi = len(cestas) - n_unitarias
    unitarias_varios_items = sum(
        1 for oid, c in cestas.items() if len(c) == 1 and n_items_por_pedido[oid] > 1
    )

    n_entregados = n_con_items
    n_vacios = None
    advertencias = []
    if pedidos is not None:
        ent = pedidos[pedidos['es_entregado'].eq('True').fillna(False)]
        n_entregados = len(ent)
        n_vacios = int(ent['sin_items'].eq('True').sum())
        if n_entregados - n_vacios != n_con_items:
            advertencias.append(
                'Los pedidos entregados con ítems no coinciden entre pedidos_procesados.csv '
                f'({n_entregados - n_vacios}) e items_procesados.csv ({n_con_items}).'
            )

    composicion = {
        'pedidos_entregados': n_entregados,
        'vacias': n_vacios,
        'sin_categoria_conocida': n_sin_categoria_conocida,
        'unitarias': n_unitarias,
        'multicategoria': n_multi,
        'universo': len(cestas),
        'unitarias_con_varios_items': unitarias_varios_items,
        'advertencias': advertencias,
    }
    return cestas, composicion


POBLACIONES = ('todas', 'multicategoria')


def descripcion_poblacion(n_universo, poblacion='todas'):
    if poblacion == 'multicategoria':
        return (
            'Pedidos entregados con 2 o más categorías conocidas distintas (cestas multicategoría); '
            f'una cesta por order_id; N={n_universo}'
        )
    return (
        'Pedidos entregados con al menos un ítem de categoría conocida; '
        f'una cesta por order_id con categorías distintas; N={n_universo}'
    )


# ---------------------------------------------------------------------------
# Algoritmos. Entrada: lista de tuplas ordenadas de ítems distintos.
# Salida: {frozenset(itemset): número de cestas que lo contienen}.
# ---------------------------------------------------------------------------

def _candidatos(previos, k):
    """Unión y poda de Apriori a partir de los conjuntos frecuentes de tamaño k-1."""
    conjunto = set(previos)
    candidatos = set()
    for i, a in enumerate(previos):
        for b in previos[i + 1:]:
            if a[:-1] != b[:-1]:
                break
            c = a + (b[-1],)
            if all(sub in conjunto for sub in combinations(c, k - 1)):
                candidatos.add(c)
    return candidatos


def apriori(cestas, min_count, max_len):
    """Apriori por niveles: cuenta candidatos de tamaño k recorriendo las cestas."""
    conteo = Counter()
    for cesta in cestas:
        conteo.update(cesta)
    nivel = {(item,): n for item, n in conteo.items() if n >= min_count}
    salida = {frozenset(k): n for k, n in nivel.items()}
    frecuentes = {k[0] for k in nivel}
    k = 2
    while nivel and k <= max_len:
        candidatos = _candidatos(sorted(nivel), k)
        if not candidatos:
            break
        conteo = Counter()
        for cesta in cestas:
            if len(cesta) < k:
                continue
            items = [i for i in cesta if i in frecuentes]
            if len(items) < k:
                continue
            for comb in combinations(items, k):
                if comb in candidatos:
                    conteo[comb] += 1
        nivel = {c: n for c, n in conteo.items() if n >= min_count}
        salida.update({frozenset(c): n for c, n in nivel.items()})
        k += 1
    return salida


class _NodoFP:
    __slots__ = ('item', 'cuenta', 'padre', 'hijos')

    def __init__(self, item, padre):
        self.item = item
        self.cuenta = 0
        self.padre = padre
        self.hijos = {}


def _arbol_fp(caminos):
    """Construye un FP-tree; devuelve la tabla de nodos por ítem."""
    raiz = _NodoFP(None, None)
    tabla = {}
    for items, cuenta in caminos:
        nodo = raiz
        for item in items:
            hijo = nodo.hijos.get(item)
            if hijo is None:
                hijo = _NodoFP(item, nodo)
                nodo.hijos[item] = hijo
                tabla.setdefault(item, []).append(hijo)
            hijo.cuenta += cuenta
            nodo = hijo
    return tabla


def _minar_fp(tabla, sufijo, min_count, max_len, salida):
    for item, nodos in tabla.items():
        soporte = sum(n.cuenta for n in nodos)
        if soporte < min_count:
            continue
        nuevo = sufijo + (item,)
        salida[frozenset(nuevo)] = soporte
        if len(nuevo) >= max_len:
            continue
        base = []
        conteo = Counter()
        for nodo in nodos:
            camino = []
            padre = nodo.padre
            while padre.item is not None:
                camino.append(padre.item)
                padre = padre.padre
            if camino:
                camino.reverse()
                base.append((camino, nodo.cuenta))
                for it in camino:
                    conteo[it] += nodo.cuenta
        frecuentes = {it for it, n in conteo.items() if n >= min_count}
        if not frecuentes:
            continue
        caminos = [(tuple(i for i in camino if i in frecuentes), n) for camino, n in base]
        _minar_fp(_arbol_fp(caminos), nuevo, min_count, max_len, salida)


def fp_growth(cestas, min_count, max_len):
    """FP-Growth: dos pasadas, FP-tree y minería por bases condicionales."""
    conteo = Counter()
    for cesta in cestas:
        conteo.update(cesta)
    frecuentes = {i: n for i, n in conteo.items() if n >= min_count}
    if not frecuentes:
        return {}
    orden = {i: pos for pos, (i, _) in enumerate(
        sorted(frecuentes.items(), key=lambda x: (-x[1], x[0])))}
    caminos = (
        (tuple(sorted((i for i in cesta if i in frecuentes), key=orden.get)), 1)
        for cesta in cestas
    )
    salida = {}
    _minar_fp(_arbol_fp(caminos), (), min_count, max_len, salida)
    return salida


# ---------------------------------------------------------------------------
# Reglas
# ---------------------------------------------------------------------------

def _log_comb(n, k):
    return math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)


@lru_cache(maxsize=None)
def _p_hipergeometrico(n_ac, n_total, n_a, n_c):
    maximo = min(n_a, n_c)
    if n_ac > maximo:
        return 0.0
    minimo = max(0, n_a + n_c - n_total)
    log_total = _log_comb(n_total, n_c)
    p = sum(
        math.exp(_log_comb(n_a, x) + _log_comb(n_total - n_a, n_c - x) - log_total)
        for x in range(max(n_ac, minimo), maximo + 1)
    )
    return min(1.0, p)


def p_hipergeometrico(n_ac, n_total, n_a, n_c):
    """P(X >= n_ac) si X cuenta cestas con A y C bajo independencia (cola superior).

    Es simétrica en A y C, por lo que A -> C y C -> A comparten el mismo valor.
    """
    a, c = sorted((n_a, n_c))
    return _p_hipergeometrico(n_ac, n_total, a, c)


def generar_reglas(itemsets, n_total, min_confianza):
    """Reglas A -> C a partir de conjuntos frecuentes; el denominador es n_total."""
    reglas = []
    for conjunto, n_ac in itemsets.items():
        if len(conjunto) < 2:
            continue
        items = sorted(conjunto)
        for r in range(1, len(items)):
            for ant in combinations(items, r):
                cons = tuple(i for i in items if i not in ant)
                n_a = itemsets[frozenset(ant)]
                n_c = itemsets[frozenset(cons)]
                confianza = n_ac / n_a
                if confianza < min_confianza:
                    continue
                reglas.append({
                    'antecedente': ant,
                    'consecuente': cons,
                    'soporte': n_ac / n_total,
                    'confianza': confianza,
                    'lift': n_ac * n_total / (n_a * n_c),
                    'conviccion': (1 - n_c / n_total) / (1 - confianza) if confianza < 1 else None,
                    'p_valor': p_hipergeometrico(n_ac, n_total, n_a, n_c),
                    'n_pedidos': n_ac,
                    'n_pedidos_antecedente': n_a,
                    'n_pedidos_consecuente': n_c,
                    'soporte_antecedente': n_a / n_total,
                    'soporte_consecuente': n_c / n_total,
                    'asociacion_positiva': n_ac * n_total > n_a * n_c,
                })
    reglas.sort(key=lambda r: (-r['lift'], -r['n_pedidos'], r['antecedente'], r['consecuente']))
    return reglas


def clave_regla(regla):
    return regla['antecedente'], regla['consecuente']


def comparar_reglas(reglas_a, reglas_b):
    """Compara dos listas de reglas por clave y por métricas exactas."""
    a = {clave_regla(r): r for r in reglas_a}
    b = {clave_regla(r): r for r in reglas_b}
    comunes = a.keys() & b.keys()
    iguales = sum(1 for k in comunes if a[k] == b[k])
    return {
        'reglas_en_comun': len(comunes),
        'reglas_con_metricas_iguales': iguales,
        'solo_en_primero': len(a.keys() - b.keys()),
        'solo_en_segundo': len(b.keys() - a.keys()),
        'coinciden': a.keys() == b.keys() and iguales == len(comunes),
    }


def medir(funcion, repeticiones, *args):
    tiempos = []
    resultado = None
    for _ in range(repeticiones):
        inicio = time.perf_counter()
        resultado = funcion(*args)
        tiempos.append(time.perf_counter() - inicio)
    return resultado, tiempos


# ---------------------------------------------------------------------------
# Trazabilidad y diagnóstico de umbrales
# ---------------------------------------------------------------------------

def indice_multicategoria(cestas):
    """categoría -> conjunto de order_id de cestas con 2 o más categorías."""
    indice = {}
    for oid, cesta in cestas.items():
        if len(cesta) >= 2:
            for categoria in cesta:
                indice.setdefault(categoria, set()).add(oid)
    return indice


def pedidos_de_regla(regla, indice):
    categorias = list(regla['antecedente']) + list(regla['consecuente'])
    conjuntos = [indice.get(c, set()) for c in categorias]
    return sorted(set.intersection(*conjuntos)) if conjuntos else []


def trazabilidad(reglas, ids, indice):
    """Filas (regla_id, order_id). Verifica que cada regla tenga n_pedidos pedidos."""
    filas = []
    for regla, regla_id in zip(reglas, ids):
        pedidos = pedidos_de_regla(regla, indice)
        if len(pedidos) != regla['n_pedidos']:
            raise RuntimeError(
                f'{regla_id}: {len(pedidos)} pedidos rastreados frente a '
                f'n_pedidos={regla["n_pedidos"]}'
            )
        filas.extend((regla_id, oid) for oid in pedidos)
    return filas


def diagnostico_umbrales(cestas, min_count_elegido):
    """Cuántos pares de categorías superan cada umbral de pedidos."""
    n_total = len(cestas)
    individuales = Counter()
    pares = Counter()
    for cesta in cestas.values():
        individuales.update(cesta)
        if len(cesta) >= 2:
            pares.update(combinations(cesta, 2))
    umbrales = sorted(set(UMBRALES_DIAGNOSTICO) | {min_count_elegido})
    filas = []
    for umbral in umbrales:
        elegibles = {p: n for p, n in pares.items() if n >= umbral}
        positivos = sum(
            1 for (a, c), n in elegibles.items()
            if n * n_total > individuales[a] * individuales[c]
        )
        filas.append({
            'umbral_pedidos': umbral,
            'soporte_equivalente': round(umbral / n_total, 8) if n_total else None,
            'pares_frecuentes': len(elegibles),
            'pares_lift_mayor_1': positivos,
            'umbral_elegido': umbral == min_count_elegido,
        })
    return filas, len(pares)


# ---------------------------------------------------------------------------
# Exportación
# ---------------------------------------------------------------------------

def sha256(ruta):
    h = hashlib.sha256()
    with open(ruta, 'rb') as f:
        for bloque in iter(lambda: f.read(1 << 20), b''):
            h.update(bloque)
    return h.hexdigest()


def guardar_csv(df, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding='utf-8-sig', lineterminator='\n')


def tabla_reglas(reglas, ids, n_total, poblacion_analisis='todas'):
    poblacion = descripcion_poblacion(n_total, poblacion_analisis)
    filas = []
    for regla, regla_id in zip(reglas, ids):
        filas.append({
            'regla_id': regla_id,
            'antecedente': SEPARADOR_ITEMS.join(regla['antecedente']),
            'consecuente': SEPARADOR_ITEMS.join(regla['consecuente']),
            'soporte': round(regla['soporte'], 6),
            'confianza': round(regla['confianza'], 6),
            'lift': round(regla['lift'], 6),
            'conviccion': None if regla['conviccion'] is None else round(regla['conviccion'], 6),
            'p_valor': float(f"{regla['p_valor']:.6g}"),
            'n_pedidos': regla['n_pedidos'],
            'n_pedidos_antecedente': regla['n_pedidos_antecedente'],
            'n_pedidos_consecuente': regla['n_pedidos_consecuente'],
            'soporte_antecedente': round(regla['soporte_antecedente'], 6),
            'soporte_consecuente': round(regla['soporte_consecuente'], 6),
            'asociacion_positiva': regla['asociacion_positiva'],
            'total_cestas': n_total,
            'poblacion_referencia': poblacion,
        })
    return pd.DataFrame(filas, columns=COLUMNAS_REGLAS)


def tabla_composicion(c):
    entregados = c['pedidos_entregados']
    universo = c['universo']

    def fila(concepto, valor, en_universo):
        return {
            'concepto': concepto,
            'pedidos': valor,
            'pct_pedidos_entregados': None if valor is None or not entregados
            else round(100 * valor / entregados, 4),
            'pct_universo': round(100 * valor / universo, 4)
            if en_universo and valor is not None and universo else None,
            'en_universo': en_universo,
        }

    return pd.DataFrame([
        fila('pedidos_entregados', entregados, False),
        fila('vacias_sin_items', c['vacias'], False),
        fila('sin_categoria_conocida', c['sin_categoria_conocida'], False),
        fila('unitarias_una_categoria', c['unitarias'], True),
        fila('multicategoria_dos_o_mas', c['multicategoria'], True),
        fila('universo_total', universo, True),
        fila('informativo_unitarias_con_varios_items', c['unitarias_con_varios_items'], True),
    ])


def ejecutar(items_csv, pedidos_csv, output_root, min_pedidos=10, min_soporte=None,
             min_confianza=0.0, max_len=2, repeticiones=5, poblacion='todas', salida=print):
    if poblacion not in POBLACIONES:
        raise ValueError(f'poblacion debe ser una de {POBLACIONES}')
    items = leer_csv(items_csv, COLUMNAS_ITEMS, 'items_procesados.csv')
    pedidos = None
    if Path(pedidos_csv).is_file():
        pedidos = leer_csv(pedidos_csv, COLUMNAS_PEDIDOS, 'pedidos_procesados.csv')
    else:
        salida(f'Aviso: no existe {pedidos_csv}; no se informarán los pedidos vacíos.')

    cestas, composicion = construir_cestas(items, pedidos)
    for aviso in composicion['advertencias']:
        salida(f'Aviso: {aviso}')
    if poblacion == 'multicategoria':
        cestas = {oid: c for oid, c in cestas.items() if len(c) >= 2}
    n_total = len(cestas)
    if n_total == 0:
        raise ValueError('La población de análisis está vacía: no hay cestas con las condiciones pedidas.')
    sufijo = '_multicategoria' if poblacion == 'multicategoria' else ''

    if min_soporte is not None:
        min_count = max(1, math.ceil(min_soporte * n_total - 1e-9))
    else:
        min_count = int(min_pedidos)
    min_soporte_efectivo = min_count / n_total
    transacciones = list(cestas.values())

    resultados = {}
    for nombre, funcion in [('Apriori', apriori), ('FP-Growth', fp_growth)]:
        itemsets, tiempos = medir(funcion, repeticiones, transacciones, min_count, max_len)
        resultados[nombre] = {
            'itemsets': itemsets,
            'reglas': generar_reglas(itemsets, n_total, min_confianza),
            'tiempos': tiempos,
        }
    comparacion = comparar_reglas(resultados['Apriori']['reglas'], resultados['FP-Growth']['reglas'])
    mismos_itemsets = resultados['Apriori']['itemsets'] == resultados['FP-Growth']['itemsets']
    if not (comparacion['coinciden'] and mismos_itemsets):
        salida('ADVERTENCIA: Apriori y FP-Growth no coinciden; revisar antes de usar los resultados.')

    reglas = resultados['Apriori']['reglas']
    ids = [f'AR-{i:03d}' for i in range(1, len(reglas) + 1)]
    indice = indice_multicategoria(cestas)
    filas_trazabilidad = trazabilidad(reglas, ids, indice)
    diagnostico, n_pares_observados = diagnostico_umbrales(cestas, min_count)

    raiz = Path(output_root) / 'resultados'
    guardar_csv(tabla_reglas(reglas, ids, n_total, poblacion), raiz / f'reglas_asociacion{sufijo}.csv')
    guardar_csv(
        pd.DataFrame(filas_trazabilidad, columns=['regla_id', 'order_id']),
        raiz / f'reglas_asociacion_trazabilidad{sufijo}.csv',
    )
    guardar_csv(tabla_composicion(composicion), raiz / 'composicion_cestas.csv')
    guardar_csv(pd.DataFrame(diagnostico), raiz / f'umbrales_asociacion{sufijo}.csv')

    filas_comparacion = []
    for nombre, r in resultados.items():
        filas_comparacion.append({
            'algoritmo': nombre,
            'poblacion': poblacion,
            'conjuntos_frecuentes': len(r['itemsets']),
            'reglas': len(r['reglas']),
            'reglas_en_comun': comparacion['reglas_en_comun'],
            'reglas_con_metricas_iguales': comparacion['reglas_con_metricas_iguales'],
            'coincide_con_el_otro': comparacion['coinciden'] and mismos_itemsets,
            'tiempo_minimo_s': round(min(r['tiempos']), 6),
            'tiempo_mediana_s': round(statistics.median(r['tiempos']), 6),
            'repeticiones': repeticiones,
            'min_pedidos': min_count,
            'min_soporte': round(min_soporte_efectivo, 8),
            'min_confianza': min_confianza,
            'max_len': max_len,
            'total_cestas': n_total,
        })
    guardar_csv(pd.DataFrame(filas_comparacion), raiz / f'comparacion_asociacion{sufijo}.csv')

    metadata = {
        'ejecutado_en_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(),
        'pandas': pd.__version__,
        'items_csv': str(items_csv),
        'items_sha256': sha256(items_csv),
        'poblacion_analisis': poblacion,
        'poblacion_referencia': descripcion_poblacion(n_total, poblacion),
        'total_cestas_analisis': n_total,
        'composicion': {k: v for k, v in composicion.items() if k != 'advertencias'},
        'parametros': {
            'min_pedidos': min_count,
            'min_soporte': min_soporte_efectivo,
            'min_confianza': min_confianza,
            'max_len': max_len,
            'repeticiones_tiempo': repeticiones,
            'aleatoriedad': 'ninguna; los resultados son deterministas',
        },
        'pares_de_categorias_observados': n_pares_observados,
        'reglas': len(reglas),
        'pedidos_rastreados_en_total': len(filas_trazabilidad),
        'algoritmos_coinciden': bool(comparacion['coinciden'] and mismos_itemsets),
    }
    ruta_meta = raiz / f'asociacion_metadata{sufijo}.json'
    ruta_meta.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding='utf-8')

    salida('=' * 64)
    salida(f"Población de análisis: {poblacion} ({n_total} cestas)")
    salida(f"Universo: {composicion['universo']} pedidos (entregados con categoría conocida)")
    salida(f"  unitarias: {composicion['unitarias']} | multicategoría: {composicion['multicategoria']}")
    salida(f"  fuera del universo: vacías={composicion['vacias']}, "
           f"sin categoría conocida={composicion['sin_categoria_conocida']}")
    salida(f'Parámetros: min_pedidos={min_count} (soporte {min_soporte_efectivo:.6f}), '
           f'min_confianza={min_confianza}, max_len={max_len}')
    for fila in filas_comparacion:
        salida(f"{fila['algoritmo']:<10} reglas={fila['reglas']:<5} "
               f"conjuntos={fila['conjuntos_frecuentes']:<5} "
               f"tiempo mínimo={fila['tiempo_minimo_s']:.6f} s")
    salida(f"Coinciden: {metadata['algoritmos_coinciden']}")
    salida(f'Archivos escritos en {raiz}')
    return {
        'composicion': composicion, 'reglas': reglas, 'ids': ids,
        'comparacion': filas_comparacion, 'metadata': metadata, 'min_count': min_count,
        'n_total': n_total,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--items', type=Path,
                        default=ROOT / 'data' / 'processed' / 'items_procesados.csv')
    parser.add_argument('--pedidos', type=Path,
                        default=ROOT / 'data' / 'processed' / 'pedidos_procesados.csv')
    parser.add_argument('--output-root', type=Path, default=ROOT,
                        help='Raíz donde se escribe resultados/.')
    umbral = parser.add_mutually_exclusive_group()
    umbral.add_argument('--min-pedidos', type=int, default=10,
                        help='Número mínimo de pedidos que contienen el conjunto (provisional: '
                             'validar con resultados/umbrales_asociacion.csv).')
    umbral.add_argument('--min-soporte', type=float, default=None,
                        help='Soporte mínimo como proporción del universo (alternativa a --min-pedidos).')
    parser.add_argument('--poblacion', choices=POBLACIONES, default='todas',
                        help="'todas' (principal) o 'multicategoria' (solo cestas de 2 o más categorías; "
                             "archivos con sufijo _multicategoria).")
    parser.add_argument('--min-confianza', type=float, default=0.0)
    parser.add_argument('--max-len', type=int, default=2,
                        help='Tamaño máximo del conjunto (2 = reglas entre pares de categorías).')
    parser.add_argument('--repeticiones', type=int, default=5,
                        help='Veces que se mide cada algoritmo.')
    args = parser.parse_args(argv)

    if args.min_pedidos < 1:
        parser.error('--min-pedidos debe ser al menos 1.')
    if args.min_soporte is not None and not 0 < args.min_soporte <= 1:
        parser.error('--min-soporte debe estar entre 0 y 1.')
    if not 0 <= args.min_confianza <= 1:
        parser.error('--min-confianza debe estar entre 0 y 1.')
    if args.max_len < 2:
        parser.error('--max-len debe ser al menos 2.')
    if args.repeticiones < 1:
        parser.error('--repeticiones debe ser al menos 1.')

    ejecutar(args.items, args.pedidos, args.output_root, args.min_pedidos, args.min_soporte,
             args.min_confianza, args.max_len, args.repeticiones, args.poblacion)


if __name__ == '__main__':
    main()
