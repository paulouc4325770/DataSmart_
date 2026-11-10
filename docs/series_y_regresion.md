# Informe de Modelado Predictivo: Series Temporales, Regresión y Evaluación Multimodelo

**Proyecto:** DataSmart — Minería de Datos (UNMSM FISI - 2026-II)  
**Bloque de Trabajo:** Modelado Predictivo, Evaluación y Consolidación  
**Autor:** Brandon (Senior Frontend & Predictive Modeling)  
**Coordinación de Equipo:** Jerson (Preparación y Calidad), Paulo (Negocio, Asociación y Prototipo), Anderson (Clustering y Grafos)  
**Fecha:** Noviembre 2026  
**Criterio de Cierre:** Los resultados de evaluación predictiva corresponden estrictamente a datos cronológicamente posteriores a los de entrenamiento (evaluación fuera de muestra sin fuga de información).

---

## 1. Resumen Ejecutivo y Metodología CRISP-DM

Este informe documenta la implementación, validación y evaluación de los modelos analíticos predictivos desarrollados para responder a las preguntas de negocio **PN-03/PN-04 (Pronóstico de Ventas)** y **PN-07/PN-08 (Tiempo de Entrega y Riesgo Logístico)** sobre el dataset oficial del marketplace Olist (Brasil).

### Mapeo CRISP-DM del Bloque Predictivo

```mermaid
flowchart LR
    A["1. Comprensión del Negocio<br/>PN-03, PN-04, PN-07"] --> B["2. Comprensión y Prep.<br/>pedidos & items procesados"]
    B --> C["3. Modelado Predictivo<br/>Split Cronológico Estricto"]
    C --> D["Series: Suavizamiento Exponencial<br/>Regresión: Ridge & Random Forest"]
    D --> E["4. Evaluación Fuera de Muestra<br/>MAE, RMSE, R²"]
    E --> F["5. Consolidación Multimodelo<br/>evaluacion_comparativa.csv"]
```

---

## 2. Series Temporales de Ventas (PN-03 & PN-04)

### 2.1. Definición del Problema y Justificación de la Frecuencia Semanal

Para la planificación de inventarios, asignación de soporte de atención y provisión de servidores en campañas promocionales, se requiere pronosticar el flujo monetario de transacciones.

- **Definición de Venta:** Suma de `valor_articulos` (precio de productos comprados) en pedidos con estado verificado `delivered`. Se excluyen fletes, recargos de pago y pedidos cancelados o en tránsito.
- **Ventana Histórica Completa:** Los datos de 2016 representan solo 267 pedidos fragmentarios, y la última semana de agosto de 2018 sufre censura por derecha (pedidos comprados que aún no completaban su entrega al momento del corte). Por tanto, la ventana regular y completa comprende **84 semanas continuas**: del lunes **2017-01-09** al domingo **2018-08-19** (ancla semanal `W-SUN`).
- **Justificación de Frecuencia:** En frecuencia mensual, la historia regular abarca únicamente 20 observaciones, lo cual imposibilita ajustar estacionalidades complejas sin sobreajuste severo. La frecuencia semanal proporciona **84 periodos completos**, garantizando una muestra robusta para estimar niveles y tendencias.

### 2.2. Partición Cronológica Estricta (Sin Fuga Temporal)

- **Conjunto de Entrenamiento (`train`):** 72 semanas (2017-01-15 a 2018-05-27), representando el **85,7%** de la serie.
- **Conjunto de Prueba (`test`):** 12 semanas (2018-06-03 a 2018-08-19), equivalente al **14,3%** (horizonte de 3 meses).
- **Control de Fuga:** Prohibido el uso de técnicas como `train_test_split` aleatorio o K-Fold con barajado (`shuffle=True`), que permitirían interpolar información del futuro.

### 2.3. Modelos Evaluados y Comparación de Métricas

Se comparó un baseline ingenuo contra variantes de suavizamiento exponencial ajustadas mediante estimación por máxima verosimilitud en `train`:

1. **`baseline_ultimo` (Persistencia Naïve):** Proyecta como valor constante el último registro observado en el periodo de entrenamiento ($\hat{y}_{t+h} = y_T = 286.082,10\text{ BRL}$).
2. **`suavizamiento_exponencial_simple` (SES):** Modelo autorregresivo con ponderación geométrica decreciente ($\alpha = 0,1839$).
3. **`suavizamiento_exponencial_holt` (Holt con Tendencia Amortiguada):** Modela nivel y tendencia con factor de amortiguamiento ($\alpha = 0,2241, \beta = 0,0412, \phi = 0,9200$).

#### Tabla Oficial de Evaluación de Series Temporales (`resultados/evaluacion_series.csv`)

| Modelo | Frecuencia | Train Inicio | Train Fin | Test Inicio | Test Fin | $n_{train}$ | $n_{test}$ | MAE (BRL) | RMSE (BRL) | Reducción MAE vs Baseline |
|---|---|---|---|---|---|---:|---:|---:|---:|---:|
| **`baseline_ultimo`** | `W-SUN` | 2017-01-15 | 2018-05-27 | 2018-06-03 | 2018-08-19 | 72 | 12 | 77.679,09 | 86.643,00 | Base (0,0%) |
| **`suavizamiento_exponencial_simple`** | `W-SUN` | 2017-01-15 | 2018-05-27 | 2018-06-03 | 2018-08-19 | 72 | 12 | **39.858,13** | **49.725,61** | **-48,69%** |
| **`suavizamiento_exponencial_holt`** | `W-SUN` | 2017-01-15 | 2018-05-27 | 2018-06-03 | 2018-08-19 | 72 | 12 | 43.183,69 | 51.611,93 | -44,41% |

El **Suavizamiento Exponencial Simple** logra una reducción del **48,69%** en el error absoluto medio (MAE) respecto a la persistencia ingenua, estabilizando la varianza observada tras el pico de ventas del primer trimestre de 2018.

Gráfico generado: `resultados/graficos/series_temporales_prediccion.png`.

---

## 3. Regresión Predictiva de Días de Entrega (PN-07 & PN-08)

### 3.1. Definición del Problema y Momento de Predicción

Para mitigar insatisfacciones y predecir entregas tardías antes de que ocurran, el modelo debe estimar los **días reales entre la compra y la entrega física** (`dias_entrega = (order_delivered_customer_date - order_purchase_timestamp).days`).

- **Momento de Predicción Estricto:** **Instante del Checkout** (`order_purchase_timestamp`).
- **Población Evaluada:** 96.470 pedidos entregados con valor de entrega estrictamente positivo (`dias_entrega > 0`).

### 3.2. Prevención Estricta de Fuga de Información (Data Leakage)

En un entorno productivo real, al momento de pulsar "Comprar", el sistema **NO** conoce eventos futuros. Por ello, se auditaron y excluyeron explícitamente:
- ❌ Fecha de entrega real (`order_delivered_customer_date`) y fecha de despacho al transportista (`order_delivered_carrier_date`).
- ❌ Variables derivadas de retraso (`dias_retraso_calendario`, `entrega_tardia`).
- ❌ Reseñas y calificaciones (`review_score`, `cantidad_resenas`, `sin_resenas`).
- ❌ Variables de post-procesamiento (clusters RFM históricos globales o PageRank de grafos calculados con todo el dataset).

### 3.3. Ingeniería de Atributos Disponibles al Comprar

Los atributos de ítems se agregaron a nivel de pedido (`order_id`) antes de la unión para mantener la granularidad 1 a 1 sin duplicar importes:
1. **Físicos y Carga:** `peso_total_g` ($\sum \text{peso}$), `volumen_total_cm3` ($\sum \text{volumen}$).
2. **Geográficos:** `distancia_media_km` (media geodésica cliente-vendedores), `distancia_max_km`, `ruta_interestatal` (flag binario si cliente y vendedor residen en estados distintos).
3. **Comerciales y Promesa:** `dias_prometidos` ($\text{fecha estimada} - \text{fecha compra}$), `cantidad_items`, `cantidad_productos`, `cantidad_vendedores`, `valor_articulos`, `valor_flete`.
4. **Contexto Temporal:** `mes_compra`, `dia_semana_compra`, `hora_compra`.
5. **Regionales Categóricos:** `customer_state` (27 estados), `seller_state_principal` (estado modal de vendedores).

### 3.4. Partición Cronológica

- **Corte de Separación:** `2018-06-01 00:00:00`.
- **Entrenamiento (`train`):** **77.867 pedidos** (15 Sep 2016 al 31 May 2018; 80,72%).
- **Prueba (`test`):** **18.603 pedidos** (01 Jun 2018 al 29 Ago 2018; 19,28%).
- **Pipeline:** Imputación por mediana + escalado estándar para numéricas; OneHotEncoder para categóricas con `handle_unknown='ignore'`. Todo el preprocesamiento se ajusta **únicamente en train**.

### 3.5. Comparación de Modelos de Regresión

#### Tabla Oficial de Evaluación de Regresión (`resultados/evaluacion_regresion.csv`)

| Modelo | Partición Test | $n_{train}$ | $n_{test}$ | MAE (días) | RMSE (días) | $R^2$ Score | Tiempo Ajuste (s) |
|---|---|---:|---:|---:|---:|---:|---:|
| **`baseline_mediana`** | Jun – Ago 2018 | 77.867 | 18.603 | 4,9532 | 6,3560 | -0,1922 | < 0,01 s |
| **`ridge`** ($\alpha=10.0$) | Jun – Ago 2018 | 77.867 | 18.603 | 5,0913 | 6,5281 | -0,2577 | 0,27 s |
| **`random_forest`** | Jun – Ago 2018 | 77.867 | 18.603 | **4,1289** | **5,6080** | **+0,0719** | 8,91 s |

#### Hallazgos Técnicos:
1. **No Linealidad Logística:** La regresión lineal (Ridge) sufre para capturar los cuellos de botella geográficos no lineales (e.g., pedidos a la región Norte/Nordeste donde la distancia no escala linealmente debido a la infraestructura fluvial o aérea).
2. **Rendimiento de Random Forest:** El ensamble Random Forest reduce el error absoluto medio a **4,13 días** (una mejora de **16,64%** frente a la mediana histórica y de **18,9%** frente a Ridge) y alcanza un $R^2$ positivo de **+0,0719** en datos completamente futuros, demostrando capacidad real de generalización.
3. Gráficos generados:
   - `resultados/graficos/regresion_real_vs_predicho.png`
   - `resultados/graficos/regresion_residuos.png`

---

## 4. Consolidación Comparativa Multimodelo

El archivo `resultados/evaluacion_comparativa.csv` consolida las 5 familias analíticas del proyecto:

| Familia Técnica | Modelos Comparados | Métrica Clave | Mejor Desempeño | Responsable |
|---|---|---|---|---|
| **Reglas de Asociación** | Apriori vs FP-Growth | Reglas generadas / Tiempo | FP-Growth (0,07 s vs 0,15 s) | Paulo |
| **Clustering RFM** | K-Means ($k=2..6$) | Silhouette / Davies-Bouldin | $k=2$ (Sil: 0,711; DB: 0,477) | Anderson |
| **Grafos y Redes** | Bipartita Vendedor-Producto | PageRank / Grado Ponderado | Hub Top PageRank: `4a3ca9...` | Anderson |
| **Series Temporales** | Naïve vs Suavizamiento Exponencial | MAE (BRL) semanal | SES (MAE: 39.858 BRL, -48,7%) | Brandon |
| **Regresión Predictiva** | Mediana vs Ridge vs Random Forest | MAE (días) / $R^2$ | Random Forest (4,13 d, $R^2$: 0,072) | Brandon |

> [!NOTE]
> Las métricas entre familias analíticas distintas no son conmensurables entre sí (no se puede comparar MAE en BRL con MAE en días o Silhouette con Lift). La comparativa se estructura por familia técnica.

---

## 5. Reproducibilidad y Comandos de Ejecución

Todos los módulos predictivos pueden ejecutarse directamente desde la raíz del repositorio con Python 3.11:

```powershell
# 1. Ejecutar pronóstico de series temporales
python src/series_temporales.py

# 2. Ejecutar regresión de días de entrega
python src/regresion.py

# 3. Consolidar matriz multimodelo
python src/consolidar_evaluacion.py

# 4. Ejecutar suite de pruebas unitarias automatizadas
python -m unittest discover tests
```
