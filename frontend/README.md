# DataSmart Frontend — Plataforma Inteligente de Minería de Datos

Interfaz web analítica interactiva del proyecto **DataSmart** (Curso: Minería de Datos — UNMSM FISI), diseñada para integrar el Análisis Exploratorio de Datos (EDA), la Auditoría de Calidad, el Diccionario de Datos (52 columnas), las 10 Preguntas de Negocio (`PN-01` a `PN-10`) y los Simuladores de Modelos Predictivos y Explicabilidad (`SHAP / LIME`) sobre el dataset **Brazilian E-Commerce Public Dataset by Olist**.

---

## Arquitectura del Frontend (`frontend/`)

```text
frontend/
├── index.html                        # Shell principal SPA con tipografía Inter & JetBrains Mono
├── package.json                      # Configuración de paquetes y scripts Vite
├── vite.config.js                    # Configuración de servidor Vite con acceso a ../resultados
├── server.py                         # Servidor Python zero-dependency + /api/resultados y /api/asociacion
└── src/
    ├── main.js                       # Controlador reactivo SPA, estado global y eventos
    ├── styles/
    │   └── main.css                  # Design System Enterprise Analytics (Modo Oscuro / Claro)
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
        ├── businessModelsView.js     # Módulo 4: Workbench PN-01..10 (RFM, Apriori, Series, SHAP, NLP, Grafos)
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
npm install
npm run dev
```
La aplicación se abrirá automáticamente en `http://localhost:5173`.


---

## Reglas de asociación reales (PN-05)

La pestaña **Asociación** no usa datos de ejemplo: lee los archivos que genera `src/asociacion.py`.

```powershell
py src/asociacion.py                              # análisis principal
py src/asociacion.py --poblacion multicategoria   # análisis complementario
py frontend/server.py
```

- `GET /api/asociacion` devuelve las reglas, la comparación Apriori / FP-Growth, la composición de las cestas
  y los `order_id` que sustentan cada regla. Si faltan los archivos, la web muestra qué comando ejecutar.
- Con Vite (`npm run dev`) no hay API: la web lee directamente los CSV de `resultados/`.
- Cada regla muestra su población de referencia (N) y se verifica que los pedidos rastreados coincidan con `n_pedidos`.
- Los demás laboratorios (RFM, series, SHAP, NLP, grafos) siguen mostrando datos de ejemplo, marcados así en la
  columna *Estado*, hasta que se integren los resultados de cada integrante.

Pruebas: `node --test frontend/tests/asociacion.test.mjs` (interfaz) y `py -m unittest discover -s tests -v` (API y análisis).
