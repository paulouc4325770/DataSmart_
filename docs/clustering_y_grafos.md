# DataSmart — Segmentación de Clientes (Clustering RFM) y Análisis de Relaciones (Grafos)

**Responsable:** Brandon (Rol: Clustering, Grafos y Metodología CRISP-DM)  
**Curso:** Minería de Datos, octavo ciclo (UNMSM – FISI)  
**Metodología:** CRISP-DM (Fase 1: Negocio, Fase 3: Preparación, Fase 4: Modelado, Fase 5: Evaluación y Fase 6: Despliegue)  
**Dataset:** Brazilian E-Commerce Public Dataset by Olist (Kaggle), datos procesados en `data/processed/`  
**Entregables de código:** `src/clustering.py` y `src/grafos.py`  
**Pruebas unitarias:** `tests/test_clustering.py` y `tests/test_grafos.py`  

---

## 1. Introducción y Preguntas de Negocio

Este entregable responde directamente a tres de las diez preguntas estratégicas de negocio formuladas en el proyecto DataSmart:

- **PN-01 (Clientes):** *¿Qué grupos de clientes presentan perfiles de compra similares?*  
  Abordado mediante segmentación **RFM (Recencia, Frecuencia, Monto) + K-Means**.
- **PN-02 (Clientes):** *¿Qué compradores concentran los mayores importes y cómo se diferencian de la masa transaccional?*  
  Identificación de clientes de alto valor y recurrentes frente a compradores de compra única.
- **PN-09 (Relaciones):** *¿Qué conexiones forman los comerciantes y los productos en el ecosistema de Olist?*  
  Abordado mediante **Análisis de Redes Bipartitas Vendedor–Producto** con métricas de centralidad, componentes conexas y **PageRank**.

---

## 2. Marco Metodológico CRISP-DM

### 2.1 Comprensión del Negocio y de los Datos
En el marketplace de Olist, el comportamiento de los clientes presenta dos características estructurales críticas:
1. **Baja tasa de recompra histórica:** De los 96.096 compradores únicos en pedidos totales (y 93.358 en pedidos entregados), solo el **3,00 % a 3,12 %** ha realizado más de un pedido.
2. **Alta dispersión en el gasto acumulado:** El monto de compra por cliente varía desde **R$ 0,85 hasta R$ 13.440,00**, con una mediana de **R$ 89,73** y una media de **R$ 141,62**, lo que evidencia una marcada asimetría positiva a la derecha.

### 2.2 Preparación de Variables para Clustering
Para construir los atributos RFM a nivel de comprador único (`customer_unique_id`):
- **Recencia ($R$):** Días transcurridos entre la fecha de la última compra (`order_purchase_timestamp`) y una fecha de corte explícita fijada exactamente un día después del último pedido entregado del dataset: `2018-08-30 15:00:37 UTC`.
- **Frecuencia ($F$):** Cantidad de órdenes distintas (`order_id.nunique()`).
- **Monto ($M$):** Importe acumulado de los artículos adquiridos (`sum(valor_articulos)`).

#### Transformación y Escalado
Dado que $F$ y $M$ presentan distribuciones con sesgo extremo (outliers superiores), aplicar distancia euclidiana directa en K-Means provocaría que el 1% de compradores extremos distorsione por completo los centroides. Se aplicó:
1. **Transformación logarítmica:** $x' = \ln(1 + x)$ (`np.log1p`) sobre $R, F, M$ para normalizar las varianzas.
2. **Estandarización Z-score:** `StandardScaler()` ($\mu = 0, \sigma = 1$) para que ninguna dimensión domine artificialmente sobre las demás.

---

## 3. Resultados de Segmentación con K-Means

Se ejecutó K-Means con inicialización `k-means++` (10 reinicios, semilla pseudoaleatoria fija `semilla=42`) explorando valores de $k$ desde 2 hasta 6. La evaluación combinó:
- **Inercia (WCSS):** Criterio del codo para medir compactación interna.
- **Davies-Bouldin Index:** Relación de similitud intra-cluster vs inter-cluster (menor valor indica mejor partición).
- **Silhouette Score:** Cohesión y separación sobre una muestra representativa estratificada ($N = 10.000$, con semilla 42 para comparabilidad idéntica).

### 3.1 Tabla Comparativa de Modelos ($k=2$ a $6$)

| $k$ | Inercia (WCSS) | Silhouette Score | Davies-Bouldin Index | Decisión Metodológica |
|:---:|:---:|:---:|:---:|:---|
| **2** | 190.705,98 | 0,7118 | 0,4713 | Separa únicamente clientes con 1 pedido vs clientes recurrentes; no diferencia hábitos de gasto. |
| **3** | 129.575,59 | 0,4125 | 0,8393 | Agrupa clientes sin granularidad en ticket mediano. |
| **4** | **83.288,79** | **0,3912** | **0,7591** | **ÓPTIMO:** Davies-Bouldin mínimo entre $k \ge 3$, fuerte caída de inercia y 4 cuadrantes de negocio claros. |
| **5** | 69.096,90 | 0,3510 | 0,8230 | Fragmenta el segmento de bajo ticket sin aportar nueva acción comercial. |
| **6** | 58.869,67 | 0,3503 | 0,7910 | Sobresegmentación con degradación del Silhouette. |

> Se selecciona **$k = 4$** como la partición analítica y comercialmente óptima.

### 3.2 Perfiles Reales de los 4 Segmentos Obtenidos

| Cluster | Segmento Asignado | Clientes | % Base | Recencia Mediana | Frecuencia Mediana | Monto Mediano | Acción Comercial Propuesta |
|:---:|:---|---:|---:|---:|---:|---:|:---|
| **0** | **Nuevos / Prometedores Recientes** | 16.276 | 17,43 % | 38,1 días | 1,0x | R$ 83,94 | Incentivo rápido de 2da compra: cupón de descuento con vigencia de 30 días en categorías afines. |
| **1** | **Compradores Ocasionales de Bajo Ticket** | 36.605 | 39,21 % | 268,7 días | 1,0x | R$ 44,99 | Campañas automatizadas por email de bajo coste; no subsidiar gastos de flete. |
| **2** | **Clientes Leales / Recurrentes** | 2.801 | 3,00 % | 199,8 días | 2,0x | R$ 182,10 | Programa de lealtad VIP, soporte prioritario, ofertas cruzadas personalizadas y acceso anticipado. |
| **3** | **Ticket Alto Inactivo / Gran Desembolso** | 37.676 | 40,36 % | 261,6 días | 1,0x | R$ 150,00 | Campañas de reactivación personalizada orientadas a productos de alta gama en temporadas pico. |

---

## 4. Análisis de Grafos y Redes Bipartitas Vendedor–Producto

Para abordar **PN-09**, se construyó una red real bipartita no dirigida $G = (V_{sellers} \cup V_{products}, E)$ a partir de `items_procesados.csv` sobre los 110.197 ítems correspondientes a pedidos entregados.

### 4.1 Métricas Topológicas de la Red

| Métrica de Red | Valor Obtenido | Interpretación de Negocio |
|:---|---:|:---|
| **Nodos Totales** | 35.186 | Universo completo de actores comerciales en pedidos entregados. |
| **Vendedores Distintos ($V_{sellers}$)** | 2.970 | Comerciantes activos en la plataforma. |
| **Productos Distintos ($V_{products}$)** | 32.216 | Catálogo de artículos efectivamente vendidos. |
| **Aristas Únicas ($E$)** | 33.659 | Relaciones de venta vendedor ↔ producto. |
| **Grafo Bipartito** | Sí (`True`) | Las conexiones ocurren estrictamente entre vendedores y productos. |
| **Componentes Conexas** | 2.320 | Coexistencia de submercados aislados y nichos independientes. |
| **Componente Gigante** | 9.358 nodos (26,6 %) | El núcleo denso del marketplace donde interactúan los principales vendedores y productos. |
| **Densidad de la Red** | 0,000054 | Red dispersa típica de marketplaces con catálogos masivos (long-tail). |

### 4.2 Nodos Clave por PageRank Ponderado

El algoritmo **PageRank** ponderado por la cantidad de unidades vendidas (`weight=peso_items`) identifica los comerciantes y productos de mayor impacto estructural:

1. **Vendedor `4a3ca9315b744ce9f8e9374361493884` (SP):**  
   - PageRank: `0,005080` (Líder absoluto de la red).  
   - Grado ponderado: 1.984 unidades vendidas en 398 productos distintos.  
   - Rol: Gran distribuidor multisurtido del estado de São Paulo.
2. **Vendedor `cca3071e3e9bb7d12640c9fbe2301306` (SP):**  
   - PageRank: `0,004091`.  
   - Grado ponderado: 830 unidades vendidas.  
   - Rol: Polo textil y de artículos de cama, mesa y baño.
3. **Vendedor `d91fb3b7d041e83b64a00a3edfb37e4f` (SP):**  
   - PageRank: `0,003968`.  
   - Grado ponderado: 1.188 unidades vendidas.

### 4.3 Subgrafo Legible y Visualización
Dado que una red de 35.186 nodos resulta incomprensible visualmente ("hairball"), `src/grafos.py` extrae un **subgrafo legible** conformado por los **12 principales vendedores según PageRank y sus 4 productos estrella de mayor volumen** (60 nodos y 48 enlaces).  
Este subgrafo permite observar con claridad:
- Comerciantes de alto volumen que concentran ventas masivas en pocos artículos bandera.
- Comerciantes diversificados que dispersan sus ventas en catálogos extensos.
- La exportación en `resultados/grafo_subgrafo.json` permite su renderizado reactivo e interactivo en la interfaz web de DataSmart.

---

## 5. Trazabilidad y Archivos Entregados

Todos los resultados son 100 % reproducibles ejecutando los scripts desde la raíz del repositorio:

```bash
# 1. Ejecución de Clustering
python src/clustering.py

# 2. Ejecución de Grafos
python src/grafos.py

# 3. Verificación de Pruebas Unitarias
python -m unittest tests/test_clustering.py tests/test_grafos.py
```

### Inventario de Resultados Generados en `resultados/`

- `resultados/clientes_clusters.csv`: 93.358 compradores clasificados con $R, F, M$ y cluster asignado.
- `resultados/perfiles_clusters.csv`: Tabla consolidada de métricas, descripciones y acciones comerciales por segmento.
- `resultados/evaluacion_clustering.csv`: Comparativa de Inercia, Silhouette y Davies-Bouldin para $k=2..6$.
- `resultados/clustering_metadata.json`: Metadatos de ejecución, parámetros y semillas.
- `resultados/grafo_aristas.csv`: 33.659 aristas vendedor-producto con peso en ítems y valor monetario.
- `resultados/grafo_metricas.csv`: 35.186 nodos con grado, grado ponderado, PageRank y componente conexa.
- `resultados/grafo_metadata.json`: Estadísticas topológicas globales de la red.
- `resultados/grafo_subgrafo.json`: Estructura JSON para consumo en la interfaz web.
- `resultados/graficos/04_clustering_codo_silhouette.png`: Gráfico oficial del codo y Silhouette.
- `resultados/graficos/05_clustering_distribucion_segmentos.png`: Distribución de clientes y ticket mediano.
- `resultados/graficos/06_grafo_red_vendedor_producto.png`: Visualización topológica del subgrafo legible.
