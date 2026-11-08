"""Preparación reproducible de Olist: datos, diccionarios y auditoría.

Ejecutar: python src/preparar_datos.py
Las rutas por defecto son relativas al proyecto, no al directorio de ejecución.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
from math import asin, cos, isclose, radians, sin, sqrt
from pathlib import Path
import platform
from zipfile import BadZipFile, ZipFile

import pandas as pd

from esquema_olist import ARCHIVOS, CLAVES, ESQUEMA, RELACIONES


ROOT = Path(__file__).resolve().parents[1]
INCIDENCIA_COLUMNAS = [
    'tabla', 'registro', 'columna', 'regla', 'valor_original', 'tratamiento', 'afectados',
]
PERFIL_COLUMNAS = [
    'tabla', 'filas', 'columnas', 'columna', 'tipo', 'nulos', 'porcentaje_nulos',
    'valores_distintos', 'filas_duplicadas_exactas', 'duplicados_clave',
]
CONTADORES = [
    'cantidad_items', 'cantidad_productos', 'cantidad_vendedores',
    'cantidad_registros_pago', 'cantidad_resenas',
]
FISICOS = ['product_weight_g', 'product_length_cm', 'product_height_cm', 'product_width_cm']

# Descripción, fórmula/origen, unidad, disponibilidad y uso recomendado.
DERIVADAS = {
    'categoria_presentacion': ('Categoría para reportes; no sustituye el valor original.', 'product_category_name.fillna("Sin categoría")', 'categoría', 'catalogo', 'descriptor'),
    'sin_categoria': ('Producto sin categoría original.', 'product_category_name.isna()', 'booleano', 'catalogo', 'auditoria'),
    'sin_traduccion': ('Categoría conocida sin traducción al inglés.', 'categoría no nula y traducción nula', 'booleano', 'catalogo', 'auditoria'),
    'datos_fisicos_incompletos': ('Falta al menos una dimensión o el peso.', 'isna en peso, largo, alto o ancho', 'booleano', 'catalogo', 'auditoria'),
    'datos_fisicos_invalidos': ('Algún peso o dimensión conocido es menor o igual a cero.', 'any(valor físico <= 0)', 'booleano', 'catalogo', 'auditoria'),
    'volumen_cm3': ('Volumen calculado del paquete; nulo si faltan dimensiones o son inválidas.', 'largo * alto * ancho, con dimensiones > 0', 'cm³', 'catalogo', 'candidato_predictor'),
    'latitud_mediana': ('Latitud representativa del prefijo postal.', 'mediana de pares de coordenadas válidos tras deduplicar filas', 'grados decimales', 'catalogo', 'descriptor'),
    'longitud_mediana': ('Longitud representativa del prefijo postal.', 'mediana de pares de coordenadas válidos tras deduplicar filas', 'grados decimales', 'catalogo', 'descriptor'),
    'cantidad_observaciones': ('Observaciones del prefijo tras deduplicar, incluidas las de coordenadas inválidas.', 'size por prefijo postal', 'observaciones', 'catalogo', 'auditoria'),
    'cantidad_coordenadas_validas': ('Observaciones con latitud y longitud válidas simultáneamente.', 'sum(coordenadas_validas) por prefijo', 'observaciones', 'catalogo', 'auditoria'),
    'coordenadas_validas': ('Ambas coordenadas están presentes y dentro de sus rangos geográficos.', 'latitud en [-90,90] y longitud en [-180,180]', 'booleano', 'catalogo', 'auditoria'),
    'customer_lat': ('Latitud mediana del prefijo del cliente.', 'geolocalizacion_agrupada.latitud_mediana', 'grados decimales', 'catalogo', 'candidato_predictor'),
    'customer_lng': ('Longitud mediana del prefijo del cliente.', 'geolocalizacion_agrupada.longitud_mediana', 'grados decimales', 'catalogo', 'candidato_predictor'),
    'seller_lat': ('Latitud mediana del prefijo del vendedor.', 'geolocalizacion_agrupada.latitud_mediana', 'grados decimales', 'catalogo', 'candidato_predictor'),
    'seller_lng': ('Longitud mediana del prefijo del vendedor.', 'geolocalizacion_agrupada.longitud_mediana', 'grados decimales', 'catalogo', 'candidato_predictor'),
    'sin_geolocalizacion_cliente': ('No hay par de coordenadas utilizable para el cliente.', 'customer_lat o customer_lng nulo', 'booleano', 'catalogo', 'auditoria'),
    'sin_geolocalizacion_vendedor': ('No hay par de coordenadas utilizable para el vendedor.', 'seller_lat o seller_lng nulo', 'booleano', 'catalogo', 'auditoria'),
    'distancia_km': ('Distancia aproximada en línea recta por ítem; no es distancia por carretera.', 'Haversine entre medianas postales; radio terrestre 6371.0088 km', 'km', 'catalogo', 'candidato_predictor'),
    'ruta_interestatal': ('Cliente y vendedor pertenecen a estados distintos.', 'customer_state != seller_state; nulo si falta algún estado', 'booleano', 'compra', 'candidato_predictor'),
    'anio_compra': ('Año de compra.', 'order_purchase_timestamp.dt.year', 'año', 'compra', 'candidato_predictor'),
    'mes_compra': ('Mes de compra, de 1 a 12.', 'order_purchase_timestamp.dt.month', 'mes', 'compra', 'candidato_predictor'),
    'dia_semana_compra': ('Día de compra: lunes=0, domingo=6.', 'order_purchase_timestamp.dt.dayofweek', 'día de semana', 'compra', 'candidato_predictor'),
    'dias_entrega': ('Duración observada; solo pedidos entregados con fecha y duración no negativa.', '(entrega - compra).total_seconds() / 86400', 'días', 'post_evento', 'objetivo_regresion'),
    'dias_prometidos': ('Tiempo entre compra y fecha prometida a medianoche; no se redondea.', '(fecha estimada - compra).total_seconds() / 86400', 'días', 'compra', 'candidato_predictor'),
    'dias_retraso_calendario': ('Diferencia de fechas calendario; negativa significa entrega anticipada.', 'normalize(entrega) - normalize(fecha estimada), en días', 'días', 'post_evento', 'resultado_no_predictor'),
    'entrega_tardia': ('Entrega después del día prometido; nulo cuando no se puede evaluar.', 'dias_retraso_calendario > 0', 'booleano', 'post_evento', 'resultado_no_predictor'),
    'es_entregado': ('Estado final observado igual a delivered.', 'order_status == "delivered"', 'booleano', 'post_evento', 'filtro_no_predictor'),
    'tiene_fecha_entrega': ('Existe una fecha de entrega convertible.', 'order_delivered_customer_date.notna()', 'booleano', 'post_evento', 'auditoria'),
    'compra_despues_aprobacion': ('La compra figura después de la aprobación.', 'compra > aprobación, con ambas fechas presentes', 'booleano', 'post_evento', 'auditoria'),
    'aprobacion_despues_despacho': ('La aprobación figura después del despacho.', 'aprobación > despacho, con ambas fechas presentes', 'booleano', 'post_evento', 'auditoria'),
    'despacho_despues_entrega': ('El despacho figura después de la entrega.', 'despacho > entrega, con ambas fechas presentes', 'booleano', 'post_evento', 'auditoria'),
    'entrega_antes_compra': ('La fecha de entrega precede a la compra.', 'entrega < compra, con ambas fechas presentes', 'booleano', 'post_evento', 'auditoria'),
    'valor_articulos': ('Suma de precios de ítems; nulo si no existen ítems.', 'sum(price, min_count=1) por order_id', 'BRL', 'compra', 'candidato_predictor'),
    'valor_flete': ('Suma de fletes de ítems; nulo si no existen ítems.', 'sum(freight_value, min_count=1) por order_id', 'BRL', 'compra', 'candidato_predictor'),
    'cantidad_items': ('Número de filas de ítem en el pedido.', 'size por order_id; 0 sin ítems', 'ítems', 'compra', 'candidato_predictor'),
    'cantidad_productos': ('Productos distintos en el pedido.', 'nunique(product_id) por order_id; 0 sin ítems', 'productos', 'compra', 'candidato_predictor'),
    'cantidad_vendedores': ('Vendedores distintos en el pedido.', 'nunique(seller_id) por order_id; 0 sin ítems', 'vendedores', 'compra', 'candidato_predictor'),
    'valor_pagado': ('Suma de registros de pago; nulo si no hay registros.', 'sum(payment_value, min_count=1) por order_id', 'BRL', 'pago', 'descriptor'),
    'cantidad_registros_pago': ('Número de registros de pago.', 'size por order_id; 0 sin pagos', 'registros', 'pago', 'auditoria'),
    'cuotas_cero': ('Algún pago tiene cero cuotas; no se imputa.', 'any(payment_installments == 0) por order_id', 'booleano', 'pago', 'auditoria'),
    'cantidad_resenas': ('Número de reseñas asociadas al pedido.', 'size por order_id; 0 sin reseñas', 'reseñas', 'post_evento', 'auditoria'),
    'calificacion_media': ('Media de las puntuaciones válidas del pedido, sin sumar ni escoger una arbitrariamente.', 'mean(review_score) por order_id', 'estrellas', 'post_evento', 'resultado_no_predictor'),
    'sin_items': ('No existen registros de ítem para el pedido.', 'cantidad_items == 0', 'booleano', 'compra', 'auditoria'),
    'sin_pago': ('No existen registros de pago para el pedido.', 'cantidad_registros_pago == 0', 'booleano', 'pago', 'auditoria'),
    'sin_resenas': ('No existen reseñas para el pedido.', 'cantidad_resenas == 0', 'booleano', 'post_evento', 'auditoria'),
}


def claves_registro(tabla, df):
    """Número de fila CSV (cabecera=1) más claves de negocio si existen."""
    registros = pd.Series([f'fila_csv={i + 2}' for i in range(len(df))], index=df.index)
    claves = CLAVES.get(tabla, ['review_id', 'order_id'] if tabla == 'opiniones' else [])
    for columna in claves:
        registros += ';' + columna + '=' + df[columna].astype('string').fillna('<nulo>')
    return registros


def registrar(incidencias, tabla, df, mascara, columna, regla, tratamiento):
    mascara = mascara.fillna(False)
    if not mascara.any():
        return
    parte = df.loc[mascara]
    registros = claves_registro(tabla, df).loc[mascara]
    if isinstance(columna, list):
        valores = parte[columna].astype('string').fillna('<nulo>').apply(
            lambda fila: ' | '.join(f'{campo}={fila[campo]}' for campo in columna), axis=1,
        )
        columna = ' + '.join(columna)
    else:
        valores = parte[columna].astype('string').fillna('<nulo>')
    for registro, valor in zip(registros, valores):
        incidencias.append({
            'tabla': tabla, 'registro': registro, 'columna': columna, 'regla': regla,
            'valor_original': valor, 'tratamiento': tratamiento, 'afectados': 1,
        })


def cargar_tablas(ruta_zip):
    if not ruta_zip.is_file():
        raise FileNotFoundError(f'No se encontró {ruta_zip}. Coloca archive.zip en data/raw/.')
    with ZipFile(ruta_zip) as archivo:
        faltantes = set(ARCHIVOS.values()) - set(archivo.namelist())
        if faltantes:
            raise ValueError(f'Faltan archivos en el ZIP: {sorted(faltantes)}')
        tablas = {}
        for nombre, csv in ARCHIVOS.items():
            # Todo como texto inicialmente: conserva ceros postales y permite
            # contabilizar fallos de conversión antes de cualquier imputación.
            df = pd.read_csv(archivo.open(csv), dtype='string', encoding='utf-8-sig')
            if list(df.columns) != list(ESQUEMA[nombre]):
                raise ValueError(f'Esquema inesperado en {csv}: {list(df.columns)}')
            tablas[nombre] = df
    return tablas


def auditar_tablas(tablas, claves=None):
    claves = CLAVES if claves is None else claves
    filas = []
    for nombre, df in tablas.items():
        duplicados = int(df.duplicated().sum())
        duplicados_clave = int(df.duplicated(claves[nombre]).sum()) if nombre in claves else pd.NA
        for columna in df.columns:
            filas.append({
                'tabla': nombre, 'filas': len(df), 'columnas': len(df.columns),
                'columna': columna, 'tipo': str(df[columna].dtype),
                'nulos': int(df[columna].isna().sum()),
                'porcentaje_nulos': round(df[columna].isna().mean() * 100, 4),
                'valores_distintos': int(df[columna].nunique()),
                'filas_duplicadas_exactas': duplicados, 'duplicados_clave': duplicados_clave,
            })
    return pd.DataFrame(filas, columns=PERFIL_COLUMNAS)


def limpiar_tablas(originales, incidencias):
    tablas = {}
    for nombre, original in originales.items():
        df = original.copy()
        for columna, (tipo, _, _, _) in ESQUEMA[nombre].items():
            fuente = original[columna]
            if tipo == 'datetime64[ns]':
                valor = pd.to_datetime(fuente, format='ISO8601', errors='coerce')
            elif tipo in ('Int64', 'Float64'):
                valor = pd.to_numeric(fuente, errors='coerce')
                valor = valor.mask(valor.isin([float('inf'), float('-inf')]))
                if tipo == 'Int64':
                    valor = valor.mask(valor.notna() & valor.mod(1).ne(0))
                valor = valor.astype(tipo)
            elif 'zip_code_prefix' in columna:
                valor = fuente.str.strip()
                valor = valor.where(valor.str.fullmatch(r'\d{1,5}', na=False)).str.zfill(5)
            else:
                valor = fuente
            registrar(
                incidencias, nombre, original, fuente.notna() & valor.isna(), columna,
                'conversion_invalida', 'Conservar fila; valor procesado nulo; revisar incidencia.',
            )
            df[columna] = valor
        tablas[nombre] = df
    return tablas


def validar_entradas(tablas, incidencias):
    controles = []
    for tabla, claves in CLAVES.items():
        df = tablas[tabla]
        duplicados = int(df.duplicated(claves).sum())
        nulos = int(df[claves].isna().any(axis=1).sum())
        controles.extend([
            control(f'clave_unica_{tabla}', 0, duplicados),
            control(f'clave_no_nula_{tabla}', 0, nulos),
        ])
        registrar(incidencias, tabla, df, df.duplicated(claves, keep=False), claves[0],
                  'clave_duplicada', 'Requiere corrección antes de exportar tablas procesadas.')
    for hija, fk, padre, pk in RELACIONES:
        df = tablas[hija]
        sin_padre = ~df[fk].isin(tablas[padre][pk])
        controles.append(control(f'referencia_{hija}_{fk}_{padre}', 0, int(sin_padre.sum())))
        registrar(incidencias, hija, df, sin_padre, fk, 'referencia_ausente',
                  'Requiere corrección antes de exportar tablas procesadas.')
    for tabla, columna in [('clientes', 'customer_unique_id'),
                           ('pedidos', 'order_purchase_timestamp'), ('pedidos', 'order_status')]:
        df = tablas[tabla]
        controles.append(control(f'requerido_{tabla}_{columna}', 0, int(df[columna].isna().sum())))
        registrar(incidencias, tabla, df, df[columna].isna(), columna, 'dato_requerido_ausente',
                  'Requiere corrección antes de exportar tablas procesadas.')
    rangos = [
        ('detalles', 'price', lambda s: s.isna() | s.le(0)),
        ('detalles', 'freight_value', lambda s: s.isna() | s.lt(0)),
        ('pagos', 'payment_value', lambda s: s.isna() | s.lt(0)),
        ('opiniones', 'review_score', lambda s: ~s.between(1, 5).fillna(False)),
    ]
    for tabla, columna, fuera_rango in rangos:
        df = tablas[tabla]
        mascara = fuera_rango(df[columna])
        controles.append(control(f'rango_{tabla}_{columna}', 0, int(mascara.sum())))
        registrar(incidencias, tabla, df, mascara, columna, 'rango_invalido',
                  'Requiere corrección antes de exportar tablas procesadas.')
    # La conversión inválida nunca se confunde con un faltante de origen.
    controles.append(control('conversiones_invalidas', 0, sum(
        i['afectados'] for i in incidencias if i['regla'] == 'conversion_invalida'
    )))
    return controles


def preparar_geolocalizacion(df, incidencias):
    duplicados = df.duplicated()
    if duplicados.any():
        incidencias.append({
            'tabla': 'geolocalizacion', 'registro': 'tabla completa', 'columna': '*',
            'regla': 'duplicados_exactos', 'valor_original': '',
            'tratamiento': 'Eliminar repeticiones exactas antes de la mediana postal.',
            'afectados': int(duplicados.sum()),
        })
    limpia = df.loc[~duplicados].copy()
    validas = (limpia['geolocation_lat'].between(-90, 90)
               & limpia['geolocation_lng'].between(-180, 180)).fillna(False)
    registrar(incidencias, 'geolocalizacion', df,
              ~(df['geolocation_lat'].between(-90, 90)
                & df['geolocation_lng'].between(-180, 180)).fillna(False),
              ['geolocation_lat', 'geolocation_lng'], 'coordenadas_invalidas',
              'Excluir el par de coordenadas del cálculo de medianas; conservar su conteo.')
    limpia['coordenadas_validas'] = validas.astype('boolean')
    # Se invalidan pares completos: evita fabricar un par a partir de dos
    # observaciones que nunca tuvieron ambas coordenadas válidas.
    limpia.loc[~validas, ['geolocation_lat', 'geolocation_lng']] = pd.NA
    agrupada = limpia.groupby('geolocation_zip_code_prefix', as_index=False).agg(
        latitud_mediana=('geolocation_lat', 'median'),
        longitud_mediana=('geolocation_lng', 'median'),
        cantidad_observaciones=('geolocation_zip_code_prefix', 'size'),
        cantidad_coordenadas_validas=('coordenadas_validas', 'sum'),
    )
    for columna in ['cantidad_observaciones', 'cantidad_coordenadas_validas']:
        agrupada[columna] = agrupada[columna].astype('Int64')
    return limpia, agrupada


def unir_geolocalizacion(df, geo, entidad):
    prefijo = f'{entidad}_zip_code_prefix'
    ubicaciones = geo[['geolocation_zip_code_prefix', 'latitud_mediana', 'longitud_mediana']].rename(columns={
        'geolocation_zip_code_prefix': prefijo,
        'latitud_mediana': f'{entidad}_lat', 'longitud_mediana': f'{entidad}_lng',
    })
    return df.merge(ubicaciones, on=prefijo, how='left', validate='many_to_one')


def distancia_haversine(df):
    distancias = []
    for lat1, lng1, lat2, lng2 in df[['customer_lat', 'customer_lng', 'seller_lat', 'seller_lng']].itertuples(index=False, name=None):
        if any(pd.isna(v) for v in (lat1, lng1, lat2, lng2)):
            distancias.append(pd.NA)
            continue
        lat1, lng1, lat2, lng2 = map(radians, (lat1, lng1, lat2, lng2))
        a = sin((lat2 - lat1) / 2) ** 2 + cos(lat1) * cos(lat2) * sin((lng2 - lng1) / 2) ** 2
        distancias.append(6371.0088 * 2 * asin(sqrt(min(1.0, max(0.0, a)))))
    return pd.Series(distancias, index=df.index, dtype='Float64')


def construir_items(tablas, geo, incidencias):
    productos = tablas['productos'].merge(tablas['categorias'], on='product_category_name',
                                          how='left', validate='many_to_one')
    productos['sin_categoria'] = productos['product_category_name'].isna().astype('boolean')
    productos['sin_traduccion'] = (productos['product_category_name'].notna()
                                  & productos['product_category_name_english'].isna()).astype('boolean')
    productos['categoria_presentacion'] = productos['product_category_name'].fillna('Sin categoría')
    productos['datos_fisicos_incompletos'] = productos[FISICOS].isna().any(axis=1).astype('boolean')
    productos['datos_fisicos_invalidos'] = productos[FISICOS].le(0).any(axis=1).astype('boolean')
    dimensiones = ['product_length_cm', 'product_height_cm', 'product_width_cm']
    productos['volumen_cm3'] = productos[dimensiones].prod(axis=1, min_count=3).astype('Float64')
    productos.loc[~productos[dimensiones].gt(0).all(axis=1) | productos[dimensiones].isna().any(axis=1), 'volumen_cm3'] = pd.NA
    for bandera, columna in [('sin_categoria', 'product_category_name'),
                             ('sin_traduccion', 'product_category_name'),
                             ('datos_fisicos_incompletos', FISICOS),
                             ('datos_fisicos_invalidos', FISICOS)]:
        registrar(incidencias, 'productos', productos, productos[bandera], columna, bandera,
                  'Conservar producto e indicador; no imputar atributos físicos.')
    clientes = unir_geolocalizacion(tablas['clientes'], geo, 'customer')
    vendedores = unir_geolocalizacion(tablas['vendedores'], geo, 'seller')
    pedidos = tablas['pedidos'][['order_id', 'customer_id', 'order_status', 'order_purchase_timestamp']]
    pedidos = pedidos.merge(clientes, on='customer_id', how='left', validate='many_to_one')
    items = tablas['detalles'].merge(productos, on='product_id', how='left', validate='many_to_one')
    items = items.merge(vendedores, on='seller_id', how='left', validate='many_to_one')
    items = items.merge(pedidos, on='order_id', how='left', validate='many_to_one')
    items['sin_geolocalizacion_cliente'] = items[['customer_lat', 'customer_lng']].isna().any(axis=1).astype('boolean')
    items['sin_geolocalizacion_vendedor'] = items[['seller_lat', 'seller_lng']].isna().any(axis=1).astype('boolean')
    items['distancia_km'] = distancia_haversine(items)
    items['ruta_interestatal'] = items['customer_state'].ne(items['seller_state']).astype('boolean')
    return items.sort_values(['order_id', 'order_item_id']).reset_index(drop=True)


def agregar_items(items):
    grupo = items.groupby('order_id', sort=True)
    agregados = grupo.agg(
        cantidad_items=('order_item_id', 'size'),
        cantidad_productos=('product_id', 'nunique'),
        cantidad_vendedores=('seller_id', 'nunique'),
    )
    agregados[['valor_articulos', 'valor_flete']] = grupo[['price', 'freight_value']].sum(min_count=1)
    return agregados.reset_index()


def agregar_pagos(pagos):
    pagos = pagos.assign(cuotas_cero=pagos['payment_installments'].eq(0))
    grupo = pagos.groupby('order_id', sort=True)
    agregados = grupo.agg(cantidad_registros_pago=('payment_sequential', 'size'),
                         cuotas_cero=('cuotas_cero', 'any'))
    agregados['valor_pagado'] = grupo['payment_value'].sum(min_count=1)
    return agregados.reset_index()


def construir_pedidos(tablas, items, geo, incidencias):
    clientes = unir_geolocalizacion(tablas['clientes'], geo, 'customer')
    pedidos = tablas['pedidos'].merge(clientes, on='customer_id', how='left', validate='many_to_one')
    resenas = tablas['opiniones'].groupby('order_id', as_index=False).agg(
        cantidad_resenas=('review_id', 'size'), calificacion_media=('review_score', 'mean'),
    )
    for agregado in (agregar_items(items), agregar_pagos(tablas['pagos']), resenas):
        pedidos = pedidos.merge(agregado, on='order_id', how='left', validate='one_to_one')
    for columna in CONTADORES:
        pedidos[columna] = pedidos[columna].fillna(0).astype('Int64')
    # Sin pagos no equivale a "se pagó sin cuotas": conserva el booleano nulo.
    pedidos['cuotas_cero'] = pedidos['cuotas_cero'].astype('boolean')
    for bandera, contador in [('sin_items', 'cantidad_items'), ('sin_pago', 'cantidad_registros_pago'),
                              ('sin_resenas', 'cantidad_resenas')]:
        pedidos[bandera] = pedidos[contador].eq(0).astype('boolean')
        registrar(incidencias, 'pedidos', pedidos, pedidos[bandera], 'order_id', bandera,
                  'Conservar pedido; contador cero e importes/puntuaciones desconocidos nulos.')
    pedidos['sin_geolocalizacion_cliente'] = pedidos[['customer_lat', 'customer_lng']].isna().any(axis=1).astype('boolean')
    compra = pedidos['order_purchase_timestamp']
    entrega = pedidos['order_delivered_customer_date']
    estimada = pedidos['order_estimated_delivery_date']
    pedidos['anio_compra'] = compra.dt.year.astype('Int64')
    pedidos['mes_compra'] = compra.dt.month.astype('Int64')
    pedidos['dia_semana_compra'] = compra.dt.dayofweek.astype('Int64')
    pedidos['es_entregado'] = pedidos['order_status'].eq('delivered').astype('boolean')
    pedidos['tiene_fecha_entrega'] = entrega.notna().astype('boolean')
    duracion = (entrega - compra).dt.total_seconds() / 86400
    elegible = pedidos['es_entregado'] & entrega.notna() & compra.notna() & duracion.ge(0)
    pedidos['dias_entrega'] = duracion.where(elegible).astype('Float64')
    pedidos['dias_prometidos'] = ((estimada - compra).dt.total_seconds() / 86400).astype('Float64')
    retraso = (entrega.dt.normalize() - estimada.dt.normalize()).dt.days
    evaluable = elegible & estimada.notna()
    pedidos['dias_retraso_calendario'] = retraso.where(evaluable).astype('Int64')
    pedidos['entrega_tardia'] = pedidos['dias_retraso_calendario'].gt(0).astype('boolean')
    secuencias = [
        ('order_purchase_timestamp', 'order_approved_at', 'compra_despues_aprobacion'),
        ('order_approved_at', 'order_delivered_carrier_date', 'aprobacion_despues_despacho'),
        ('order_delivered_carrier_date', 'order_delivered_customer_date', 'despacho_despues_entrega'),
        ('order_purchase_timestamp', 'order_delivered_customer_date', 'entrega_antes_compra'),
    ]
    for izquierda, derecha, bandera in secuencias:
        a, b = pedidos[izquierda], pedidos[derecha]
        comparacion = a.gt(b)
        pedidos[bandera] = (a.notna() & b.notna() & comparacion).astype('boolean')
        registrar(incidencias, 'pedidos', pedidos, pedidos[bandera], izquierda, bandera,
                  'Conservar fechas y bandera; seleccionar casos según el análisis.')
    registrar(incidencias, 'pedidos', pedidos,
              pedidos['es_entregado'] & ~pedidos['tiene_fecha_entrega'],
              'order_delivered_customer_date', 'entregado_sin_fecha',
              'Conservar pedido; duración y puntualidad nulas; excluir solo de tareas que las necesitan.')
    registrar(incidencias, 'pagos', tablas['pagos'], tablas['pagos']['payment_installments'].eq(0),
              'payment_installments', 'cuotas_cero', 'Conservar cero e indicador; no imputar una cuota.')
    repetidas = tablas['opiniones']['order_id'].duplicated(keep=False)
    registrar(incidencias, 'opiniones', tablas['opiniones'], repetidas, 'order_id',
              'multiples_resenas', 'Conservar reseñas originales; agregar media y cantidad por pedido.')
    for nombre, df, columna, bandera in [
        ('clientes', clientes, 'customer_zip_code_prefix', 'sin_geolocalizacion_cliente'),
        ('vendedores', unir_geolocalizacion(tablas['vendedores'], geo, 'seller'),
         'seller_zip_code_prefix', 'sin_geolocalizacion_vendedor'),
    ]:
        entidad = 'customer' if nombre == 'clientes' else 'seller'
        mascara = df[[f'{entidad}_lat', f'{entidad}_lng']].isna().any(axis=1)
        registrar(incidencias, nombre, df, mascara, columna, bandera,
                  'Conservar entidad; coordenadas y distancias desconocidas nulas.')
    return pedidos.sort_values('order_id').reset_index(drop=True)


def control(nombre, esperado, obtenido, tolerancia=0):
    correcto = isclose(float(esperado), float(obtenido), rel_tol=0, abs_tol=tolerancia)
    return {'control': nombre, 'esperado': esperado, 'obtenido': obtenido,
            'tolerancia': tolerancia, 'resultado': 'OK' if correcto else 'ERROR'}


def validar_resultados(tablas, pedidos, items, geo):
    controles = [
        control('filas_pedidos', len(tablas['pedidos']), len(pedidos)),
        control('filas_items', len(tablas['detalles']), len(items)),
        control('clave_unica_pedidos_procesados', 0, pedidos.duplicated('order_id').sum()),
        control('clave_unica_items_procesados', 0, items.duplicated(['order_id', 'order_item_id']).sum()),
        control('clave_unica_geolocalizacion_agrupada', 0, geo.duplicated('geolocation_zip_code_prefix').sum()),
        control('clave_no_nula_geolocalizacion_agrupada', 0, geo['geolocation_zip_code_prefix'].isna().sum()),
        control('observaciones_geograficas_conciliadas', len(tablas['geolocalizacion'].drop_duplicates()),
                geo['cantidad_observaciones'].sum()),
        control('cantidad_items_conciliada', len(items), pedidos['cantidad_items'].sum()),
        control('cantidad_pagos_conciliada', len(tablas['pagos']), pedidos['cantidad_registros_pago'].sum()),
        control('cantidad_resenas_conciliada', len(tablas['opiniones']), pedidos['cantidad_resenas'].sum()),
    ]
    for fuente, columna, destino in [
        ('detalles', 'price', 'valor_articulos'), ('detalles', 'freight_value', 'valor_flete'),
        ('pagos', 'payment_value', 'valor_pagado'),
    ]:
        esperado = tablas[fuente][columna].sum()
        controles.append(control(f'conciliacion_{destino}', esperado, pedidos[destino].sum(), 0.005))
    entregados_originales = tablas['pedidos'].loc[tablas['pedidos']['order_status'].eq('delivered'), 'order_id']
    detalles_entregados = tablas['detalles'].loc[tablas['detalles']['order_id'].isin(entregados_originales)]
    controles.extend([
        control('pedidos_entregados_conservados', len(entregados_originales), pedidos['es_entregado'].sum()),
        control('ventas_entregadas_conciliadas', detalles_entregados['price'].sum(),
                pedidos.loc[pedidos['es_entregado'], 'valor_articulos'].sum(), 0.005),
        control('importe_nulo_pedidos_sin_items', int(pedidos['sin_items'].sum()),
                int(pedidos.loc[pedidos['sin_items'], 'valor_articulos'].isna().sum())),
        control('importe_nulo_pedidos_sin_pago', int(pedidos['sin_pago'].sum()),
                int(pedidos.loc[pedidos['sin_pago'], 'valor_pagado'].isna().sum())),
        control('duraciones_negativas', 0, int(pedidos['dias_entrega'].lt(0).sum())),
        control('distancias_negativas', 0, int(items['distancia_km'].lt(0).sum())),
        control('puntualidad_desconocida_sin_duracion', int(pedidos['dias_entrega'].isna().sum()),
                int(pedidos.loc[pedidos['dias_entrega'].isna(), 'entrega_tardia'].isna().sum())),
        control('bandera_entrega_antes_compra',
                int(pedidos['order_delivered_customer_date'].lt(pedidos['order_purchase_timestamp']).sum()),
                int(pedidos['entrega_antes_compra'].sum())),
    ])
    # Conciliar por pedido detecta desplazamientos que una suma global oculta.
    esperado = tablas['detalles'].groupby('order_id')['price'].sum(min_count=1)
    obtenido = pedidos.set_index('order_id')['valor_articulos'].reindex(esperado.index)
    controles.append(control('importes_por_pedido', 0,
                             int((esperado - obtenido).abs().gt(0.005).sum()) + int(obtenido.isna().sum())))
    return controles


def diccionario_original(originales, tablas):
    filas = []
    for tabla, campos in ESQUEMA.items():
        for columna, (tipo, descripcion, unidad, disponibilidad) in campos.items():
            claves = CLAVES.get(tabla, [])
            relaciones = [f'{p}.{pk}' for h, fk, p, pk in RELACIONES if h == tabla and fk == columna]
            rol = 'parte de clave: ' + ' + '.join(claves) if columna in claves else ''
            if relaciones:
                rol += ('; ' if rol else '') + 'referencia: ' + ', '.join(relaciones)
            tratamiento = 'Conservar valor y faltantes originales.'
            if 'zip_code_prefix' in columna:
                tratamiento = 'Texto de cinco dígitos; inválidos registrados como incidencia.'
            elif tipo != 'string':
                tratamiento = 'Conversión explícita; fallos contabilizados por registro.'
            filas.append({
                'tabla': tabla, 'columna': columna, 'descripcion': descripcion,
                'tipo_lectura': str(originales[tabla][columna].dtype), 'tipo_propuesto': tipo,
                'tipo_procesado': str(tablas[tabla][columna].dtype), 'unidad': unidad,
                'clave_o_relacion': rol, 'nulos_origen': int(originales[tabla][columna].isna().sum()),
                'permite_nulos_en_salida': columna not in claves,
                'disponibilidad': disponibilidad, 'tratamiento': tratamiento,
            })
    return pd.DataFrame(filas)


def diccionario_procesados(procesadas):
    fuentes = {
        'pedidos_procesados': ['pedidos', 'clientes'],
        'items_procesados': ['detalles', 'productos', 'vendedores', 'pedidos', 'clientes', 'categorias'],
        'geolocalizacion_agrupada': ['geolocalizacion'],
    }
    filas = []
    for tabla, df in procesadas.items():
        for columna in df.columns:
            derivada = columna in DERIVADAS
            if derivada:
                descripcion, formula, unidad, disponibilidad, uso = DERIVADAS[columna]
            else:
                origen = next(nombre for nombre in fuentes[tabla] if columna in ESQUEMA[nombre])
                _, descripcion, unidad, disponibilidad = ESQUEMA[origen][columna]
                formula = f'{origen}.{columna}; unión por claves validadas'
                uso = 'identificador' if columna.endswith('_id') or 'zip_code_prefix' in columna else 'descriptor'
                if disponibilidad == 'post_evento':
                    uso = 'resultado_no_predictor'
            no_nula = columna in {
                'order_id', 'order_item_id', 'product_id', 'seller_id', 'customer_id',
                'customer_unique_id', 'geolocation_zip_code_prefix', *CONTADORES,
                'cantidad_observaciones', 'cantidad_coordenadas_validas', 'order_status',
                'order_purchase_timestamp', 'anio_compra', 'mes_compra', 'dia_semana_compra',
            } or (str(df[columna].dtype) == 'boolean' and columna not in {
                'entrega_tardia', 'ruta_interestatal', 'cuotas_cero',
            })
            filas.append({
                'tabla': tabla, 'columna': columna, 'descripcion': descripcion,
                'tipo': str(df[columna].dtype), 'unidad': unidad, 'es_derivada': derivada,
                'permite_nulos': not no_nula,
                'nulos_observados': int(df[columna].isna().sum()), 'formula_o_fuente': formula,
                'disponibilidad': disponibilidad, 'uso_recomendado': uso,
            })
    return pd.DataFrame(filas)


def guardar_csv(df, ruta):
    ruta.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(ruta, index=False, encoding='utf-8-sig', date_format='%Y-%m-%dT%H:%M:%S', lineterminator='\n')


def resumen_indicadores(pedidos, items):
    entregados = pedidos.loc[pedidos['es_entregado']]
    frecuencia = pedidos.groupby('customer_unique_id').size()
    evaluables = entregados['entrega_tardia'].notna()
    return {
        'pedidos_totales': len(pedidos), 'items_totales': len(items),
        'pedidos_entregados': len(entregados),
        'clientes_unicos_todos_estados': len(frecuencia),
        'clientes_recurrentes_todos_estados': int(frecuencia.gt(1).sum()),
        'porcentaje_clientes_recurrentes': round(frecuencia.gt(1).mean() * 100, 6),
        'clientes_unicos_entregados': int(entregados['customer_unique_id'].nunique()),
        'ventas_articulos_entregados_BRL': round(float(entregados['valor_articulos'].sum()), 2),
        'pedidos_sin_items': int(pedidos['sin_items'].sum()),
        'pedidos_sin_pago': int(pedidos['sin_pago'].sum()),
        'pedidos_sin_resenas': int(pedidos['sin_resenas'].sum()),
        'pedidos_con_multiples_resenas': int(pedidos['cantidad_resenas'].gt(1).sum()),
        'entregados_sin_fecha': int((entregados['tiene_fecha_entrega'].eq(False)).sum()),
        'pedidos_evaluables_puntualidad_calendario': int(evaluables.sum()),
        'entregas_tardias_calendario': int(entregados['entrega_tardia'].sum()),
        'tasa_entregas_tardias_calendario_pct': round(float(entregados.loc[evaluables, 'entrega_tardia'].mean()) * 100, 6) if evaluables.any() else None,
    }


def generar_informe(pedidos, items, geo, incidencias, controles, indicadores, sha256, resumen_calidad):
    reglas = incidencias.groupby(['tabla', 'regla'], sort=True)['afectados'].sum()
    filas_reglas = '\n'.join(f'| {tabla} | {regla} | {int(cantidad):,} |'
                            for (tabla, regla), cantidad in reglas.items())
    filas_indicadores = '\n'.join(f'| `{nombre}` | {valor} |' for nombre, valor in indicadores.items())
    filas_calidad = '\n'.join(
        f'| {tabla} | {antes} | {despues} | {nulos_antes} | {nulos_despues} |'
        for tabla, antes, despues, nulos_antes, nulos_despues in resumen_calidad
    )
    return f'''# Preparación y calidad de Olist — entrega de Jerson

Informe generado por `python src/preparar_datos.py`.

## Fuente y granularidad

- Fuente: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
- Archivo: `data/raw/archive.zip`; SHA-256: `{sha256}`.
- Nueve tablas originales y **52 campos** sumados entre tablas.
- Compra mínima/máxima observada: {pedidos['order_purchase_timestamp'].min()} / {pedidos['order_purchase_timestamp'].max()}.
- Pedidos: **{len(pedidos):,} filas**, una por `order_id`, con todos los estados.
- Ítems: **{len(items):,} filas**, una por `order_id` + `order_item_id`.
- Geolocalización: **{len(geo):,} prefijos únicos**, con medianas de coordenadas.

## Decisiones de preparación

1. La zona raw se lee directamente del ZIP. Se carga como texto antes de convertir tipos, conservando ceros postales.
2. Fechas ISO, numéricos anulables y prefijos de cinco dígitos. Cada conversión fallida queda registrada y bloquea la publicación de tablas procesadas.
3. Las claves y referencias se validan antes de unir. Ítems, pagos y reseñas se agregan por separado por pedido; las uniones finales son izquierdas y verificadas.
4. Solo se eliminan repeticiones exactas de geolocalización. Después se agrupa por prefijo y se calcula la mediana de pares válidos. Los rangos son globales (latitud ±90, longitud ±180), no una frontera de Brasil.
5. Se conservan categorías originales y nulos; `categoria_presentacion` añade la etiqueta «Sin categoría». Las categorías conocidas sin traducción no se descartan.
6. Reseñas múltiples: media de puntuaciones y cantidad por pedido. Los textos faltantes no eliminan las puntuaciones. Los textos completos siguen disponibles en el ZIP original.
7. Sin ítems/pagos/reseñas: contador cero, indicador explícito y valores monetarios o puntuaciones desconocidos nulos. Los ceros de cuotas se conservan y señalan.
8. Secuencias temporales inconsistentes se conservan con indicadores. `dias_entrega` solo existe para pedidos entregados con compra/entrega válidas y duración no negativa; usa segundos/86400, sin truncar.
9. Puntualidad por **día calendario**: entregar el mismo día prometido no cuenta como retraso. `entrega_tardia` es nulo cuando no es evaluable. Esta definición puede diferir del 8,11 % de la vista de demostración, que compara timestamps.
10. La distancia se calcula por ítem mediante Haversine sobre medianas postales; no representa la ruta real. Coordenadas ausentes producen distancia nula, nunca cero imputado.

## Calidad antes y después

Comparación sobre los campos originales, sin sumar columnas derivadas al conteo de nulos.
La reducción de filas de geolocalización corresponde a duplicados exactos; los prefijos se agregan en una tabla aparte.
Los faltantes que siguen presentes son explícitos y se conservan según las reglas anteriores.

| Tabla | Filas antes | Filas después | Celdas nulas antes | Celdas nulas después |
|---|---:|---:|---:|---:|
{filas_calidad}

## Controles e indicadores

**{len(controles)} controles, {int(controles['resultado'].eq('ERROR').sum())} errores.**
Conciliación monetaria con tolerancia absoluta de 0,005 BRL y tolerancia relativa cero.
Incluye conciliación global y de precios por pedido, claves, referencias y conservación de filas.

| Indicador | Valor |
|---|---:|
{filas_indicadores}

## Incidencias conservadas o tratadas

Los conteos siguientes son incidencias, no filas eliminadas. Un registro puede activar varias reglas.
`incidencias.csv` identifica fila CSV y claves; los duplicados geográficos se resumen a nivel de tabla.

| Tabla | Regla | Registros afectados |
|---|---|---:|
{filas_reglas}

## Archivos de entrega

- `data/processed/pedidos_procesados.csv`: tabla de pedidos y agregados independientes.
- `data/processed/items_procesados.csv`: ítems con producto, vendedor, comprador y geografía.
- `data/processed/geolocalizacion_agrupada.csv`: una fila por prefijo postal.
- `resultados/calidad/perfil_antes.csv`: perfil del contenido leído como texto.
- `resultados/calidad/perfil_despues.csv`: perfil de las nueve tablas tipadas y las tres tablas finales; geolocalización está deduplicada.
- `resultados/calidad/validaciones.csv`, `incidencias.csv`, `indicadores_preparacion.csv` y `metadata.json`.
- `resultados/diccionario_datos.csv`: contrato de los 52 campos originales.
- `resultados/diccionario_procesados.csv`: contrato completo de las tres tablas finales.
- `resultados/diccionario_variables_derivadas.csv`: variables nuevas, fórmulas y disponibilidad.

## Entrega al equipo

- **Paulo:** filtrar ítems de pedidos entregados; formar cestas por `order_id`, deduplicando categorías por cesta. Conservar pedidos de cesta unitaria en el denominador del soporte. Excluir la etiqueta de categoría desconocida de las asociaciones e informar el universo elegido.
- **Brandon:** usar `customer_unique_id` para RFM; frecuencia = pedidos distintos, monto = `valor_articulos`, recencia respecto de una fecha explícita. Grafo con `seller_id` y `product_id` desde ítems. Las medianas geográficas usan todo el catálogo histórico: no son una reconstrucción temporal de ese catálogo.
- **Anderson:** ventas = `valor_articulos` de entregados, agrupadas por fecha de compra. Marcar periodos de borde incompletos. Objetivo de regresión = `dias_entrega`; separar entrenamiento/prueba cronológicamente y ajustar imputación/escalado solo con entrenamiento.
- `order_status`, fecha real de entrega, puntuaciones, retraso, banderas temporales y `es_entregado` son datos posteriores o de auditoría, no predictores disponibles al comprar. Los catálogos son una fotografía histórica: no se dispone de sus versiones por fecha.
- No se entrega una partición train/test universal: cada responsable define el momento de predicción, población y corte temporal de su técnica. Consultar `disponibilidad` y `uso_recomendado` en los diccionarios.

## Reproducción

Instalar `requirements.txt`, colocar el ZIP en `data/raw/` y ejecutar `python src/preparar_datos.py`.
Las rutas por defecto se resuelven desde la ubicación del script. Para otra salida: `python src/preparar_datos.py --output-root /ruta/salida`.
Los CSV de salida son UTF-8 con BOM; fechas ISO; booleanos True/False; faltantes vacíos.
Al recargar, declarar como texto los identificadores y prefijos postales para conservar los ceros iniciales.
`data/processed/` está excluido de Git: el script, los diccionarios y las instrucciones permiten regenerar la entrega.
Con el mismo ZIP y versiones de dependencias, los CSV y este informe son deterministas; solo la fecha de ejecución en metadata cambia.
'''


def ejecutar(ruta_zip, salida):
    originales = cargar_tablas(ruta_zip)
    incidencias = []
    perfil_antes = auditar_tablas(originales)
    tablas = limpiar_tablas(originales, incidencias)
    controles = validar_entradas(tablas, incidencias)
    calidad = salida / 'resultados' / 'calidad'
    guardar_csv(perfil_antes, calidad / 'perfil_antes.csv')
    if any(c['resultado'] == 'ERROR' for c in controles):
        guardar_csv(pd.DataFrame(controles), calidad / 'validaciones.csv')
        guardar_csv(pd.DataFrame(incidencias, columns=INCIDENCIA_COLUMNAS), calidad / 'incidencias.csv')
        raise ValueError(f'Falló la validación de entradas; revisar {calidad / "validaciones.csv"}.')
    geo_limpia, geo = preparar_geolocalizacion(tablas['geolocalizacion'], incidencias)
    items = construir_items(tablas, geo, incidencias)
    pedidos = construir_pedidos(tablas, items, geo, incidencias)
    controles.extend(validar_resultados(tablas, pedidos, items, geo))
    controles = pd.DataFrame(controles)
    incidencias = pd.DataFrame(incidencias, columns=INCIDENCIA_COLUMNAS)
    guardar_csv(controles, calidad / 'validaciones.csv')
    guardar_csv(incidencias, calidad / 'incidencias.csv')
    if controles['resultado'].eq('ERROR').any():
        raise ValueError(f'Falló la validación de resultados; revisar {calidad / "validaciones.csv"}.')
    procesadas = {'pedidos_procesados': pedidos, 'items_procesados': items,
                  'geolocalizacion_agrupada': geo}
    tipadas = {**tablas, 'geolocalizacion': geo_limpia}
    resumen_calidad = [
        (nombre, len(df), len(tipadas[nombre]), int(df.isna().sum().sum()),
         int(tipadas[nombre][list(df.columns)].isna().sum().sum()))
        for nombre, df in originales.items()
    ]
    claves_salida = {**CLAVES, 'pedidos_procesados': ['order_id'],
                    'items_procesados': ['order_id', 'order_item_id'],
                    'geolocalizacion_agrupada': ['geolocation_zip_code_prefix']}
    perfil_despues = auditar_tablas({**tipadas, **procesadas}, claves_salida)
    guardar_csv(perfil_despues, calidad / 'perfil_despues.csv')
    guardar_csv(diccionario_original(originales, tablas), salida / 'resultados' / 'diccionario_datos.csv')
    diccionario = diccionario_procesados(procesadas)
    guardar_csv(diccionario, salida / 'resultados' / 'diccionario_procesados.csv')
    guardar_csv(diccionario.loc[diccionario['es_derivada']], salida / 'resultados' / 'diccionario_variables_derivadas.csv')
    for nombre, df in procesadas.items():
        guardar_csv(df, salida / 'data' / 'processed' / f'{nombre}.csv')
    indicadores = resumen_indicadores(pedidos, items)
    guardar_csv(pd.DataFrame(indicadores.items(), columns=['indicador', 'valor']), calidad / 'indicadores_preparacion.csv')
    digest = hashlib.sha256()
    with ruta_zip.open('rb') as archivo:
        for bloque in iter(lambda: archivo.read(1024 * 1024), b''):
            digest.update(bloque)
    sha256 = digest.hexdigest()
    metadata = {
        'archivo_origen': ruta_zip.name, 'sha256_origen': sha256,
        'ejecutado_en_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(), 'pandas': pd.__version__,
        'tablas_origen': len(originales), 'campos_origen': sum(len(df.columns) for df in originales.values()),
        'filas_origen': {nombre: len(df) for nombre, df in originales.items()},
        'filas_salida': {nombre: len(df) for nombre, df in procesadas.items()},
        'controles_ok': int(controles['resultado'].eq('OK').sum()),
        'controles_error': int(controles['resultado'].eq('ERROR').sum()),
        'definicion_puntualidad': 'fecha real normalizada > fecha prometida normalizada',
    }
    (calidad / 'metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    docs = salida / 'docs'
    docs.mkdir(parents=True, exist_ok=True)
    (docs / 'preparacion_y_calidad.md').write_text(
        generar_informe(pedidos, items, geo, incidencias, controles, indicadores, sha256, resumen_calidad),
        encoding='utf-8',
    )
    print(f'Preparación completada: {len(pedidos):,} pedidos, {len(items):,} ítems y {len(geo):,} prefijos.')
    print(f'Validaciones: {len(controles)} OK; ventas entregadas: R$ {indicadores["ventas_articulos_entregados_BRL"]:,.2f}.')
    print(f'Datos: {salida / "data" / "processed"}')
    print(f'Informe: {docs / "preparacion_y_calidad.md"}')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--zip', type=Path, default=ROOT / 'data' / 'raw' / 'archive.zip', help='ZIP original de Olist.')
    parser.add_argument('--output-root', type=Path, default=ROOT, help='Raíz para data/, resultados/ y docs/ generados.')
    args = parser.parse_args()
    try:
        ejecutar(args.zip.resolve(), args.output_root.resolve())
    except (FileNotFoundError, BadZipFile, ValueError) as error:
        parser.exit(1, f'Error de preparación: {error}\n')


if __name__ == '__main__':
    main()
