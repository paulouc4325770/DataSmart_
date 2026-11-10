"""Grafo bipartito no dirigido vendedor–producto de transacciones reales de Olist.

Ejecutar: python src/grafos.py
El peso es número de filas de ítem entregado, no importe monetario.
"""

import argparse
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
import networkx as nx
import numpy as np
import pandas as pd

from asociacion import guardar_csv, leer_csv, sha256


ROOT = Path(__file__).resolve().parents[1]
COLUMNAS = ['order_id', 'order_item_id', 'seller_id', 'product_id', 'order_status', 'price']
INICIO = '<!-- INICIO RESULTADOS GRAFOS -->'
FIN = '<!-- FIN RESULTADOS GRAFOS -->'


def construir_grafo(items):
    if items[['order_id', 'order_item_id']].isna().any().any() or items.duplicated(['order_id', 'order_item_id']).any():
        raise ValueError('La clave order_id + order_item_id debe ser única y no nula; revisar preparación.')
    entregados = items.loc[items['order_status'].eq('delivered').fillna(False)].copy()
    sin_claves = entregados[['seller_id', 'product_id']].isna().any(axis=1)
    elegibles = entregados.loc[~sin_claves].copy()
    if elegibles.empty:
        raise ValueError('No hay ítems entregados con seller_id y product_id para construir el grafo.')
    # Un importe desconocido no impide contar un ítem ni se imputa como cero.
    precios = pd.to_numeric(elegibles['price'], errors='coerce').astype(float)
    elegibles['precio'] = precios.where(np.isfinite(precios) & precios.ge(0))
    grupo = elegibles.groupby(['seller_id', 'product_id'], sort=True)
    aristas = grupo.agg(peso=('order_item_id', 'size'), pedidos_distintos=('order_id', 'nunique'),
                        importes_conocidos=('precio', 'count'))
    aristas['valor_articulos_conocido'] = grupo['precio'].sum(min_count=1)
    aristas['importes_desconocidos'] = aristas['peso'] - aristas['importes_conocidos']
    aristas = aristas.reset_index()
    grafo = nx.Graph()
    # Prefijos impiden confundir identificadores iguales entre las dos particiones.
    for vendedor in sorted(elegibles['seller_id'].unique()):
        grafo.add_node('v:' + vendedor, identificador=vendedor, tipo_nodo='vendedor', bipartite=0)
    for producto in sorted(elegibles['product_id'].unique()):
        grafo.add_node('p:' + producto, identificador=producto, tipo_nodo='producto', bipartite=1)
    grafo.add_weighted_edges_from(
        (('v:' + fila.seller_id, 'p:' + fila.product_id, int(fila.peso)) for fila in aristas.itertuples()),
        weight='peso',
    )
    poblacion = {
        'items_entrada': len(items), 'items_entregados': len(entregados),
        'items_otros_estados_excluidos': len(items) - len(entregados),
        'items_entregados_sin_claves_excluidos': int(sin_claves.sum()),
        'items_utilizados': len(elegibles), 'pedidos_utilizados': int(elegibles['order_id'].nunique()),
        'importes_desconocidos': int(elegibles['precio'].isna().sum()),
    }
    if int(aristas['peso'].sum()) != len(elegibles) or not nx.is_bipartite(grafo):
        raise ValueError('Los pesos no concilian con los ítems o el grafo no es bipartito.')
    return grafo, aristas, poblacion


def calcular_metricas(grafo):
    componentes = sorted(nx.connected_components(grafo), key=lambda c: (-len(c), min(c)))
    pertenencia = {nodo: i for i, componente in enumerate(componentes) for nodo in componente}
    # Convergencia estricta: NetworkX usa len(G)*tol como criterio L1.
    pagerank = nx.pagerank(grafo, alpha=.85, weight='peso', max_iter=1000, tol=1e-12)
    grados = dict(grafo.degree())
    ponderados = dict(grafo.degree(weight='peso'))
    metricas = pd.DataFrame([
        {'nodo_id': nodo, 'identificador': atributos['identificador'], 'tipo_nodo': atributos['tipo_nodo'],
         'grado': grados[nodo], 'grado_ponderado': ponderados[nodo],
         'pagerank': pagerank[nodo], 'componente': pertenencia[nodo]}
        for nodo, atributos in sorted(grafo.nodes(data=True))
    ])
    resumen_componentes = pd.DataFrame([
        {'componente': i, 'nodos': len(componente),
         'vendedores': sum(grafo.nodes[n]['tipo_nodo'] == 'vendedor' for n in componente),
         'productos': sum(grafo.nodes[n]['tipo_nodo'] == 'producto' for n in componente),
         'aristas': grafo.subgraph(componente).number_of_edges()}
        for i, componente in enumerate(componentes)
    ])
    if not np.isfinite(metricas['pagerank']).all() or not np.isclose(metricas['pagerank'].sum(), 1, atol=1e-9):
        raise ValueError('PageRank no es finito o no suma uno.')
    if metricas['grado'].sum() != 2 * grafo.number_of_edges():
        raise ValueError('Los grados no concilian con las aristas.')
    return metricas, resumen_componentes


def graficar(grafo, metricas, carpeta, top_vendedores=5, productos_por_vendedor=12):
    carpeta.mkdir(parents=True, exist_ok=True)
    vendedores = metricas.loc[metricas['tipo_nodo'].eq('vendedor')].sort_values(
        ['grado_ponderado', 'identificador'], ascending=[False, True],
    )
    principales = vendedores.head(top_vendedores)['nodo_id'].tolist()
    seleccionados = set(principales)
    for vendedor in principales:
        vecinos = sorted(grafo[vendedor], key=lambda n: (-grafo[vendedor][n]['peso'], n))
        seleccionados.update(vecinos[:productos_por_vendedor])
    subgrafo = grafo.subgraph(sorted(seleccionados)).copy()
    posiciones = nx.spring_layout(subgrafo, seed=42, weight='peso', iterations=80)
    fig, ax = plt.subplots(figsize=(12, 8))
    nx.draw_networkx_edges(subgrafo, posiciones, ax=ax, alpha=.35,
                           width=[.5 + np.log1p(d['peso']) / 2 for _, _, d in subgrafo.edges(data=True)])
    for tipo, color, base in [('vendedor', '#c0392b', 350), ('producto', '#2874a6', 45)]:
        nodos = [n for n, d in subgrafo.nodes(data=True) if d['tipo_nodo'] == tipo]
        nx.draw_networkx_nodes(subgrafo, posiciones, nodelist=nodos, node_color=color,
                               node_size=[base + 10 * np.log1p(grafo.degree(n, weight='peso')) for n in nodos], ax=ax)
    pesos = dict(grafo.degree(weight='peso'))
    productos = sorted((n for n in subgrafo if n.startswith('p:')), key=lambda n: (-pesos[n], n))[:5]
    etiquetas = {n: n[:2] + grafo.nodes[n]['identificador'][:8] for n in principales + productos}
    nx.draw_networkx_labels(subgrafo, posiciones, labels=etiquetas, font_size=8, ax=ax)
    ax.set_title(f'Subgrafo comercial: {len(principales)} vendedores de mayor volumen\n'
                 f'Hasta {productos_por_vendedor} productos por vendedor; {subgrafo.number_of_nodes()} nodos')
    ax.legend(handles=[Line2D([], [], marker='o', linestyle='', color=c, label=t)
                        for t, c in [('Vendedor', '#c0392b'), ('Producto', '#2874a6')]])
    ax.axis('off')
    fig.tight_layout()
    fig.savefig(carpeta / 'grafo_vendedores_productos.png', dpi=160)
    plt.close(fig)
    top = vendedores.head(10).iloc[::-1]
    fig, ax = plt.subplots(figsize=(10, 5))
    barras = ax.barh(top['identificador'].str[:10], top['grado_ponderado'], color='#2874a6')
    ax.bar_label(barras, padding=3)
    ax.set(xlabel='Grado ponderado: ítems entregados', ylabel='seller_id (primeros 10 caracteres)',
           title='Diez principales vendedores por volumen de ítems')
    ax.margins(x=.15)
    fig.tight_layout()
    fig.savefig(carpeta / 'grafo_principales_vendedores.png', dpi=160)
    plt.close(fig)
    return {'top_vendedores': top_vendedores, 'productos_por_vendedor': productos_por_vendedor,
            'nodos': subgrafo.number_of_nodes(), 'aristas': subgrafo.number_of_edges(),
            'nodos_seleccionados': sorted(subgrafo), 'semilla_layout': 42,
            'criterio': 'Top vendedores por grado ponderado; top productos por peso de su arista; subgrafo inducido.'}


def publicar_resumen(salida, texto):
    ruta = salida / 'docs' / 'clustering_y_grafos.md'
    if ruta.is_file():
        contenido = ruta.read_text(encoding='utf-8')
        if INICIO in contenido and FIN in contenido:
            antes, resto = contenido.split(INICIO, 1)
            _, despues = resto.split(FIN, 1)
            ruta.write_text(antes + INICIO + '\n\n' + texto + '\n\n' + FIN + despues, encoding='utf-8')


def ejecutar(items_csv, salida, top_vendedores=5, productos_por_vendedor=12):
    items = leer_csv(items_csv, COLUMNAS, 'items_procesados.csv')
    grafo, aristas, poblacion = construir_grafo(items)
    metricas, componentes = calcular_metricas(grafo)
    peso_total = int(aristas['peso'].sum())
    if metricas['grado_ponderado'].sum() != 2 * peso_total:
        raise ValueError('La suma de grados ponderados no coincide con dos veces el peso de aristas.')
    resultados = salida / 'resultados'
    guardar_csv(aristas, resultados / 'grafo_aristas.csv')
    guardar_csv(metricas, resultados / 'grafo_metricas.csv')
    guardar_csv(componentes, resultados / 'grafo_componentes.csv')
    visualizacion = graficar(grafo, metricas, resultados / 'graficos', top_vendedores, productos_por_vendedor)
    metadata = {
        'fuente': str(items_csv), 'sha256_entrada': sha256(items_csv),
        'python': platform.python_version(), 'networkx': nx.__version__, 'pandas': pd.__version__,
        'numpy': np.__version__, 'matplotlib': matplotlib.__version__,
        'poblacion': poblacion, 'nodos': grafo.number_of_nodes(), 'aristas': grafo.number_of_edges(),
        'vendedores': int(metricas['tipo_nodo'].eq('vendedor').sum()),
        'productos': int(metricas['tipo_nodo'].eq('producto').sum()),
        'componentes': len(componentes), 'peso_total': peso_total,
        'pagerank': {'alpha': .85, 'tol': 1e-12, 'max_iter': 1000, 'weight': 'peso', 'suma': float(metricas['pagerank'].sum())},
        'visualizacion': visualizacion,
    }
    (resultados / 'grafos_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lineas = [
        f'**Red real: {metadata["nodos"]:,} nodos ({metadata["vendedores"]:,} vendedores y {metadata["productos"]:,} productos), {metadata["aristas"]:,} aristas y {len(componentes):,} componentes.**',
        f'Ítems: {poblacion["items_entrada"]:,} de entrada, {poblacion["items_entregados"]:,} entregados, {poblacion["items_utilizados"]:,} utilizados; peso total {peso_total:,}. '
        f'Excluidos: {poblacion["items_otros_estados_excluidos"]:,} de otros estados y {poblacion["items_entregados_sin_claves_excluidos"]:,} entregados sin claves. '
        f'Importes desconocidos: {poblacion["importes_desconocidos"]:,}; no afectan al conteo de ítems.',
        '\nPrincipales componentes:\n\n| Componente | Nodos | Vendedores | Productos | Aristas |\n|---:|---:|---:|---:|---:|',
    ]
    for fila in componentes.head(10).itertuples():
        lineas.append(f'| {fila.componente} | {fila.nodos} | {fila.vendedores} | {fila.productos} | {fila.aristas} |')
    for tipo in ['vendedor', 'producto']:
        top = metricas.loc[metricas['tipo_nodo'].eq(tipo)].sort_values(['grado_ponderado', 'identificador'], ascending=[False, True]).head(5)
        lineas += [f'\nPrincipales nodos de tipo **{tipo}** por ítems:\n',
                   '| Identificador | Grado | Ítems | PageRank | Componente |\n|---|---:|---:|---:|---:|']
        for fila in top.itertuples():
            lineas.append(f'| `{fila.identificador}` | {fila.grado} | {fila.grado_ponderado} | {fila.pagerank:.7f} | {fila.componente} |')
        lider = top.iloc[0]
        significado = 'productos distintos vendidos' if tipo == 'vendedor' else 'vendedores asociados'
        lineas.append(f'\nEl {tipo} `{lider["identificador"]}` lidera el volumen con {lider["grado_ponderado"]:,} ítems y {lider["grado"]:,} {significado}. No equivale a liderar ingresos o calidad.')
        central = metricas.loc[metricas['tipo_nodo'].eq(tipo)].sort_values(['pagerank', 'identificador'], ascending=[False, True]).iloc[0]
        lineas.append(f'El mayor PageRank dentro de este tipo corresponde a `{central["identificador"]}` ({central["pagerank"]:.7f}); es centralidad estructural ponderada, no reputación.')
    lineas += ['\nRelaciones más intensas:\n\n| seller_id | product_id | Ítems | Pedidos distintos |\n|---|---|---:|---:|']
    for fila in aristas.sort_values(['peso', 'seller_id', 'product_id'], ascending=[False, True, True]).head(5).itertuples():
        lineas.append(f'| `{fila.seller_id}` | `{fila.product_id}` | {fila.peso} | {fila.pedidos_distintos} |')
    productos_compartidos = int(metricas.loc[metricas['tipo_nodo'].eq('producto'), 'grado'].gt(1).sum())
    lineas += [f'\nHay {productos_compartidos:,} productos asociados a más de un vendedor. El componente mayor reúne {int(componentes.iloc[0]["nodos"]):,} nodos ({componentes.iloc[0]["nodos"] / len(metricas) * 100:.2f}% de la red).',
               f'Visualización: top {top_vendedores} vendedores por ítems y hasta {productos_por_vendedor} productos por vendedor según peso de arista; subgrafo inducido de {visualizacion["nodos"]} nodos y {visualizacion["aristas"]} aristas; semilla 42. Los identificadores completos están en los CSV.',
               'Conclusión: las conexiones reflejan asociaciones comerciales observadas y concentración de ítems; no son rutas logísticas, preferencias de compradores ni prueba de competencia. Las métricas se calcularon sobre toda la red, no sobre el dibujo.']
    texto = '\n\n'.join(lineas[:2]) + '\n' + '\n'.join(lineas[2:])
    (resultados / 'grafos_resumen.md').write_text(texto + '\n', encoding='utf-8')
    publicar_resumen(salida, texto)
    print(f'Grafo: {metadata["nodos"]:,} nodos; {metadata["aristas"]:,} aristas; {len(componentes):,} componentes; peso total={peso_total:,}.')
    print(f'CSV, metadatos y gráficos: {resultados}')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--items', type=Path, default=ROOT / 'data/processed/items_procesados.csv')
    parser.add_argument('--output-root', type=Path, default=ROOT)
    parser.add_argument('--top-vendedores', type=int, default=5, help='Entre 1 y 10 vendedores para el dibujo.')
    parser.add_argument('--productos-por-vendedor', type=int, default=12, help='Entre 1 y 20 productos por vendedor para el dibujo.')
    args = parser.parse_args()
    if not 1 <= args.top_vendedores <= 10 or not 1 <= args.productos_por_vendedor <= 20:
        parser.error('Visualización limitada a 1–10 vendedores y 1–20 productos por vendedor.')
    try:
        ejecutar(args.items.resolve(), args.output_root.resolve(), args.top_vendedores, args.productos_por_vendedor)
    except (OSError, ValueError, nx.PowerIterationFailedConvergence) as error:
        parser.exit(1, f'Error de grafos: {error}\n')


if __name__ == '__main__':
    main()
