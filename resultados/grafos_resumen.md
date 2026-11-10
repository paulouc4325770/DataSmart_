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
