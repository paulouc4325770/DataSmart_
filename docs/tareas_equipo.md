# Tareas pendientes del equipo — DataSmart

## Objetivo

Completar los entregables de las semanas 7, 10 y 13 antes del martes,
aprovechando la preparación de datos implementada por Jerson.

**Distribución vigente:** Anderson — clustering, grafos y CRISP-DM;
Brandon — series temporales, regresión y evaluación predictiva. Esta distribución
prevalece sobre las referencias históricas invertidas en documentos de preparación.

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

## 3. Anderson — Clustering, grafos y metodología

**Estado: bloque de Anderson completado y verificado con Olist.** Clustering sobre
93.358 compradores: k=2, Silhouette 0,7111425 y Davies-Bouldin 0,4765102. Grafo:
35.186 nodos, 33.659 aristas, 2.320 componentes y peso total 110.197 ítems.
CSV, metadatos y seis gráficos disponibles; documentación y handoff finalizados.
Ver [informe de Anderson](clustering_y_grafos.md) y
[guion de presentación](presentacion_anderson.md).

### A. Clustering — Semana 13

- [x] Crear `src/clustering.py`.
- [x] Definir la población de clientes y las exclusiones del análisis.
- [x] Construir y ejecutar RFM por `customer_unique_id`:
  - Recencia: días desde la última compra a una fecha explícita.
  - Frecuencia: pedidos distintos.
  - Monto: suma de `valor_articulos`.
- [x] Revisar distribuciones y justificar transformaciones y escalado.
- [x] Ejecutar K-Means con distintos valores de `k`, de 2 a 6.
- [x] Fijar la semilla para reproducibilidad.
- [x] Comparar Silhouette, Davies-Bouldin e inercia.
- [x] Implementar una muestra común para Silhouette, por defecto 1.800 compradores.
- [x] Exportar compradores con su cluster y perfiles de los grupos.
- [x] Proponer una acción comercial por segmento, distinguiendo propuestas de efectos demostrados.

Poblaciones verificadas:

- Todos los estados: 96.096 compradores.
- Solo pedidos entregados: 93.358 compradores.

### B. Grafos — Semana 13

- [x] Crear `src/grafos.py`.
- [x] Construir y ejecutar el grafo vendedor–producto desde `items_procesados.csv`.
- [x] Definir la población y el significado de las aristas.
- [x] Implementar la agregación de repeticiones para obtener el peso de cada conexión.
- [x] Calcular grado, grado ponderado, componentes y PageRank.
- [x] Exportar aristas, métricas y componentes.
- [x] Visualizar un subgrafo legible e indicar cómo se seleccionó.
- [x] Explicar los principales vendedores, productos y relaciones.

La red entregada se construyó desde transacciones, no desde el grafo predefinido
de la interfaz. Su integración web corresponde a Paulo y no condiciona este cierre.

### C. Metodología y presentación

- [x] Documentar cómo se aplica CRISP-DM al trabajo realizado.
- [x] Distinguir preparación, modelado y evaluación con resultados reales.
- [x] Preparar el guion de seis diapositivas en `docs/presentacion_anderson.md`.
- [x] Generar gráficos reales de clustering y grafos para las diapositivas.
- [x] Documentar el contrato de CSV para Paulo en `docs/clustering_y_grafos.md`.
- [x] Dejar disponibles para Paulo los resultados calculados y su estructura; integración web pendiente a su cargo.
- [x] Preparar `docs/handoff_brandon.md` con entradas, claves, tipos y contratos propuestos.

### Entregables finales de Anderson

- `src/clustering.py`.
- `src/grafos.py`.
- `resultados/clientes_clusters.csv`.
- `resultados/perfiles_clusters.csv`.
- `resultados/evaluacion_clustering.csv`.
- `resultados/grafo_aristas.csv`.
- `resultados/grafo_metricas.csv`.
- `resultados/grafo_componentes.csv` y `resultados/rfm_distribuciones.csv`.
- `resultados/clustering_metadata.json`, `resultados/grafos_metadata.json` y resúmenes Markdown.
- `docs/clustering_y_grafos.md`.
- `docs/presentacion_anderson.md` y `docs/handoff_brandon.md`.
- Seis PNG en `resultados/graficos/` con prefijos `clustering_` y `grafo_`.

### Criterio de cierre

Los segmentos tienen una evaluación documentada.
Las conexiones y los pesos del grafo provienen de transacciones reales.
**Criterio satisfecho.** Se verificaron conciliaciones, perfiles, hashes y archivos;
se corrigió el aviso deprecado de fecha sin modificar el modelo ni sus resultados.
No se hizo commit ni push. Las tareas de Brandon se mantienen pendientes.

---

## 4. Brandon — Series temporales, regresión y evaluación

Entradas, prevención de fuga de información y contratos propuestos:
[handoff de Anderson a Brandon](handoff_brandon.md). No hay modelos ni resultados
predictivos nuevos; se conservan todas las tareas de ejecución pendientes.

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

- [ ] Consolidar las métricas enviadas por Paulo y Anderson.
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
