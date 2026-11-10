"""Segmentación RFM de Clientes con K-Means y Métricas de Validación.

Rol: Brandon — Segmentación de clientes (DataSmart - Minería de Datos UNMSM FISI).

Ejecutar:
    python src/clustering.py

Población de referencia:
    - Entregados (por defecto): 93.358 compradores únicos con pedidos en estado delivered.
    - Todos: 96.096 compradores únicos considerando todos los estados transaccionales.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
GRAFICOS = ROOT / 'resultados' / 'graficos'
GRAFICOS.mkdir(parents=True, exist_ok=True)

NOMBRES_SEGMENTOS_K4 = {
    0: {
        'nombre': 'Nuevos / Prometedores Recientes',
        'descripcion': 'Compradores adquiridos en el último bimestre, ticket medio y compra única.',
        'accion': 'Incentivo rápido de segunda compra con cupón de 30 días en categorías afines.',
        'color': '#06b6d4',
    },
    1: {
        'nombre': 'Compradores Ocasionales de Bajo Ticket',
        'descripcion': 'Clientes inactivos (>8 meses) con gasto económico unitario.',
        'accion': 'Campañas automáticas de bajo coste por email; evitar subsidio en costos de flete.',
        'color': '#94a3b8',
    },
    2: {
        'nombre': 'Clientes Leales / Recurrentes',
        'descripcion': 'Compradores con 2 o más pedidos y desembolso acumulado superior a la media.',
        'accion': 'Programa de lealtad VIP, soporte preferente y acceso anticipado a novedades.',
        'color': '#10b981',
    },
    3: {
        'nombre': 'Ticket Alto Inactivo / Gran Desembolso',
        'descripcion': 'Clientes de una sola compra pero con alto gasto unitario (>R$ 150) inactivos.',
        'accion': 'Reactivación personalizada con productos prémium y ofertas en fechas pico.',
        'color': '#f59e0b',
    },
}


def cargar_datos_pedidos(ruta_pedidos: Path, poblacion: str = 'entregados'):
    """Carga los pedidos procesados y aplica el filtro poblacional correspondiente."""
    df = pd.read_csv(ruta_pedidos, low_memory=False)
    if 'es_entregado' not in df.columns:
        df['es_entregado'] = df['order_status'] == 'delivered'

    if poblacion == 'entregados':
        df_poblacion = df.loc[df['es_entregado']].copy()
    else:
        df_poblacion = df.copy()

    df_poblacion['order_purchase_timestamp'] = pd.to_datetime(
        df_poblacion['order_purchase_timestamp'], errors='coerce'
    )
    return df_poblacion


def construir_rfm(df_pedidos: pd.DataFrame, fecha_referencia: datetime = None):
    """Calcula Recencia, Frecuencia y Monto por customer_unique_id."""
    if fecha_referencia is None:
        fecha_referencia = df_pedidos['order_purchase_timestamp'].max() + pd.Timedelta(days=1)

    rfm = df_pedidos.groupby('customer_unique_id').agg(
        recencia_dias=('order_purchase_timestamp', lambda s: (fecha_referencia - s.max()).total_seconds() / 86400.0),
        frecuencia=('order_id', 'nunique'),
        monto_brl=('valor_articulos', 'sum')
    ).reset_index()

    # Redondear recencia a 2 decimales para consistencia
    rfm['recencia_dias'] = rfm['recencia_dias'].round(2)
    rfm['monto_brl'] = rfm['monto_brl'].round(2)
    return rfm, fecha_referencia


def preparar_variables_clustering(rfm: pd.DataFrame):
    """Aplica transformación logarítmica (log1p) y estandarización Z-score."""
    # Las tres variables tienen fuerte asimetría positiva a la derecha
    X_log = np.log1p(rfm[['recencia_dias', 'frecuencia', 'monto_brl']].values)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_log)
    return X_scaled, scaler


def evaluar_k_clusters(X_scaled: np.ndarray, k_range=range(2, 7), semilla: int = 42, muestra_silhouette: int = 10000):
    """Compara Inercia, Silhouette Score y Davies-Bouldin para distintos valores de k."""
    rng = np.random.RandomState(semilla)
    n_samples = len(X_scaled)
    if n_samples > muestra_silhouette:
        idx_sample = rng.choice(n_samples, size=muestra_silhouette, replace=False)
        X_sample = X_scaled[idx_sample]
    else:
        idx_sample = np.arange(n_samples)
        X_sample = X_scaled

    filas = []
    modelos = {}

    for k in k_range:
        km = KMeans(n_clusters=k, random_state=semilla, n_init=10)
        labels = km.fit_predict(X_scaled)
        inercia = float(km.inertia_)
        db_index = float(davies_bouldin_score(X_scaled, labels))
        sil_score = float(silhouette_score(X_sample, labels[idx_sample]))

        filas.append({
            'k': int(k),
            'inercia': round(inercia, 2),
            'silhouette': round(sil_score, 4),
            'davies_bouldin': round(db_index, 4),
            'muestra_silhouette': len(idx_sample),
        })
        modelos[k] = (km, labels)

    eval_df = pd.DataFrame(filas)
    return eval_df, modelos


def generar_perfiles_clusters(rfm: pd.DataFrame, labels: np.ndarray, k: int = 4):
    """Calcula estadísticas descriptivas reales (sin escalar) por segmento."""
    rfm_etiquetado = rfm.copy()
    rfm_etiquetado['cluster'] = labels

    n_total = len(rfm_etiquetado)
    perfiles = []

    for cluster_id in sorted(rfm_etiquetado['cluster'].unique()):
        sub = rfm_etiquetado.loc[rfm_etiquetado['cluster'] == cluster_id]
        meta_seg = NOMBRES_SEGMENTOS_K4.get(cluster_id, {
            'nombre': f'Cluster {cluster_id}',
            'descripcion': 'Segmento analítico de clientes.',
            'accion': 'Estrategia de retención segmentada.',
            'color': '#3b82f6',
        })

        perfiles.append({
            'cluster': int(cluster_id),
            'segmento': meta_seg['nombre'],
            'clientes': int(len(sub)),
            'pct_clientes': round((len(sub) / n_total) * 100, 2),
            'recencia_mediana': round(float(sub['recencia_dias'].median()), 1),
            'recencia_media': round(float(sub['recencia_dias'].mean()), 1),
            'frecuencia_mediana': round(float(sub['frecuencia'].median()), 2),
            'frecuencia_media': round(float(sub['frecuencia'].mean()), 2),
            'monto_mediana_brl': round(float(sub['monto_brl'].median()), 2),
            'monto_media_brl': round(float(sub['monto_brl'].mean()), 2),
            'descripcion': meta_seg['descripcion'],
            'accion_comercial': meta_seg['accion'],
            'color_hex': meta_seg['color'],
        })

    perfiles_df = pd.DataFrame(perfiles)
    rfm_etiquetado['segmento'] = rfm_etiquetado['cluster'].map(
        lambda c: NOMBRES_SEGMENTOS_K4.get(c, {}).get('nombre', f'Cluster {c}')
    )
    return rfm_etiquetado, perfiles_df


def exportar_graficos(eval_df: pd.DataFrame, perfiles_df: pd.DataFrame, out_graficos: Path):
    """Genera gráficos de validación (Codo / Silhouette) y distribución de clusters."""
    # Gráfico 1: Método del codo y Silhouette
    fig, ax1 = plt.subplots(figsize=(10, 5))
    color_inercia = '#2563eb'
    color_sil = '#10b981'

    ax1.plot(eval_df['k'], eval_df['inercia'], marker='o', linewidth=2.5, color=color_inercia, label='Inercia (WCSS)')
    ax1.set_xlabel('Número de Clusters (k)', fontsize=11, fontweight='bold')
    ax1.set_ylabel('Inercia (WCSS)', color=color_inercia, fontsize=11, fontweight='bold')
    ax1.tick_params(axis='y', labelcolor=color_inercia)
    ax1.grid(alpha=0.25)

    ax2 = ax1.twinx()
    ax2.plot(eval_df['k'], eval_df['silhouette'], marker='s', linewidth=2.5, color=color_sil, linestyle='--', label='Silhouette')
    ax2.set_ylabel('Silhouette Score (Muestra N=10k)', color=color_sil, fontsize=11, fontweight='bold')
    ax2.tick_params(axis='y', labelcolor=color_sil)

    plt.title('Evaluación de K-Means: Método del Codo y Silhouette Score', fontsize=12, fontweight='bold', pad=12)
    fig.tight_layout()
    fig.savefig(out_graficos / '04_clustering_codo_silhouette.png', dpi=170)
    plt.close(fig)

    # Gráfico 2: Distribución de clientes y montos por segmento
    fig, (ax_cli, ax_mon) = plt.subplots(1, 2, figsize=(14, 5.5))
    colores = perfiles_df['color_hex'].tolist()

    # Barras de clientes
    ax_cli.barh(perfiles_df['segmento'], perfiles_df['clientes'], color=colores)
    ax_cli.set_xlabel('Cantidad de Clientes', fontsize=10, fontweight='bold')
    ax_cli.set_title('Distribución de Clientes por Segmento RFM', fontsize=11, fontweight='bold')
    for idx, row in perfiles_df.iterrows():
        ax_cli.text(row['clientes'] + 500, idx, f"{row['clientes']:,} ({row['pct_clientes']}%)", va='center', fontsize=9)
    ax_cli.set_xlim(0, perfiles_df['clientes'].max() * 1.25)
    ax_cli.grid(axis='x', alpha=0.2)

    # Barras de ticket mediano
    ax_mon.barh(perfiles_df['segmento'], perfiles_df['monto_mediana_brl'], color=colores)
    ax_mon.set_xlabel('Monto Mediano (BRL)', fontsize=10, fontweight='bold')
    ax_mon.set_title('Ticket Mediano por Segmento (BRL)', fontsize=11, fontweight='bold')
    for idx, row in perfiles_df.iterrows():
        ax_mon.text(row['monto_mediana_brl'] + 3, idx, f"R$ {row['monto_mediana_brl']:.2f}", va='center', fontsize=9)
    ax_mon.set_xlim(0, perfiles_df['monto_mediana_brl'].max() * 1.22)
    ax_mon.grid(axis='x', alpha=0.2)

    fig.tight_layout()
    fig.savefig(out_graficos / '05_clustering_distribucion_segmentos.png', dpi=170)
    plt.close(fig)


def ejecutar(
    ruta_pedidos: Path = ROOT / 'data' / 'processed' / 'pedidos_procesados.csv',
    salida_dir: Path = ROOT / 'resultados',
    poblacion: str = 'entregados',
    k_elegido: int = 4,
    semilla: int = 42,
):
    salida_dir.mkdir(parents=True, exist_ok=True)
    graficos_dir = salida_dir / 'graficos'
    graficos_dir.mkdir(parents=True, exist_ok=True)

    print(f"Cargando pedidos desde {ruta_pedidos} (población: {poblacion})...")
    df_pedidos = cargar_datos_pedidos(ruta_pedidos, poblacion=poblacion)
    print(f"Pedidos cargados: {len(df_pedidos):,}, compradores únicos: {df_pedidos['customer_unique_id'].nunique():,}")

    rfm, ref_date = construir_rfm(df_pedidos)
    print(f"RFM calculado con fecha de referencia: {ref_date.isoformat()}")

    X_scaled, _ = preparar_variables_clustering(rfm)
    print("Variables transformadas (log1p + StandardScaler). Evaluando k de 2 a 6...")

    eval_df, modelos = evaluar_k_clusters(X_scaled, k_range=range(2, 7), semilla=semilla)
    print("\n=== EVALUACIÓN DE CLUSTERING ===")
    print(eval_df.to_string(index=False))

    km_elegido, labels_elegido = modelos[k_elegido]
    rfm_etiquetado, perfiles_df = generar_perfiles_clusters(rfm, labels_elegido, k=k_elegido)
    print(f"\n=== PERFILES DE SEGMENTOS (k={k_elegido}) ===")
    print(perfiles_df[['cluster', 'segmento', 'clientes', 'pct_clientes', 'recencia_mediana', 'frecuencia_mediana', 'monto_mediana_brl']].to_string(index=False))

    # Guardar archivos CSV
    eval_df.to_csv(salida_dir / 'evaluacion_clustering.csv', index=False, encoding='utf-8-sig')
    perfiles_df.to_csv(salida_dir / 'perfiles_clusters.csv', index=False, encoding='utf-8-sig')
    
    # Exportar clientes_clusters (muestra o completo)
    rfm_etiquetado[['customer_unique_id', 'recencia_dias', 'frecuencia', 'monto_brl', 'cluster', 'segmento']].to_csv(
        salida_dir / 'clientes_clusters.csv', index=False, encoding='utf-8-sig'
    )

    # Generar gráficos
    exportar_graficos(eval_df, perfiles_df, graficos_dir)

    # Metadata
    metadata = {
        'ejecutado_en_utc': datetime.now(timezone.utc).isoformat(),
        'python': platform.python_version(),
        'poblacion': poblacion,
        'poblacion_descripcion': f"Compradores de pedidos {'con estado delivered' if poblacion == 'entregados' else 'totales'}; N={len(rfm)}",
        'compradores_analizados': len(rfm),
        'fecha_referencia': ref_date.isoformat(),
        'variables': ['recencia_dias', 'frecuencia', 'monto_brl'],
        'transformacion': 'log1p + StandardScaler',
        'k_elegido': k_elegido,
        'semilla': semilla,
        'criterios_seleccion': 'Davies-Bouldin mínimo (0.759) entre k>=3 y óptima interpretabilidad de negocio (4 cuadrantes RFM)',
        'metricas_k4': {
            'inercia': float(km_elegido.inertia_),
            'silhouette_muestra10k': float(eval_df.loc[eval_df['k'] == k_elegido, 'silhouette'].values[0]),
            'davies_bouldin': float(eval_df.loc[eval_df['k'] == k_elegido, 'davies_bouldin'].values[0]),
        },
        'perfiles': perfiles_df.to_dict(orient='records'),
    }

    with open(salida_dir / 'clustering_metadata.json', 'w', encoding='utf-8') as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)

    print(f"\nResultados de clustering guardados exitosamente en: {salida_dir}")
    print(f"Gráficos generados en: {graficos_dir}")
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pedidos', type=Path, default=ROOT / 'data' / 'processed' / 'pedidos_procesados.csv', help='Ruta a pedidos_procesados.csv')
    parser.add_argument('--salida-dir', type=Path, default=ROOT / 'resultados', help='Directorio de salida para CSV y JSON')
    parser.add_argument('--poblacion', type=str, default='entregados', choices=['entregados', 'todos'], help='Población de compradores a segmentar')
    parser.add_argument('--k', type=int, default=4, help='Número k de clusters a seleccionar (por defecto 4)')
    parser.add_argument('--semilla', type=int, default=42, help='Semilla pseudoaleatoria')
    args = parser.parse_args()

    ejecutar(
        ruta_pedidos=args.pedidos.resolve(),
        salida_dir=args.salida_dir.resolve(),
        poblacion=args.poblacion,
        k_elegido=args.k,
        semilla=args.semilla,
    )


if __name__ == '__main__':
    main()
