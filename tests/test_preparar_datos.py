"""Casos pequeños de negocio: evita depender del ZIP privado para probar."""

from contextlib import redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
from tempfile import TemporaryDirectory
import unittest
from zipfile import ZipFile

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from esquema_olist import ARCHIVOS, ESQUEMA
from preparar_datos import (
    construir_items, construir_pedidos, diccionario_original, diccionario_procesados,
    distancia_haversine, ejecutar, limpiar_tablas, preparar_geolocalizacion,
    validar_entradas, validar_resultados,
)


def datos_ejemplo():
    """Dos ítems, dos pagos y dos reseñas en A revelarían un join cartesiano.

    B no tiene detalles. C tiene entrega anterior a la compra. D está marcado
    como entregado sin fecha. Una categoría no tiene traducción y otra falta.
    """
    filas = {
        'clientes': [
            {'customer_id': f'c{x}', 'customer_unique_id': f'u{x}',
             'customer_zip_code_prefix': '00100', 'customer_city': 'Ciudad', 'customer_state': 'SP'}
            for x in 'abcd'
        ],
        'geolocalizacion': [
            {'geolocation_zip_code_prefix': '00100', 'geolocation_lat': lat,
             'geolocation_lng': '-40', 'geolocation_city': 'Ciudad', 'geolocation_state': 'SP'}
            for lat in ['-10', '-10', '-20']
        ] + [
            {'geolocation_zip_code_prefix': '00300', 'geolocation_lat': '95',
             'geolocation_lng': '-40', 'geolocation_city': 'Otra', 'geolocation_state': 'RJ'},
        ],
        'detalles': [
            {'order_id': pedido, 'order_item_id': numero, 'product_id': producto,
             'seller_id': vendedor, 'shipping_limit_date': '2020-01-02 00:00:00',
             'price': precio, 'freight_value': '5'}
            for pedido, numero, producto, vendedor, precio in [
                ('a', '1', 'p1', 's1', '100'), ('a', '2', 'p2', 's2', '50'),
                ('c', '1', 'p3', 's1', '20'), ('d', '1', 'p1', 's1', '30'),
            ]
        ],
        'pagos': [
            {'order_id': 'a', 'payment_sequential': secuencia, 'payment_type': 'credit_card',
             'payment_installments': cuotas, 'payment_value': valor}
            for secuencia, cuotas, valor in [('1', '2', '100'), ('2', '0', '60')]
        ],
        'opiniones': [
            {'review_id': f'r{i}', 'order_id': 'a', 'review_score': score,
             'review_creation_date': '2020-01-04 00:00:00',
             'review_answer_timestamp': '2020-01-05 12:00:00'}
            for i, score in enumerate(['1', '5'])
        ],
        'pedidos': [
            {'order_id': x, 'customer_id': f'c{x}', 'order_status': estado,
             'order_purchase_timestamp': '2020-01-01 12:00:00',
             'order_approved_at': '2020-01-01 13:00:00',
             'order_delivered_carrier_date': '2020-01-02 12:00:00',
             'order_delivered_customer_date': entrega,
             'order_estimated_delivery_date': '2020-01-03 00:00:00'}
            for x, estado, entrega in [
                ('a', 'delivered', '2020-01-03 21:00:00'), ('b', 'canceled', pd.NA),
                ('c', 'delivered', '2019-12-31 12:00:00'), ('d', 'delivered', pd.NA),
            ]
        ],
        'productos': [
            {'product_id': producto, 'product_category_name': categoria,
             'product_name_lenght': '10', 'product_description_lenght': '20',
             'product_photos_qty': '1', 'product_weight_g': '100',
             'product_length_cm': largo, 'product_height_cm': '2', 'product_width_cm': '3'}
            for producto, categoria, largo in [('p1', 'cat_a', '10'), ('p2', 'cat_b', '10'), ('p3', pd.NA, '0')]
        ],
        'vendedores': [
            {'seller_id': vendedor, 'seller_zip_code_prefix': postal,
             'seller_city': 'Ciudad', 'seller_state': 'SP'}
            for vendedor, postal in [('s1', '00100'), ('s2', '99999')]
        ],
        'categorias': [{'product_category_name': 'cat_a', 'product_category_name_english': 'Category A'}],
    }
    return {nombre: pd.DataFrame(filas[nombre], columns=list(campos), dtype='string')
            for nombre, campos in ESQUEMA.items()}


class PreparacionTests(unittest.TestCase):
    def setUp(self):
        self.originales = datos_ejemplo()
        self.incidencias = []
        self.tablas = limpiar_tablas(self.originales, self.incidencias)
        self.geo_limpia, self.geo = preparar_geolocalizacion(self.tablas['geolocalizacion'], self.incidencias)
        self.items = construir_items(self.tablas, self.geo, self.incidencias)
        self.pedidos = construir_pedidos(self.tablas, self.items, self.geo, self.incidencias)

    def test_agregaciones_evitan_multiplicacion_de_importes(self):
        a = self.pedidos.set_index('order_id').loc['a']
        self.assertEqual(len(self.pedidos), 4)
        self.assertEqual(len(self.items), 4)
        self.assertEqual(a['valor_articulos'], 150)
        self.assertEqual(a['valor_flete'], 10)
        self.assertEqual(a['valor_pagado'], 160)
        self.assertEqual(a['cantidad_items'], 2)
        self.assertEqual(a['cantidad_registros_pago'], 2)
        self.assertEqual(a['cantidad_resenas'], 2)
        self.assertEqual(a['calificacion_media'], 3)
        self.assertTrue(a['cuotas_cero'])
        controles = validar_entradas(self.tablas, self.incidencias)
        controles += validar_resultados(self.tablas, self.pedidos, self.items, self.geo)
        self.assertTrue(all(c['resultado'] == 'OK' for c in controles))

    def test_ausencia_no_se_imputa_como_importe_o_puntuacion_cero(self):
        b = self.pedidos.set_index('order_id').loc['b']
        self.assertTrue(b['sin_items'])
        self.assertTrue(b['sin_pago'])
        self.assertTrue(b['sin_resenas'])
        self.assertEqual(b['cantidad_items'], 0)
        for campo in ['valor_articulos', 'valor_flete', 'valor_pagado', 'calificacion_media', 'cuotas_cero']:
            self.assertTrue(pd.isna(b[campo]), campo)

    def test_tiempo_fraccionario_y_puntualidad_por_dia_calendario(self):
        a = self.pedidos.set_index('order_id').loc['a']
        self.assertEqual(a['dias_entrega'], 2.375)
        self.assertEqual(a['dias_retraso_calendario'], 0)
        self.assertFalse(a['entrega_tardia'])
        self.assertFalse(a['entrega_antes_compra'])

    def test_fechas_invalidas_para_objetivo_se_conservan_con_bandera(self):
        pedidos = self.pedidos.set_index('order_id')
        self.assertTrue(pedidos.loc['c', 'entrega_antes_compra'])
        self.assertTrue(pedidos.loc['c', 'despacho_despues_entrega'])
        for pedido in ['b', 'c', 'd']:
            self.assertTrue(pd.isna(pedidos.loc[pedido, 'dias_entrega']))
            self.assertTrue(pd.isna(pedidos.loc[pedido, 'entrega_tardia']))
        self.assertTrue(pedidos.loc['d', 'es_entregado'])
        self.assertFalse(pedidos.loc['d', 'tiene_fecha_entrega'])

    def test_retraso_positivo_y_fecha_prometida_ausente(self):
        self.tablas['pedidos'].loc[0, 'order_delivered_customer_date'] = pd.Timestamp('2020-01-04 21:00:00')
        pedidos = construir_pedidos(self.tablas, self.items, self.geo, [])
        a = pedidos.set_index('order_id').loc['a']
        self.assertEqual(a['dias_retraso_calendario'], 1)
        self.assertTrue(a['entrega_tardia'])
        self.tablas['pedidos'].loc[0, 'order_estimated_delivery_date'] = pd.NaT
        pedidos = construir_pedidos(self.tablas, self.items, self.geo, [])
        a = pedidos.set_index('order_id').loc['a']
        self.assertFalse(pd.isna(a['dias_entrega']))
        self.assertTrue(pd.isna(a['entrega_tardia']))

    def test_mediana_sin_peso_artificial_de_duplicados_y_par_invalido(self):
        geo = self.geo.set_index('geolocation_zip_code_prefix')
        self.assertEqual(geo.loc['00100', 'latitud_mediana'], -15)
        self.assertEqual(geo.loc['00100', 'cantidad_observaciones'], 2)
        self.assertEqual(geo.loc['00300', 'cantidad_coordenadas_validas'], 0)
        self.assertTrue(pd.isna(geo.loc['00300', 'latitud_mediana']))
        self.assertTrue(pd.isna(geo.loc['00300', 'longitud_mediana']))
        conocido = self.items.loc[self.items['seller_id'].eq('s1'), 'distancia_km']
        self.assertTrue(conocido.eq(0).all())
        desconocido = self.items.loc[self.items['seller_id'].eq('s2'), 'distancia_km']
        self.assertTrue(desconocido.isna().all())

    def test_distancia_tiene_escala_geografica_correcta(self):
        puntos = pd.DataFrame({'customer_lat': [0], 'customer_lng': [0], 'seller_lat': [0], 'seller_lng': [1]})
        self.assertAlmostEqual(distancia_haversine(puntos).iloc[0], 111.195, places=3)

    def test_categorias_y_dimensiones_no_se_inventan(self):
        items = self.items.set_index('product_id')
        self.assertTrue(items.loc['p2', 'sin_traduccion'])
        self.assertFalse(items.loc['p2', 'sin_categoria'])
        self.assertEqual(items.loc['p3', 'categoria_presentacion'], 'Sin categoría')
        self.assertTrue(pd.isna(items.loc['p3', 'product_category_name']))
        self.assertTrue(items.loc['p3', 'datos_fisicos_invalidos'])
        self.assertTrue(pd.isna(items.loc['p3', 'volumen_cm3']))

    def test_conversiones_invalidas_se_registran_y_bloquean(self):
        originales = datos_ejemplo()
        originales['pagos'].loc[0, 'payment_installments'] = '1.5'
        originales['clientes'].loc[0, 'customer_zip_code_prefix'] = 'ABCDE'
        originales['pedidos'].loc[0, 'order_purchase_timestamp'] = 'fecha imposible'
        incidencias = []
        tablas = limpiar_tablas(originales, incidencias)
        errores = [i for i in incidencias if i['regla'] == 'conversion_invalida']
        self.assertEqual(len(errores), 3)
        self.assertTrue(any(i['valor_original'] == '1.5' for i in errores))
        controles = validar_entradas(tablas, incidencias)
        self.assertTrue(any(c['control'] == 'conversiones_invalidas' and c['resultado'] == 'ERROR' for c in controles))

    def test_claves_duplicadas_y_referencias_huerfanas_se_detectan(self):
        self.tablas['detalles'].loc[1, ['order_id', 'order_item_id']] = ['a', 1]
        self.tablas['detalles'].loc[0, 'seller_id'] = 'vendedor_inexistente'
        controles = {c['control']: c['resultado'] for c in validar_entradas(self.tablas, [])}
        self.assertEqual(controles['clave_unica_detalles'], 'ERROR')
        self.assertEqual(controles['referencia_detalles_seller_id_vendedores'], 'ERROR')

    def test_diccionarios_cubren_campos_y_procedencia(self):
        original = diccionario_original(self.originales, self.tablas)
        self.assertEqual(len(original), 52)
        diccionario = diccionario_procesados({'pedidos_procesados': self.pedidos,
                                              'items_procesados': self.items,
                                              'geolocalizacion_agrupada': self.geo})
        self.assertEqual(len(diccionario), sum(len(df.columns) for df in [self.pedidos, self.items, self.geo]))
        categoria = diccionario.loc[diccionario['tabla'].eq('items_procesados')
                                    & diccionario['columna'].eq('product_category_name')].iloc[0]
        self.assertIn('productos.product_category_name', categoria['formula_o_fuente'])
        objetivo = diccionario.loc[diccionario['columna'].eq('dias_entrega')].iloc[0]
        self.assertEqual(objetivo['uso_recomendado'], 'objetivo_regresion')

    def test_exportacion_reproducible_y_rechazo_de_entradas_invalidas(self):
        with TemporaryDirectory() as temporal:
            raiz = Path(temporal)
            zip_path = raiz / 'archive.zip'
            with ZipFile(zip_path, 'w') as archivo:
                for nombre, df in self.originales.items():
                    archivo.writestr(ARCHIVOS[nombre], df.to_csv(index=False))
            with redirect_stdout(io.StringIO()):
                primera = ejecutar(zip_path, raiz / 'primera')
                segunda = ejecutar(zip_path, raiz / 'segunda')
            self.assertEqual(primera['sha256_origen'], segunda['sha256_origen'])
            self.assertEqual(primera['controles_error'], 0)
            for ruta in (raiz / 'primera').rglob('*.csv'):
                otra = raiz / 'segunda' / ruta.relative_to(raiz / 'primera')
                self.assertEqual(hashlib.sha256(ruta.read_bytes()).hexdigest(),
                                 hashlib.sha256(otra.read_bytes()).hexdigest(), str(ruta))
            geo = pd.read_csv(raiz / 'primera/data/processed/geolocalizacion_agrupada.csv',
                              dtype={'geolocation_zip_code_prefix': 'string'}, encoding='utf-8-sig')
            self.assertEqual(geo.iloc[0]['geolocation_zip_code_prefix'], '00100')
            metadata = json.loads((raiz / 'primera/resultados/calidad/metadata.json').read_text())
            self.assertEqual(metadata['filas_salida']['pedidos_procesados'], 4)
            originales = datos_ejemplo()
            originales['detalles'].loc[0, 'price'] = '-1'
            with ZipFile(zip_path, 'w') as archivo:
                for nombre, df in originales.items():
                    archivo.writestr(ARCHIVOS[nombre], df.to_csv(index=False))
            with self.assertRaisesRegex(ValueError, 'validación de entradas'):
                ejecutar(zip_path, raiz / 'invalida')
            self.assertFalse((raiz / 'invalida/data/processed').exists())
            self.assertTrue((raiz / 'invalida/resultados/calidad/incidencias.csv').is_file())


if __name__ == '__main__':
    unittest.main()
