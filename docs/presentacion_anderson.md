# Exposición de Anderson — seis diapositivas listas para presentar

**Duración orientativa: seis minutos.** Cifras contrastadas con los CSV y metadatos
de la ejecución real de Olist. Los seis PNG existen en `resultados/graficos/`.
Usar coma decimal y punto de miles en las diapositivas; conservar los números de
cluster del CSV. Los hashes abreviados de vendedor/producto no son nombres reales.

## 1. Objetivo: compradores y relaciones comerciales (40 s)

**Contenido sugerido**

- ¿Cómo diferenciar la compra única de la recurrencia y orientar acciones?
- ¿Qué vendedores y productos destacan por volumen y estructura comercial?
- Dos técnicas descriptivas: RFM + K-Means y grafo bipartito ponderado.
- Alcance: 93.358 compradores y 110.197 ítems de pedidos entregados.

**Gráfico:** `resultados/graficos/clustering_clientes_por_cluster.png`.
Destacar como anticipo el reparto 3 % / 97 %; explicar los perfiles en la diapositiva 4.

**Guion oral:** «Mi parte combina segmentación de compradores y análisis de
relaciones vendedor–producto. Usamos las tablas preparadas por Jerson y pedidos
entregados para mantener una población comercial consistente. El objetivo es
describir comportamientos y proponer acciones que después se puedan validar.
Como anticipo, el reparto es muy desigual: tres por ciento de compradores
recurrentes y noventa y siete por ciento con una sola compra entregada. No estamos
prediciendo ventas ni afirmando que una campaña ya funcionó».

## 2. Datos y RFM: una fila por comprador (55 s)

**Contenido sugerido**

- 96.478 pedidos entregados → 93.358 `customer_unique_id`.
- R = días desde última compra; F = pedidos distintos; M = artículos en BRL sin flete.
- Referencia reproducible: **30/08/2018**; última compra: 29/08/2018.
- 2.963 pedidos de otros estados excluidos; ninguna exclusión adicional por historia incompleta.
- Log1p en F y M; R sin logaritmo; después StandardScaler.

**Gráfico:** `resultados/graficos/clustering_distribuciones_rfm.png`.
Señalar que la asimetría de M pasa de 9,747 a 0,280; la de F, de 11,095 a 6,522.
R no se transforma porque su asimetría original es solo 0,447.

**Guion oral:** «Agrupamos por el identificador único del comprador, no por el
registro transaccional del cliente. La frecuencia cuenta pedidos distintos y el
monto suma artículos sin duplicarlos mediante joins. La referencia es el día
siguiente a la última compra y no cambia con el reloj del ordenador. Frecuencia
y monto tienen colas largas: usamos logaritmos para reducir su asimetría y luego
estandarizamos las tres variables. La frecuencia sigue siendo muy desigual,
porque la gran mayoría solo compró una vez».

## 3. Evaluación: por qué elegimos k=2 (60 s)

**Contenido sugerido**

- K-Means con k=2–6; `random_state=42`, `n_init=10`.
- Ajuste con 93.358 compradores; Silhouette en la misma muestra de 1.800.
- **k=2: Silhouette 0,7111; Davies-Bouldin 0,4765; inercia 190.688,46.**
- k=3–6: Silhouette entre 0,3473 y 0,3648; más particiones no mejoran la separación.

**Gráfico:** `resultados/graficos/clustering_evaluacion_k.png`.
Señalar la línea roja de k=2, el máximo Silhouette y el mínimo Davies-Bouldin.

**Guion oral:** «Comparamos cinco alternativas con las mismas transformaciones
y la misma muestra de evaluación. Elegimos el mayor Silhouette: k igual a dos
también obtiene el menor Davies-Bouldin, por lo que las dos métricas coinciden.
La inercia disminuye al añadir grupos, como es esperable, pero eso no basta para
preferirlos. El Silhouette es muestral, no una evaluación exacta de todos los
clientes, y una buena separación interna no demuestra estabilidad temporal ni
un efecto comercial de las acciones propuestas».

## 4. Resultados: recurrencia frente a compra única (75 s)

**Contenido sugerido**

| Resultado | C0: recurrentes | C1: una compra entregada |
|---|---:|---:|
| Compradores | 2.801 (3,00 %) | 90.557 (97,00 %) |
| R media / mediana, días | 220,8 / 200 | 239,0 / 220 |
| F media / mediana, pedidos | 2,114 / 2 | 1 / 1 |
| M media / mediana, BRL | 260,05 / 182,10 | 137,96 / 86,96 |
| Participación del monto | 5,51 % | 94,49 % |
| Acción a validar | Retención y recomendaciones | Segunda compra y reactivación según recencia |

**Gráfico:** `resultados/graficos/clustering_perfiles_rfm.png`.

**Guion oral:** «Los grupos coinciden exactamente con la recurrencia observada:
todos los del cluster cero hicieron dos o más pedidos; todos los del uno hicieron
solo uno. El primer grupo acumula unos 260 reales por comprador frente a 138,
pero eso no significa un mayor ticket por pedido, porque suma varias compras.
La diferencia de recencia es moderada: unos dieciocho días. Por eso no los llamamos
VIP ni clientes perdidos. Proponemos probar retención en recurrentes y una segunda
compra en el grupo mayoritario, midiendo resultados frente a un control».

## 5. Grafo: volumen, centralidad y fragmentación (85 s)

**Contenido sugerido**

- 2.970 vendedores + 32.216 productos = **35.186 nodos**.
- **33.659 aristas**; peso total **110.197 ítems**; **2.320 componentes**.
- Mayor componente: 9.358 nodos, **26,60 %** del total.
- Líder por volumen: `6560211a…`, 1.996 ítems y 254 productos.
- Líder por PageRank: `4a3ca931…`, 0,0051863; 1.949 ítems y 394 productos.
- Producto de mayor volumen: `aca2eb7d…`, 520 ítems con `955fee92…` en 425 pedidos.

**Gráficos:** `resultados/graficos/grafo_vendedores_productos.png` y, como apoyo,
`resultados/graficos/grafo_principales_vendedores.png`.
El dibujo contiene **65 nodos y 60 aristas**, no los 35.186 nodos completos.

**Guion oral:** «Una arista indica que un vendedor vendió un producto; su peso
cuenta ítems, no ingresos. Calculamos todas las métricas en la red completa,
pero solo dibujamos cinco vendedores de alto volumen y hasta doce productos
por vendedor. El líder por volumen no es el líder por PageRank: esa medida depende
también del vecindario y de los componentes. La red está fragmentada: el componente
mayor contiene alrededor de una cuarta parte de los nodos y solo el 3,69 por ciento
de los productos aparece con varios vendedores. Eso no prueba monopolios ni ausencia
de productos equivalentes con otro identificador».

## 6. Conclusiones, CRISP-DM y continuidad (45 s)

**Contenido sugerido**

- Hallazgo RFM: recurrencia escasa; k=2 separa compra única y repetida, no fidelidad demostrada.
- Hallazgo de red: volumen, catálogo y PageRank son dimensiones distintas; fragmentación elevada.
- CRISP-DM: negocio → datos → agregación → modelos → métricas/conciliación → CSV, PNG e informe.
- Límites: Olist histórico, estado final delivered, exposición desigual y ausencia de causalidad.
- Brandon: series, regresión y evaluación predictiva; Paulo: integración de estos resultados.

**Visual:** tabla CRISP-DM de `docs/clustering_y_grafos.md`; mantener una miniatura
de `resultados/graficos/clustering_evaluacion_k.png` como evidencia de evaluación.
No es necesario generar un séptimo gráfico.

**Guion oral:** «La principal conclusión es que los resultados tienen una
interpretación concreta y también límites. La separación de compradores está
dominada por la recurrencia y la red distingue volumen de centralidad, sin
demostrar causalidad. CRISP-DM conecta estas preguntas con datos, modelos,
evaluación y entregables reproducibles. Brandon recibe las entradas y los
contratos para hacer series y regresión, cuidando los cortes temporales y la fuga
de información. Paulo puede integrar los CSV sin usar valores de demostración».

### Apoyo para preguntas

- Silhouette exacto: **0,7111425180867478**; a cuatro decimales, **0,7111**, no 0,7114.
- Recurrencia: **3,0003 % entre compradores de entregados**; no mezclar con el
  3,1188 % histórico entre compradores de todos los estados.
- No se interpretan pesos como BRL ni PageRank como reputación.
- Resultados completos, claves y limitaciones: `docs/clustering_y_grafos.md`.
