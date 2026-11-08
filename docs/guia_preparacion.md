# Guía de ejecución y entrega de datos

## 1. Generar los archivos

Requisitos: Python 3.10 o posterior y las dependencias de `requirements.txt`.

```bash
python -m pip install -r requirements.txt
python src/preparar_datos.py
```

En PowerShell se puede sustituir `python` por `py`. Desde el entorno local del
repositorio en Linux: `.venv/bin/python src/preparar_datos.py`.

El ZIP debe estar en `data/raw/archive.zip`, con los nueve CSV originales en su
raíz. Se puede especificar otro archivo con `--zip /ruta/archive.zip` y otra raíz
de salida con `--output-root /ruta/salida`. Los valores relativos de estas opciones
se interpretan desde el directorio de ejecución; los valores por defecto se
resuelven desde la ubicación del script.

En una ejecución correcta se actualizan las tres tablas, diccionarios, reportes
e informe. Si una validación falla, el proceso termina con código 1 y los detalles
quedan en `resultados/calidad/validaciones.csv` e `incidencias.csv`; las tablas
procesadas de esa ejecución no se publican. Si ya había una salida anterior,
consultar el hash y la fecha de su `metadata.json` antes de consumirla.

## 2. Contrato de las tablas

| Archivo | Unidad de análisis | Clave | Uso |
|---|---|---|---|
| `pedidos_procesados.csv` | Pedido, con todos los estados | `order_id` | RFM, ventas, regresión, estados y calidad |
| `items_procesados.csv` | Ítem del pedido | `order_id` + `order_item_id` | Cestas, grafos y atributos físicos/geográficos |
| `geolocalizacion_agrupada.csv` | Prefijo postal | `geolocation_zip_code_prefix` | Coordenadas representativas y cobertura geográfica |

Los detalles completos de columnas, tipos, unidades, fuentes, fórmulas y
disponibilidad están en `resultados/diccionario_procesados.csv`.

- Una cantidad cero representa ausencia de registros asociados.
- Un importe nulo indica desconocimiento; no debe convertirse automáticamente en cero.
- `customer_id` es el registro transaccional; `customer_unique_id` identifica al comprador.
- Los importes están en BRL. Ventas de artículos excluye flete y pagos.
- `order_status` es el estado observado al corte, no el estado conocido al comprar.
- Los booleanos se exportan como `True`/`False` y los nulos como celdas vacías.
- Las fechas son ISO sin zona horaria: el origen no declara una zona y no se inventa una.
- El catálogo geográfico se valida con rangos mundiales; no se restringe a una
  frontera nacional ni se considera una ruta logística. Sus medianas históricas
  no representan necesariamente la ubicación conocida en cada fecha de compra.

## 3. Recargar conservando los tipos

Leer un CSV sin indicar tipos puede convertir `00100` en `100`. Este ejemplo usa
el diccionario publicado para recuperar los tipos y las fechas de cualquier tabla:

```python
from pathlib import Path
import pandas as pd

ROOT = Path('.')  # Raíz del proyecto, o raíz elegida con --output-root.
nombre = 'pedidos_procesados'  # También items_procesados o geolocalizacion_agrupada.
diccionario = pd.read_csv(
    ROOT / 'resultados/diccionario_procesados.csv', encoding='utf-8-sig'
)
campos = diccionario.loc[diccionario['tabla'].eq(nombre)]
fechas = campos.loc[campos['tipo'].eq('datetime64[ns]'), 'columna'].tolist()
tipos = dict(campos.loc[~campos['tipo'].eq('datetime64[ns]'), ['columna', 'tipo']].values)
datos = pd.read_csv(
    ROOT / 'data/processed' / f'{nombre}.csv',
    dtype=tipos,
    parse_dates=fechas,
    encoding='utf-8-sig',
)
```

## 4. Qué recibe cada integrante

### Paulo: asociación e integración

- Usar `items_procesados.csv` filtrando `order_status == 'delivered'` si se mantiene
  la misma población que el EDA.
- Formar una cesta por pedido, con categorías distintas. Repetir varias unidades
  de un producto no implica varias categorías en la cesta.
- Eliminar etiquetas desconocidas de la cesta, conservando explícitamente el
  universo de pedidos elegido. Informar cuántos quedan vacíos y el denominador
  usado para el soporte. Mantener las cestas unitarias en ese denominador.
- Exportar reglas calculadas y conectar la web a los archivos reales.
- Actualizar las etiquetas de 53 campos a 52, la recurrencia y el estado de los
  módulos de demostración al integrar las nuevas salidas.

### Brandon: RFM y grafos

- RFM se construye desde pedidos: agrupar por `customer_unique_id`, contar
  `order_id` distintos y sumar `valor_articulos`.
- Definir una fecha de referencia para recencia usando la población elegida.
- En este ZIP hay 96.096 compradores considerando todos los estados y 93.358
  considerando solo entregados. No mezclar los denominadores.
- El grafo vendedor–producto se construye con `seller_id` y `product_id` desde
  ítems, agregando repeticiones para el peso de cada arista.

### Anderson: series y regresión

- Ventas históricas: pedidos entregados, fecha de compra e importe de artículos.
- Revisar los extremos de la ventana temporal y usar periodos completos.
- La selección de entregados depende del estado observado al corte: considerar
  ese límite al interpretar las semanas finales.
- Objetivo de regresión: `dias_entrega`, con población evaluable explícita.
- Para añadir variables físicas y distancia, agregar primero los ítems por pedido
  con una regla documentada. Un pedido puede tener varios vendedores.
- Las banderas de inconsistencia sirven para definir población y análisis de
  sensibilidad. No se eliminaron esos pedidos globalmente.
- Seleccionar predictores conocidos al momento definido. `dias_entrega`, fecha
  real de entrega, reseñas, retraso y estado final no son entradas disponibles al
  comprar. Consultar `disponibilidad` y `uso_recomendado` en el diccionario.
- Ajustar imputación, codificación y escalado exclusivamente con entrenamiento.

## 5. Puntualidad y objetivos

`dias_entrega` conserva fracciones de día: diferencia en segundos entre compra y
entrega dividida entre 86.400. Solo se calcula para pedidos entregados, con ambas
fechas y duración no negativa. Una fecha ausente no equivale a cero días.

`entrega_tardia` compara los días calendario de entrega y promesa. Una entrega a
las 21:00 del día prometido cuenta como puntual aunque la fecha prometida se
registre a medianoche. Por esta convención, en el ZIP actual hay 6.534 entregas
tardías sobre 96.470 evaluables (6,77309 %), en lugar del porcentaje de la vista
de demostración basada en timestamps completos.

## 6. Verificación y reproducción

```bash
python -m unittest discover -s tests -v
python src/preparar_datos.py --output-root /ruta/verificacion
```

Comparar los CSV de ambas ejecuciones por su SHA-256. También debe coincidir el
informe generado. En `metadata.json` cambia `ejecutado_en_utc`; el hash del ZIP,
conteos, controles y versiones deben coincidir si se usa el mismo entorno.
La suite usa datos sintéticos pequeños y comprueba uniones con multiplicidad,
faltantes, puntualidad, cronología, coordenadas, conversiones, trazabilidad y
exportación reproducible. No requiere el ZIP de Olist.

## 7. Material para la exposición

- Informe con cifras: `docs/preparacion_y_calidad.md`.
- Guion de diapositivas: `docs/presentacion_jerson.md`.
- Evidencias: `resultados/calidad/validaciones.csv`, perfiles e incidencias.
- El informe y los CSV se regeneran; las decisiones y el guion se mantienen en
  esta guía y en las diapositivas.
