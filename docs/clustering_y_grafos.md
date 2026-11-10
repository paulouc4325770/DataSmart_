# Clustering RFM y grafos de Olist — Anderson

## Estado de la entrega

**Entrega de Anderson ejecutada, verificada y documentada con el Olist original.**
Se analizaron **93.358 compradores** mediante RFM y una red de **35.186 nodos**.
Los CSV, metadatos y seis gráficos están disponibles en `resultados/`. Se verificaron
sus conciliaciones y los hashes de las entradas, sin repetir el ajuste de modelos.
El código, el informe, el guion de exposición y el handoff están listos para su
publicación; la integración del frontend sigue siendo responsabilidad de Paulo.

Responsabilidades vigentes: Anderson desarrolla clustering, grafos y CRISP-DM;
Brandon continúa con series temporales, regresión y evaluación predictiva. Las
asignaciones invertidas de documentos históricos no sustituyen este acuerdo.

## 1. Objetivos y fuente

- Segmentar compradores según recencia, frecuencia y monto para proponer acciones
  comerciales verificables, no para predecir la respuesta a una campaña.
- Describir el volumen y la estructura de las relaciones vendedor–producto mediante
  una red bipartita de transacciones observadas.
- Fuente: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce),
  preparado por `src/preparar_datos.py`. No se reutilizan las simulaciones del frontend.

`pedidos_procesados.csv` tiene una fila por `order_id`; `items_procesados.csv`, una
por `order_id` + `order_item_id`. Se filtra `order_status == 'delivered'` en ambas
técnicas. Se verificaron **99.441 pedidos** y **112.650 ítems** de entrada;
la población entregada comprende **96.478 pedidos**, **93.358 compradores** y
**110.197 ítems**. No hubo exclusiones adicionales por claves, fechas de compra
o importes incompletos dentro de la población entregada.

Procedencia: ZIP con SHA-256
`967e41e04fc306fe604e2a693f488995a8b41e5047418f8a5c8e4abd6deca784`.
Los hashes de `pedidos_procesados.csv` e `items_procesados.csv`, registrados en
`clustering_metadata.json` y `grafos_metadata.json`, coinciden con los archivos
presentes. La preparación registra **50 controles OK y cero errores**.

## 2. Variables y preparación RFM

Para cada comprador `customer_unique_id = c`, sobre sus pedidos entregados:

- **R(c)** = fecha de referencia − fecha de su última compra, en días calendario.
- **F(c)** = cantidad de `order_id` distintos.
- **M(c)** = suma de `valor_articulos`, en BRL; excluye flete y pagos.

La referencia por defecto es el día posterior a la máxima compra de la población
elegible, a medianoche, nunca la fecha actual del sistema. Se normaliza la última
compra a día calendario. `--fecha-referencia YYYY-MM-DD` permite otro corte explícito
posterior a todas las compras incluidas; no filtra automáticamente compras futuras.

Se valida la unicidad de pedidos antes de agrupar y **no se hacen joins**. Pedidos
sin comprador no pueden agruparse. Si un comprador tiene algún pedido entregado
sin fecha válida, con importe desconocido/no finito o negativo, se excluye su
historia entregada completa: así no se subestiman F y M sumando solo los pedidos
conocidos. No se convierten importes desconocidos en cero. No se requiere fecha
real de entrega para RFM; las incidencias logísticas no eliminan compras válidas.

Se exportan mínimo, cuartiles, mediana, promedio, percentil 95, máximo y asimetrías
en `rfm_distribuciones.csv`. Para cada variable se aplica `log1p(x)` únicamente si
su asimetría absoluta original supera 1 y la transformación reduce esa asimetría.
En caso contrario se conserva su escala original. La regla se fijó antes de los
resultados: se conservó R y se transformaron F y M, como muestra la tabla calculada.

Después se aplica `StandardScaler`: `z = (x − media) / desviación`, con parámetros
ajustados sobre la población completa. Los perfiles se interpretan siempre en
RFM original, no en logaritmos ni puntuaciones estandarizadas.

## 3. K-Means y evaluación

K-Means minimiza la suma de distancias euclidianas cuadráticas entre observaciones
y su centroide. Se ajustan cinco modelos, `k = 2, 3, 4, 5, 6`, sobre **todos los
compradores elegibles**, con `random_state=42`, `n_init=10`, inicialización
`k-means++`, algoritmo `lloyd`, `max_iter=300`, `tol=0.0001` y un hilo de cálculo.

- **Silhouette**: promedio de `(b − a) / max(a, b)`; mayor es mejor. Se calcula solo
  en una muestra aleatoria común, sin reemplazo, de hasta **1.800 compradores**;
  semilla 42 y orden estable por identificador. La opción CLI nunca permite más
  de 2.000. Esta evaluación describe la muestra, no es una puntuación exacta del
  universo. Los identificadores muestreados quedan en los metadatos.
- **Davies-Bouldin**: similitud media con el grupo más próximo según dispersión y
  separación; menor es mejor. Se calcula sobre la población completa.
- **Inercia**: suma de cuadrados intracluster; suele disminuir al incrementar k y
  no debe utilizarse por sí sola para elegir la partición.

Regla automática: seleccionar el **mayor Silhouette**, desempatar por menor
Davies-Bouldin y luego por menor k. Se publican las tres métricas para revisar el
compromiso; no se promedian métricas de escalas incompatibles ni se reentrena el
modelo elegido. No se incorpora DBSCAN ni una búsqueda costosa adicional.

### Evaluación, perfiles y acciones calculadas

El siguiente bloque procede de la ejecución real y se regenera al ejecutar el
script. La interpretación ampliada posterior se conserva fuera de ese bloque.

<!-- INICIO RESULTADOS CLUSTERING -->

**Ejecución real: k=2; N=93,358 compradores.**

Referencia: 2018-08-30; ventana de compra: 2016-09-15 12:16:38 a 2018-08-29 15:00:37.

Pedidos: 99,441 de entrada; 96,478 entregados; 96,478 utilizados.

Excluidos: 2,963 de otros estados; 0 entregados sin comprador; 0 compradores con historia incompleta (0 pedidos entregados excluidos en total).

Silhouette utiliza los mismos 1,800 compradores para todos los k; ajuste, Davies-Bouldin e inercia usan toda la población.

| k | Silhouette | Davies-Bouldin | Inercia | Seleccionado |
|---:|---:|---:|---:|---|
| 2 | 0.71114 | 0.47651 | 190688.46 | Sí |
| 3 | 0.35709 | 0.92189 | 126765.12 | No |
| 4 | 0.36484 | 0.78212 | 86756.34 | No |
| 5 | 0.35440 | 0.83539 | 71132.44 | No |
| 6 | 0.34733 | 0.86979 | 60173.38 | No |

Se elige el mayor Silhouette; Davies-Bouldin desempata e inercia contextualiza la compactación, sin comparar escalas entre métricas.

| Variable | Asimetría original | Asimetría log1p | Transformación |
|---|---:|---:|---|
| recencia | 0.447 | -1.197 | identidad |
| frecuencia | 11.095 | 6.522 | log1p |
| monto | 9.747 | 0.280 | log1p |

| Cluster | Clientes | % | R media/mediana (días) | F media/mediana | M media/mediana (BRL) |
|---:|---:|---:|---:|---:|---:|
| 0 | 2801 | 3.00 | 220.8/200.0 | 2.114/2.0 | 260.05/182.10 |
| 1 | 90557 | 97.00 | 239.0/220.0 | 1.000/1.0 | 137.96/86.96 |

**C0: R menor/igual, F mayor/igual, M mayor/igual.** Recencia media 220.8 días; frecuencia media 2.114 pedidos; monto medio 260.05 BRL. Las comparaciones R/F/M se refieren a las medias de la población analizada. Acción propuesta: Probar retención con seguimiento de recompra; evaluar ofertas personalizadas sin asumir rentabilidad.

**C1: R mayor, F menor, M menor.** Recencia media 239.0 días; frecuencia media 1.000 pedidos; monto medio 137.96 BRL. Las comparaciones R/F/M se refieren a las medias de la población analizada. Acción propuesta: Probar reactivación orientada a una segunda compra; limitar incentivos y medir su retorno.

Conclusión: la partición seleccionada separa perfiles RFM con Silhouette 0.71114; es segmentación descriptiva, no evidencia causal ni validación de campañas.

<!-- FIN RESULTADOS CLUSTERING -->

### Lectura comercial de los dos segmentos

La asignación coincide exactamente con la recurrencia observada: **todos los
2.801 compradores de C0 hicieron al menos dos pedidos entregados** (entre 2 y 15);
los **90.557 de C1 hicieron exactamente uno**. La recurrencia entregada es por tanto
**3,0003 %**, distinta del 3,1188 % histórico calculado considerando todos los estados.

| Perfil descriptivo | Pedidos entregados | Monto total (BRL) | % del monto total | Acción propuesta y evaluación |
|---|---:|---:|---:|---|
| C0: compradores recurrentes, 3,00 % | 5.921 | 728.408,75 | 5,51 % | Probar retención y recomendaciones; medir recompra incremental y margen frente a un grupo de control |
| C1: una sola compra entregada, 97,00 % | 90.557 | 12.493.089,36 | 94,49 % | Probar una segunda compra y reactivación diferenciada por recencia; medir conversión y costo del incentivo frente a control |
| Total | 96.478 | 13.221.498,11 | 100,00 % | No se han ejecutado campañas ni estimado retornos causales |

El gasto acumulado medio de C0 es **260,05 BRL**, frente a **137,96 BRL** en C1
(aproximadamente 1,89 veces); esto no demuestra un mayor ticket por pedido ni mayor
rentabilidad, porque M acumula varias compras. La recencia media difiere en **18,2
días** y la mediana en 20 días: no corresponde llamar «activos» a todos los miembros
de C0 ni «perdidos» a todos los de C1. Las acciones se refieren al corte histórico
2018-08-30, no son una campaña actual basada en actividad de 2026.

**Conclusión del modelado:** k=2 tiene tanto el mayor Silhouette (**0,7111425**) como
el menor Davies-Bouldin (**0,4765102**) entre los cinco candidatos. k=3–6 reducen la
inercia, pero su Silhouette queda entre 0,3473 y 0,3648. El buen resultado interno
refleja principalmente la separación entre una compra y recurrencia, fuertemente
marcada por F estandarizada; no prueba la existencia de dos tipos universales de
cliente ni una segmentación comercial fina. No se cambió el modelo para obtener
otros tamaños o nombres más atractivos.

**Precisión para la exposición:** el CSV contiene Silhouette 0,7111425180867478;
redondeado a cuatro decimales es **0,7111**, no 0,7114. Davies-Bouldin se redondea
a **0,4765**. La muestra fija tiene 1.800 compradores y no se presenta como una
evaluación exacta de los 93.358.

Las etiquetas descriptivas comparan las medias R/F/M de cada cluster con las de
toda la población: por ejemplo, R menor implica compras más recientes, no mayor
lealtad demostrada. El CSV incluye también medianas, porcentaje de recurrentes y
monto total para no ocultar la asimetría. Las acciones generadas son **propuestas
para validar**, no retornos comerciales comprobados. Los números de cluster son
identificadores arbitrarios y no deben compararse entre reentrenamientos sin alinear
los perfiles.

## 4. Grafo bipartito y métricas

Se agrupan primero los ítems entregados por `(seller_id, product_id)`. Cada relación
produce una arista no dirigida con **peso = cantidad de filas de ítem**, no pedidos
ni BRL. Se añaden pedidos distintos e importe conocido como información auxiliar,
con cantidad de precios conocidos/desconocidos. Una suma parcial se etiqueta como
`valor_articulos_conocido`; si todos los precios faltan queda nula. El peso no
depende de que el precio sea conocido. Ítems entregados sin vendedor o producto
se excluyen y se contabilizan. Las claves de ítem duplicadas detienen la ejecución.

- Partición vendedor: identificador interno `v:<seller_id>`.
- Partición producto: identificador interno `p:<product_id>`.
- Los prefijos impiden colisiones entre identificadores de distinto tipo.
- **Grado**: vecinos distintos. Para un vendedor es diversidad de productos; para
  un producto, cantidad de vendedores observados.
- **Grado ponderado**: suma de pesos incidentes, equivalente a ítems entregados
  asociados al nodo; no es rentabilidad ni cantidad de clientes.
- **Componentes conectados**: se numeran desde cero por tamaño decreciente;
  empate por identificador mínimo. No son comunidades detectadas ni territorios.
- **PageRank ponderado**: paseo aleatorio con probabilidades proporcionales a
  `peso`, amortiguación 0,85 y teletransporte uniforme; `max_iter=1000`,
  `tol=1e-12`. La tolerancia de convergencia L1 utilizada por NetworkX es `N*tol`.
  Es centralidad estructural; en una red no dirigida suele estar estrechamente
  relacionada con el grado ponderado. No mide reputación o calidad.

Las métricas usan **el grafo completo**. Solo para el dibujo se seleccionan los
cinco vendedores de mayor grado ponderado y hasta doce productos por vendedor,
ordenados por peso de su arista; los empates usan identificador. Se dibuja el
subgrafo inducido de esos nodos con `spring_layout(seed=42)`. Por defecto son como
máximo 65 nodos; no representa la distribución completa de la red. El CSV y los
metadatos conservan identificadores completos; el gráfico los abrevia.

### Resultados e interpretación de la red

<!-- INICIO RESULTADOS GRAFOS -->

**Red real: 35,186 nodos (2,970 vendedores y 32,216 productos), 33,659 aristas y 2,320 componentes.**

Ítems: 112,650 de entrada, 110,197 entregados, 110,197 utilizados; peso total 110,197. Excluidos: 2,453 de otros estados y 0 entregados sin claves. Importes desconocidos: 0; no afectan al conteo de ítems.

Principales componentes:

| Componente | Nodos | Vendedores | Productos | Aristas |
|---:|---:|---:|---:|---:|
| 0 | 9358 | 379 | 8979 | 9812 |
| 1 | 795 | 38 | 757 | 869 |
| 2 | 635 | 8 | 627 | 644 |
| 3 | 514 | 26 | 488 | 641 |
| 4 | 327 | 2 | 325 | 328 |
| 5 | 310 | 1 | 309 | 309 |
| 6 | 307 | 2 | 305 | 323 |
| 7 | 278 | 19 | 259 | 281 |
| 8 | 255 | 1 | 254 | 254 |
| 9 | 229 | 4 | 225 | 259 |

Principales nodos de tipo **vendedor** por ítems:

| Identificador | Grado | Ítems | PageRank | Componente |
|---|---:|---:|---:|---:|
| `6560211a19b47992c3666cc44a7e94c0` | 254 | 1996 | 0.0033321 | 8 |
| `4a3ca9315b744ce9f8e9374361493884` | 394 | 1949 | 0.0051863 | 2 |
| `1f50f920176fa81dab994f9023523100` | 23 | 1926 | 0.0003157 | 201 |
| `cc419e0650a3c5ba77189a1882b7556a` | 37 | 1719 | 0.0005351 | 0 |
| `da8622b14eb17ae2831f4ac5b9dab84a` | 221 | 1548 | 0.0029012 | 10 |

El vendedor `6560211a19b47992c3666cc44a7e94c0` lidera el volumen con 1,996 ítems y 254 productos distintos vendidos. No equivale a liderar ingresos o calidad.
El mayor PageRank dentro de este tipo corresponde a `4a3ca9315b744ce9f8e9374361493884` (0.0051863); es centralidad estructural ponderada, no reputación.

Principales nodos de tipo **producto** por ítems:

| Identificador | Grado | Ítems | PageRank | Componente |
|---|---:|---:|---:|---:|
| `aca2eb7d00ea1a7b8ebd4e68314663af` | 1 | 520 | 0.0004226 | 0 |
| `422879e10f46682990de24d770e7f83d` | 1 | 484 | 0.0000717 | 201 |
| `99a4788cb24856965c36a24e339b6058` | 2 | 477 | 0.0010868 | 2 |
| `389d119b48cf3043d311335e499d9c6b` | 1 | 390 | 0.0000586 | 201 |
| `368c6c730842d78016ad823897a372db` | 1 | 388 | 0.0000583 | 201 |

El producto `aca2eb7d00ea1a7b8ebd4e68314663af` lidera el volumen con 520 ítems y 1 vendedores asociados. No equivale a liderar ingresos o calidad.
El mayor PageRank dentro de este tipo corresponde a `99a4788cb24856965c36a24e339b6058` (0.0010868); es centralidad estructural ponderada, no reputación.

Relaciones más intensas:

| seller_id | product_id | Ítems | Pedidos distintos |
|---|---|---:|---:|
| `955fee9216a65b617aa5c0531780ce60` | `aca2eb7d00ea1a7b8ebd4e68314663af` | 520 | 425 |
| `1f50f920176fa81dab994f9023523100` | `422879e10f46682990de24d770e7f83d` | 484 | 352 |
| `4a3ca9315b744ce9f8e9374361493884` | `99a4788cb24856965c36a24e339b6058` | 471 | 450 |
| `1f50f920176fa81dab994f9023523100` | `389d119b48cf3043d311335e499d9c6b` | 390 | 309 |
| `1f50f920176fa81dab994f9023523100` | `368c6c730842d78016ad823897a372db` | 388 | 291 |

Hay 1,189 productos asociados a más de un vendedor. El componente mayor reúne 9,358 nodos (26.60% de la red).
Visualización: top 5 vendedores por ítems y hasta 12 productos por vendedor según peso de arista; subgrafo inducido de 65 nodos y 60 aristas; semilla 42. Los identificadores completos están en los CSV.
Conclusión: las conexiones reflejan asociaciones comerciales observadas y concentración de ítems; no son rutas logísticas, preferencias de compradores ni prueba de competencia. Las métricas se calcularon sobre toda la red, no sobre el dibujo.

<!-- FIN RESULTADOS GRAFOS -->

### Interpretación estructural y comercial

- **Volumen y variedad no son equivalentes.** `6560211a…` encabeza el volumen con
  1.996 ítems y 254 productos; `1f50f920…` registra 1.926 ítems en solo 23 productos.
  Son perfiles de catálogo distintos, no evidencia de diferente calidad o margen.
  Los cinco vendedores de mayor volumen suman **8,29 %** de los ítems entregados:
  ese ranking no permite afirmar que la mayoría del volumen esté en cinco vendedores.
- **PageRank no reproduce el ranking de ventas.** El líder es `4a3ca931…`, con
  394 productos y PageRank 0,0051863; el segundo y tercero por PageRank son
  `cca3071e…` (318 productos, 817 ítems, 0,0041752) y `d91fb3b7…` (309 productos,
  525 ítems, 0,0040503). La centralidad depende de los pesos, el vecindario y la
  estructura/tamaño de los componentes con teletransporte uniforme, no solo de ítems.
- **Red fragmentada.** El componente mayor reúne 9.358 nodos (**26,60 %**),
  379 vendedores, 8.979 productos y 9.812 aristas. El siguiente tiene 795 nodos:
  no existe un único componente que contenga la mayoría de la red. **2.205 de
  2.320 componentes (95,04 %)** contienen un solo vendedor. Solo **1.189 de
  32.216 productos (3,69 %)** aparecen con varios vendedores. Esto describe los
  identificadores del catálogo observado, no monopolios ni ausencia de alternativas.
- **Producto y relación principal.** `aca2eb7d…` suma 520 ítems, todos asociados
  a `955fee92…`, en **425 pedidos distintos**. El producto con mayor PageRank es
  `99a4788c…`: 477 ítems con dos vendedores; 471 provienen de `4a3ca931…`.
  La diferencia entre ítems y pedidos evita confundir ventas unitarias con cestas.
- **Uso sugerido:** revisar disponibilidad y dependencia de relaciones de alto
  volumen, y priorizar una auditoría de equivalencias del catálogo antes de inferir
  competencia. No se dispone de stock, márgenes ni proveedores alternativos para
  recomendar sustituciones concretas.

Los identificadores abreviados anteriores son solo para lectura; las tablas del
bloque calculado y los CSV conservan los identificadores completos. El dibujo de
65 nodos y 60 aristas es una selección de alto volumen, no la red completa: sus
cinco grupos visibles no equivalen a los 2.320 componentes globales. Las posiciones
del layout no representan geografía ni una distancia comercial medible.

## 5. Limitaciones metodológicas

1. El dataset es histórico y está truncado; no representa clientes activos hoy.
   Antigüedad y distinto tiempo de exposición afectan RFM; F no es una tasa anual.
2. El filtro delivered usa el estado final conocido al corte: hay sesgo de selección
   y censura hacia el final del periodo. No se afirma disponibilidad al comprar.
3. M es gasto observado en artículos, no margen ni valor de vida del cliente.
4. La escasa recurrencia puede concentrar F en uno; estandarizar una variable poco
   dispersa y K-Means pueden crear grupos pequeños de recurrentes. Hay que revisar
   tamaños, medianas y dispersión antes de usar los segmentos comercialmente.
5. Silhouette muestral y una única semilla no prueban estabilidad temporal. No hay
   etiquetas verdaderas ni validación causal de las acciones sugeridas.
6. El grafo agrega toda la historia y no incorpora dirección temporal, stock ni
   exposición. Ausencia de arista no demuestra ausencia de oferta comercial.
7. Conexiones entre vendedores a través de productos no prueban colaboración o
   competencia. Un identificador de producto no garantiza equivalencia entre otros
   identificadores de artículos similares; eso afecta la fragmentación observada.
8. Los rankings por volumen están condicionados al tiempo observado. El dibujo
   privilegia vendedores de alto volumen y no permite inferir la densidad global.

## 6. Aplicación de CRISP-DM

| Fase | Aplicación en este bloque | Evidencia / estado |
|---|---|---|
| Comprensión del negocio | Segmentación comercial y relaciones del catálogo vendido | Objetivos y límites anteriores; negocio general a cargo de Paulo |
| Comprensión de datos | Claves, granularidad, estados, cobertura y recurrencia | Tablas y diccionarios contrastados; 93.358 compradores y 3,0003 % recurrentes entregados |
| Preparación | Reutilizar tablas limpias; filtrar, agregar RFM y relaciones sin multiplicar importes | Código implementado; limpieza original sin cambios |
| Modelado | K-Means k=2–6 y red bipartita ponderada | k=2 seleccionado; 35.186 nodos y 33.659 aristas calculados |
| Evaluación | Métricas internas, perfiles originales, conciliación y lectura crítica de red | Silhouette/DB, tablas de perfiles y red conciliadas con entradas reales |
| Despliegue académico | CSV, PNG, informe reproducible y contratos para Paulo/Brandon | Archivos publicados en el árbol local y listos para GitHub; integración web a cargo de Paulo |

CRISP-DM es iterativo: una población inadecuada exige volver a comprensión y
preparación, no ajustar métricas hasta obtener una narrativa favorable. La evaluación
predictiva de Brandon no se reemplaza con los indicadores descriptivos de este bloque.

## 7. Reproducción

Desde la raíz, con Python 3.10 o posterior (entorno revisado: Python 3.12.10):

```powershell
python -m pip install -r requirements.txt
# Colocar antes el ZIP original en data/raw/archive.zip:
python src/preparar_datos.py
python src/clustering.py
python src/grafos.py
```

Con el entorno virtual local, utilizar `.\.venv\Scripts\python.exe` en lugar de `python`.
No es necesario regenerar la preparación si las tablas válidas ya están disponibles.

Opciones básicas:

```powershell
python src/clustering.py --muestra-silhouette 1800
python src/grafos.py --top-vendedores 5 --productos-por-vendedor 12
python src/clustering.py --pedidos C:/datos/pedidos_procesados.csv --output-root C:/entrega
python src/grafos.py --items C:/datos/items_procesados.csv --output-root C:/entrega
```

Los valores por defecto son relativos al repositorio, independientemente del
directorio de ejecución. Las rutas CLI relativas parten del directorio actual.
Los scripts crean carpetas, exportan CSV UTF-8 con BOM y conservan faltantes.
Cada ejecución registra versiones, hash SHA-256 de entrada y parámetros. Con
las mismas entradas, versiones y parámetros, los resultados son reproducibles;
pequeñas diferencias entre plataformas numéricas pueden cambiar centroides.

El informe se actualiza por bloques independientes si existe en la raíz de salida;
con otra raíz se guardan siempre `clustering_resumen.md` y `grafos_resumen.md` en
su carpeta `resultados/`. No se sobreescriben las secciones metodológicas manuales.
Los scripts no deben editar el mismo informe de manera simultánea.

## 8. Contrato de salida para Paulo

Todos los archivos siguientes son **salidas existentes verificadas con Olist**.
CSV: coma, punto decimal, UTF-8 BOM, cabecera,
sin índice, identificadores de negocio como texto; faltantes como celdas vacías.

| Archivo en `resultados/` | Granularidad y columnas |
|---|---|
| `clientes_clusters.csv` | Comprador; `customer_unique_id` texto único; `recencia` días enteros, `frecuencia` pedidos enteros, `monto` BRL real, `cluster` entero, `segmento` texto |
| `perfiles_clusters.csv` | Cluster; `cluster`, `cantidad_clientes`, `porcentaje` (0–100), `recencia_promedio`, `recencia_mediana`, `frecuencia_promedio`, `frecuencia_mediana`, `monto_promedio`, `monto_mediana`, `porcentaje_recurrentes`, `monto_total`, `segmento`, `interpretacion`, `accion_sugerida` |
| `evaluacion_clustering.csv` | k; `k`, `silhouette`, `davies_bouldin`, `inercia`, `random_state`, `n_init`, `init`, `algorithm`, `max_iter`, `tol`, `iteraciones`, `clientes_ajuste`, `muestra_silhouette`, `escala`, `seleccionado` booleano |
| `rfm_distribuciones.csv` | Variable; distribución original, asimetría antes/después y transformación aplicada |
| `grafo_aristas.csv` | Pareja única; `seller_id`, `product_id` texto; `peso`, `pedidos_distintos`, `importes_conocidos`, `importes_desconocidos` enteros; `valor_articulos_conocido` BRL real anulable |
| `grafo_metricas.csv` | Nodo; `nodo_id` texto único prefijado, `identificador` texto original, `tipo_nodo` vendedor/producto, `grado`, `grado_ponderado` enteros, `pagerank` real, `componente` entero |
| `grafo_componentes.csv` | Componente; `componente`, `nodos`, `vendedores`, `productos`, `aristas`, todos enteros |

`identificador` no es una clave universal: usar `nodo_id` o `(tipo_nodo,
identificador)`. El `porcentaje` de perfiles usa compradores elegibles, no pedidos.
No sumar `grado_ponderado` de vendedores y productos para obtener volumen: duplica
los ítems por las dos puntas de cada arista. Análogamente la suma de grados es 2E.

Gráficos existentes en `resultados/graficos/`:

- `clustering_clientes_por_cluster.png`.
- `clustering_evaluacion_k.png`.
- `clustering_perfiles_rfm.png`.
- `clustering_distribuciones_rfm.png`.
- `grafo_vendedores_productos.png`.
- `grafo_principales_vendedores.png`.

También existen `clustering_metadata.json`, `grafos_metadata.json` y los dos
resúmenes Markdown. Para la web, cargar preferentemente perfiles/evaluación y
rankings agregados; no enviar decenas de miles de nodos al navegador. No se ha
cambiado el frontend ni se afirma que ya consuma estos contratos.

## 9. Verificación y conclusiones

La preparación y ambos análisis fueron ejecutados por Anderson; este cierre revisó
los archivos reales sin repetir K-Means ni PageRank. Comprobaciones prácticas:

| Control sobre los archivos entregados | Resultado |
|---|---|
| Compradores únicos y tamaños de clusters | 93.358 = 2.801 + 90.557; sin duplicados |
| Frecuencia y monto RFM | 96.478 pedidos y 13.221.498,11 BRL conciliados con entradas |
| Medias/medianas originales y porcentajes | Recalculados desde clientes; coinciden con perfiles; porcentajes suman 100 % |
| Evaluación k=2–6 | Cinco filas, métricas finitas y un único k seleccionado |
| Muestra | 1.800 identificadores distintos existentes en la población |
| Relaciones y métricas por tipo de nodo | 33.659 parejas únicas; grados y pesos reconstruidos desde aristas coinciden |
| Suma de grados / grados ponderados | 67.318 = 2E; 220.394 = 2 × 110.197 |
| Componentes | 2.320; sus tamaños/aristas suman 35.186/33.659; cada arista une nodos del mismo componente |
| PageRank exportado | Valores finitos, no negativos y suma uno con tolerancia numérica |
| Procedencia | SHA-256 de ambas entradas coinciden con los metadatos |
| Esquemas de entrada | 41 columnas de pedidos, 40 de ítems y 5 de geografía; tipos contrastados con el diccionario |
| PNG | Seis imágenes válidas y no vacías; métricas, perfiles y subgrafo revisados visualmente |

Se corrigió el `DeprecationWarning` de NumPy/Pandas usando
`pd.Timedelta(1, unit='D')` en la referencia temporal. Es el mismo incremento de un
día: RFM se contrastó con el CSV existente; no se cambiaron población,
transformaciones, semillas, hiperparámetros ni resultados del modelo. Los CSV y PNG
originales de la ejecución se conservaron. No se ejecutó una suite extensa.

Entorno de los metadatos: Python 3.12.10, Pandas 2.3.3, NumPy 2.5.4, Matplotlib
3.11.2, scikit-learn 1.9.1 y NetworkX 3.7. La verificación inicial ya había comprobado
dependencias y tres pruebas existentes de preparación/asociación/API. El cierre
no modifica la limpieza, asociación ni frontend.

### Conclusiones técnicas

1. La partición seleccionada identifica **recurrencia frente a compra única**;
   el elevado Silhouette se interpreta dentro de ese desequilibrio 3 %/97 %, no
   como evidencia de fidelidad o respuesta a campañas.
2. Los recurrentes muestran más gasto acumulado y algo menos de recencia, pero
   representan solo el 5,51 % del importe observado. La oportunidad de segunda
   compra es una hipótesis comercial amplia, no una rentabilidad demostrada.
3. El grafo distingue volumen de ítems, amplitud de catálogo y centralidad. Su
   fragmentación y los identificadores de producto limitan inferencias de competencia.
4. Los resultados son trazables y aptos para una entrega académica; Brandon
   recibe tablas reales y contratos, no modelos predictivos ni atributos históricos
   completos que pueda usar sin controlar fuga temporal.

## 10. Publicación y transferencia

Los entregables finales son los dos scripts; este informe; el guion de seis
diapositivas; el handoff; los siete CSV de la tabla de contratos; los dos metadatos;
`clustering_resumen.md`, `grafos_resumen.md`; y los seis PNG enumerados.
También se incluyen los cambios de `README.md`, `requirements.txt` y la sección
de Anderson en `docs/tareas_equipo.md`.

Los archivos están organizados en `src/`, `docs/`, `resultados/` y
`resultados/graficos/`; el mayor resultado individual ocupa aproximadamente 7,4 MB,
por debajo del límite de 100 MiB de GitHub. No requieren Git LFS para esta entrega.
`.gitignore` mantiene fuera `data/raw/`, `data/processed/`, `.venv/` y cachés.
Brandon debe regenerar las tablas o recibirlas por un canal acordado: clonar GitHub
no descarga automáticamente el dataset. Véase [handoff de Brandon](handoff_brandon.md).

Hay cambios locales preexistentes en reportes/diccionarios de preparación,
producidos al regenerarlos, además de los entregables de Anderson. Se conservaron
sin editar; revisar su inclusión por separado y evitar `git add .` indiscriminado.
No se ha hecho staging, commit ni push. La integración web y las tareas predictivas
no forman parte del criterio de cierre de Anderson.
