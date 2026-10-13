/**
 * Módulo 5: Metodología CRISP-DM, Arquitectura Modular y Cronograma de Entregas (Semanas 7, 10, 13, 16)
 * Cubre las Secciones 11, 12 y 13 del Informe de Avance.
 */

export function renderCrispDmRoadmapView(store) {
  const { roadmap, meta } = store;

  return `
    <!-- Resumen de Metodología CRISP-DM (Sección 11) -->
    <section class="context-banner">
      <div class="context-banner-info">
        <h2>
          🔄 Metodología ${meta.methodology}
          <span class="chip chip-blue">Ciclo Iterativo</span>
        </h2>
        <p>
          CRISP-DM se aplica de forma iterativa: si durante el modelado emergen sesgos, pérdidas de información o
          métricas insuficientes, el flujo retorna a <strong>Preparación y Comprensión de los Datos</strong>.
        </p>
      </div>
    </section>

    <!-- Hoja de Ruta por Entrega (Semanas 7, 10, 13 y 16 — Sección 12.4 y 13.3) -->
    <section class="grid-2">
      ${roadmap
        .map(
          stage => `
        <article class="card">
          <div class="card-header">
            <div class="card-title-group">
              <h3>
                <span class="chip chip-blue mono">${stage.week}</span>
                ${stage.phase}
              </h3>
              <p class="mono" style="margin-top:0.3rem; color:var(--accent-cyan);">
                Stack: ${stage.techStack}
              </p>
            </div>
            <span class="chip ${stage.progress === 100 ? 'chip-emerald' : 'chip-purple'}">
              ${stage.status} (${stage.progress}%)
            </span>
          </div>

          <div class="progress-bar-track">
            <div class="progress-bar-fill" style="width:${stage.progress}%;"></div>
          </div>

          <ul style="padding-left:1.15rem; display:flex; flex-direction:column; gap:0.45rem; font-size:0.82rem; color:var(--text-secondary);">
            ${stage.deliverables.map(d => `<li>${d}</li>`).join('')}
          </ul>
        </article>
      `
        )
        .join('')}
    </section>

    <!-- Sección 12.3: Estructura Modular del Repositorio DataSmart_ -->
    <section class="grid-2">
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>📂 Estructura Modular del Repositorio (Sección 12.3)</h3>
            <p>Arquitectura distribuida en Git / GitHub (<code>DataSmart_</code>)</p>
          </div>
          <span class="chip chip-emerald">Git & GitHub Trazable</span>
        </div>

        <pre class="mono" style="background:var(--bg-secondary); padding:1.1rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle); font-size:0.77rem; color:var(--text-primary); overflow-x:auto; line-height:1.65;">
DataSmart_/
├── src/
│   └── eda_olist.py              # Procesamiento de los 9 CSV, KPIs y gráficos Matplotlib
├── resultados/
│   ├── indicadores_kpi.csv       # Métricas clave (99.441 pedidos, R$ 13,22M ventas)
│   ├── resumen_tablas.csv        # Filas, columnas, nulos y duplicados por tabla
│   ├── diccionario_perfilado.csv # 53 columnas perfiladas con tipos y cardinalidad
│   ├── ventas_mensuales.csv      # Serie temporal mensual de artículos entregados
│   └── graficos/                 # 3 visualizaciones PNG en español (170 DPI)
├── frontend/                     # Aplicación Web Analítica (Arquitectura Modular ES/Vite)
│   ├── index.html                # Punto de entrada SPA con diseño Dark/Light
│   ├── package.json              # Scripts de desarrollo y construcción Vite
│   ├── server.py                 # Servidor local + API JSON conectada a resultados/
│   └── src/
│       ├── main.js               # Controlador reactivo, router y eventos
│       ├── data/olistData.js     # Store oficial sincronizado con Semana 7
│       ├── services/             # Conector API / CSV
│       ├── components/           # Motor de gráficos vectoriales SVG
│       └── views/                # 5 vistas modulares (Dashboard, Calidad, Diccionario, Modelos, CRISP-DM)
├── data/raw/                     # Zona local para archive.zip (excluida en .gitignore)
├── requirements.txt              # Dependencias Python (pandas, matplotlib)
└── README.md                     # Documentación de ejecución y notas metodológicas</pre>
      </article>

      <!-- Sección 13.2: Limitaciones del Análisis y Buenas Prácticas -->
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>⚠️ Limitaciones Metodológicas Declaradas (Sección 13.2)</h3>
            <p>Transparencia analítica y gobierno de datos sobre el dataset Olist</p>
          </div>
        </div>

        <div style="display:flex; flex-direction:column; gap:0.7rem; font-size:0.81rem; color:var(--text-secondary);">
          <div style="padding:0.75rem 0.9rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-primary);">
            <strong>1. Cobertura en Meses Extremos (2016 y fin de 2018):</strong>
            Los meses iniciales de 2016 y los registros posteriores a agosto de 2018 presentan truncamiento de captura y deben filtrarse antes del entrenamiento de series temporales.
          </div>

          <div style="padding:0.75rem 0.9rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-amber);">
            <strong>2. Ausencia de Variables Demográficas y de Churn Explícito:</strong>
            Olist es un dataset transaccional anonimizado; no incluye edad, género, costos de adquisición (CAC), navegación web ni etiqueta contractual de abandono.
          </div>

          <div style="padding:0.75rem 0.9rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-emerald);">
            <strong>3. Ingresos Brutos de Artículos vs Margen Neto:</strong>
            El indicador de R$ 13.221.498,11 mide el valor de los productos (<code>price</code>) sin flete (<code>freight_value</code>) ni costos operativos del vendedor, por lo que no equivale a utilidad neta.
          </div>

          <div style="padding:0.75rem 0.9rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-purple);">
            <strong>4. Higiene de Repositorio (.gitignore):</strong>
            Los archivos pesados (<code>data/raw/archive.zip</code>), entornos virtuales (<code>.venv/</code>), <code>node_modules/</code> y credenciales permanecen estrictamente fuera de Git.
          </div>
        </div>
      </article>
    </section>
  `;
}
