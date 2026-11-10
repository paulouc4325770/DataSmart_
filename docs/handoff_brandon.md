# Handoff de Anderson a Brandon — series, regresión y evaluación

## 1. Responsabilidades y disponibilidad real

La distribución vigente es **Anderson: clustering RFM, grafos y CRISP-DM**;
**Brandon: series temporales, regresión y evaluación predictiva**. Jerson entrega
la preparación y Paulo negocio, asociación y frontend. Algunas referencias de la
preparación histórica tienen los dos nombres invertidos; prevalece esta distribución.

**Entradas locales listas y verificadas; bloque de Anderson terminado.** Existen
las tres tablas de `data/processed/`, el ZIP original, los scripts de preparación y
asociación, los diccionarios, los reportes de calidad y los resultados reales de
clustering/grafos. No existen todavía
`src/series_temporales.py`, `src/regresion.py`, sus resultados ni
`docs/series_y_regresion.md`. Anderson no los implementó ni generó placeholders.

Los esquemas siguientes se contrastaron con los **CSV procesados existentes**,
cargados con los tipos y fechas del diccionario. Coinciden en nombres, orden y tipos:
41 columnas de pedidos, 40 de ítems y 5 de geolocalización. Un CSV no conserva tipos
por sí solo; usar la carga tipada de la sección 3. No es necesario repetir la
preparación ni los análisis de Anderson para comenzar en esta copia.

## 2. Entradas, claves y granularidad

| Archivo | Grano | Clave | Filas verificadas |
|---|---|---|---:|
| `data/processed/pedidos_procesados.csv` | Pedido, todos los estados | `order_id` | 99.441 |
| `data/processed/items_procesados.csv` | Ítem transaccional | `order_id` + `order_item_id` | 112.650 |
| `data/processed/geolocalizacion_agrupada.csv` | Prefijo postal | `geolocation_zip_code_prefix` | 19.015 |

Población comprobada: **96.478 pedidos entregados**, **93.358 compradores**,
**110.197 ítems entregados** y **13.221.498,11 BRL** de artículos. Todos los
entregados tienen importe conocido; **96.470** tienen `dias_entrega` evaluable.
No convertir los ocho objetivos ausentes en cero. Las exclusiones adicionales
de incidencias para regresión siguen siendo una decisión metodológica de Brandon.

Fechas de compra observadas:

- Todos los estados: 2016-09-04 21:15:19 a 2018-10-17 17:30:18.
- Solo entregados: **2016-09-15 12:16:38 a 2018-08-29 15:00:37**.

El final de la serie de ventas entregadas no es octubre de 2018: no utilizar la
ventana de todos los estados para rellenar septiembre/octubre como ventas cero.
Revisar además semanas parciales y censura del estado final antes de fijar el test.

Procedencia comprobada:

- SHA-256 del ZIP: `967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784`.
- SHA-256 de pedidos: `c5b3758ec2e130e4604a794b6e803128ca7966213be38a056c2396962e64627d`.
- SHA-256 de ítems: `cff2bd4af6bf56493ce6641c809d0fe7fe27162bdfde48d1011667e86a3a03fe`.
- `resultados/calidad/validaciones.csv`: **50 OK, cero errores**.

Las claves de pedidos, ítems y geografía se comprobaron sin duplicados; todas las
referencias de ítems tienen pedido y la suma de `cantidad_items` concilia con
112.650 filas. Si cambia el archivo de origen, revalidar estas cifras.

`customer_id` identifica el registro transaccional del cliente asociado al pedido;
no sirve para reconocer compras repetidas de una persona. `customer_unique_id`
identifica al comprador y puede repetirse en varios pedidos. Los identificadores y
prefijos postales deben leerse como texto. Los nombres de vendedor/producto no
están disponibles: no inventarlos a partir de los hashes.

### Columnas de pedidos (41)

Esta lista agrupa **todas** las columnas documentadas por tipo:

| Tipo Pandas | Columnas |
|---|---|
| `string` | `order_id`, `customer_id`, `order_status`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state` |
| `datetime64[ns]` | `order_purchase_timestamp`, `order_approved_at`, `order_delivered_carrier_date`, `order_delivered_customer_date`, `order_estimated_delivery_date` |
| `Int64` anulable | `cantidad_items`, `cantidad_productos`, `cantidad_vendedores`, `cantidad_registros_pago`, `cantidad_resenas`, `anio_compra`, `mes_compra`, `dia_semana_compra`, `dias_retraso_calendario` |
| `Float64` anulable | `customer_lat`, `customer_lng`, `valor_articulos`, `valor_flete`, `valor_pagado`, `calificacion_media`, `dias_entrega`, `dias_prometidos` |
| `boolean` anulable | `cuotas_cero`, `sin_items`, `sin_pago`, `sin_resenas`, `sin_geolocalizacion_cliente`, `es_entregado`, `tiene_fecha_entrega`, `entrega_tardia`, `compra_despues_aprobacion`, `aprobacion_despues_despacho`, `despacho_despues_entrega`, `entrega_antes_compra` |

### Columnas de ítems (40)

| Tipo Pandas | Columnas |
|---|---|
| `string` | `order_id`, `product_id`, `seller_id`, `product_category_name`, `product_category_name_english`, `categoria_presentacion`, `seller_zip_code_prefix`, `seller_city`, `seller_state`, `customer_id`, `order_status`, `customer_unique_id`, `customer_zip_code_prefix`, `customer_city`, `customer_state` |
| `datetime64[ns]` | `shipping_limit_date`, `order_purchase_timestamp` |
| `Int64` anulable | `order_item_id`, `product_name_lenght`, `product_description_lenght`, `product_photos_qty` |
| `Float64` anulable | `price`, `freight_value`, `product_weight_g`, `product_length_cm`, `product_height_cm`, `product_width_cm`, `volumen_cm3`, `seller_lat`, `seller_lng`, `customer_lat`, `customer_lng`, `distancia_km` |
| `boolean` anulable | `sin_categoria`, `sin_traduccion`, `datos_fisicos_incompletos`, `datos_fisicos_invalidos`, `sin_geolocalizacion_cliente`, `sin_geolocalizacion_vendedor`, `ruta_interestatal` |

### Columnas de geolocalización (5; entrada auxiliar)

`geolocation_zip_code_prefix` es `string`; `latitud_mediana` y `longitud_mediana`
son `Float64`; `cantidad_observaciones` y `cantidad_coordenadas_validas` son
`Int64`. Ya hay coordenadas y distancia incorporadas en las tablas de trabajo;
no es obligatorio hacer otra unión geográfica.

Se conserva la ortografía original `lenght`. Las fechas son ISO sin zona horaria;
los importes están en BRL, longitudes en cm, peso en gramos y duración en días
fraccionarios. Booleanos CSV `True`/`False`, faltantes vacíos; no interpretar una
cadena `'False'` mediante `bool(...)`, pues produciría verdadero.

### Diccionarios y variables derivadas existentes

- `resultados/diccionario_procesados.csv`: columnas, tipos, nulos, unidad,
  fuente/fórmula, disponibilidad y uso recomendado de las tres tablas.
- `resultados/diccionario_variables_derivadas.csv`: fórmulas y disponibilidad
  de las variables nuevas; subconjunto del diccionario anterior.
- `resultados/diccionario_datos.csv`: los 52 campos originales entre nueve tablas.
- `resultados/calidad/validaciones.csv`, `incidencias.csv`, perfiles y `metadata.json`:
  validaciones y trazabilidad de la preparación realizada con el ZIP original.

Variables especialmente útiles:

- `valor_articulos = sum(price, min_count=1)` por pedido, ya agregado sin duplicar.
- `valor_flete`: suma de fletes de los ítems; no confundir con ventas de artículos.
- `cantidad_items`, `cantidad_productos`, `cantidad_vendedores`: conteos al comprar.
- `dias_entrega = (entrega_real − compra).total_seconds() / 86400`, solo para
  entregados con fechas presentes y duración no negativa. **Objetivo, no predictor.**
- `dias_prometidos = (fecha_estimada − compra).total_seconds() / 86400`, disponible
  al comprar; la promesa está registrada a medianoche.
- `entrega_tardia`: compara días calendario, no horas. Es posterior al resultado.
- `distancia_km`: Haversine entre medianas de prefijos; distancia recta, no ruta.
- `volumen_cm3`: largo × alto × ancho, nulo con dimensiones ausentes/inválidas.
- `ruta_interestatal`, estados, calendario de compra y atributos de productos:
  candidatos a revisar según momento de predicción y cobertura del catálogo.

## 3. Regenerar y comprobar las entradas

**En esta copia las tablas ya están listas.** Basta instalar dependencias y aplicar
la comprobación tipada siguiente. En una copia recién clonada, obtener el ZIP
original de Olist, con sus nueve CSV en la raíz del archivo, y guardarlo como
`data/raw/archive.zip` (no subirlo a Git); después ejecutar la preparación:

```powershell
python -m pip install -r requirements.txt
python src/preparar_datos.py
```

También se puede usar `.\.venv\Scripts\python.exe` en lugar de `python` en el
entorno virtual local. Para otro ZIP o raíz consultar `python src/preparar_datos.py --help`.
La preparación no debe ejecutarse hasta tener el ZIP; no puede reconstruirse con
los CSV agregados de resultados ni con el frontend.

Comprobación mínima desde la raíz (fragmento para consola Python o notebook, no
un modelo de Brandon):

```python
from pathlib import Path
import pandas as pd

root = Path('.')
dic = pd.read_csv(root / 'resultados/diccionario_procesados.csv', encoding='utf-8-sig')
tablas = {}
for nombre in ['pedidos_procesados', 'items_procesados']:
    campos = dic.loc[dic['tabla'].eq(nombre)]
    fechas = campos.loc[campos['tipo'].eq('datetime64[ns]'), 'columna'].tolist()
    tipos = dict(campos.loc[~campos['tipo'].eq('datetime64[ns]'), ['columna', 'tipo']].values)
    ruta = root / 'data/processed' / f'{nombre}.csv'
    if not ruta.is_file():
        raise FileNotFoundError(f'Falta {ruta}; ejecutar primero la preparación con el ZIP original.')
    tabla = pd.read_csv(ruta, dtype=tipos, parse_dates=fechas, encoding='utf-8-sig')
    assert list(tabla.columns) == campos['columna'].tolist()
    assert not tabla.empty
    tablas[nombre] = tabla
    print(nombre, tabla.shape, 'fechas', tabla['order_purchase_timestamp'].min(),
          tabla['order_purchase_timestamp'].max())

p = tablas['pedidos_procesados']
i = tablas['items_procesados']
assert p['order_id'].notna().all() and p['order_id'].is_unique
assert i[['order_id', 'order_item_id']].notna().all().all()
assert not i.duplicated(['order_id', 'order_item_id']).any()
assert i['order_id'].isin(p['order_id']).all()
assert int(p['cantidad_items'].sum()) == len(i)
ent = p.loc[p['order_status'].eq('delivered')]
print('Entregados:', len(ent), 'compradores:', ent['customer_unique_id'].nunique())
print('Ventas conocidas BRL:', ent['valor_articulos'].sum(min_count=1))
print('Objetivos evaluables:', ent['dias_entrega'].notna().sum())
controles = pd.read_csv(root / 'resultados/calidad/validaciones.csv', encoding='utf-8-sig')
assert controles['resultado'].eq('OK').all()
```

Contrastar también el hash de origen y conteos de `metadata.json`. En GitHub se
incluyen resultados y diccionarios, **no el ZIP ni `data/processed/`**. Por ello
Brandon necesitará regenerar las tablas con el mismo ZIP o recibirlas por un canal
acordado: los reportes versionados por sí solos no reemplazan las entradas.
Si cambia el ZIP, revalidar todos los conteos.

## 4. Pendiente exclusivo de Brandon: series temporales

Crear **`src/series_temporales.py`**:

1. Filtrar pedidos entregados; definir ventas como suma de `valor_articulos` por
   fecha de compra. No sumar pagos/flete ni unir ítems para obtener ventas.
2. Definir tratamiento de importes desconocidos. Una suma de valores conocidos
   con faltantes no es una venta total; usar `min_count=1` y reportar cobertura.
3. Revisar extremos: primera/última semana parcial, meses aislados iniciales y
   censura de entregados al final. En el informe histórico la ventana mensual
   regular tiene solo 20 puntos. Elegir y justificar una ventana regular completa;
   serie semanal preferible. No asumir estacionalidad anual con tan poca historia.
4. Explicitar ancla semanal y convención de fecha. Distinguir semana sin ventas
   comprobada (puede ser cero) de semana desconocida/incompleta (no imputar cero).
5. Separar entrenamiento y prueba **cronológicamente**, sin `shuffle`. Publicar
   fechas, horizonte y tamaño. Comparar baseline ingenuo (último valor) con
   suavizamiento exponencial sobre los mismos periodos. Ajustar hiperparámetros
   usando solo entrenamiento o validación anterior al test.
6. Reportar **MAE** y **RMSE** en BRL por periodo, sin confundir ventas semanales
   con diarias. Analizar bordes y sesgo del filtro de estado final.

Las dependencias para un suavizamiento exponencial, si usa `statsmodels`, las
incorporará Brandon al implementar; no se añadieron bibliotecas que aún no se usan.

## 5. Pendiente exclusivo de Brandon: regresión

Crear **`src/regresion.py`** para predecir **`dias_entrega`** al comprar:

1. Definir la población con objetivo no nulo/no negativo y selección explícita de
   incidencias temporales. No borrar globalmente todas las banderas de auditoría.
2. Definir predictores conocidos en el instante de compra. Candidatos: calendario,
   estado cliente/vendedor, cantidad de ítems/productos/vendedores, importes de
   artículos/flete, promesa, atributos físicos y geografía con sus limitaciones.
3. **Agregar ítems a una fila por `order_id` antes del join**. Por ejemplo, peso y
   volumen totales con `min_count=1`, media/máximo de distancia, vendedores distintos
   y cobertura de atributos. Documentar si las medias ponderan unidades o vendedores.
   Un pedido multivendedor no tiene una única distancia inequívoca.
4. Unir sobre `order_id` con `validate='one_to_one'`; comprobar que no cambian filas
   ni importes. Evitar duplicar `valor_articulos`, que ya existe agregado en pedidos.
5. Comparar **baseline**, **Ridge** y **Random Forest** con el mismo corte temporal.
   Baseline recomendado: mediana de duración calculada solo con entrenamiento.
6. Ajustar imputación, codificación, escalado y selección de atributos únicamente
   con entrenamiento, preferentemente con `Pipeline`/`ColumnTransformer`. Categorías
   desconocidas del test no deben provocar errores. Semilla 42 donde corresponda.
7. Reportar **MAE (días)**, **RMSE (días)** y **R²** sobre las mismas observaciones
   futuras; exportar objetivo y predicción por pedido. No usar k-fold aleatorio
   para aparentar rendimiento fuera de tiempo. Advertir compradores compartidos
   entre periodos y evitar identificadores hash como predictores sin justificación.

**Excluir como predictores al comprar:**

- `dias_entrega`, entrega real, `dias_retraso_calendario`, `entrega_tardia`.
- `order_status`, `es_entregado`, `tiene_fecha_entrega`.
- `calificacion_media`, `cantidad_resenas`, `sin_resenas` y textos de reseñas.
- Banderas de secuencia temporal, despacho real, aprobación y otras variables de
  pago/operación cuando ocurren después del instante de predicción declarado.
- Los clusters RFM calculados con toda la historia: incorporan compras futuras
  respecto de pedidos antiguos. Si se quisieran utilizar habría que reconstruirlos
  con información anterior a cada corte, fuera del alcance actual.
- PageRank/grados del grafo histórico completo para predecir pedidos anteriores:
  también contienen transacciones futuras y no son entradas temporales seguras.

Las medianas geográficas y atributos del catálogo son una fotografía histórica sin
versiones por fecha. Documentar esa limitación si se usan como candidatos disponibles
al comprar; no afirmar una reconstrucción temporal que el origen no permite.

## 6. Contratos propuestos de resultados (NO son archivos existentes)

Brandon puede ajustar estos contratos antes de integrar con Paulo. Formato propuesto:
CSV UTF-8 con BOM, coma, punto decimal, fechas ISO, identificadores texto,
faltantes vacíos. Nombres de modelo estables y explícitos.

| Archivo futuro en `resultados/` | Grano / clave propuesta | Columnas propuestas |
|---|---|---|
| `pronosticos_ventas.csv` | `(fecha, modelo)` en test | `fecha` fecha de periodo; `modelo` texto (`baseline_ultimo`, `suavizamiento_exponencial`); `venta_real` real BRL; `venta_predicha` real BRL; `particion` texto (`test`); `frecuencia` texto (p. ej. `W-SUN`) |
| `evaluacion_series.csv` | Modelo y corte | `modelo`, `frecuencia`, `train_inicio`, `train_fin`, `test_inicio`, `test_fin`, `n_train`, `n_test`, `mae_brl`, `rmse_brl`, `parametros_json`, `tiempo_ajuste_s`, `tiempo_prediccion_s` |
| `predicciones_entrega.csv` | `(order_id, modelo)` en test | `order_id` texto; `order_purchase_timestamp` fecha/hora; `modelo` texto (`baseline_mediana`, `ridge`, `random_forest`); `dias_entrega_real`, `dias_entrega_predicha` reales en días; `particion` texto (`test`) |
| `evaluacion_regresion.csv` | Modelo y corte | `modelo`, `train_inicio`, `train_fin`, `test_inicio`, `test_fin`, `n_train`, `n_test`, `mae_dias`, `rmse_dias`, `r2`, `random_state`, `parametros_json`, `tiempo_ajuste_s`, `tiempo_prediccion_s` |
| `evaluacion_comparativa.csv` | `(tecnica, modelo, metrica, poblacion, particion)` | `tecnica`, `modelo`, `metrica`, `valor` real, `unidad`, `poblacion`, `particion`, `n_evaluacion` entero, `parametros_json` texto JSON, `tiempo_s` real |

Fechas sin hora en series; marcas ISO sin zona en pedidos. Cantidades enteras;
métricas/predicciones reales. `r2` puede ser negativo y no debe truncarse.
Si una métrica no aplica, no inventar cero. Conservar metadatos de fuente/hash,
ventana, filtros, versiones y parámetros en el informe o archivo adicional.

La comparativa consolida asociación de Paulo, clustering/grafos de Anderson y
predicción de Brandon **por familia**. Silhouette, lift, PageRank, MAE y R² no
forman un ranking global comparable; tampoco comparar MAE de BRL con MAE de días.
Los tiempos de familias distintas no prueban que un modelo sea mejor.

Crear **`docs/series_y_regresion.md`** con población, momento de predicción,
ventanas/cortes, tratamiento de nulos/bordes, baseline, parámetros, métricas reales,
gráficos, limitaciones, conclusiones y comandos. No generar ningún archivo de esa
lista hasta disponer de resultados verdaderos.

## 7. Secuencia de continuación

1. En esta copia, cargar y verificar las tablas existentes; en otra máquina,
   proporcionar ZIP/tablas como se explica en la sección 3.
2. Consultar los resultados **ya completos** de Anderson: k=2, Silhouette
   0,7111425, Davies-Bouldin 0,4765102; red con 35.186 nodos, 33.659 aristas y
   2.320 componentes. No hace falta reentrenarlos para implementar predicción.
3. Crear `src/series_temporales.py` y `src/regresion.py`, implementar modelos,
   evaluación temporal y `docs/series_y_regresion.md`.
4. Exportar los cinco CSV predictivos/comparativos propuestos y entregar contratos
   definitivos a Paulo para integrar sin tocar sus vistas.

Comandos disponibles para reproducir el bloque cerrado de Anderson, solo si se
necesita regenerarlo:

```powershell
python src/clustering.py
python src/grafos.py
```

Los comandos futuros `python src/series_temporales.py` y `python src/regresion.py`
solo serán válidos **después** de que Brandon cree los archivos; no se anuncian
como funcionalidades existentes.

No hay división train/test universal ni modelos predictivos preentrenados que
Brandon deba heredar. Las salidas de Anderson son descriptivas y no sustituyen sus
entradas originales de pedidos/ítems.
