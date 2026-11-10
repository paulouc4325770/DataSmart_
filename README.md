# DataSmart — Análisis de datos y plataforma web de Olist

Proyecto de minería de datos basado en **Brazilian E-Commerce Public Dataset by
Olist**, organizado con CRISP-DM. Incluye análisis exploratorio (EDA), preparación
y calidad, reglas de asociación, clustering RFM, grafos, series temporales,
regresión, evaluación comparativa e interfaz web.

## Guía de ejecución

1. [Requisitos](#1-requisitos).
2. [Descargar el dataset](#2-descargar-el-dataset).
3. [Preparar el entorno](#3-preparar-el-entorno).
4. [Ejecutar todos los análisis](#4-ejecutar-todos-los-análisis).
5. [Iniciar el frontend](#5-iniciar-el-frontend).
6. [Ejecutar las pruebas](#6-ejecutar-las-pruebas).
7. [Consultar opciones y cambiar rutas](#7-consultar-opciones-y-cambiar-rutas).
8. [Resolver problemas frecuentes](#8-resolver-problemas-frecuentes).

**Directorio de trabajo:** abre la terminal en la raíz del proyecto, donde están
este `README.md`, `requirements.txt`, `src/` y `frontend/`. Los comandos siguientes
se ejecutan desde esa carpeta.

## 1. Requisitos

- **Python 3.11 o posterior recomendado**, con `pip` y soporte para entornos
  virtuales (`venv`). El entorno local también se ha ejecutado con Python 3.13.
- El ZIP original de Olist para regenerar los datos y análisis.
- Un navegador actualizado para la plataforma web.
- **Node.js 20 o posterior y npm**, si vas a utilizar Vite, compilar el frontend
  o ejecutar las pruebas JavaScript. El servidor web de Python utiliza únicamente
  la biblioteca estándar y puede iniciarse sin Node.js.

Las dependencias analíticas se instalan desde `requirements.txt`: Pandas,
Matplotlib, scikit-learn, NetworkX y statsmodels, junto con sus dependencias.

### Estructura principal

```text
DataSmart_/
├── data/
│   ├── raw/archive.zip       # Dataset original descargado de Kaggle
│   └── processed/            # Tablas generadas por preparar_datos.py
├── docs/                     # Informes, metodología y presentaciones
├── frontend/                 # Interfaz web, servidor Python y configuración Vite
├── resultados/               # CSV, JSON, resúmenes y gráficos generados
├── src/                      # Scripts de preparación, análisis y modelos
├── tests/                    # Pruebas Python
├── requirements.txt
└── README.md
```

El dataset, las tablas procesadas y el entorno `.venv/` están excluidos de Git.
Cada persona que clone o descargue el proyecto debe preparar su entorno y
regenerar los datos procesados.

## 2. Descargar el dataset

1. Descargar **Brazilian E-Commerce Public Dataset by Olist** desde
   [Kaggle](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce).
2. Crear `data/raw/` si todavía no existe.
3. Colocar el ZIP descargado en **`data/raw/archive.zip`**. Renombrarlo si la
   descarga tiene otro nombre; los scripts lo leen directamente, sin descomprimir.

El ZIP debe contener estos nueve CSV en su raíz:

```text
olist_customers_dataset.csv
olist_geolocation_dataset.csv
olist_order_items_dataset.csv
olist_order_payments_dataset.csv
olist_order_reviews_dataset.csv
olist_orders_dataset.csv
olist_products_dataset.csv
olist_sellers_dataset.csv
product_category_name_translation.csv
```

## 3. Preparar el entorno

### Linux / Debian / Ubuntu

Desde la raíz del proyecto:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si Debian o Ubuntu informa que `venv` no está disponible, instalar el soporte y
volver a crear el entorno:

```bash
sudo apt install python3-venv
```

### Windows / PowerShell

Desde la raíz del proyecto:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Si `py` no está disponible, utilizar `python -m venv .venv`.

### Volver a trabajar otro día

En cada terminal nueva, activar el entorno existente antes de ejecutar los
análisis. La creación de `.venv` y la instalación se hacen inicialmente; volver
a instalar las dependencias si cambia `requirements.txt`.

| Sistema | Activación | Intérprete directo, sin activar |
|---|---|---|
| Linux | `source .venv/bin/activate` | `.venv/bin/python` |
| Windows / PowerShell | `.\.venv\Scripts\Activate.ps1` | `.\.venv\Scripts\python.exe` |

Con el entorno activado, **`python`** en los comandos de esta guía utiliza el
intérprete del proyecto. Comprobarlo con `python --version` y
`python -m pip --version`. Para salir del entorno, ejecutar `deactivate`.

Antes de iniciar todos los análisis, comprobar que las dependencias están
instaladas en ese intérprete:

```bash
python -c "import pandas, matplotlib, sklearn, networkx, statsmodels; print('Dependencias listas')"
```

## 4. Ejecutar todos los análisis

Con el entorno activado y `data/raw/archive.zip` disponible, ejecutar en este
orden. Esperar a que termine cada paso; si uno falla, resolverlo antes de continuar.

```bash
# 1. EDA, indicadores y gráficos del dashboard desde el ZIP original.
python src/eda_olist.py

# 2. Preparación, validaciones, diccionarios y tablas procesadas.
python src/preparar_datos.py

# 3. Asociación principal: todas las cestas elegibles, incluidas las unitarias.
python src/asociacion.py

# 4. Asociación complementaria: solo cestas con dos o más categorías.
python src/asociacion.py --poblacion multicategoria

# 5. Segmentación RFM y comparación de K-Means k=2..6.
python src/clustering.py

# 6. Red bipartita vendedor-producto y métricas de grafos.
python src/grafos.py

# 7. Pronóstico de ventas semanales y evaluación cronológica.
python src/series_temporales.py

# 8. Regresión de días de entrega: baseline, Ridge y Random Forest.
python src/regresion.py

# 9. Consolidación de las métricas de los análisis anteriores.
python src/consolidar_evaluacion.py
```

**Dependencias entre pasos:** EDA y preparación leen el ZIP original. Asociación,
clustering, grafos, series y regresión consumen las tablas de la preparación.
La consolidación debe ejecutarse al final para incluir los resultados disponibles
de todas las familias; omite los archivos de entrada que no encuentre.

Los comandos vuelven a generar sus salidas en `resultados/` y, en el caso de la
preparación, en `data/processed/` y `docs/preparacion_y_calidad.md`. Clustering y
grafos también actualizan sus bloques calculados en `docs/clustering_y_grafos.md`
si el informe existe. `src/esquema_olist.py` define el contrato de datos que importa
la preparación; no es un paso adicional de ejecución.

### Archivos principales que genera cada paso

| Módulo | Salidas principales |
|---|---|
| EDA | `resultados/resumen_tablas.csv`, `diccionario_perfilado.csv`, `indicadores_kpi.csv`, `ventas_mensuales.csv` y tres PNG en `resultados/graficos/`. |
| Preparación | `data/processed/pedidos_procesados.csv`, `items_procesados.csv`, `geolocalizacion_agrupada.csv`; auditoría en `resultados/calidad/`; diccionarios en `resultados/`. |
| Asociación | `resultados/reglas_asociacion.csv`, `reglas_asociacion_trazabilidad.csv`, `comparacion_asociacion.csv`, `umbrales_asociacion.csv`, `composicion_cestas.csv` y `asociacion_metadata.json`. La variante complementaria utiliza el sufijo `_multicategoria` en las salidas de su población. |
| Clustering | `resultados/clientes_clusters.csv`, `perfiles_clusters.csv`, `evaluacion_clustering.csv`, `rfm_distribuciones.csv`, `clustering_metadata.json`, `clustering_resumen.md` y gráficos. |
| Grafos | `resultados/grafo_aristas.csv`, `grafo_metricas.csv`, `grafo_componentes.csv`, `grafos_metadata.json`, `grafos_resumen.md` y gráficos. |
| Series temporales | `resultados/pronosticos_ventas.csv`, `evaluacion_series.csv`, `series_temporales_metadata.json` y `resultados/graficos/series_temporales_prediccion.png`. |
| Regresión | `resultados/predicciones_entrega.csv`, `evaluacion_regresion.csv`, `regresion_metadata.json` y dos gráficos en `resultados/graficos/`. |
| Consolidación | `resultados/evaluacion_comparativa.csv` y `evaluacion_comparativa_resumen.json`. |

En las tablas procesadas, cada fila representa un pedido, un ítem o un prefijo
postal, respectivamente. La preparación publica el diccionario de los **52 campos
originales**, el de tablas procesadas y el de variables derivadas. Si una
validación falla, consultar `resultados/calidad/validaciones.csv` e
`incidencias.csv` antes de consumir las tablas.

## 5. Iniciar el frontend

### Servidor Python — recomendado para ejecutar la plataforma completa

Desde la raíz del proyecto, con el entorno activado:

```bash
python frontend/server.py
```

Abrir **[http://localhost:8080](http://localhost:8080)**. También funciona
[http://127.0.0.1:8080](http://127.0.0.1:8080).

El comando mantiene el servidor en ejecución: dejar esa terminal abierta y usar
otra para nuevos comandos. Para detenerlo, pulsar **Ctrl+C** en su terminal.
Para reiniciarlo después de modificar `frontend/server.py`, detenerlo y ejecutar
de nuevo el mismo comando.

| Dirección | Contenido |
|---|---|
| `http://localhost:8080/` | Plataforma web: dashboard, calidad, diccionario, modelos y hoja de ruta. |
| `http://localhost:8080/api/resultados` | Indicadores, resúmenes y diccionario generados por Python. |
| `http://localhost:8080/api/asociacion` | Reglas reales, comparación, poblaciones y pedidos de trazabilidad. |
| `http://localhost:8080/resultados/graficos/01_pedidos_por_estado.png` | Ejemplo de gráfico generado servido por la web. |

La interfaz utiliza un **único tema claro**, con petróleo, rosa, terracota,
lavanda y salvia. El servidor envía `Cache-Control: no-store` para sus recursos.
Los cambios de CSS, JavaScript e imágenes se consultan recargando la página;
los cambios del servidor Python requieren reiniciarlo.

### Qué resultados carga actualmente la web

- La pestaña **Asociación** carga los resultados reales desde la API y permite
  consultar la población, las métricas y los pedidos que sustentan cada regla.
- Los KPI compatibles se actualizan desde `/api/resultados`; las otras vistas
  conservan parte de sus datos de presentación en `frontend/src/data/olistData.js`.
- La galería del dashboard muestra los tres PNG generados por `src/eda_olist.py`.
- Los laboratorios de RFM, pronóstico, SHAP, NLP y el grafo interactivo siguen
  mostrando datos de demostración. Ejecutar los scripts genera los resultados
  reales en disco; esos laboratorios todavía requieren su integración con ellos.

### Vite — desarrollo de la interfaz con Node.js

Con Node.js y npm instalados, estos comandos también se ejecutan desde la raíz:

```bash
npm --prefix frontend install
npm --prefix frontend run dev
```

Abrir **[http://localhost:5173](http://localhost:5173)**. Vite ofrece recarga de
la interfaz durante el desarrollo. La API Python está disponible con
`frontend/server.py`; con Vite, Asociación intenta cargar los CSV directamente y
los indicadores usan los valores locales de respaldo.

Para compilar y revisar el paquete del frontend:

```bash
npm --prefix frontend run build
npm --prefix frontend run preview
```

La compilación se guarda en `frontend/dist/` y la vista previa utiliza
**[http://localhost:4173](http://localhost:4173)**. La vista previa es estática y
no incorpora la API de Python. Detener Vite o la vista previa con **Ctrl+C**.

## 6. Ejecutar las pruebas

Desde la raíz, con las dependencias Python instaladas y el entorno activado:

```bash
python -m unittest discover -s tests -v
```

La suite incluye preparación, asociación, API HTTP, clustering, grafos, series,
regresión y consolidación. Las pruebas de datos y modelos utilizan entradas
pequeñas; la prueba de consolidación consulta los archivos disponibles en
`resultados/`. No es necesario descargar el ZIP original ni iniciar manualmente
el servidor para ejecutar la suite.

Con Node.js instalado, ejecutar las pruebas de la interfaz:

```bash
node --test frontend/tests/asociacion.test.mjs
```

La comprobación del empaquetado es `npm --prefix frontend run build`, después de
instalar las dependencias del frontend con npm.

## 7. Consultar opciones y cambiar rutas

Los módulos con argumentos de línea de comandos son preparación, asociación,
clustering y grafos:

```bash
python src/preparar_datos.py --help
python src/asociacion.py --help
python src/clustering.py --help
python src/grafos.py --help
```

Ejemplos, reemplazando las rutas por las de tu equipo:

```bash
# Preparar datos desde otro ZIP y escribir en una raíz independiente.
python src/preparar_datos.py --zip "/ruta/archive.zip" --output-root "/ruta/salida"

# Consumir las tablas de esa preparación para generar asociaciones.
python src/asociacion.py --items "/ruta/salida/data/processed/items_procesados.csv" --pedidos "/ruta/salida/data/processed/pedidos_procesados.csv" --output-root "/ruta/salida"

# Controlar el tamaño de la evaluación de clustering o del dibujo del grafo.
python src/clustering.py --muestra-silhouette 1000
python src/grafos.py --top-vendedores 3 --productos-por-vendedor 8
```

Usar `--output-root` en un módulo no cambia automáticamente las entradas de los
demás: indicar también `--items` o `--pedidos` cuando corresponda. EDA, series,
regresión, consolidación y el servidor web utilizan las rutas del repositorio.
El flujo completo de la sección 4 usa esas rutas por defecto.

## 8. Resolver problemas frecuentes

| Problema | Solución |
|---|---|
| `python: command not found` en Linux | Crear el entorno con `python3 -m venv .venv` y activarlo con `source .venv/bin/activate`. También se puede llamar directamente a `.venv/bin/python`. |
| `ModuleNotFoundError` al ejecutar un análisis | Activar `.venv` y ejecutar `python -m pip install -r requirements.txt` en esa misma terminal. |
| PowerShell bloquea `Activate.ps1` | Utilizar directamente `.\.venv\Scripts\python.exe` en lugar de `python`, tanto para instalar dependencias como para ejecutar scripts. |
| No se encuentra `archive.zip` | Revisar el nombre y la ubicación `data/raw/archive.zip`, y que los nueve CSV estén en la raíz del ZIP. |
| Faltan `pedidos_procesados.csv` o `items_procesados.csv` | Ejecutar primero `python src/preparar_datos.py`. |
| Asociación muestra «sin resultados» | Ejecutar `python src/asociacion.py`; para habilitar la otra población, ejecutar también `python src/asociacion.py --poblacion multicategoria`. Recargar la web. |
| `OSError: [Errno 98] Address already in use` | Ya hay un proceso en el puerto 8080. Si es el servidor del proyecto, abrir su URL o detenerlo con Ctrl+C en la terminal que lo inició antes de volver a arrancarlo. En Linux, identificarlo con `ss -ltnp 'sport = :8080'`. |
| Se sigue viendo una versión anterior de la interfaz | Confirmar que la URL es `http://localhost:8080`, reiniciar el servidor si se modificó `server.py` y recargar con Ctrl+Shift+R. Para descartar una copia previa del HTML, abrir `http://localhost:8080/?v=petrol-pastel-1`. |
| Se abre el HTML pero fallan datos o módulos | Acceder mediante el servidor HTTP; abrir `frontend/index.html` como archivo local no proporciona la API ni el servicio de archivos del proyecto. |

## Notas metodológicas

- Olist es un dataset histórico; sus resultados no representan ventas actuales.
- Las ventas reportadas suman artículos de pedidos entregados y excluyen flete.
- La preparación conserva todos los estados de pedido; cada análisis define su
  población. Distingue faltantes de cero y mide la puntualidad por **día calendario**.
- Los tipos de `diccionario_perfilado.csv` son inferidos por Pandas; los contratos
  de salida están en `diccionario_procesados.csv` y `diccionario_variables_derivadas.csv`.
- RFM agrupa por `customer_unique_id`, utiliza una referencia temporal
  reproducible y compara K-Means k=2–6. Silhouette usa una muestra fija de hasta
  1.800 compradores por defecto, con un máximo configurable de 2.000.
- El grafo es bipartito vendedor–producto; el peso de cada relación es su número
  de ítems. Las métricas se calculan sobre toda la red y el dibujo es un subgrafo.
- Series y regresión usan particiones cronológicas. Las métricas se interpretan
  dentro de cada familia: MAE en BRL, MAE en días y Silhouette tienen unidades
  diferentes.

## Documentación y responsables

| Bloque | Responsable | Documentación |
|---|---|---|
| Preparación y calidad | Jerson | [Guía de preparación](docs/guia_preparacion.md), [informe generado](docs/preparacion_y_calidad.md), [presentación](docs/presentacion_jerson.md). |
| Negocio y asociación | Paulo | [Negocio, resultados y reproducción](docs/negocio_y_asociacion.md). |
| Clustering y grafos | Anderson | [Informe y contrato de resultados](docs/clustering_y_grafos.md), [presentación](docs/presentacion_anderson.md), [handoff](docs/handoff_brandon.md). |
| Series, regresión y evaluación | Brandon | [Informe predictivo](docs/series_y_regresion.md), [presentación](docs/presentacion_predictiva.md). |
| Interfaz web | Documentación técnica | [README del frontend](frontend/README.md). |
