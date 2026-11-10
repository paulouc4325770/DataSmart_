"""Segmentación RFM reproducible de compradores reales de Olist.

Ejecutar: python src/clustering.py
Requiere data/processed/pedidos_procesados.csv; no genera datos de demostración.
"""

import argparse
import json
from pathlib import Path
import platform

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn
from sklearn.cluster import KMeans
from sklearn.metrics import davies_bouldin_score, silhouette_score
from sklearn.preprocessing import StandardScaler
from threadpoolctl import threadpool_limits

from asociacion import guardar_csv, leer_csv, sha256


ROOT = Path(__file__).resolve().parents[1]
VARIABLES = ['recencia', 'frecuencia', 'monto']
COLUMNAS = ['order_id', 'customer_unique_id', 'order_status',
            'order_purchase_timestamp', 'valor_articulos']
INICIO = '<!-- INICIO RESULTADOS CLUSTERING -->'
FIN = '<!-- FIN RESULTADOS CLUSTERING -->'


def construir_rfm(pedidos, fecha_referencia=None):
    """Excluye compradores con algún pedido entregado incompleto, no sumas parciales."""
    if pedidos['order_id'].isna().any() or pedidos['order_id'].duplicated().any():
        raise ValueError('order_id debe ser único y no nulo; revisar la preparación.')
    entregados = pedidos.loc[pedidos['order_status'].eq('delivered').fillna(False)].copy()
    if entregados.empty:
        raise ValueError('No hay pedidos delivered para construir RFM.')
    entregados['compra'] = pd.to_datetime(
        entregados['order_purchase_timestamp'], format='ISO8601', errors='coerce',
    )
    entregados['importe'] = pd.to_numeric(entregados['valor_articulos'], errors='coerce')
    incompleto = (entregados['compra'].isna() | entregados['importe'].isna()
                  | ~np.isfinite(entregados['importe'].astype(float))
                  | entregados['importe'].lt(0).fillna(False))
    sin_id = entregados['customer_unique_id'].isna()
    compradores_incompletos = entregados.loc[incompleto & ~sin_id, 'customer_unique_id'].unique()
    excluir = sin_id | entregados['customer_unique_id'].isin(compradores_incompletos)
    elegibles = entregados.loc[~excluir].copy()
    if elegibles.empty:
        raise ValueError('No hay compradores con pedidos entregados completos para RFM.')
    referencia = (elegibles['compra'].max().normalize() + pd.Timedelta(1, unit='D')
                  if fecha_referencia is None else pd.Timestamp(fecha_referencia).normalize())
    if referencia.tzinfo is not None or referencia <= elegibles['compra'].max():
        raise ValueError('La fecha de referencia debe ser sin zona horaria y posterior a la última compra.')
    grupo = elegibles.groupby('customer_unique_id', sort=True)
    rfm = grupo.agg(ultima_compra=('compra', 'max'), frecuencia=('order_id', 'nunique'))
    rfm['monto'] = grupo['importe'].sum(min_count=1)
    rfm['recencia'] = (referencia - rfm.pop('ultima_compra').dt.normalize()).dt.days
    rfm = rfm[VARIABLES].reset_index()
    resumen = {
        'pedidos_entrada': len(pedidos), 'pedidos_entregados': len(entregados),
        'pedidos_otros_estados_excluidos': len(pedidos) - len(entregados),
        'compradores_entregados_antes_exclusiones': int(entregados['customer_unique_id'].nunique()),
        'pedidos_entregados_sin_comprador': int(sin_id.sum()),
        'pedidos_entregados_con_fecha_o_importe_invalido': int(incompleto.sum()),
        'compradores_excluidos_por_historia_incompleta': len(compradores_incompletos),
        'pedidos_excluidos_por_comprador_o_historia_incompleta': int(excluir.sum()),
        'pedidos_utilizados': len(elegibles), 'compradores_utilizados': len(rfm),
        'compra_minima': str(elegibles['compra'].min()),
        'compra_maxima': str(elegibles['compra'].max()),
        'fecha_referencia': referencia.date().isoformat(),
        'monto_total_BRL': float(rfm['monto'].sum()),
        'compradores_recurrentes': int(rfm['frecuencia'].gt(1).sum()),
    }
    if rfm['frecuencia'].sum() != len(elegibles):
        raise ValueError('La frecuencia RFM no concilia con los pedidos utilizados.')
    return rfm, resumen


def transformar_rfm(rfm):
    """Log1p solo si |asimetría| > 1 y disminuye al transformar; luego estandariza."""
    originales = rfm[VARIABLES].astype(float)
    transformadas = originales.copy()
    distribuciones = []
    for variable in VARIABLES:
        valores = originales[variable]
        logaritmos = np.log1p(valores)
        asimetria, asimetria_log = float(valores.skew()), float(logaritmos.skew())
        usar_log = abs(asimetria) > 1 and abs(asimetria_log) < abs(asimetria)
        transformadas[variable] = logaritmos if usar_log else valores
        distribuciones.append({
            'variable': variable, 'minimo': float(valores.min()),
            'p25': float(valores.quantile(.25)), 'mediana': float(valores.median()),
            'promedio': float(valores.mean()), 'p75': float(valores.quantile(.75)),
            'p95': float(valores.quantile(.95)), 'maximo': float(valores.max()),
            'asimetria_original': asimetria, 'asimetria_log1p': asimetria_log,
            'transformacion': 'log1p' if usar_log else 'identidad',
        })
    escalador = StandardScaler()
    escaladas = escalador.fit_transform(transformadas)
    return escaladas, pd.DataFrame(distribuciones), transformadas, escalador


def evaluar_modelos(escaladas, muestra=1800):
    if len(escaladas) <= 6 or np.unique(escaladas, axis=0).shape[0] < 6:
        raise ValueError('Se necesitan más de 6 compradores y al menos 6 perfiles RFM distintos.')
    indices = np.sort(np.random.default_rng(42).choice(
        len(escaladas), size=min(muestra, len(escaladas)), replace=False,
    ))
    evaluacion, etiquetas = [], {}
    # Evita sobrecarga de hilos en matrices pequeñas y mantiene el mismo entorno numérico.
    with threadpool_limits(limits=1):
        for k in range(2, 7):
            modelo = KMeans(n_clusters=k, init='k-means++', random_state=42, n_init=10,
                            algorithm='lloyd', max_iter=300, tol=1e-4)
            labels = modelo.fit_predict(escaladas)
            presentes = np.unique(labels[indices]).size
            if not 1 < presentes < len(indices):
                raise ValueError(f'La muestra fija no permite evaluar k={k}; aumentar --muestra-silhouette.')
            sil = float(silhouette_score(escaladas[indices], labels[indices]))
            db = float(davies_bouldin_score(escaladas, labels))
            if not np.isfinite([sil, db, modelo.inertia_]).all() or np.unique(labels).size != k:
                raise ValueError(f'Métricas o partición inválidas para k={k}.')
            evaluacion.append({
                'k': k, 'silhouette': sil, 'davies_bouldin': db, 'inercia': float(modelo.inertia_),
                'random_state': 42, 'n_init': 10, 'init': 'k-means++', 'algorithm': 'lloyd',
                'max_iter': modelo.max_iter, 'tol': modelo.tol, 'iteraciones': int(modelo.n_iter_),
                'clientes_ajuste': len(escaladas), 'muestra_silhouette': len(indices),
                'escala': 'StandardScaler',
            })
            etiquetas[k] = labels
    evaluacion = pd.DataFrame(evaluacion)
    # Regla fijada antes de observar resultados, sin elegir visualmente a conveniencia.
    mejor = evaluacion.sort_values(['silhouette', 'davies_bouldin', 'k'], ascending=[False, True, True]).iloc[0]
    elegido = int(mejor['k'])
    evaluacion['seleccionado'] = evaluacion['k'].eq(elegido)
    return evaluacion, etiquetas[elegido], indices


def perfilar_clusters(clientes):
    grupo = clientes.groupby('cluster', sort=True)
    perfiles = grupo.agg(cantidad_clientes=('customer_unique_id', 'size'))
    perfiles['porcentaje'] = perfiles['cantidad_clientes'] / len(clientes) * 100
    for variable in VARIABLES:
        perfiles[f'{variable}_promedio'] = grupo[variable].mean()
        perfiles[f'{variable}_mediana'] = grupo[variable].median()
    perfiles['porcentaje_recurrentes'] = grupo['frecuencia'].apply(lambda s: s.gt(1).mean() * 100)
    perfiles['monto_total'] = grupo['monto'].sum(min_count=1)
    globales = clientes[VARIABLES].mean()
    for cluster, fila in perfiles.iterrows():
        menor_r = fila['recencia_promedio'] <= globales['recencia']
        mayor_f = fila['frecuencia_promedio'] >= globales['frecuencia']
        mayor_m = fila['monto_promedio'] >= globales['monto']
        perfiles.loc[cluster, 'segmento'] = (
            f'C{cluster}: R {"menor/igual" if menor_r else "mayor"}, '
            f'F {"mayor/igual" if mayor_f else "menor"}, M {"mayor/igual" if mayor_m else "menor"}'
        )
        perfiles.loc[cluster, 'interpretacion'] = (
            f'Recencia media {fila["recencia_promedio"]:.1f} días; '
            f'frecuencia media {fila["frecuencia_promedio"]:.3f} pedidos; '
            f'monto medio {fila["monto_promedio"]:.2f} BRL. '
            'Las comparaciones R/F/M se refieren a las medias de la población analizada.'
        )
        accion = 'Probar retención' if menor_r else 'Probar reactivación'
        accion += ' con seguimiento de recompra' if mayor_f else ' orientada a una segunda compra'
        accion += '; evaluar ofertas personalizadas sin asumir rentabilidad.' if mayor_m else '; limitar incentivos y medir su retorno.'
        perfiles.loc[cluster, 'accion_sugerida'] = accion
    return perfiles.reset_index()


def graficar(clientes, perfiles, evaluacion, distribuciones, transformadas, carpeta):
    carpeta.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4))
    barras = ax.bar(perfiles['cluster'].astype(str), perfiles['cantidad_clientes'], color='#2874a6')
    ax.bar_label(barras, labels=[f'{p:.1f}%' for p in perfiles['porcentaje']], padding=3)
    ax.set(xlabel='Cluster', ylabel='Compradores', title=f'Población RFM: {len(clientes):,} compradores')
    ax.margins(y=.15)
    fig.tight_layout()
    fig.savefig(carpeta / 'clustering_clientes_por_cluster.png', dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 3.8))
    for ax, metrica, titulo in zip(axes, ['silhouette', 'davies_bouldin', 'inercia'],
                                 ['Silhouette (mayor es mejor)', 'Davies-Bouldin (menor es mejor)', 'Inercia (menor con más k)']):
        ax.plot(evaluacion['k'], evaluacion[metrica], 'o-', color='#2874a6')
        ax.axvline(int(evaluacion.loc[evaluacion['seleccionado'], 'k'].iloc[0]), color='#c0392b', linestyle='--')
        ax.set(xlabel='k', title=titulo, xticks=range(2, 7))
    fig.tight_layout()
    fig.savefig(carpeta / 'clustering_evaluacion_k.png', dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(1, 3, figsize=(12, 4))
    for ax, variable, unidad in zip(axes, VARIABLES, ['días', 'pedidos', 'BRL']):
        x = np.arange(len(perfiles))
        ax.bar(x - .18, perfiles[f'{variable}_promedio'], .36, label='Promedio')
        ax.bar(x + .18, perfiles[f'{variable}_mediana'], .36, label='Mediana')
        ax.set(title=variable.capitalize(), ylabel=unidad, xlabel='Cluster', xticks=x,
               xticklabels=perfiles['cluster'].astype(str))
        ax.legend()
    fig.tight_layout()
    fig.savefig(carpeta / 'clustering_perfiles_rfm.png', dpi=160)
    plt.close(fig)
    fig, axes = plt.subplots(2, 3, figsize=(12, 6))
    for j, variable in enumerate(VARIABLES):
        axes[0, j].hist(clientes[variable], bins=50, color='#2874a6')
        axes[0, j].set(title=f'{variable}: original', ylabel='Compradores')
        nombre = distribuciones.set_index('variable').loc[variable, 'transformacion']
        axes[1, j].hist(transformadas[variable], bins=50, color='#148f77')
        axes[1, j].set(title=f'{variable}: {nombre}', ylabel='Compradores')
    fig.tight_layout()
    fig.savefig(carpeta / 'clustering_distribuciones_rfm.png', dpi=160)
    plt.close(fig)


def publicar_resumen(salida, texto):
    """Mantiene el bloque calculado del informe; no altera las secciones de grafos."""
    ruta = salida / 'docs' / 'clustering_y_grafos.md'
    if ruta.is_file():
        contenido = ruta.read_text(encoding='utf-8')
        if INICIO in contenido and FIN in contenido:
            antes, resto = contenido.split(INICIO, 1)
            _, despues = resto.split(FIN, 1)
            ruta.write_text(antes + INICIO + '\n\n' + texto + '\n\n' + FIN + despues, encoding='utf-8')


def ejecutar(pedidos_csv, salida, muestra=1800, fecha_referencia=None):
    pedidos = leer_csv(pedidos_csv, COLUMNAS, 'pedidos_procesados.csv')
    clientes, poblacion = construir_rfm(pedidos, fecha_referencia)
    escaladas, distribuciones, transformadas, escalador = transformar_rfm(clientes)
    evaluacion, labels, indices = evaluar_modelos(escaladas, muestra)
    clientes['cluster'] = labels
    perfiles = perfilar_clusters(clientes)
    clientes['segmento'] = clientes['cluster'].map(perfiles.set_index('cluster')['segmento'])
    if clientes['customer_unique_id'].duplicated().any() or perfiles['cantidad_clientes'].sum() != len(clientes):
        raise ValueError('No concilian los compradores y los tamaños de clusters.')
    resultados = salida / 'resultados'
    for nombre, tabla in [('clientes_clusters', clientes), ('perfiles_clusters', perfiles),
                          ('evaluacion_clustering', evaluacion), ('rfm_distribuciones', distribuciones)]:
        guardar_csv(tabla, resultados / f'{nombre}.csv')
    graficar(clientes, perfiles, evaluacion, distribuciones, transformadas, resultados / 'graficos')
    mejor = evaluacion.loc[evaluacion['seleccionado']].iloc[0]
    metadata = {
        'fuente': str(pedidos_csv), 'sha256_entrada': sha256(pedidos_csv),
        'python': platform.python_version(), 'pandas': pd.__version__,
        'numpy': np.__version__, 'scikit_learn': sklearn.__version__,
        'matplotlib': matplotlib.__version__, 'poblacion': poblacion,
        'k_seleccionado': int(mejor['k']),
        'criterio_seleccion': 'Mayor Silhouette en muestra fija; desempate menor Davies-Bouldin y menor k.',
        'transformaciones': dict(zip(distribuciones['variable'], distribuciones['transformacion'])),
        'media_standard_scaler': escalador.mean_.tolist(), 'escala_standard_scaler': escalador.scale_.tolist(),
        'semilla': 42, 'n_init': 10, 'hilos_ajuste': 1,
        'muestra_silhouette': len(indices),
        'compradores_muestra': clientes.iloc[indices]['customer_unique_id'].tolist(),
    }
    (resultados / 'clustering_metadata.json').write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    lineas = [
        f'**Ejecución real: k={int(mejor["k"])}; N={len(clientes):,} compradores.**',
        f'Referencia: {poblacion["fecha_referencia"]}; ventana de compra: {poblacion["compra_minima"]} a {poblacion["compra_maxima"]}.',
        f'Pedidos: {poblacion["pedidos_entrada"]:,} de entrada; {poblacion["pedidos_entregados"]:,} entregados; {poblacion["pedidos_utilizados"]:,} utilizados.',
        f'Excluidos: {poblacion["pedidos_otros_estados_excluidos"]:,} de otros estados; {poblacion["pedidos_entregados_sin_comprador"]:,} entregados sin comprador; {poblacion["compradores_excluidos_por_historia_incompleta"]:,} compradores con historia incompleta ({poblacion["pedidos_excluidos_por_comprador_o_historia_incompleta"]:,} pedidos entregados excluidos en total).',
        f'Silhouette utiliza los mismos {len(indices):,} compradores para todos los k; ajuste, Davies-Bouldin e inercia usan toda la población.',
        '\n| k | Silhouette | Davies-Bouldin | Inercia | Seleccionado |\n|---:|---:|---:|---:|---|',
    ]
    for fila in evaluacion.itertuples():
        lineas.append(f'| {fila.k} | {fila.silhouette:.5f} | {fila.davies_bouldin:.5f} | {fila.inercia:.2f} | {"Sí" if fila.seleccionado else "No"} |')
    lineas += ['\nSe elige el mayor Silhouette; Davies-Bouldin desempata e inercia contextualiza la compactación, sin comparar escalas entre métricas.',
               '\n| Variable | Asimetría original | Asimetría log1p | Transformación |\n|---|---:|---:|---|']
    for fila in distribuciones.itertuples():
        lineas.append(f'| {fila.variable} | {fila.asimetria_original:.3f} | {fila.asimetria_log1p:.3f} | {fila.transformacion} |')
    lineas += ['\n| Cluster | Clientes | % | R media/mediana (días) | F media/mediana | M media/mediana (BRL) |\n|---:|---:|---:|---:|---:|---:|']
    for fila in perfiles.itertuples():
        lineas.append(f'| {fila.cluster} | {fila.cantidad_clientes} | {fila.porcentaje:.2f} | {fila.recencia_promedio:.1f}/{fila.recencia_mediana:.1f} | {fila.frecuencia_promedio:.3f}/{fila.frecuencia_mediana:.1f} | {fila.monto_promedio:.2f}/{fila.monto_mediana:.2f} |')
    for fila in perfiles.itertuples():
        lineas += [f'\n**{fila.segmento}.** {fila.interpretacion} Acción propuesta: {fila.accion_sugerida}']
    lineas += [f'\nConclusión: la partición seleccionada separa perfiles RFM con Silhouette {mejor["silhouette"]:.5f}; es segmentación descriptiva, no evidencia causal ni validación de campañas.']
    texto = '\n\n'.join(lineas[:5]) + '\n' + '\n'.join(lineas[5:])
    (resultados / 'clustering_resumen.md').write_text(texto + '\n', encoding='utf-8')
    publicar_resumen(salida, texto)
    print(f'RFM: {len(clientes):,} compradores; k={int(mejor["k"])}; Silhouette={mejor["silhouette"]:.5f}; Davies-Bouldin={mejor["davies_bouldin"]:.5f}.')
    print(f'CSV, metadatos y gráficos: {resultados}')
    return metadata


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pedidos', type=Path, default=ROOT / 'data/processed/pedidos_procesados.csv')
    parser.add_argument('--output-root', type=Path, default=ROOT)
    parser.add_argument('--fecha-referencia', help='Fecha ISO posterior a la última compra; por defecto día siguiente al máximo.')
    parser.add_argument('--muestra-silhouette', type=int, default=1800, help='Muestra fija entre 100 y 2000 compradores (máximo).')
    args = parser.parse_args()
    if not 100 <= args.muestra_silhouette <= 2000:
        parser.error('--muestra-silhouette debe estar entre 100 y 2000.')
    try:
        ejecutar(args.pedidos.resolve(), args.output_root.resolve(), args.muestra_silhouette, args.fecha_referencia)
    except (OSError, ValueError) as error:
        parser.exit(1, f'Error de clustering: {error}\n')


if __name__ == '__main__':
    main()
