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
