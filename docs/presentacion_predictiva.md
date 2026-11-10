# Guion de Presentación: Modelado Predictivo, Series y Regresión

**Expositor:** Brandon  
**Tema:** Pronóstico de Ventas (PN-03/04), Regresión Logística de Entrega (PN-07/08) y Evaluación Multimodelo  
**Tiempo estimado:** 8 a 10 minutos (6 diapositivas)

---

### Diapositiva 1 — Título y Alcance Predictivo
- **Título:** Modelado Predictivo: Anticipando la Demanda y Optimizando la Logística de Olist
- **Subtítulo:** De la descripción a la anticipación con validación temporal estricta
- **Puntos Clave:**
  - Preguntas de Negocio resueltas: PN-03/04 (Series Temporales) y PN-07/08 (Tiempos de Entrega).
  - Regla de oro metodológica: Partición cronológica estricta sin barajado (`shuffle=False`) para evitar cualquier fuga de datos (data leakage).

---

### Diapositiva 2 — Series Temporales de Ventas: Justificación y Granularidad
- **Título:** Pronóstico de Ventas Semanales (84 Semanas Completas)
- **Visual:** `resultados/graficos/series_temporales_prediccion.png`
- **Puntos Clave:**
  - ¿Por qué semanal y no mensual? La ventana regular tiene solo 20 meses, insuficiente para modelos estables. Semanalmente disponemos de 84 periodos completos.
  - Filtro: Pedidos entregados (`delivered`) y variable `valor_articulos` (13,04M BRL).
  - Split: 72 semanas en Train (Ene 2017 a May 2018) y 12 semanas en Test (Jun a Ago 2018).

---

### Diapositiva 3 — Evaluación de Series Temporales: Suavizamiento Exponencial
- **Título:** Desempeño Fuera de Muestra: SES vs Baseline Ingenuo
- **Visual:** Tabla de errores y métricas comparativas.
- **Puntos Clave:**
  - Baseline (Persistencia Naïve): MAE = 77.679 BRL, RMSE = 86.643 BRL.
  - Suavizamiento Exponencial Simple: MAE = 39.858 BRL, RMSE = 49.726 BRL.
  - **Conclusión de Negocio:** Reducción del **48,69%** en el error absoluto, permitiendo presupuestar el flujo de caja semanal con un margen de error acotado.

---

### Diapositiva 4 — Regresión de Días de Entrega: Prevención de Fuga de Información
- **Título:** Predicción de Días de Entrega en el Momento del Checkout
- **Puntos Clave:**
  - Objetivo: Predecir `dias_entrega` al pulsar "Comprar".
  - Auditoría contra Data Leakage: Exclusión total de fechas de entrega real, retrasos observados, reseñas y eventos de transporte posteriores.
  - Variables disponibles: Peso y volumen agregado de ítems, distancia geodésica media y máxima, ruta interestatal, días prometidos, estado cliente/vendedor y hora/día de compra.

---

### Diapositiva 5 — Desempeño de Modelos de Regresión: Ridge vs Random Forest
- **Título:** Random Forest Supera la Mediana Histórica y Captura la No Linealidad
- **Visual:** `resultados/graficos/regresion_real_vs_predicho.png` y `regresion_residuos.png`
- **Puntos Clave:**
  - Baseline Mediana: MAE = 4,95 días | $R^2 = -0,192$
  - Ridge Regression ($\alpha=10.0$): MAE = 5,09 días | $R^2 = -0,258$
  - **Random Forest:** MAE = **4,13 días** | RMSE = **5,61 días** | **$R^2 = +0,072$**
  - Mejora de **16,64%** frente al baseline y generalización positiva en 18.603 pedidos futuros no vistos.

---

### Diapositiva 6 — Síntesis Multimodelo y Cierre de la Entrega
- **Título:** Matriz de Evaluación Consolidada de Minería de Datos
- **Visual:** Tabla comparativa consolidada (`evaluacion_comparativa.csv`).
- **Puntos Clave:**
  - 5 Familias consolidadas: Asociación (Paulo), Clustering y Grafos (Anderson), Series y Regresión (Brandon).
  - Trazabilidad y Reproducibilidad: Scripts en `src/`, resultados en `resultados/` y suite de pruebas unitarias al 100%.
