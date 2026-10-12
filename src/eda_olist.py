from pathlib import Path
from zipfile import ZipFile

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import FuncFormatter
import pandas as pd

# Rutas del proyecto (independientes del directorio de ejecucion).
ROOT = Path(__file__).resolve().parents[1]
ZIP = ROOT / 'data' / 'raw' / 'archive.zip'
OUT = ROOT / 'resultados'
GRAFICOS = OUT / 'graficos'
GRAFICOS.mkdir(parents=True, exist_ok=True)

ARCHIVOS = {
    'clientes': 'olist_customers_dataset.csv',
    'geolocalizacion': 'olist_geolocation_dataset.csv',
    'detalles': 'olist_order_items_dataset.csv',
    'pagos': 'olist_order_payments_dataset.csv',
    'opiniones': 'olist_order_reviews_dataset.csv',
    'pedidos': 'olist_orders_dataset.csv',
    'productos': 'olist_products_dataset.csv',
    'vendedores': 'olist_sellers_dataset.csv',
    'categorias': 'product_category_name_translation.csv',
}

# Las categorias del CSV original se mantienen sin cambios.
# Estas etiquetas se utilizan solo para presentar los graficos.
CATEGORIAS_ES = {
    'beleza_saude': 'Belleza y salud',
    'relogios_presentes': 'Relojes y regalos',
    'cama_mesa_banho': 'Cama, mesa y baño',
    'esporte_lazer': 'Deportes y ocio',
    'informatica_acessorios': 'Accesorios informáticos',
    'moveis_decoracao': 'Muebles y decoración',
    'utilidades_domesticas': 'Artículos para el hogar',
    'cool_stuff': 'Artículos variados',
    'automotivo': 'Automotriz',
    'brinquedos': 'Juguetes',
}

ESTADOS_ES = {
    'delivered': 'Entregado',
    'shipped': 'Enviado',
    'canceled': 'Cancelado',
    'unavailable': 'No disponible',
    'invoiced': 'Facturado',
    'processing': 'En preparación',
    'created': 'Creado',
    'approved': 'Aprobado',
}


def moneda_br(valor):
    """Formato: R$ 1.234.567 (para etiquetas de graficos)."""
    return 'R$ ' + f'{valor:,.0f}'.replace(',', '.')


def entero_es(valor, posicion=None):
    return f'{valor:,.0f}'.replace(',', '.')


if not ZIP.exists():
    raise FileNotFoundError(f'No se encontró {ZIP}. Coloca archive.zip en data/raw/.')

with ZipFile(ZIP) as archivo_zip:
    nombres = set(archivo_zip.namelist())
    faltantes = [archivo for archivo in ARCHIVOS.values() if archivo not in nombres]
    if faltantes:
        raise ValueError(f'Faltan archivos en el ZIP: {faltantes}')
    tablas = {
        nombre: pd.read_csv(archivo_zip.open(archivo), low_memory=False)
        for nombre, archivo in ARCHIVOS.items()
    }

# 1. Resumen de calidad y diccionario automatico.
resumen = []
diccionario = []
for nombre, df in tablas.items():
    resumen.append({
        'tabla': nombre,
        'filas': len(df),
        'columnas': len(df.columns),
        'celdas_nulas': int(df.isna().sum().sum()),
        'filas_duplicadas_exactas': int(df.duplicated().sum()),
    })
    for columna in df.columns:
        diccionario.append({
            'tabla': nombre,
            'columna': columna,
            'tipo_pandas': str(df[columna].dtype),
            'nulos': int(df[columna].isna().sum()),
            'porcentaje_nulos': round(df[columna].isna().mean() * 100, 2),
            'valores_distintos': int(df[columna].nunique(dropna=True)),
        })

pd.DataFrame(resumen).to_csv(OUT / 'resumen_tablas.csv', index=False, encoding='utf-8-sig')
pd.DataFrame(diccionario).to_csv(OUT / 'diccionario_perfilado.csv', index=False, encoding='utf-8-sig')

# 2. Preparacion de pedidos entregados y KPI.
clientes = tablas['clientes']
pedidos = tablas['pedidos'].copy()
detalles = tablas['detalles']
pedidos['order_purchase_timestamp'] = pd.to_datetime(
    pedidos['order_purchase_timestamp'], errors='coerce'
)

entregados = pedidos.loc[
    pedidos['order_status'] == 'delivered',
    ['order_id', 'customer_id', 'order_purchase_timestamp']
]
detalles_entregados = detalles.merge(
    entregados[['order_id']], on='order_id', how='inner', validate='many_to_one'
)
ventas = detalles_entregados['price'].sum()
ticket = ventas / entregados['order_id'].nunique()
clientes_unicos = clientes['customer_unique_id'].nunique()

indicadores = pd.DataFrame([
    {'indicador': 'pedidos_totales', 'valor': len(pedidos)},
    {'indicador': 'pedidos_entregados', 'valor': len(entregados)},
    {'indicador': 'clientes_unicos', 'valor': clientes_unicos},
    {'indicador': 'productos', 'valor': len(tablas['productos'])},
    {'indicador': 'ventas_articulos_entregados_BRL', 'valor': round(ventas, 2)},
    {'indicador': 'ticket_promedio_entregado_BRL', 'valor': round(ticket, 2)},
    {'indicador': 'opiniones_con_mensaje', 'valor': int(tablas['opiniones']['review_comment_message'].notna().sum())},
])
indicadores.to_csv(OUT / 'indicadores_kpi.csv', index=False, encoding='utf-8-sig')

# 3. Grafico de pedidos por estado, en espanol.
estados = pedidos['order_status'].value_counts()
etiquetas_estado = [ESTADOS_ES.get(estado, estado) for estado in estados.index]
fig, ax = plt.subplots(figsize=(12, 5.5))
barras = ax.bar(etiquetas_estado, estados.to_numpy(), color='#2563eb')
ax.set(title='Pedidos según su estado', xlabel='Estado del pedido', ylabel='Cantidad de pedidos')
ax.yaxis.set_major_formatter(FuncFormatter(entero_es))
ax.bar_label(barras, labels=[entero_es(v) for v in estados.to_numpy()], padding=3, fontsize=8)
ax.tick_params(axis='x', rotation=25)
ax.grid(axis='y', alpha=0.2)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(GRAFICOS / '01_pedidos_por_estado.png', dpi=170)
plt.close(fig)

# 4. Ventas mensuales segun fecha de compra; se excluye el costo de flete.
ventas_pedido = detalles_entregados.groupby('order_id', as_index=False)['price'].sum()
ventas_fechadas = entregados.merge(
    ventas_pedido, on='order_id', how='inner', validate='one_to_one'
)
serie = (ventas_fechadas.set_index('order_purchase_timestamp')['price']
         .resample('MS').sum())
serie.rename('ventas_articulos_BRL').to_csv(
    OUT / 'ventas_mensuales.csv', encoding='utf-8-sig'
)
fig, ax = plt.subplots(figsize=(12, 5.5))
ax.plot(serie.index, serie.values, marker='o', color='#2563eb', linewidth=2)
ax.set(title='Ventas mensuales de artículos (pedidos entregados)',
       xlabel='Mes de compra', ylabel='Ventas (BRL)')
ax.yaxis.set_major_formatter(FuncFormatter(lambda valor, _: moneda_br(valor)))
ax.grid(alpha=0.25)
fig.autofmt_xdate(rotation=30)
fig.tight_layout()
fig.savefig(GRAFICOS / '02_ventas_mensuales.png', dpi=170)
plt.close(fig)

# 5. Top 10 de categorias traducidas al espanol.
ventas_categoria = (
    detalles_entregados.merge(
        tablas['productos'][['product_id', 'product_category_name']],
        on='product_id', how='left', validate='many_to_one'
    )
    .groupby('product_category_name', dropna=False)['price']
    .sum()
    .nlargest(10)
    .sort_values()
)
etiquetas_categoria = [
    CATEGORIAS_ES.get(categoria, str(categoria).replace('_', ' ').capitalize())
    if pd.notna(categoria) else 'Sin categoría'
    for categoria in ventas_categoria.index
]
fig, ax = plt.subplots(figsize=(12, 6))
barras = ax.barh(etiquetas_categoria, ventas_categoria.values, color='#2563eb')
ax.set(title='Las 10 categorías con mayores ventas de artículos',
       xlabel='Ventas (BRL)', ylabel='Categoría de producto')
ax.xaxis.set_major_formatter(FuncFormatter(lambda valor, _: moneda_br(valor)))
ax.bar_label(barras, labels=[moneda_br(v) for v in ventas_categoria.values], padding=4, fontsize=9)
ax.set_xlim(0, ventas_categoria.max() * 1.24)
ax.grid(axis='x', alpha=0.2)
ax.set_axisbelow(True)
fig.tight_layout()
fig.savefig(GRAFICOS / '03_top_categorias.png', dpi=170)
plt.close(fig)

print('\n=== TABLAS ANALIZADAS ===')
print(pd.DataFrame(resumen).to_string(index=False))
print('\n=== INDICADORES KPI ===')
print(indicadores.to_string(index=False))
print(f'\nResultados guardados en: {OUT}')
print('Se generaron 3 gráficos con etiquetas en español.')
print('Nota: ventas = suma de price en pedidos entregados; excluye freight_value.')
print('Nota: los meses extremos de 2016 y 2018 pueden estar incompletos.')
