# Tareas pendientes del equipo — DataSmart

## Objetivo

Completar los entregables de las semanas 7, 10 y 13 antes del martes,
aprovechando la preparación de datos implementada por Jerson.

## 1. Base disponible

Ejecutar desde la raíz del proyecto:

```bash
python src/preparar_datos.py
```

Archivos generados:

| Archivo | Contenido |
|---|---|
| `data/processed/pedidos_procesados.csv` | 99.441 pedidos; una fila por pedido |
| `data/processed/items_procesados.csv` | 112.650 ítems; una fila por ítem |
| `data/processed/geolocalizacion_agrupada.csv` | 19.015 prefijos postales |
| `resultados/diccionario_procesados.csv` | Tipos, unidades, fuentes y disponibilidad |
| `resultados/diccionario_variables_derivadas.csv` | Fórmulas de las variables nuevas |
| `resultados/calidad/` | Validaciones, perfiles, incidencias y metadatos |

Documentación de referencia:

- [Guía de preparación](guia_preparacion.md).
- [Informe de preparación y calidad](preparacion_y_calidad.md).

La preparación supera 50 controles de datos y tiene 12 pruebas automatizadas.
Las cifras corresponden al ZIP auditado; contrastarlas con el informe si cambia
el archivo de origen.

Los archivos de `data/processed/` están excluidos de Git.
Cada integrante debe regenerarlos utilizando el mismo ZIP original.

---

## 2. Paulo — Negocio, asociación e integración del frontend

### A. Comprensión del negocio — Semana 7

- [ ] Redactar el problema de negocio y delimitar el alcance.
- [ ] Definir el objetivo general y los objetivos específicos.
- [ ] Revisar las 10 preguntas de negocio existentes.
- [ ] Relacionar las preguntas con datos, técnicas y resultados esperados.
- [ ] Incorporar estas secciones al informe y a la presentación.

### B. Asociación — Semana 10

- [ ] Crear `src/asociacion.py`.
- [ ] Utilizar `items_procesados.csv` y definir la población analizada.
- [ ] Construir una cesta por `order_id`.
- [ ] Utilizar categorías distintas dentro de cada cesta.
- [ ] Informar pedidos vacíos, unitarios y multicategoría.
- [ ] Mantener las cestas unitarias en el denominador del soporte.
- [ ] Ejecutar Apriori y FP-Growth con los mismos parámetros.
- [ ] Justificar los umbrales según la escasez de compras multicategoría.
- [ ] Exportar soporte, confianza, lift y pedidos por regla.
- [ ] Comparar resultados y tiempo de ejecución.
- [ ] Interpretar las reglas y sus limitaciones comerciales.

Las reglas actuales de la interfaz son valores de demostración.
Deben sustituirse por resultados calculados.

### C. Integración del frontend — Semanas 10 y 13

- [ ] Ampliar `frontend/server.py` para entregar los nuevos resultados.
- [ ] Modificar `frontend/src/services/dataService.js` para incorporar la respuesta
  de la API al estado de la aplicación.
- [ ] Conectar las vistas con indicadores, diccionarios y calidad reales.
- [ ] Mostrar los perfiles antes/después y los controles de validación.
- [ ] Actualizar las etiquetas de 53 campos a 52.
- [ ] Mostrar 3,12 % de compradores recurrentes, con su población definida.
- [ ] Mostrar 6,77 % de entregas tardías, indicando la comparación por día calendario.
- [ ] Integrar los resultados de Brandon y Anderson conforme estén disponibles.
- [ ] Diferenciar resultados calculados de simulaciones o módulos pendientes.
- [ ] Mostrar un estado claro cuando falten archivos o falle la conexión.
- [ ] Verificar navegación, filtros y exportaciones.

Para gráficos y KPIs, utilizar resultados agregados; evitar cargar todas las filas
de pedidos e ítems en el navegador.

### Entregables propuestos

- `src/asociacion.py`.
- `resultados/reglas_asociacion.csv`.
- `resultados/comparacion_asociacion.csv`.
- `docs/negocio_y_asociacion.md`.
- Frontend conectado a resultados reales.
- Diapositivas del bloque de negocio, asociación y prototipo.

### Criterio de cierre

Cada regla mostrada puede rastrearse hasta las cestas originales.
Los valores de la web coinciden con los archivos generados.

---

## 3. Brandon — Clustering, grafos y metodología

### A. Clustering — Semana 13

- [ ] Crear `src/clustering.py`.
- [ ] Definir la población de clientes utilizada.
- [ ] Construir RFM por `customer_unique_id`:
  - Recencia: días desde la última compra a una fecha explícita.
  - Frecuencia: pedidos distintos.
  - Monto: suma de `valor_articulos`.
- [ ] Revisar distribuciones y justificar transformaciones y escalado.
- [ ] Ejecutar K-Means con distintos valores de `k`, inicialmente de 2 a 6.
- [ ] Fijar la semilla para reproducibilidad.
- [ ] Comparar Silhouette y Davies-Bouldin.
- [ ] Utilizar una muestra común para Silhouette si resulta necesario.
- [ ] Exportar compradores con su cluster y perfiles de los grupos.
- [ ] Proponer una acción comercial por segmento.

Poblaciones verificadas:

- Todos los estados: 96.096 compradores.
- Solo pedidos entregados: 93.358 compradores.

### B. Grafos — Semana 13

- [ ] Crear `src/grafos.py`.
- [ ] Construir un grafo vendedor–producto desde `items_procesados.csv`.
- [ ] Definir la población y el significado de las aristas.
- [ ] Agregar repeticiones para obtener el peso de cada conexión.
- [ ] Calcular grado, grado ponderado, componentes y PageRank.
- [ ] Exportar aristas y métricas.
- [ ] Visualizar un subgrafo legible e indicar cómo se seleccionó.
- [ ] Explicar los principales vendedores, productos y relaciones.

El grafo actual de la interfaz es predefinido.
La nueva red debe construirse desde las transacciones.

### C. Metodología y presentación

- [ ] Documentar cómo se aplica CRISP-DM al trabajo realizado.
- [ ] Distinguir preparación, modelado y evaluación.
- [ ] Preparar gráficos y diapositivas de clustering y grafos.
- [ ] Entregar a Paulo los resultados y su estructura para integrarlos.

### Entregables propuestos

- `src/clustering.py`.
- `src/grafos.py`.
- `resultados/clientes_clusters.csv`.
- `resultados/perfiles_clusters.csv`.
- `resultados/evaluacion_clustering.csv`.
- `resultados/grafo_aristas.csv`.
- `resultados/grafo_metricas.csv`.
- `docs/clustering_y_grafos.md`.
- Gráficos y diapositivas correspondientes.

### Criterio de cierre

Los segmentos tienen una evaluación documentada.
Las conexiones y los pesos del grafo provienen de transacciones reales.

---

## 4. Anderson — Series temporales, regresión y evaluación

### A. Series temporales — Semana 13

- [ ] Crear `src/series_temporales.py`.
- [ ] Definir ventas como `valor_articulos` de pedidos entregados.
- [ ] Agrupar por fecha de compra.
- [ ] Revisar y excluir periodos de borde incompletos.
- [ ] Construir preferentemente una serie semanal.
- [ ] Separar entrenamiento y prueba cronológicamente.
- [ ] Comparar un pronóstico base con suavizamiento exponencial.
- [ ] Reportar MAE y RMSE sobre los mismos periodos de prueba.
- [ ] Exportar fechas, valores reales y predicciones.
- [ ] Generar un gráfico comparativo e interpretar los errores.

La ventana mensual regular tiene solo 20 observaciones.
La elección de estacionalidad debe justificarse con la historia disponible.

### B. Regresión — Semana 13

- [ ] Crear `src/regresion.py`.
- [ ] Utilizar `dias_entrega` como variable objetivo.
- [ ] Definir población y tratamiento de incidencias temporales.
- [ ] Seleccionar variables disponibles en el momento de predicción.
- [ ] Agregar atributos de ítems por pedido antes de unirlos.
- [ ] Documentar cómo se resume la distancia en pedidos con varios vendedores.
- [ ] Ajustar imputación, codificación y escalado solo con entrenamiento.
- [ ] Comparar predictor base, Ridge y Random Forest.
- [ ] Utilizar el mismo corte temporal para comparar alternativas.
- [ ] Fijar semillas cuando corresponda.
- [ ] Reportar MAE en días, RMSE y R².
- [ ] Exportar predicciones y analizar errores.

Para predecir al comprar, excluir como entradas:

- Fecha real de entrega.
- `dias_entrega` y retraso observado.
- Reseñas y calificaciones.
- Estado final del pedido.
- Indicadores conocidos únicamente después de la compra.

### C. Evaluación y presentación

- [ ] Consolidar las métricas enviadas por Paulo y Brandon.
- [ ] Comparar alternativas dentro de cada familia de técnicas.
- [ ] Registrar población, parámetros, partición, métricas y tiempo.
- [ ] Ampliar la interpretación del EDA y documentar los KPIs.
- [ ] Preparar diapositivas de series, regresión y evaluación.
- [ ] Entregar a Paulo resultados y estructura para la integración.

### Entregables propuestos

- `src/series_temporales.py`.
- `src/regresion.py`.
- `resultados/pronosticos_ventas.csv`.
- `resultados/evaluacion_series.csv`.
- `resultados/predicciones_entrega.csv`.
- `resultados/evaluacion_regresion.csv`.
- `resultados/evaluacion_comparativa.csv`.
- `docs/series_y_regresion.md`.
- Gráficos y diapositivas correspondientes.

### Criterio de cierre

La evaluación utiliza datos posteriores a los de entrenamiento.
Las métricas corresponden a predicciones calculadas y poblaciones explícitas.

---

## 5. Reglas comunes de entrega

Cada integrante debe aportar:

- [ ] Código ejecutable desde la raíz del proyecto.
- [ ] Dependencias utilizadas registradas en `requirements.txt`.
- [ ] Datos de entrada y población documentados.
- [ ] Parámetros y semillas de ejecución.
- [ ] Resultados exportados.
- [ ] Evaluación adecuada a la técnica.
- [ ] Al menos un gráfico o tabla interpretable.
- [ ] Una conclusión de negocio respaldada por resultados.
- [ ] Diapositivas de su bloque.
- [ ] Instrucciones para reproducir el análisis.

Los nombres de archivos propuestos deben acordarse antes de integrar el frontend.

## 6. Orden de trabajo hasta el martes

1. Confirmar que todos pueden regenerar y cargar los datos procesados.
2. Ejecutar una primera versión de cada análisis.
3. Cerrar parámetros, evaluación e interpretación.
4. Entregar resultados a Paulo para integrar las vistas.
5. Consolidar informes y presentaciones.
6. Ejecutar el flujo completo y contrastar cifras entre CSV y web.
7. Realizar un ensayo conjunto antes de la exposición.
