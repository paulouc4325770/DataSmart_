"""Pruebas de asociación con cestas pequeñas; no requieren descargar Olist."""

from itertools import combinations
import json
from math import comb
from pathlib import Path
import random
import sys
from tempfile import TemporaryDirectory
import unittest

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from asociacion import (
    apriori, comparar_reglas, construir_cestas, diagnostico_umbrales, ejecutar, fp_growth,
    generar_reglas, indice_multicategoria, p_hipergeometrico, pedidos_de_regla, trazabilidad,
)


def fuerza_bruta(cestas, min_count, max_len):
    """Referencia: cuenta todos los subconjuntos posibles de cada cesta."""
    conteo = {}
    for cesta in cestas:
        for k in range(1, min(max_len, len(cesta)) + 1):
            for comb in combinations(cesta, k):
                conteo[frozenset(comb)] = conteo.get(frozenset(comb), 0) + 1
    return {c: n for c, n in conteo.items() if n >= min_count}


def cestas_aleatorias(semilla, n=300, categorias=12):
    azar = random.Random(semilla)
    nombres = [f'cat_{i:02d}' for i in range(categorias)]
    cestas = []
    for _ in range(n):
        tamano = azar.choices([1, 2, 3, 4, 5], weights=[60, 22, 10, 5, 3])[0]
        cestas.append(tuple(sorted(azar.sample(nombres, tamano))))
    return cestas


def items_ejemplo():
    """Pedidos entregados y no entregados, con categorías repetidas y desconocidas."""
    filas = [
        # P1: dos categorías distintas
        ('P1', 'delivered', 'cama', 'False'), ('P1', 'delivered', 'deco', 'False'),
        # P2: dos ítems de la misma categoría -> unitaria con varios ítems
        ('P2', 'delivered', 'cama', 'False'), ('P2', 'delivered', 'cama', 'False'),
        # P3: unitaria
        ('P3', 'delivered', 'deco', 'False'),
        # P4: cama + deco + categoría desconocida -> multicategoría (la desconocida se ignora)
        ('P4', 'delivered', 'cama', 'False'), ('P4', 'delivered', 'deco', 'False'),
        ('P4', 'delivered', 'Sin categoría', 'True'),
        # P5: solo categoría desconocida -> fuera del universo
        ('P5', 'delivered', 'Sin categoría', 'True'),
        # P6: cancelado, no debe contar
        ('P6', 'canceled', 'cama', 'False'), ('P6', 'canceled', 'deco', 'False'),
        # P7: unitaria
        ('P7', 'delivered', 'cama', 'False'),
    ]
    return pd.DataFrame(filas, columns=['order_id', 'order_status', 'categoria_presentacion', 'sin_categoria'],
                        dtype='string')


def pedidos_ejemplo():
    filas = [
        ('P1', 'True', 'False'), ('P2', 'True', 'False'), ('P3', 'True', 'False'),
        ('P4', 'True', 'False'), ('P5', 'True', 'False'), ('P6', 'False', 'False'),
        ('P7', 'True', 'False'), ('P8', 'True', 'True'),  # P8: entregado sin ítems
        ('P9', 'False', 'True'),
    ]
    return pd.DataFrame(filas, columns=['order_id', 'es_entregado', 'sin_items'], dtype='string')


class PruebasAlgoritmos(unittest.TestCase):
    def test_coinciden_con_fuerza_bruta(self):
        for semilla in range(5):
            cestas = cestas_aleatorias(semilla)
            for min_count in (1, 3, 10):
                for max_len in (2, 3, 4):
                    esperado = fuerza_bruta(cestas, min_count, max_len)
                    self.assertEqual(apriori(cestas, min_count, max_len), esperado,
                                     f'apriori semilla={semilla} min={min_count} len={max_len}')
                    self.assertEqual(fp_growth(cestas, min_count, max_len), esperado,
                                     f'fp_growth semilla={semilla} min={min_count} len={max_len}')

    def test_umbral_sin_conjuntos_frecuentes(self):
        cestas = [('a',), ('b',), ('a', 'b')]
        self.assertEqual(apriori(cestas, 5, 2), {})
        self.assertEqual(fp_growth(cestas, 5, 2), {})

    def test_reglas_iguales_entre_algoritmos(self):
        cestas = cestas_aleatorias(11)
        ra = generar_reglas(apriori(cestas, 3, 3), len(cestas), 0.0)
        rf = generar_reglas(fp_growth(cestas, 3, 3), len(cestas), 0.0)
        self.assertTrue(comparar_reglas(ra, rf)['coinciden'])
        self.assertGreater(len(ra), 0)


class PruebasReglas(unittest.TestCase):
    def test_metricas_calculadas_a_mano(self):
        # 10 cestas: A en 4, B en 5, A y B juntos en 2.
        cestas = [('A', 'B')] * 2 + [('A',)] * 2 + [('B',)] * 3 + [('C',)] * 3
        reglas = generar_reglas(apriori(cestas, 1, 2), len(cestas), 0.0)
        a_b = next(r for r in reglas if r['antecedente'] == ('A',) and r['consecuente'] == ('B',))
        self.assertEqual(a_b['n_pedidos'], 2)
        self.assertAlmostEqual(a_b['soporte'], 0.2)
        self.assertAlmostEqual(a_b['confianza'], 0.5)           # 2 / 4
        self.assertAlmostEqual(a_b['lift'], 1.0)                # 0.5 / (5/10)
        self.assertFalse(a_b['asociacion_positiva'])
        b_a = next(r for r in reglas if r['antecedente'] == ('B',) and r['consecuente'] == ('A',))
        self.assertAlmostEqual(b_a['confianza'], 0.4)           # 2 / 5
        self.assertAlmostEqual(b_a['lift'], 1.0)

    def test_cestas_unitarias_permanecen_en_el_denominador(self):
        con_unitarias = [('A', 'B')] * 2 + [('A',)] * 8
        sin_unitarias = [('A', 'B')] * 2
        r1 = generar_reglas(apriori(con_unitarias, 1, 2), len(con_unitarias), 0.0)
        r2 = generar_reglas(apriori(sin_unitarias, 1, 2), len(sin_unitarias), 0.0)
        self.assertAlmostEqual(r1[0]['soporte'], 0.2)
        self.assertAlmostEqual(r2[0]['soporte'], 1.0)

    def test_confianza_minima_filtra(self):
        cestas = [('A', 'B')] * 2 + [('A',)] * 8
        reglas = generar_reglas(apriori(cestas, 1, 2), len(cestas), 0.5)
        self.assertEqual([(r['antecedente'], r['consecuente']) for r in reglas], [(('B',), ('A',))])

    def test_conviccion_nula_con_confianza_uno(self):
        cestas = [('A', 'B')] * 3 + [('A',)] * 3
        reglas = generar_reglas(apriori(cestas, 1, 2), len(cestas), 0.0)
        b_a = next(r for r in reglas if r['antecedente'] == ('B',))
        self.assertEqual(b_a['confianza'], 1.0)
        self.assertIsNone(b_a['conviccion'])


class PruebasCestas(unittest.TestCase):
    def test_poblacion_y_composicion(self):
        cestas, c = construir_cestas(items_ejemplo(), pedidos_ejemplo())
        self.assertEqual(set(cestas), {'P1', 'P2', 'P3', 'P4', 'P7'})
        self.assertEqual(cestas['P1'], ('cama', 'deco'))
        self.assertEqual(cestas['P2'], ('cama',))                # categoría repetida: una sola
        self.assertEqual(cestas['P4'], ('cama', 'deco'))         # «Sin categoría» no es ítem
        self.assertEqual(c['pedidos_entregados'], 7)             # P1-P5, P7, P8
        self.assertEqual(c['vacias'], 1)                         # P8
        self.assertEqual(c['sin_categoria_conocida'], 1)         # P5
        self.assertEqual(c['unitarias'], 3)                      # P2, P3, P7
        self.assertEqual(c['multicategoria'], 2)                 # P1, P4
        self.assertEqual(c['universo'], 5)
        self.assertEqual(c['unitarias_con_varios_items'], 1)     # P2
        self.assertEqual(c['advertencias'], [])
        # La composición cierra: entregados = vacías + sin categoría conocida + universo.
        self.assertEqual(c['pedidos_entregados'],
                         c['vacias'] + c['sin_categoria_conocida'] + c['universo'])

    def test_sin_archivo_de_pedidos(self):
        _, c = construir_cestas(items_ejemplo(), None)
        self.assertIsNone(c['vacias'])
        self.assertEqual(c['pedidos_entregados'], 6)             # P1-P5, P7 con ítems

    def test_advierte_si_no_concilian_pedidos_e_items(self):
        pedidos = pedidos_ejemplo()
        pedidos = pedidos[pedidos['order_id'] != 'P7']
        _, c = construir_cestas(items_ejemplo(), pedidos)
        self.assertEqual(len(c['advertencias']), 1)


class PruebasTrazabilidad(unittest.TestCase):
    def test_cada_regla_se_rastrea_hasta_sus_pedidos(self):
        cestas, _ = construir_cestas(items_ejemplo(), pedidos_ejemplo())
        reglas = generar_reglas(apriori(list(cestas.values()), 1, 2), len(cestas), 0.0)
        ids = [f'AR-{i:03d}' for i in range(1, len(reglas) + 1)]
        indice = indice_multicategoria(cestas)
        self.assertEqual(pedidos_de_regla(reglas[0], indice), ['P1', 'P4'])
        filas = trazabilidad(reglas, ids, indice)
        self.assertEqual(len(filas), 2 * len(reglas))
        self.assertEqual({oid for _, oid in filas}, {'P1', 'P4'})

    def test_error_si_n_pedidos_no_coincide(self):
        cestas = {'P1': ('A', 'B'), 'P2': ('A', 'B')}
        regla = {'antecedente': ('A',), 'consecuente': ('B',), 'n_pedidos': 5}
        with self.assertRaises(RuntimeError):
            trazabilidad([regla], ['AR-001'], indice_multicategoria(cestas))

    def test_diagnostico_de_umbrales(self):
        cestas = {f'P{i}': ('A', 'B') for i in range(6)}
        cestas.update({f'U{i}': ('A',) for i in range(14)})
        filas, n_pares = diagnostico_umbrales(cestas, 5)
        self.assertEqual(n_pares, 1)
        por_umbral = {f['umbral_pedidos']: f for f in filas}
        self.assertEqual(por_umbral[5]['pares_frecuentes'], 1)
        self.assertTrue(por_umbral[5]['umbral_elegido'])
        self.assertEqual(por_umbral[10]['pares_frecuentes'], 0)


class PruebaDeExtremoAExtremo(unittest.TestCase):
    def test_exporta_archivos_coherentes(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            items = items_ejemplo()
            items.to_csv(tmp / 'items.csv', index=False, encoding='utf-8-sig')
            pedidos_ejemplo().to_csv(tmp / 'pedidos.csv', index=False, encoding='utf-8-sig')
            mensajes = []
            r = ejecutar(tmp / 'items.csv', tmp / 'pedidos.csv', tmp, min_pedidos=2,
                         repeticiones=2, salida=mensajes.append)
            res = tmp / 'resultados'
            for nombre in ['reglas_asociacion.csv', 'reglas_asociacion_trazabilidad.csv',
                           'comparacion_asociacion.csv', 'composicion_cestas.csv',
                           'umbrales_asociacion.csv', 'asociacion_metadata.json']:
                self.assertTrue((res / nombre).is_file(), nombre)

            reglas = pd.read_csv(res / 'reglas_asociacion.csv', encoding='utf-8-sig')
            self.assertEqual(len(reglas), 2)
            self.assertTrue((reglas['total_cestas'] == 5).all())
            self.assertTrue(reglas['poblacion_referencia'].str.contains('N=5').all())
            self.assertAlmostEqual(reglas.loc[0, 'soporte'], 0.4)      # 2 de 5 cestas
            self.assertAlmostEqual(reglas.loc[0, 'lift'], round(2 * 5 / (4 * 3), 6))

            traza = pd.read_csv(res / 'reglas_asociacion_trazabilidad.csv', encoding='utf-8-sig')
            por_regla = traza.groupby('regla_id').size()
            for _, fila in reglas.iterrows():
                self.assertEqual(por_regla[fila['regla_id']], fila['n_pedidos'])

            comp = pd.read_csv(res / 'comparacion_asociacion.csv', encoding='utf-8-sig')
            self.assertEqual(list(comp['algoritmo']), ['Apriori', 'FP-Growth'])
            self.assertTrue(comp['coincide_con_el_otro'].all())
            self.assertTrue((comp['reglas'] == 2).all())

            meta = json.loads((res / 'asociacion_metadata.json').read_text(encoding='utf-8'))
            self.assertTrue(meta['algoritmos_coinciden'])
            self.assertEqual(meta['composicion']['universo'], 5)
            self.assertEqual(r['min_count'], 2)

    def test_error_claro_si_falta_el_archivo(self):
        with TemporaryDirectory() as tmp:
            with self.assertRaises(FileNotFoundError):
                ejecutar(Path(tmp) / 'no_existe.csv', Path(tmp) / 'p.csv', tmp, salida=lambda *_: None)


def p_exacto(n_ac, n_total, n_a, n_c):
    """Referencia con enteros exactos: P(X >= n_ac), X ~ Hipergeométrica."""
    return sum(comb(n_a, x) * comb(n_total - n_a, n_c - x)
               for x in range(n_ac, min(n_a, n_c) + 1)) / comb(n_total, n_c)


class PruebasPValor(unittest.TestCase):
    def test_coincide_con_el_calculo_exacto(self):
        for n_ac, n_total, n_a, n_c in [(2, 10, 4, 5), (1, 10, 4, 5), (0, 10, 4, 5),
                                       (4, 10, 4, 5), (3, 50, 10, 12), (7, 200, 40, 30)]:
            self.assertAlmostEqual(p_hipergeometrico(n_ac, n_total, n_a, n_c),
                                   p_exacto(n_ac, n_total, n_a, n_c), places=12)

    def test_caso_real_cama_casa_conforto(self):
        # 43 pedidos observados; 38,2 esperados bajo independencia (N=95.146).
        self.assertAlmostEqual(p_hipergeometrico(43, 95146, 9272, 392), 0.2283, places=3)

    def test_es_simetrico_y_acotado(self):
        self.assertEqual(p_hipergeometrico(5, 100, 20, 30), p_hipergeometrico(5, 100, 30, 20))
        self.assertEqual(p_hipergeometrico(11, 100, 10, 30), 0.0)       # imposible
        self.assertAlmostEqual(p_hipergeometrico(2, 2, 2, 2), 1.0)

    def test_las_reglas_incluyen_el_p_valor(self):
        cestas = [('A', 'B')] * 2 + [('A',)] * 2 + [('B',)] * 3 + [('C',)] * 3
        reglas = generar_reglas(apriori(cestas, 1, 2), len(cestas), 0.0)
        a_b = next(r for r in reglas if r['antecedente'] == ('A',))
        self.assertAlmostEqual(a_b['p_valor'], p_exacto(2, 10, 4, 5), places=12)
        b_a = next(r for r in reglas if r['antecedente'] == ('B',) and r['consecuente'] == ('A',))
        self.assertEqual(a_b['p_valor'], b_a['p_valor'])


class PruebaPoblacionMulticategoria(unittest.TestCase):
    def preparar(self, tmp):
        items_ejemplo().to_csv(tmp / 'items.csv', index=False, encoding='utf-8-sig')
        pedidos_ejemplo().to_csv(tmp / 'pedidos.csv', index=False, encoding='utf-8-sig')

    def test_analisis_complementario_con_su_propia_poblacion(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.preparar(tmp)
            ejecutar(tmp / 'items.csv', tmp / 'pedidos.csv', tmp, min_pedidos=2,
                     repeticiones=1, salida=lambda *_: None)
            r = ejecutar(tmp / 'items.csv', tmp / 'pedidos.csv', tmp, min_pedidos=2,
                         repeticiones=1, poblacion='multicategoria', salida=lambda *_: None)
            res = tmp / 'resultados'

            self.assertEqual(r['n_total'], 2)                         # solo P1 y P4
            multi = pd.read_csv(res / 'reglas_asociacion_multicategoria.csv', encoding='utf-8-sig')
            self.assertEqual(len(multi), 2)
            self.assertTrue((multi['total_cestas'] == 2).all())
            self.assertTrue(multi['poblacion_referencia'].str.contains('2 o más categorías').all())
            self.assertTrue(multi['poblacion_referencia'].str.contains('N=2').all())
            self.assertTrue((multi['confianza'] == 1.0).all())
            self.assertTrue((multi['lift'] == 1.0).all())

            # El análisis principal no se sobrescribe.
            principal = pd.read_csv(res / 'reglas_asociacion.csv', encoding='utf-8-sig')
            self.assertTrue((principal['total_cestas'] == 5).all())
            self.assertIn('p_valor', principal.columns)

            traza = pd.read_csv(res / 'reglas_asociacion_trazabilidad_multicategoria.csv',
                                encoding='utf-8-sig')
            self.assertEqual(set(traza['order_id']), {'P1', 'P4'})
            comp = pd.read_csv(res / 'comparacion_asociacion_multicategoria.csv', encoding='utf-8-sig')
            self.assertTrue((comp['poblacion'] == 'multicategoria').all())
            self.assertTrue(comp['coincide_con_el_otro'].all())
            meta = json.loads((res / 'asociacion_metadata_multicategoria.json').read_text(encoding='utf-8'))
            self.assertEqual(meta['poblacion_analisis'], 'multicategoria')
            self.assertEqual(meta['total_cestas_analisis'], 2)
            self.assertEqual(meta['composicion']['universo'], 5)

    def test_poblacion_invalida_y_vacia(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            self.preparar(tmp)
            with self.assertRaises(ValueError):
                ejecutar(tmp / 'items.csv', tmp / 'pedidos.csv', tmp, poblacion='otra',
                         salida=lambda *_: None)
            solo_unitarias = items_ejemplo()
            solo_unitarias = solo_unitarias[solo_unitarias['order_id'].isin(['P2', 'P3', 'P7'])]
            solo_unitarias.to_csv(tmp / 'unitarias.csv', index=False, encoding='utf-8-sig')
            with self.assertRaises(ValueError):
                ejecutar(tmp / 'unitarias.csv', tmp / 'pedidos.csv', tmp, poblacion='multicategoria',
                         salida=lambda *_: None)


if __name__ == '__main__':
    unittest.main()
