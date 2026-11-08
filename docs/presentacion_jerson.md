# Preparación y calidad de datos — Jerson

Guion de seis diapositivas. Las cifras corresponden al ZIP auditado; contrastarlas
con `docs/preparacion_y_calidad.md` si cambia el archivo de origen.

## 1. Fuente y unidad de análisis

- Dataset público Olist, comercio electrónico brasileño histórico de 2016–2018.
- Nueve tablas y 52 campos originales.
- 99.441 pedidos y 112.650 ítems.
- Tres salidas: pedidos, ítems y geolocalización agrupada.
- Claves: `order_id`; `order_id` + `order_item_id`; prefijo postal.

**Explicación:** «Separamos los pedidos de sus ítems porque cada análisis necesita
una granularidad diferente. Conservamos todos los estados en la base general».

## 2. Calidad inicial

- 261.831 duplicados exactos en geolocalización.
- 610 productos sin categoría; dos nombres de categoría conocidos sin traducción.
- 775 pedidos sin ítems, un pedido sin pago y 768 sin reseñas.
- 547 pedidos con múltiples reseñas.
- Ocho pedidos entregados sin fecha de entrega.
- 1.359 aprobaciones posteriores al despacho y 23 despachos posteriores a la entrega.

**Evidencia:** `perfil_antes.csv` e `incidencias.csv` en `resultados/calidad/`.

## 3. Reglas de preparación

- Tipado explícito de fechas y números; prefijos postales como texto de cinco dígitos.
- Duplicados geográficos exactos eliminados antes de calcular medianas por prefijo.
- Categoría original conservada; etiqueta auxiliar para valores ausentes.
- Reseñas resumidas por media y cantidad; los textos opcionales no invalidan el score.
- Anomalías temporales señaladas, con criterios de selección por análisis.
- Contadores ausentes a cero; importes y puntuaciones desconocidos quedan nulos.

**Explicación:** «Cada tratamiento responde al significado del dato. La ausencia
de una fecha real no se imputa como entrega inmediata».

## 4. Uniones sin inflación de importes

```text
Pedidos + Clientes
        + Ítems agregados por pedido
        + Pagos agregados por pedido
        + Reseñas agregadas por pedido
```

- Uniones izquierdas con cardinalidad validada.
- Conservación de 99.441 pedidos y 112.650 ítems.
- Ventas de artículos entregados conciliadas: **R$ 13.221.498,11**.
- Tolerancia monetaria absoluta: 0,005 BRL.

**Demostración:** abrir `resultados/calidad/validaciones.csv` y mostrar que todos
los controles terminan en `OK`.

## 5. Variables y disponibilidad

- Calendario: año, mes y día de semana de compra.
- Compra: cantidades de ítems/productos/vendedores, artículos y flete.
- Producto: categoría, peso, dimensiones y volumen.
- Geografía: medianas postales, distancia Haversine por ítem y ruta interestatal.
- Objetivo logístico: días reales de entrega, con fracciones de día.
- Puntualidad por día calendario: 6.534 / 96.470 = **6,77 %** de entregas tardías.

**Explicación:** «Los resultados posteriores a la compra se identifican como
objetivos o datos de auditoría. Cada modelo seleccionará sus entradas según el
momento en que se hará la predicción».

## 6. Reproducción y entrega al equipo

```bash
python src/preparar_datos.py
python -m unittest discover -s tests -v
```

- Paulo recibe ítems con categorías y estados para cestas.
- Brandon recibe compradores, fechas e importes para RFM y relaciones para grafos.
- Anderson recibe pedidos, fechas e importes; puede agregar atributos por ítem.
- Diccionarios con fórmulas, unidades y disponibilidad.
- ZIP identificado por SHA-256; metadatos de ejecución y reportes verificables.

**Cierre:** «La base común ya permite que todos construyan sus modelos sobre las
mismas definiciones, con registros e importes conciliados».
