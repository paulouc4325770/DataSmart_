"""Análisis de Redes y Grafos de Relaciones Vendedor–Producto en Olist.

Rol: Brandon — Análisis de relaciones y grafos (DataSmart - Minería de Datos UNMSM FISI).

Ejecutar:
    python src/grafos.py

Población y significado:
    - Red Bipartita Vendedor–Producto construida desde items_procesados.csv.
    - Población: pedidos entregados con ítems válidos (110.197 ítems analizados).
    - Arista (seller_id <-> product_id): representa la venta efectiva de un producto por
      un comerciante en el marketplace, ponderada por la cantidad total de unidades despachadas.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
GRAFICOS = ROOT / 'resultados' / 'graficos'
GRAFICOS.mkdir(parents=True, exist_ok=True)


def cargar_datos_items(ruta_items: Path, solo_entregados: bool = True):
    """Carga los ítems procesados y extrae relaciones vendedor-producto."""
    df = pd.read_csv(ruta_items, low_memory=False)
    if solo_entregados:
        df = df.loc[df['order_status'] == 'delivered'].copy()
    return df


def construir_grafo_bipartito(df_items: pd.DataFrame):
    """Construye el grafo bipartito ponderado (Vendedor <-> Producto)."""
    # 1. Agregar repeticiones para obtener peso_items y valor_total_brl
    aristas_df = df_items.groupby(['seller_id', 'product_id']).agg(
        peso_items=('order_item_id', 'count'),
        valor_total_brl=('price', 'sum')
    ).reset_index()
    aristas_df['valor_total_brl'] = aristas_df['valor_total_brl'].round(2)

    # 2. Catálogos descriptivos de nodos
    cat_vendedores = df_items.groupby('seller_id').agg(
        ciudad=('seller_city', 'first'),
        estado=('seller_state', 'first')
    ).reset_index()

    cat_productos = df_items.groupby('product_id').agg(
        categoria=('categoria_presentacion', 'first')
    ).reset_index()

    dict_sellers = {r['seller_id']: {'ciudad': r['ciudad'], 'estado': r['estado']} for _, r in cat_vendedores.iterrows()}
    dict_products = {r['product_id']: {'categoria': r['categoria']} for _, r in cat_productos.iterrows()}

    # 3. Instanciar NetworkX Graph
    G = nx.Graph()
    for s_id, info in dict_sellers.items():
        G.add_node(s_id, tipo='vendedor', label=s_id[:8] + '...', estado=info['estado'], ciudad=info['ciudad'])

    for p_id, info in dict_products.items():
        G.add_node(p_id, tipo='producto', label=p_id[:8] + '...', categoria=info['categoria'])

    for _, row in aristas_df.iterrows():
        G.add_edge(
            row['seller_id'],
            row['product_id'],
            weight=int(row['peso_items']),
            monto=float(row['valor_total_brl'])
        )

    return G, aristas_df, dict_sellers, dict_products


def calcular_metricas_red(G: nx.Graph):
    """Calcula métricas de centralidad, componentes conexas y PageRank."""
    # Componentes conexas
    componentes = list(nx.connected_components(G))
    componentes_ordenadas = sorted(componentes, key=len, reverse=True)
    comp_map = {}
    for comp_id, comp_nodes in enumerate(componentes_ordenadas, start=1):
        for node in comp_nodes:
            comp_map[node] = comp_id

    # Grado simple y Grado ponderado (fuerza / volumen de ítems)
    grados = dict(G.degree())
    grados_ponderados = dict(G.degree(weight='weight'))

    # PageRank ponderado
    pagerank = nx.pagerank(G, weight='weight', max_iter=100)

    # Consolidar dataframe de métricas por nodo
    filas = []
    for node, attrs in G.nodes(data=True):
        filas.append({
            'nodo': node,
            'tipo_nodo': attrs.get('tipo', 'desconocido'),
            'etiqueta_corta': attrs.get('label', node[:8]),
            'grado': int(grados.get(node, 0)),
            'grado_ponderado': int(grados_ponderados.get(node, 0)),
            'pagerank': round(float(pagerank.get(node, 0.0)), 7),
            'componente_id': int(comp_map.get(node, 0)),
            'estado': attrs.get('estado', ''),
            'ciudad': attrs.get('ciudad', ''),
            'categoria': attrs.get('categoria', ''),
        })

    metricas_df = pd.DataFrame(filas).sort_values('pagerank', ascending=False)
    return metricas_df, componentes_ordenadas, pagerank


def extraer_subgrafo_legible(G: nx.Graph, metricas_df: pd.DataFrame, max_vendedores: int = 12, max_productos_por_vendedor: int = 4):
    """Selecciona un subgrafo representativo y altamente legible para inspección e interfaz."""
    top_sellers = metricas_df.loc[metricas_df['tipo_nodo'] == 'vendedor'].head(max_vendedores)['nodo'].tolist()

    sub_nodes = set(top_sellers)
    for s_node in top_sellers:
        # Obtener los productos más vendidos de cada uno
        vecinos = sorted(
            G[s_node].items(),
            key=lambda item: item[1]['weight'],
            reverse=True
        )[:max_productos_por_vendedor]
        for p_node, _ in vecinos:
            sub_nodes.add(p_node)

    subG = G.subgraph(sub_nodes).copy()

    # Formato JSON listo para la Web (D3 / SVG)
    nodos_json = []
    for n in subG.nodes():
        attrs = subG.nodes[n]
        deg = subG.degree[n]
        deg_w = subG.degree(weight='weight')[n]
        nodos_json.append({
            'id': n,
            'label': attrs.get('label', n[:8]),
            'tipo': attrs.get('tipo'),
            'categoria': attrs.get('categoria', ''),
            'estado': attrs.get('estado', ''),
            'ciudad': attrs.get('ciudad', ''),
            'grado': int(deg),
            'grado_ponderado': int(deg_w),
        })

    enlaces_json = []
    for u, v, d in subG.edges(data=True):
        enlaces_json.append({
            'source': u,
            'target': v,
            'weight': int(d['weight']),
            'monto': float(d['monto']),
        })

    subgrafo_dict = {
        'total_nodos': len(nodos_json),
        'total_enlaces': len(enlaces_json),
        'criterio_seleccion': f'Top {max_vendedores} vendedores por PageRank y sus hasta {max_productos_por_vendedor} productos estrella',
        'nodes': nodos_json,
        'links': enlaces_json,
    }

    return subG, subgrafo_dict


def exportar_grafico_red(subG: nx.Graph, out_graficos: Path):
    """Genera la visualización gráfica de la red legible."""
    fig, ax = plt.subplots(figsize=(13, 8.5))
    pos = nx.spring_layout(subG, k=0.45, seed=42)

    vendedores = [n for n, d in subG.nodes(data=True) if d.get('tipo') == 'vendedor']
    productos = [n for n, d in subG.nodes(data=True) if d.get('tipo') == 'producto']

    # Dibujar aristas con grosor proporcional al peso
    pesos = [subG[u][v]['weight'] for u, v in subG.edges()]
    max_p = max(pesos) if pesos else 1
    grosores = [1.2 + (w / max_p) * 4.5 for w in pesos]

    nx.draw_networkx_edges(subG, pos, width=grosores, alpha=0.35, edge_color='#64748b', ax=ax)

    # Dibujar nodos Vendedores (Azul) y Productos (Esmeralda/Verde)
    nx.draw_networkx_nodes(subG, pos, nodelist=vendedores, node_color='#2563eb', node_size=550, alpha=0.9, label='Vendedores (Hubs)', ax=ax)
    nx.draw_networkx_nodes(subG, pos, nodelist=productos, node_color='#10b981', node_size=280, alpha=0.85, label='Productos Estrella', ax=ax)

    # Etiquetas de vendedores
    labels_vendedores = {v: f"Vend {subG.nodes[v]['estado']}\n({subG.nodes[v]['label']})" for v in vendedores}
    nx.draw_networkx_labels(subG, pos, labels=labels_vendedores, font_size=8, font_weight='bold', font_color='#0f172a', ax=ax)

    ax.set_title('Subgrafo Bipartito Olist: Vendedores Principales y Productos Más Despachados', fontsize=12, fontweight='bold', pad=14)
    ax.legend(loc='upper right', frameon=True, fontsize=9.5)
    ax.axis('off')

    fig.tight_layout()
    fig.savefig(out_graficos / '06_grafo_red_vendedor_producto.png', dpi=170)
    plt.close(fig)


def ejecutar(
    ruta_items: Path = ROOT / 'data' / 'processed' / 'items_procesados.csv',
    salida_dir: Path = ROOT / 'resultados',
    solo_entregados: bool = True,
):
    salida_dir.mkdir(parents=True, exist_ok=True)
    graficos_dir = salida_dir / 'graficos'
    graficos_dir.mkdir(parents=True, exist_ok=True)

    print(f"Cargando ítems desde {ruta_items} (solo entregados: {solo_entregados})...")
    df_items = cargar_datos_items(ruta_items, solo_entregados=solo_entregados)
    print(f"Ítems analizados: {len(df_items):,}")

    G, aristas_df, _, _ = construir_grafo_bipartito(df_items)
    n_vendedores = len([n for n, d in G.nodes(data=True) if d.get('tipo') == 'vendedor'])
    n_productos = len([n for n, d in G.nodes(data=True) if d.get('tipo') == 'producto'])
    print(f"Red construida: {G.number_of_nodes():,} nodos ({n_vendedores:,} vendedores, {n_productos:,} productos) y {G.number_of_edges():,} aristas.")

    print("Calculando centralidades, componentes y PageRank ponderado...")
    metricas_df, componentes, pagerank = calcular_metricas_red(G)

    print(f"Número de componentes conexas: {len(componentes):,}")
    print(f"Componente gigante: {len(componentes[0]):,} nodos ({round(len(componentes[0])/G.number_of_nodes()*100, 2)}% de la red).")

    # Extraer y exportar subgrafo legible
    subG, subgrafo_dict = extraer_subgrafo_legible(G, metricas_df)
    print(f"Subgrafo legible extraído: {subG.number_of_nodes()} nodos y {subG.number_of_edges()} enlaces.")

    # Guardar archivos CSV y JSON
    aristas_df.to_csv(salida_dir / 'grafo_aristas.csv', index=False, encoding='utf-8-sig')
    metricas_df.to_csv(salida_dir / 'grafo_metricas.csv', index=False, encoding='utf-8-sig')

    with open(salida_dir / 'grafo_subgrafo.json', 'w', encoding='utf-8') as f:
        json.dump(subgrafo_dict, f, indent=2, ensure_ascii=False)

    # Generar visualización
    exportar_grafico_red(subG, graficos_dir)

    top_vendedores = metricas_df.loc[metricas_df['tipo_nodo'] == 'vendedor'].head(5).to_dict(orient='records')
    top_productos = metricas_df.loc[metricas_df['tipo_nodo'] == 'producto'].head(5).to_dict(orient='records')

    metadata = {
        'ejecutado_en_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(),
        'poblacion': 'pedidos entregados con ítems',
        'items_analizados': len(df_items),
        'total_nodos': G.number_of_nodes(),
        'total_vendedores': n_vendedores,
        'total_productos': n_productos,
        'total_aristas': G.number_of_edges(),
        'es_bipartito': True,
        'componentes_conexas': len(componentes),
        'tamano_componente_gigante': len(componentes[0]),
        'densidad': round(nx.density(G), 7),
        'top_vendedores_pagerank': top_vendedores,
        'top_productos_pagerank': top_productos,
        'subgrafo': {
            'nodos': subG.number_of_nodes(),
            'aristas': subG.number_of_edges(),
            'archivo_json': 'grafo_subgrafo.json',
            'archivo_png': '06_grafo_red_vendedor_producto.png',
        },
    }

    with open(salida_dir / 'grafo_metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\nResultados y métricas del grafo guardados en: {salida_dir}")
    print(f"Gráfico del subgrafo generado en: {graficos_dir / '06_grafo_red_vendedor_producto.png'}")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--items', type=Path, default=ROOT / 'data' / 'processed' / 'items_procesados.csv', help='Ruta a items_procesados.csv')
    parser.add_argument('--salida-dir', type=Path, default=ROOT / 'resultados', help='Directorio de salida')
    parser.add_argument('--todos-los-estados', action='store_true', help='Incluir todos los estados (no solo delivered)')
    args = parser.parse_args()

    ejecutar(
        ruta_items=args.items.resolve(),
        salida_dir=args.salida_dir.resolve(),
        solo_entregados=not args.todos_los_estados,
    )


if __name__ == '__main__':
    main()
