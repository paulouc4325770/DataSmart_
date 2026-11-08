# Preparación y calidad de Olist — entrega de Jerson

Informe generado por `python src/preparar_datos.py`.

## Fuente y granularidad

- Fuente: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
- Archivo: `data/raw/archive.zip`; SHA-256: `967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784`.
- Nueve tablas originales y **52 campos** sumados entre tablas.
- Compra mínima/máxima observada: 2016-09-04 21:15:19 / 2018-10-17 17:30:18.
- Pedidos: **99,441 filas**, una por `order_id`, con todos los estados.
- Ítems: **112,650 filas**, una por `order_id` + `order_item_id`.
- Geolocalización: **19,015 prefijos únicos**, con medianas de coordenadas.

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
| clientes | 99441 | 99441 | 0 | 0 |
| geolocalizacion | 1000163 | 738332 | 0 | 0 |
| detalles | 112650 | 112650 | 0 | 0 |
| pagos | 103886 | 103886 | 0 | 0 |
| opiniones | 99224 | 99224 | 145903 | 145903 |
| pedidos | 99441 | 99441 | 4908 | 4908 |
| productos | 32951 | 32951 | 2448 | 2448 |
| vendedores | 3095 | 3095 | 0 | 0 |
| categorias | 71 | 71 | 0 | 0 |

## Controles e indicadores

**50 controles, 0 errores.**
Conciliación monetaria con tolerancia absoluta de 0,005 BRL y tolerancia relativa cero.
Incluye conciliación global y de precios por pedido, claves, referencias y conservación de filas.

| Indicador | Valor |
|---|---:|
| `pedidos_totales` | 99441 |
| `items_totales` | 112650 |
| `pedidos_entregados` | 96478 |
| `clientes_unicos_todos_estados` | 96096 |
| `clientes_recurrentes_todos_estados` | 2997 |
| `porcentaje_clientes_recurrentes` | 3.118756 |
| `clientes_unicos_entregados` | 93358 |
| `ventas_articulos_entregados_BRL` | 13221498.11 |
| `pedidos_sin_items` | 775 |
| `pedidos_sin_pago` | 1 |
| `pedidos_sin_resenas` | 768 |
| `pedidos_con_multiples_resenas` | 547 |
| `entregados_sin_fecha` | 8 |
| `pedidos_evaluables_puntualidad_calendario` | 96470 |
| `entregas_tardias_calendario` | 6534 |
| `tasa_entregas_tardias_calendario_pct` | 6.77309 |

## Incidencias conservadas o tratadas

Los conteos siguientes son incidencias, no filas eliminadas. Un registro puede activar varias reglas.
`incidencias.csv` identifica fila CSV y claves; los duplicados geográficos se resumen a nivel de tabla.

| Tabla | Regla | Registros afectados |
|---|---|---:|
| clientes | sin_geolocalizacion_cliente | 278 |
| geolocalizacion | duplicados_exactos | 261,831 |
| opiniones | multiples_resenas | 1,098 |
| pagos | cuotas_cero | 2 |
| pedidos | aprobacion_despues_despacho | 1,359 |
| pedidos | despacho_despues_entrega | 23 |
| pedidos | entregado_sin_fecha | 8 |
| pedidos | sin_items | 775 |
| pedidos | sin_pago | 1 |
| pedidos | sin_resenas | 768 |
| productos | datos_fisicos_incompletos | 2 |
| productos | datos_fisicos_invalidos | 4 |
| productos | sin_categoria | 610 |
| productos | sin_traduccion | 13 |
| vendedores | sin_geolocalizacion_vendedor | 7 |

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
