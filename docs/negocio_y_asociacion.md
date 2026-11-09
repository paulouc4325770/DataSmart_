# DataSmart — Comprensión del negocio y reglas de asociación

**Responsable:** Paulo Cesar Ushiñahua Castañeda
**Curso:** Minería de Datos, octavo ciclo (UNMSM – FISI)
**Metodología:** CRISP-DM, fase 1 (comprensión del negocio) y conexión con la fase 4 (modelado: asociación)
**Dataset:** Brazilian E-Commerce Public Dataset by Olist (Kaggle), versión auditada en `resultados/calidad/metadata.json` (SHA-256 `967e41e0…a784`)
**Estado de este documento:** secciones 1 a 6 completas con los resultados reales de `src/asociacion.py` (umbral de 10 pedidos). Queda por integrar, en los pasos siguientes, la conexión con la web.

> Las cifras de este documento provienen de `resultados/calidad/indicadores_preparacion.csv` y de `resultados/indicadores_kpi.csv`. Los resultados de asociación provienen de `resultados/*.csv` generados por `src/asociacion.py`.

---

## 1. Contexto

Olist es un marketplace brasileño que conecta a pequeños vendedores con compradores en línea. El dataset público registra pedidos realizados entre **septiembre de 2016 y octubre de 2018** (compra mínima 2016-09-04, máxima 2018-10-17), con nueve tablas y 52 campos originales.

Tras la preparación de datos (entrega de Jerson, 50 controles sin errores) se dispone de:

| Elemento | Valor |
|---|---:|
| Pedidos registrados (todos los estados) | 99.441 |
| Pedidos entregados | 96.478 |
| Ítems de pedido | 112.650 |
| Pedidos sin ítems | 775 |
| Pedidos con al menos un ítem | 98.666 (99.441 − 775) |
| Compradores únicos (`customer_unique_id`) | 96.096 |
| Compradores recurrentes | 2.997 (3,12 % de los compradores únicos) |
| Ventas de artículos entregados (sin flete) | R$ 13.221.498,11 |
| Ticket promedio por pedido entregado | R$ 137,04 |

Dos hechos de esta tabla condicionan todo el proyecto:

1. **Muy pocos compradores vuelven** (3,12 %). La recompra no es una palanca disponible en la mayoría de los casos.
2. **Los pedidos son casi siempre pequeños.** Hay 112.650 ítems en 98.666 pedidos con ítems, es decir, **1,14 ítems por pedido**. La mayoría de las cestas tiene un solo ítem, y las de varias categorías son aún menos.

Por lo tanto, la oportunidad comercial que se puede analizar con los datos está **dentro del pedido**: qué se compra junto en una misma transacción.

---

## 2. Problema de negocio

### 2.1 Planteamiento

Olist vende sobre todo pedidos de un solo ítem y casi no recupera compradores. Aun así, existen pedidos en los que se combinan productos de distintas categorías, y hoy no hay evidencia cuantificada de cuáles son esas combinaciones, con qué frecuencia ocurren ni si son más frecuentes de lo que cabría esperar al azar.

Sin esa evidencia, el marketplace y sus vendedores no pueden fundamentar:

- recomendaciones de productos complementarios («quienes compran X también compran Y»);
- ofertas agrupadas (bundles) o envío compartido entre categorías afines;
- la ubicación de categorías relacionadas en el catálogo y en campañas.

El problema se formula así: **identificar y cuantificar, con reglas de asociación calculadas sobre pedidos reales, qué categorías de producto se compran juntas en un mismo pedido, y medir qué tan sólida y qué tan amplia es esa evidencia**, de modo que cada resultado se pueda rastrear hasta los pedidos que lo originan.

### 2.2 Alcance

**Dentro del alcance**

- Unidad de análisis: el **pedido** (`order_id`), tratado como una cesta de categorías distintas.
- Nivel de análisis inicial: **categoría de producto**, no producto individual. Con 32.951 productos y cestas casi siempre unitarias, el nivel de producto produciría soportes insignificantes.
- Algoritmos: Apriori y FP-Growth con los mismos parámetros, comparados en reglas obtenidas y tiempo de ejecución.
- Métricas por regla: soporte, confianza, lift y número de pedidos.
- Integración de los resultados calculados en la plataforma web, diferenciándolos de simulaciones o módulos pendientes.

**Fuera del alcance (en esta entrega)**

- Reglas a nivel de producto individual o de vendedor.
- Secuencias temporales de compra entre pedidos distintos (compras en días diferentes de un mismo comprador).
- Recomendador en producción o pruebas A/B de ofertas.
- Cualquier estimación de impacto económico de las reglas: el dataset no contiene datos de campañas ni de conversión.

### 2.3 Supuestos y limitaciones conocidas

| # | Supuesto o limitación | Consecuencia para el análisis |
|---|---|---|
| L1 | Dataset **histórico** (2016–2018) de un solo marketplace. | Los patrones no representan el comportamiento actual ni otros comercios. |
| L2 | Cestas mayoritariamente unitarias (1,14 ítems por pedido). | Pocas cestas aportan a las reglas; los soportes serán bajos y los umbrales deben justificarse con el número de pedidos, no con valores por defecto. |
| L3 | 610 productos sin categoría y 13 con categoría sin traducción. | La etiqueta «Sin categoría» no es una categoría real. El informe de preparación indica excluirla de las asociaciones e informar el universo elegido. |
| L4 | Un pedido puede incluir ítems de **varios vendedores**. | Una regla describe co-compra en el pedido, no un paquete ofrecido por un único vendedor. |
| L5 | El catálogo es una fotografía histórica. | No se conoce la categoría vigente en la fecha de cada compra. |
| L6 | Las reglas de asociación describen co-ocurrencia, no causalidad. | Un lift alto no demuestra que ofrecer B aumente la compra de A. |
| L7 | La relación «frecuente» depende del universo (todos los pedidos frente a entregados). | El universo debe declararse en cada regla mostrada (población de referencia). |

---

## 3. Objetivos

### 3.1 Objetivo general

Generar evidencia cuantificada y trazable sobre la co-compra de categorías en los pedidos de Olist mediante reglas de asociación (Apriori y FP-Growth), y presentarla en la plataforma DataSmart con resultados reales, con su población de referencia explícita y distinguidos de simulaciones o módulos pendientes.

### 3.2 Objetivos específicos

| Código | Objetivo específico | Entregable | Verificación |
|---|---|---|---|
| OE1 | Formalizar el problema, los objetivos y las preguntas de negocio reutilizando el trabajo existente (informe de la semana 7 y las preguntas PN-01 a PN-10). | Este documento, `docs/negocio_y_asociacion.md` | Cada pregunta enlaza con datos, técnica y resultado esperado (sección 4). |
| OE2 | Construir una cesta por `order_id` con categorías distintas y caracterizar la población: pedidos vacíos, unitarios y multicategoría. | `src/asociacion.py` | Los tres conteos suman el universo declarado. |
| OE3 | Ejecutar Apriori y FP-Growth con los mismos parámetros. | `resultados/comparacion_asociacion.csv` | Reglas obtenidas por cada algoritmo, coincidencia entre ambos y tiempo de ejecución. |
| OE4 | Exportar soporte, confianza, lift y número de pedidos por regla. | `resultados/reglas_asociacion.csv` | `n_pedidos` = soporte × total de cestas del universo. |
| OE5 | Justificar los umbrales según la baja cantidad de cestas multicategoría. | Sección 6 de este documento | Los umbrales se expresan también como número mínimo de pedidos. |
| OE6 | Conectar la web con los resultados calculados y actualizar los estados de avance. | Cambios en `frontend/server.py`, `dataService.js` y las vistas | Los valores de la web coinciden con los CSV. |
| OE7 | Garantizar trazabilidad de cada regla hasta las cestas originales. | Archivo de pedidos por regla | Para cada regla se pueden listar los `order_id` que la sustentan. |
| OE8 | Complementar el análisis con las cestas multicategoría, donde cada pedido puede contener un par. | `resultados/reglas_asociacion_multicategoria.csv` | La población de referencia (N) de cada archivo es explícita y distinta. |

### 3.3 Criterio de cierre

Cada regla mostrada puede rastrearse hasta las cestas originales y declara su **población de referencia** (por ejemplo, «pedidos entregados con al menos un ítem de categoría conocida, N = 95.146»). Los valores de la web coinciden con los archivos generados.

---

## 4. Preguntas de negocio

### 4.1 Las 10 preguntas del proyecto

La tabla relaciona cada pregunta con los datos, la técnica y el resultado esperado. La columna «Estado real» corrige las etiquetas de la interfaz actual, que presenta como «activo» varios módulos cuyos resultados aún son de demostración.

| ID | Pregunta | Datos | Técnica | Resultado esperado | Responsable | Estado real |
|---|---|---|---|---|---|---|
| PN-01 | ¿Qué grupos de clientes presentan perfiles de compra similares? | `items_procesados.csv` por `customer_unique_id` (recencia, frecuencia, monto) | RFM + K-Means | Segmentos con perfil y acción comercial | Brandon | Pendiente; la interfaz muestra segmentos de demostración |
| PN-02 | ¿Qué compradores concentran los mayores importes? | `valor_articulos` por comprador | Scoring RFM y curva de Pareto | Concentración del monto (cuantiles) | Brandon | Pendiente |
| PN-03 | ¿Cómo cambian las ventas por mes? | `resultados/ventas_mensuales.csv` | EDA temporal | Evolución mensual y pico de noviembre de 2017 | Equipo (EDA) | Completado en EDA |
| PN-04 | ¿Es posible pronosticar ventas futuras? | Ventas de entregados por fecha de compra | Series temporales (base vs. suavizamiento exponencial) | Pronóstico con MAE y RMSE sobre periodos de prueba | Anderson | Pendiente |
| **PN-05** | **¿Qué productos aparecen juntos en los pedidos?** | `items_procesados.csv`: `order_id`, `categoria_presentacion` | **Apriori y FP-Growth** | **Reglas con soporte, confianza, lift y n.º de pedidos** | **Paulo** | **En desarrollo (esta entrega)** |
| PN-06 | ¿Qué categorías generan mayores importes? | Precio por categoría en pedidos entregados | Agregación y Pareto | Ranking de categorías por ventas | Equipo (EDA) | Completado en EDA |
| PN-07 | ¿Qué variables se asocian con los tiempos de entrega? | `dias_entrega`, distancia, peso, volumen, flete | Regresión (base, Ridge, Random Forest) | MAE, RMSE y R² con corte temporal | Anderson | Pendiente |
| PN-08 | ¿Qué factores permiten clasificar valoraciones? | Reseñas y puntuaciones | Clasificación | Precision, recall, F1 | Sin asignar en `tareas_equipo.md` | Pendiente |
| PN-09 | ¿Qué conexiones forman clientes, productos y vendedores? | Aristas vendedor–producto desde ítems | Grafos (grado, PageRank, componentes) | Red calculada con métricas | Brandon | Pendiente; el grafo de la interfaz es predefinido |
| PN-10 | ¿Qué temas aparecen en los comentarios? | 40.977 reseñas con texto | Minería de textos | Temas y términos frecuentes | Sin asignar en `tareas_equipo.md` | Pendiente |

**Puntos a resolver con el equipo:**

- PN-08 y PN-10 no tienen responsable en `docs/tareas_equipo.md`; hay que asignarlos o declararlos fuera de esta entrega.
- PN-09 describe en la interfaz una red estados–categorías, mientras que el plan de Brandon define un grafo vendedor–producto. Deben alinearse.

### 4.2 Preguntas derivadas de PN-05 (reglas de asociación)

PN-05 es la pregunta que responde esta entrega. Se descompone en preguntas verificables:

| ID | Pregunta | Cómo se responde | Métrica |
|---|---|---|---|
| PN-05.1 | ¿Qué proporción de pedidos permite analizar asociaciones? | Conteo de cestas vacías, unitarias y multicategoría | 0,76 % del universo (723 de 95.146 cestas) |
| PN-05.2 | ¿Qué pares de categorías aparecen juntos con mayor frecuencia? | Soporte de los conjuntos frecuentes | Soporte y n.º de pedidos |
| PN-05.3 | Dado que un pedido contiene la categoría A, ¿con qué probabilidad contiene también B? | Regla A → B | Confianza |
| PN-05.4 | ¿Esa co-compra es mayor de lo esperable al azar? | Comparación con la frecuencia individual de B | Lift (> 1 indica asociación positiva) |
| PN-05.5 | ¿Cuántos pedidos sustentan cada regla? | Conteo de pedidos que contienen A y B | `n_pedidos` |
| PN-05.6 | ¿Apriori y FP-Growth producen las mismas reglas y cuál tarda menos? | Mismos parámetros y mismo universo | N.º de reglas, coincidencia y tiempo |
| PN-05.7 | ¿Las reglas son lo bastante sólidas para una acción comercial? | Lectura conjunta de lift, confianza y n.º de pedidos | Criterio de la sección 6.3 |

### 4.3 Decisiones de negocio que respaldaría cada resultado

| Resultado | Decisión posible | Condición para usarlo |
|---|---|---|
| Regla A → B con lift > 1 y soporte suficiente en pedidos | Sugerir B en la ficha o el carrito de A; probar una oferta combinada | Número de pedidos suficiente (umbral de la sección 6.3) |
| Par de categorías con alta co-compra | Agrupar categorías afines en secciones y campañas | Verificar que la relación no provenga de pocos pedidos |
| Proporción muy baja de pedidos multicategoría | Priorizar acciones que no dependan de la cesta (por ejemplo, recompra) o estimular la compra de más de un ítem | Reporte explícito de la proporción |

---

## 5. Conexión con las demás técnicas (CRISP-DM)

| Fase CRISP-DM | Trabajo en este proyecto | Estado |
|---|---|---|
| 1. Comprensión del negocio | Este documento (problema, objetivos, preguntas) | Completado |
| 2. Comprensión de los datos | EDA (`src/eda_olist.py`) y calidad | Completado |
| 3. Preparación de los datos | `src/preparar_datos.py` (Jerson) | Completado |
| 4. Modelado | Asociación (Paulo); clustering y grafos (Brandon); series y regresión (Anderson) | Asociación en desarrollo |
| 5. Evaluación | Comparación de algoritmos y métricas por regla | Pendiente |
| 6. Despliegue | Prototipo web con resultados reales | Pendiente |

---

## 6. Resultados de asociación

*(Cifras obtenidas al ejecutar `src/asociacion.py` sobre `data/processed/`.)*

### 6.1 Población de referencia

Decisión propuesta, sujeta a confirmación con el equipo antes de calcular:

| Decisión | Propuesta | Motivo |
|---|---|---|
| Universo de pedidos | Pedidos **entregados** con al menos un ítem | La preparación de datos recomienda filtrar los pedidos entregados; los cancelados o en curso no representan compras completadas. |
| Unidad de cesta | Un `order_id` = una cesta de categorías **distintas** | Evita contar dos veces la misma categoría repetida en un pedido. |
| Categoría desconocida | Excluir «Sin categoría» de los conjuntos de ítems | No es una categoría real (L3). |
| Cestas unitarias | **Se mantienen en el denominador del soporte** | Si se eliminaran, el soporte se inflaría y no sería comparable con el universo real. |
| Idioma de etiquetas | Original en portugués y nombre en español para la web | La traducción al inglés no cubre todas las categorías. |

Composición de la población (calculada con `src/asociacion.py`; fuente: `resultados/composicion_cestas.csv`):

| Concepto | Pedidos | % de los entregados | % del universo | ¿En el universo? |
|---|---:|---:|---:|---|
| Pedidos entregados (total) | 96.478 | 100,00 % | — | — |
| Vacíos (entregados sin ítems) | 0 | 0,00 % | — | No |
| Solo con categorías desconocidas | 1.332 | 1,38 % | — | No |
| Unitarios (1 categoría) | 94.423 | 97,87 % | 99,24 % | Sí |
| Multicategoría (2 o más) | 723 | 0,75 % | 0,76 % | Sí |
| **Universo (unitarios + multicategoría)** | **95.146** | 98,62 % | 100,00 % | **N del soporte** |

La composición cierra: 0 + 1.332 + 95.146 = 96.478 pedidos entregados, cifra que coincide con el indicador `pedidos_entregados` de la preparación de datos.

**Lectura.** Solo el 0,76 % del universo (723 pedidos) combina dos o más categorías conocidas. Por tanto, el soporte de cualquier par de categorías no puede superar 0,76 %, y un umbral habitual de 1 % no produciría ninguna regla. Esta es la base de la justificación de umbrales de la sección 6.3.

Los pedidos vacíos y los que solo tienen categorías desconocidas no pueden formar una cesta de categorías conocidas, por eso se informan pero quedan fuera del universo. Los unitarios sí permanecen en el denominador.

### 6.2 Parámetros comunes a ambos algoritmos

| Parámetro | Valor | Justificación |
|---|---|---|
| Soporte mínimo | 10 pedidos (0,000105 del universo de 95.146 cestas) | Se fija como número mínimo de pedidos; ver 6.3. |
| Confianza mínima | 0 (sin filtro) | Con 99,24 % de cestas unitarias, las confianzas son bajas por construcción: la mayor observada es 10,97 %. Un filtro habitual de 0,1 dejaría una sola regla. La calidad se juzga con el lift y el número de pedidos. |
| Longitud máxima del conjunto | 2 | Reglas entre pares de categorías. El par más frecuente tiene 70 pedidos; la ejecución con `--max-len 3` permite confirmar si existen tríos con 10 pedidos o más. |
| Orden de las reglas | Lift y luego número de pedidos | Evita destacar reglas con lift alto pero muy pocos pedidos. |

### 6.3 Justificación de umbrales

El umbral se fija según el número de pedidos y no con valores convencionales de soporte, porque solo 723 de las 95.146 cestas (0,76 %) combinan categorías. El par más frecuente aparece en 70 pedidos (0,074 % del universo): un umbral de 1 % o incluso de 0,1 % no produciría ninguna regla.

La tabla muestra, para cada umbral, cuántos pares de categorías lo superan (fuente: `resultados/umbrales_asociacion.csv`):

| Umbral (pedidos) | Soporte equivalente | Pares frecuentes | Pares con lift > 1 |
|---:|---:|---:|---:|
| 1 | 0,0000105 | 242 | 19 |
| 2 | 0,0000210 | 107 | 4 |
| 3 | 0,0000315 | 60 | 1 |
| 5 | 0,0000526 | 36 | 1 |
| **10 (elegido)** | **0,000105** | **17** | **1** |
| 20 | 0,000210 | 5 | 1 |
| 50 | 0,000526 | 1 | 0 |
| 100 | 0,001051 | 0 | 0 |

Razones para elegir 10 pedidos:

1. **Umbrales de 1 o 2 pedidos añaden ruido.** Pasar de 2 a 1 pedido suma 15 pares con lift mayor que 1, todos respaldados por un único pedido. Pasar de 3 a 2 suma 3 pares más, cada uno con 2 pedidos. Una frecuencia de 1 o 2 pedidos no sostiene una regla.
2. **El resultado no cambia entre 3 y 20 pedidos.** En ese rango siempre queda un único par con lift mayor que 1 (cama_mesa_banho y casa_conforto, 43 pedidos). Elegir 10 no descarta ninguna asociación positiva que 3 o 5 sí conservaran.
3. **Subir a 50 pedidos elimina ese par** (43 < 50) y deja un solo par, con lo que no quedaría nada que analizar.
4. **Con 10 pedidos quedan 17 pares (34 reglas dirigidas)**, una cantidad interpretable, cada una respaldada por al menos 10 cestas reales.

El valor de 10 es un mínimo razonable de evidencia para reportar una frecuencia, no un umbral de significancia estadística; por eso en 6.5 se evalúa además si el exceso observado es compatible con el azar.

### 6.4 Comparación Apriori y FP-Growth

Resultados con el umbral provisional de 10 pedidos (soporte 0,000105), confianza mínima 0 y conjuntos de hasta 2 categorías, sobre el universo de 95.146 cestas. Tiempos: mejor de 5 repeticiones, solo minado de conjuntos frecuentes.

| Algoritmo | Conjuntos frecuentes | Reglas obtenidas | Tiempo mínimo (s) | Coincide con el otro |
|---|---:|---:|---:|---|
| Apriori | 87 | 34 | 0,0625 | Sí |
| FP-Growth | 87 | 34 | 0,1439 | Sí |

Ambos algoritmos obtienen exactamente los mismos conjuntos y las mismas 34 reglas con métricas idénticas. FP-Growth resultó más lento que Apriori. Esto es esperable aquí: con conjuntos de a lo sumo 2 categorías, solo 70 categorías frecuentes y casi todas las cestas de un único ítem, Apriori no necesita más de dos pasadas y el costo de construir el árbol FP no se compensa. La ventaja de FP-Growth aparece con más ítems, cestas más largas o umbrales mucho menores. Estos tiempos corresponden a implementaciones propias en Python y no deben generalizarse a otras librerías.

### 6.5 Reglas principales e interpretación

**Resultado.** Con el umbral de 10 pedidos se obtienen 34 reglas, que corresponden a 17 pares de categorías. Los cinco pares con 20 pedidos o más son:

| Par de categorías | Pedidos | Lift | Confianza (A → B) | Confianza (B → A) |
|---|---:|---:|---:|---:|
| cama_mesa_banho y moveis_decoracao | 70 | 0,114 | 0,76 % | 1,11 % |
| cama_mesa_banho y casa_conforto | 43 | 1,126 | 0,46 % | 10,97 % |
| moveis_decoracao y utilidades_domesticas | 24 | 0,063 | 0,38 % | 0,42 % |
| cama_mesa_banho y utilidades_domesticas | 20 | 0,036 | 0,22 % | 0,35 % |
| bebes y cool_stuff | 20 | 0,190 | 0,71 % | 0,56 % |

La población de referencia de todas las cifras es: pedidos entregados con al menos un ítem de categoría conocida, N = 95.146. Cada regla se rastrea hasta sus pedidos en `resultados/reglas_asociacion_trazabilidad.csv`.

**Interpretación.**

1. **No hay una asociación positiva sólida.** Solo un par supera lift 1: cama_mesa_banho y casa_conforto. Aparece en 43 pedidos frente a 38,2 esperados si ambas categorías fueran independientes, con un lift de 1,13. El exceso es pequeño: la probabilidad de observar 43 pedidos o más por azar, calculada con la distribución hipergeométrica, es 0,23 (columna `p_valor` de `reglas_asociacion.csv`). El resultado es compatible con el azar. Como referencia, el 10,97 % de los pedidos con casa_conforto incluye también cama_mesa_banho, frente a 9,75 % de todos los pedidos.
2. **16 de los 17 pares tienen lift menor que 1, y no debe leerse como rechazo entre categorías.** Casi todas las cestas (99,24 %) tienen una sola categoría y no pueden contener ningún par. Por eso, medido contra un modelo de independencia sobre todas las cestas, casi cualquier par queda por debajo de lo esperado. Por ejemplo, cama_mesa_banho y moveis_decoracao aparecen en 70 pedidos frente a 614,6 esperados. La pregunta de si, entre los clientes que sí combinan categorías, algunas combinaciones son más frecuentes que otras requiere un análisis restringido a las 723 cestas multicategoría.
3. **Las categorías del hogar dominan las combinaciones.** Cuatro de los cinco pares más frecuentes (cama_mesa_banho, moveis_decoracao, utilidades_domesticas y casa_conforto) son del hogar. Parte de esa frecuencia refleja la popularidad de cada categoría: cama_mesa_banho está en el 9,75 % de las cestas.

**Limitaciones comerciales.**

- Cada par se apoya en pocos pedidos (entre 10 y 70). Las reglas son descriptivas y no sirven para estimar el efecto de una recomendación o una oferta combinada (L6).
- El dataset es histórico (2016–2018) y de un solo marketplace (L1). Un pedido puede incluir ítems de varios vendedores, así que una regla no describe un paquete de un único vendedor (L4).
- Se analizó el nivel de categoría. Con cestas casi siempre unitarias, el nivel de producto no tendría soporte suficiente.

**Conclusiones de negocio.**

- Los datos del análisis principal **no respaldan** diseñar ofertas combinadas a partir de estas reglas. La sección 6.6 examina la pregunta entre los pedidos que sí combinan categorías.
- El hallazgo accionable es estructural: 99,24 % de los pedidos entregados contiene una sola categoría conocida. La oportunidad está en estimular que el cliente agregue una segunda categoría, no en explotar afinidades ya existentes.
- cama_mesa_banho y casa_conforto puede proponerse como hipótesis para una prueba controlada; en el análisis principal no es distinguible del azar, y su asociación fuerte solo aparece entre pedidos que ya combinan categorías (6.6).

### 6.6 Análisis complementario: solo cestas multicategoría

**Motivo.** En el análisis principal, 99,24 % de las cestas son unitarias y no pueden contener ningún par, lo que reduce mecánicamente el lift de casi todos los pares (sección 6.5). Esta variante responde otra pregunta: *entre los 723 pedidos que sí combinan categorías, ¿qué combinaciones son más frecuentes de lo esperable?*

**Cómo se calcula.** Se ejecuta el mismo script con la población restringida:

```
python src/asociacion.py --poblacion multicategoria
```

| Elemento | Análisis principal | Análisis complementario |
|---|---|---|
| Población de referencia | 95.146 cestas (unitarias y multicategoría) | 723 cestas (solo multicategoría) |
| Umbral | 10 pedidos (soporte 0,000105) | 10 pedidos (soporte 10/723 = 1,38 %) |
| Archivos | `reglas_asociacion.csv` y demás | los mismos nombres con sufijo `_multicategoria` |
| Algoritmos | Apriori y FP-Growth coinciden (0,0625 s y 0,1439 s) | Apriori y FP-Growth coinciden (0,0013 s y 0,0016 s) |

El número de pedidos por par es el mismo en ambos análisis; cambian el denominador y las frecuencias individuales de cada categoría, y por eso cambian el soporte, la confianza, el lift y el `p_valor`.

**Resultados.** Se obtienen 34 reglas (17 pares), igual que en el análisis principal. Diez pares tienen lift mayor que 1 y siete lo tienen menor que 1 (todos estos con `p_valor` de 0,88 o más). Los diez pares con lift mayor que 1, ordenados por lift:

| Par de categorías | Pedidos | Lift | Confianza (A → B) | Confianza (B → A) | `p_valor` | ¿Pasa Bonferroni? |
|---|---:|---:|---:|---:|---:|---|
| beleza_saude y perfumaria | 11 | 4,61 | 15,9 % | 44,0 % | 4,2·10⁻⁶ | Sí |
| cama_mesa_banho y casa_conforto | 43 | 3,16 | 21,8 % | 86,0 % | 2,3·10⁻¹⁹ | Sí |
| bebes y brinquedos | 19 | 2,95 | 20,4 % | 38,0 % | 2,3·10⁻⁶ | Sí |
| bebes y cool_stuff | 20 | 2,36 | 21,5 % | 30,3 % | 6,6·10⁻⁵ | Sí |
| beleza_saude y esporte_lazer | 14 | 2,19 | 20,3 % | 20,9 % | 0,0024 | Sí |
| construcao_ferramentas_iluminacao y moveis_decoracao | 11 | 2,19 | 61,1 % | 5,4 % | 0,00295 | No, por muy poco |
| casa_construcao y moveis_decoracao | 13 | 1,79 | 50,0 % | 6,4 % | 0,0125 | No |
| cama_mesa_banho y moveis_decoracao | 70 | 1,27 | 35,5 % | 34,7 % | 0,0039 | No |
| esporte_lazer y utilidades_domesticas | 11 | 1,16 | 16,4 % | 10,8 % | 0,34 | No |
| ferramentas_jardim y utilidades_domesticas | 11 | 1,10 | 15,5 % | 10,8 % | 0,42 | No |

Como se evalúan 17 pares, se aplica la corrección de Bonferroni: el umbral es 0,05 / 17 = 0,00294. Cinco pares lo superan con holgura. El sexto (construcao_ferramentas_iluminacao y moveis_decoracao, `p_valor` 0,00295) queda apenas por encima.

**Interpretación.**

1. **Cinco asociaciones son estadísticamente sólidas entre los pedidos que combinan categorías:** cama_mesa_banho con casa_conforto, bebes con brinquedos, bebes con cool_stuff, beleza_saude con perfumaria y beleza_saude con esporte_lazer.
2. **La más clara es cama_mesa_banho con casa_conforto.** De los 50 pedidos multicategoría que incluyen casa_conforto, 43 (86 %) incluyen también cama_mesa_banho; el lift es 3,16 y es el único par con 40 pedidos o más que pasa la corrección.
3. **cama_mesa_banho con moveis_decoracao es el par más frecuente (70 pedidos), pero su asociación es débil:** lift 1,27 y no pasa Bonferroni. Que dos categorías grandes se combinen mucho no implica afinidad; refleja su tamaño.
4. **Los siete pares con lift menor que 1 no muestran afinidad** (`p_valor` de 0,88 o más). En esta población no deben leerse como rechazo; ver la limitación metodológica más abajo.
5. **El volumen es pequeño.** Las cinco asociaciones sólidas suman 107 coincidencias pedido-par (43 + 11 + 19 + 20 + 14), el 0,11 % de las 95.146 cestas; pueden solaparse en un mismo pedido.

**Cómo se concilia con el análisis principal.** En el principal, cama_mesa_banho y casa_conforto no resultaron distinguibles del azar (`p_valor` 0,23): el 10,97 % de los pedidos con casa_conforto incluye cama_mesa_banho, frente a 9,75 % de todos los pedidos. En el complementario la asociación es muy fuerte (`p_valor` de 2,3·10⁻¹⁹). Ambos resultados son compatibles porque responden preguntas distintas:

- Principal: para *cualquier* pedido, ¿tener casa_conforto aumenta la probabilidad de incluir cama_mesa_banho? Poco.
- Complementario: dado que el cliente *ya combina* categorías, ¿casa_conforto va con cama_mesa_banho? Casi siempre.

Por eso la evidencia sirve para recomendar una segunda categoría a quien ya muestra intención de combinar, no para recomendar a todo comprador de casa_conforto.

**Limitación metodológica.** Al exigir 2 o más categorías por cesta, las categorías dejan de ser independientes por construcción: una cesta de exactamente 2 categorías contiene un único par. El modelo de independencia usado como referencia tiende entonces a esperar más coincidencias de las que caben, de modo que los lift mayores que 1 y los `p_valor` pequeños son conclusiones conservadoras. En cambio, un lift menor que 1 no indica rechazo entre categorías. Los `p_valor` describen frecuencia y no causalidad (L6), y se calculan por par.

**Conclusiones de negocio.**

- Hay evidencia de afinidades concretas, pero en un volumen muy reducido. No justifica por sí sola una estrategia de ofertas combinadas amplia.
- cama_mesa_banho con casa_conforto es la mejor candidata para una prueba controlada (recomendación de casa_conforto en la ficha de cama_mesa_banho y viceversa), siempre para clientes que ya combinan categorías.
- Los pares bebes con brinquedos y bebes con cool_stuff sugieren una afinidad alrededor de categorías infantiles. Es una hipótesis de interpretación; los datos no indican el motivo de la compra.
- Los resultados son descriptivos, históricos (2016–2018) y de un solo marketplace (L1).

### 6.7 Prototipo web con resultados reales

La pestaña **Asociación** del frontend (módulo Preguntas de negocio) lee los resultados de `resultados/` y no usa datos de ejemplo:

- `GET /api/asociacion` entrega las reglas, la comparación de algoritmos, la composición de las cestas y los `order_id` de cada regla. Con Vite, la web lee los CSV directamente.
- Cada regla muestra su población de referencia (N), soporte, confianza, lift, `p_valor` y número de pedidos, con selector entre el análisis principal (N = 95.146) y el complementario (N = 723).
- Al seleccionar una regla se muestran los pedidos que la sustentan; la web verifica que los pedidos rastreados coincidan con `n_pedidos` (34 de 34 reglas en ambas poblaciones).
- Los indicadores de recompra (3,12 %) y entregas tardías (6,77 %) se toman de los archivos de calidad, y el diccionario se rotula con 52 campos.
- Los laboratorios aún sin resultados reales (RFM, series, SHAP, NLP, grafos) figuran como «Simulación con datos de ejemplo» hasta integrar los resultados de cada integrante.

---

## 7. Trazabilidad y reproducción

1. Regenerar los datos: `python src/preparar_datos.py` (con `data/raw/archive.zip`).
2. Ejecutar la asociación: `python src/asociacion.py` (análisis principal) y `python src/asociacion.py --poblacion multicategoria` (complementario).
3. Salidas esperadas en `resultados/`: `reglas_asociacion.csv` (incluye `p_valor`), `comparacion_asociacion.csv`, `reglas_asociacion_trazabilidad.csv`, `composicion_cestas.csv`, `umbrales_asociacion.csv` y `asociacion_metadata.json`; el análisis complementario genera los mismos con el sufijo `_multicategoria`.
4. Verificar que, para cada regla, el número de pedidos que contienen antecedente y consecuente coincide con `n_pedidos`.
5. Iniciar la web con `py frontend/server.py` y contrastar los valores con los CSV; pruebas de la interfaz: `node --test frontend/tests/asociacion.test.mjs` y de la API: `py -m unittest discover -s tests -v`.

## 8. Referencias internas

- `docs/preparacion_y_calidad.md`: decisiones de preparación e indicadores.
- `docs/guia_preparacion.md`: guía de uso y entrega.
- `docs/tareas_equipo.md`: reparto de tareas y criterios de cierre.
- `resultados/diccionario_procesados.csv`: definición de `order_id` y `categoria_presentacion`.
