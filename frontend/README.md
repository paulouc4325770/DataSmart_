# DataSmart Frontend — Plataforma Inteligente de Minería de Datos

Interfaz web analítica interactiva del proyecto **DataSmart** (Curso: Minería de Datos — UNMSM FISI), que consulta artefactos reales de EDA, preparación, asociación, segmentación, series, regresión, clasificación, NLP, explicabilidad lineal y monitoreo retrospectivo sobre **Brazilian E-Commerce Public Dataset by Olist**.

---

## Arquitectura del Frontend (`frontend/`)

```text
frontend/
├── index.html                        # Shell principal SPA con tipografía Inter & JetBrains Mono
├── package.json                      # Configuración de paquetes y scripts Vite
├── vite.config.js                    # Configuración de servidor Vite con acceso a ../resultados
├── server.py                         # Servidor Python + contratos JSON de resultados locales
└── src/
    ├── main.js                       # Controlador reactivo SPA, estado global y eventos
    ├── styles/
    │   └── main.css                  # Design System Enterprise Analytics (tema claro)
    ├── data/
    │   └── olistData.js              # Store sincronizado con resultados/*.csv e Informe Semana 7
    ├── services/
    │   └── dataService.js            # Conector híbrido API en vivo (/api/resultados) + Store local
    ├── utils/
    │   └── formatters.js             # Formateadores BRL (R$), enteros, porcentajes y exportador CSV
    ├── components/
    │   └── svgCharts.js              # Motor de gráficos vectoriales SVG (Series Temporales y Grafos NetworkX)
    └── views/
        ├── executiveDashboardView.js # Módulo 1: Dashboard Ejecutivo, 8 KPIs y EDA Interactivo
        ├── dataQualityView.js        # Módulo 2: Calidad de Datos y Plan de Tratamiento (7 reglas)
        ├── dataDictionaryView.js     # Módulo 3: Diccionario de 52 columnas y Esquema Relacional
        ├── associationView.js        # PN-05: reglas de asociación reales (resultados/reglas_asociacion*.csv)
        ├── businessModelsView.js     # Workbench con resultados Python y estados explícitos
        └── crispDmRoadmapView.js     # Módulo 5: Metodología CRISP-DM y Entregas (Semanas 7, 10, 13, 16)
```

---

## Cómo Ejecutar el Frontend

### Opción 1: Ejecución Inmediata con Python (Recomendado — Sin instalar dependencias adicionales)
Desde la raíz del repositorio `DataSmart_`:

```powershell
py frontend/server.py
```
Luego abre en tu navegador:
- **Aplicación Web**: [http://localhost:8080](http://localhost:8080)
- **API JSON de Resultados Reales (`resultados/*.csv`)**: [http://localhost:8080/api/resultados](http://localhost:8080/api/resultados)

### Opción 2: Ejecución con Node.js y Vite
Si cuentas con Node.js instalado:

```powershell
cd frontend
npm ci
npm run dev
```
La aplicación se abrirá automáticamente en `http://localhost:5173`.


---

## Tema claro y paleta de colores

La aplicación utiliza un único tema claro, incluso si el sistema operativo
prefiere modo oscuro. Los seis colores principales están definidos en
`src/styles/main.css`:

- Petróleo `#35627A`: navegación y acciones principales.
- Rosa `#E5AEA9`: fondos destacados y detalles cálidos.
- Terracota `#B46258`: incidencias y puntos destacados en gráficos.
- Lavanda `#A6A9D0`: pestañas activas, categorías y pronósticos.
- Blanco suave `#F5F5F5`: fondo general.
- Salvia `#8E9A98`: bordes, superficies suaves y nodos secundarios.

Se complementan con blanco para las tarjetas y variantes oscuras para asegurar
el contraste del texto. Los SVG y las barras utilizan variables `--chart-*`;
los nombres de acentos de las vistas existentes se resuelven a esta paleta.

- Los pronósticos usan líneas discontinuas y marcadores cuadrados; el grafo
  diferencia regiones, polos vendedores y categorías con formas y contornos.
- Los tres PNG del dashboard se generan con la misma paleta en
  `src/eda_olist.py`. Para actualizarlos, ejecutar `python src/eda_olist.py`
  desde la raíz con el dataset original disponible.
- El servidor Python envía `Cache-Control: no-store` para HTML, CSS, JavaScript,
  imágenes y API. Las entradas CSS y JavaScript también tienen una revisión en
  su URL para invalidar las copias de la interfaz anterior. Tras cambiar el
  código de `server.py`, reiniciar el servidor para cargarlo.

---

## Reglas de asociación reales (PN-05)

La pestaña **Asociación** no usa datos de ejemplo: lee los archivos que genera `src/asociacion.py`.

```powershell
py src/asociacion.py                              # análisis principal
py src/asociacion.py --poblacion multicategoria   # análisis complementario
py frontend/server.py
```

- `GET /api/asociacion` devuelve las reglas, la comparación Apriori / FP-Growth / ECLAT, la composición de las cestas
  y los `order_id` que sustentan cada regla. Si faltan los archivos, la web muestra qué comando ejecutar.
- Con Vite (`npm run dev`) no hay API: la web lee directamente los CSV de `resultados/`.
- Cada regla muestra su población de referencia (N) y se verifica que los pedidos rastreados coincidan con `n_pedidos`.
- Las vistas de RFM, evaluación temporal, regresión, grafos, clasificación, NLP,
  explicabilidad y monitoreo leen resultados generados por Python.

## Contratos de resultados y límites metodológicos

El servidor publica `/api/clustering`, `/api/series`, `/api/grafos`, `/api/regresion`,
`/api/clasificacion`, `/api/nlp`, `/api/explicabilidad`, `/api/monitoring` y
`/api/modelos`. Los CSV se devuelven con muestra limitada y total de filas.

El contrato de grafos valida `run_id`, SHA-256 de entrada, timestamp y conteos
entre `grafo_subgrafo.json` y `grafos_metadata.json`; un subgrafo heredado se
omite y el módulo se marca parcial.

- DBSCAN se evalúa en una muestra fija y no propaga etiquetas al resto de clientes.
- Clasificación usa comentarios y etiquetas proxy derivadas de `review_score`, con
  split cronológico; no es una predicción de satisfacción en checkout.
- NLP informa separadamente sentimiento léxico desde texto y sentimiento de referencia
  derivado de score. La identificación del portugués es heurística.
- Explicabilidad tiene una pestaña separada, con coeficientes por clase y ejemplos
  locales del clasificador. Son contribuciones al logit, no valores SHAP.
- Monitoreo y PSI comparan particiones históricas. No hay monitoreo productivo en tiempo real.
- Calidad y diccionario usan perfilado desde la API; el respaldo local se identifica
  en pantalla cuando no hay artefactos de preparación disponibles.

## Ejecución y pruebas

Desde la raíz, con el entorno Python activado, los módulos nuevos se ejecutan después
de tener `data/raw/archive.zip` y de entrenar la clasificación:

```powershell
python src/clasificacion_resenas.py
python src/nlp_resenas.py
python src/explicabilidad_resenas.py
python src/monitoreo_modelos.py
python src/consolidar_evaluacion.py
```

Pruebas desde la raíz: `node --test frontend/tests/asociacion.test.mjs`,
`python -m unittest discover -s tests -v` y, desde `frontend/`, `npm run build`.

El paquete usa `vite@6.4.6` con `package-lock.json`; instala de forma reproducible
con `npm ci`. La versión fue probada con Node 22.20.0 y el build del proyecto.
