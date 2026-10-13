/**
 * Módulo 1: Dashboard Ejecutivo & Análisis Exploratorio de Datos (EDA)
 * Cubre las Secciones 1, 6, 7 y 8 del Informe de Avance (Semana 7) + Gráficos Oficiales.
 */

import { renderMonthlySalesSVG } from '../components/svgCharts.js';
import { formatBRL, formatInt, formatPct } from '../utils/formatters.js';

export function renderExecutiveDashboardView(store, state) {
  const { kpis, orderStatus, monthlySales, topCategories, tablesSummary } = store;
  const { excludeExtremeMonths, categoryLimit, showPngModal } = state;

  const filteredSales = excludeExtremeMonths
    ? monthlySales.filter(m => !m.isExtreme)
    : monthlySales;

  const totalSalesFiltered = filteredSales.reduce((acc, item) => acc + item.salesBRL, 0);
  const peakMonth = [...filteredSales].sort((a, b) => b.salesBRL - a.salesBRL)[0] || monthlySales[14];

  const visibleCategories = topCategories.slice(0, categoryLimit);
  const top5Sum = topCategories.slice(0, 5).reduce((acc, c) => acc + c.salesBRL, 0);

  return `
    <!-- Hero Context Banner -->
    <section class="context-banner">
      <div class="context-banner-info">
        <h2>
          Plataforma de Inteligencia Analítica DataSmart
          <span class="chip chip-emerald">CRISP-DM Activo</span>
          <span class="chip chip-blue">Olist Dataset (9 CSVs)</span>
        </h2>
        <p>
          Análisis descriptivo, perfilado de calidad y modelado sobre <strong>99.441 pedidos históricos</strong>,
          <strong>96.096 compradores únicos</strong> y <strong>32.951 productos</strong> del comercio electrónico brasileño (2016–2018).
        </p>
      </div>
      <div class="context-meta-chips">
        <button class="btn" data-action="export-kpis" title="Descargar KPIs en formato CSV">
          ⬇ Exportar KPIs CSV
        </button>
        <button class="btn btn-primary" data-action="navigate" data-view="models">
          ⚡ Ir al Laboratorio Predictivo (PN-01..10)
        </button>
      </div>
    </section>

    <!-- Sección 7: Indicadores KPI Oficiales -->
    <section class="kpi-grid">
      ${kpis
        .map(
          kpi => `
        <article class="kpi-card">
          <div class="kpi-card-top">
            <span>${kpi.label}</span>
            <span class="chip chip-${kpi.accent}">${kpi.badge}</span>
          </div>
          <div class="kpi-value">${kpi.formatted}</div>
          <div class="kpi-sub" title="${kpi.definition}">
            <span>${kpi.definition}</span>
          </div>
        </article>
      `
        )
        .join('')}
    </section>

    <!-- Nota Metodológica Oficial (Sección 7 y 8 del Informe) -->
    <div class="method-note">
      <strong>Nota Metodológica (Sección 7 del Informe):</strong>
      La métrica de <em>Ventas de artículos entregados (R$ 13.221.498,11)</em> suma exclusivamente la columna
      <code>price</code> en pedidos cuyo estado final es <code>delivered</code> (96.478 pedidos) y excluye
      <code>freight_value</code>. La tasa de entregas tardías (8,11%) compara fechas reales vs estimadas sobre
      los 96.470 pedidos entregados con ambas fechas disponibles.
    </div>

    <!-- Sección 8.2: Evolución Mensual + Sección 8.1: Estados de Pedidos -->
    <section class="grid-asymmetric">
      <!-- Evolución mensual de ventas -->
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>📈 Figura 2. Evolución Mensual de Ventas de Artículos (Pedidos Entregados)</h3>
            <p>
              Serie histórica por fecha de compra (<code>order_purchase_timestamp</code>).
              Pico en <strong>${peakMonth.monthLabel} (${formatBRL(peakMonth.salesBRL)})</strong> asociado a campaña Black Friday.
            </p>
          </div>
          <div class="tabs-bar">
            <button
              class="tab-pill ${!excludeExtremeMonths ? 'active' : ''}"
              data-action="toggle-extreme-months"
              data-value="false"
            >
              Serie Completa (24 meses)
            </button>
            <button
              class="tab-pill ${excludeExtremeMonths ? 'active' : ''}"
              data-action="toggle-extreme-months"
              data-value="true"
            >
              Sin Meses Extremos 2016 (20 meses)
            </button>
            <button
              class="btn"
              data-action="export-monthly-sales"
              title="Exportar serie mensual CSV"
            >
              CSV
            </button>
          </div>
        </div>

        <div class="svg-chart-container">
          ${renderMonthlySalesSVG(filteredSales)}
        </div>

        <div style="display:flex; justify-content:space-between; flex-wrap:wrap; gap:0.75rem; font-size:0.78rem; color:var(--text-secondary); padding-top:0.35rem; border-top:1px solid var(--border-subtle);">
          <span><strong>Acumulado vista actual:</strong> <span class="mono">${formatBRL(totalSalesFiltered)}</span></span>
          <span><strong>Pico Histórico:</strong> <span class="mono">Nov 2017 — R$ 987.765,37</span></span>
          <span><strong>Meseta 2018 (Ene–Ago):</strong> <span class="mono">R$ 826.437 – R$ 977.544 / mes</span></span>
        </div>
      </article>

      <!-- Distribución de los estados de pedidos -->
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>📦 Figura 1. Distribución de Estados de Pedidos</h3>
            <p>Universo total: 99.441 pedidos registrados en <code>olist_orders_dataset.csv</code></p>
          </div>
          <span class="chip chip-emerald">97,02% Entregados</span>
        </div>

        <div style="display:flex; flex-direction:column; gap:0.72rem; margin-top:0.25rem;">
          ${orderStatus
            .map(st => {
              const visualWidth = Math.max(st.pct, st.count > 100 ? 3.5 : 1.2);
              return `
              <div class="bar-row">
                <div class="bar-row-label">
                  <span>
                    <strong style="color:${st.color}">●</strong>
                    ${st.label} <span class="mono" style="color:var(--text-muted)">(${st.status})</span>
                  </span>
                  <span class="mono">
                    <strong>${formatInt(st.count)}</strong> (${formatPct(st.pct)})
                  </span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" style="width:${visualWidth}%; background:${st.color};"></div>
                </div>
              </div>
            `;
            })
            .join('')}
        </div>

        <div class="method-note" style="margin-top:auto;">
          <strong>Observación Analítica (Sección 8.1):</strong>
          El 97,02% entregado y 0,63% cancelado reflejan una fotografía histórica; los estados intermedios
          (<em>shipped, invoiced, processing</em>) corresponden al corte temporal del dataset.
        </div>
      </article>
    </section>

    <!-- Sección 8.3: Top 10 Categorías + Resumen de las 9 Tablas -->
    <section class="grid-2">
      <!-- Top 10 categorías -->
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>🏆 Figura 3. Categorías con Mayores Ventas de Artículos</h3>
            <p>
              Las 5 primeras categorías concentran <strong>${formatBRL(top5Sum)} (39,83%)</strong> de las ventas entregadas.
            </p>
          </div>
          <div class="tabs-bar">
            <button
              class="tab-pill ${categoryLimit === 5 ? 'active' : ''}"
              data-action="set-category-limit"
              data-limit="5"
            >
              Top 5 (Pareto 39,83%)
            </button>
            <button
              class="tab-pill ${categoryLimit === 10 ? 'active' : ''}"
              data-action="set-category-limit"
              data-limit="10"
            >
              Top 10 Oficial
            </button>
          </div>
        </div>

        <div style="display:flex; flex-direction:column; gap:0.75rem;">
          ${visibleCategories
            .map(cat => {
              const widthPct = (cat.salesBRL / topCategories[0].salesBRL) * 100;
              const isTop5 = cat.rank <= 5;
              return `
              <div class="bar-row">
                <div class="bar-row-label">
                  <span>
                    <span class="mono" style="color:var(--text-muted); margin-right:0.35rem;">#${cat.rank}</span>
                    <strong>${cat.nameEs}</strong>
                    <span class="mono" style="color:var(--text-muted); font-size:0.73rem;">(${cat.original})</span>
                  </span>
                  <span class="mono">
                    <strong>${formatBRL(cat.salesBRL, 0)}</strong>
                    <span style="color:var(--text-muted)">(${formatPct(cat.sharePct)})</span>
                  </span>
                </div>
                <div class="bar-track">
                  <div
                    class="bar-fill"
                    style="width:${widthPct.toFixed(1)}%; background:${
                      isTop5
                        ? 'linear-gradient(90deg, #3b82f6, #10b981)'
                        : 'linear-gradient(90deg, #6366f1, #3b82f6)'
                    };"
                  ></div>
                </div>
              </div>
            `;
            })
            .join('')}
        </div>
      </article>

      <!-- Sección 6: Inventario y Resumen de las 9 Tablas de Olist -->
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>🗄️ Inventario Oficial de Tablas CSV (Fuente Olist)</h3>
            <p>Sincronizado con <code>resultados/resumen_tablas.csv</code> (9 archivos analizados)</p>
          </div>
          <button class="btn" data-action="navigate" data-view="dictionary">
            Ver Diccionario (53 cols) →
          </button>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Tabla</th>
                <th>Filas</th>
                <th>Cols</th>
                <th>Celdas Nulas</th>
                <th>Duplicados Exactos</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              ${tablesSummary
                .map(
                  t => `
                <tr>
                  <td>
                    <strong>${t.table}</strong>
                    <div class="mono" style="font-size:0.7rem; color:var(--text-muted);">${t.file}</div>
                  </td>
                  <td class="mono">${formatInt(t.rows)}</td>
                  <td class="mono">${t.cols}</td>
                  <td class="mono" style="color:${t.nullCells > 0 ? 'var(--accent-amber)' : 'var(--text-secondary)'}">
                    ${formatInt(t.nullCells)}
                  </td>
                  <td class="mono" style="color:${t.exactDuplicates > 0 ? 'var(--accent-rose)' : 'var(--text-secondary)'}">
                    ${formatInt(t.exactDuplicates)}
                  </td>
                  <td>
                    <span class="chip ${
                      t.exactDuplicates > 0
                        ? 'chip-rose'
                        : t.nullCells > 0
                        ? 'chip-amber'
                        : 'chip-emerald'
                    }">
                      ${t.exactDuplicates > 0 ? 'Deduplicar' : t.nullCells > 0 ? 'Revisar Nulos' : 'Limpio'}
                    </span>
                  </td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>
        </div>
      </article>
    </section>

    <!-- Galería de Gráficos Estáticos Oficiales generados por src/eda_olist.py -->
    <section class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h3>🖼️ Reportes Visuales Generados por <code>src/eda_olist.py</code> (Carpeta <code>resultados/graficos/</code>)</h3>
          <p>
            Visualizaciones PNG exportadas directamente por el pipeline de Python para trazabilidad con el documento de entrega.
          </p>
        </div>
        <span class="chip chip-blue">DPI 170 • Matplotlib Agg</span>
      </div>

      <div class="grid-3">
        <div class="card" style="padding:0.9rem; background:var(--bg-secondary);">
          <div style="font-size:0.82rem; font-weight:600; margin-bottom:0.4rem;">01_pedidos_por_estado.png</div>
          <img
            src="/resultados/graficos/01_pedidos_por_estado.png"
            alt="Pedidos según su estado"
            style="width:100%; border-radius:8px; border:1px solid var(--border-subtle); background:#fff;"
            onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
          />
          <div style="display:none; font-size:0.76rem; color:var(--text-muted); padding:1rem; text-align:center;">
            Ejecuta <code>py frontend/server.py</code> o <code>npm run dev</code> para servir el PNG desde <code>../resultados/graficos/</code>.
          </div>
        </div>

        <div class="card" style="padding:0.9rem; background:var(--bg-secondary);">
          <div style="font-size:0.82rem; font-weight:600; margin-bottom:0.4rem;">02_ventas_mensuales.png</div>
          <img
            src="/resultados/graficos/02_ventas_mensuales.png"
            alt="Ventas mensuales de artículos"
            style="width:100%; border-radius:8px; border:1px solid var(--border-subtle); background:#fff;"
            onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
          />
          <div style="display:none; font-size:0.76rem; color:var(--text-muted); padding:1rem; text-align:center;">
            Ejecuta <code>py frontend/server.py</code> o <code>npm run dev</code> para servir el PNG desde <code>../resultados/graficos/</code>.
          </div>
        </div>

        <div class="card" style="padding:0.9rem; background:var(--bg-secondary);">
          <div style="font-size:0.82rem; font-weight:600; margin-bottom:0.4rem;">03_top_categorias.png</div>
          <img
            src="/resultados/graficos/03_top_categorias.png"
            alt="Las 10 categorías con mayores ventas"
            style="width:100%; border-radius:8px; border:1px solid var(--border-subtle); background:#fff;"
            onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
          />
          <div style="display:none; font-size:0.76rem; color:var(--text-muted); padding:1rem; text-align:center;">
            Ejecuta <code>py frontend/server.py</code> o <code>npm run dev</code> para servir el PNG desde <code>../resultados/graficos/</code>.
          </div>
        </div>
      </div>
    </section>
  `;
}
