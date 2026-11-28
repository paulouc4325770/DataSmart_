/**
 * Dashboard: indicadores, evolución mensual, estados de pedido y categorías.
 */

import { renderMonthlySalesSVG } from '../components/svgCharts.js';
import { formatBRL, formatInt, formatPct } from '../utils/formatters.js';

export function renderExecutiveDashboardView(store, state) {
  const { kpis, orderStatus, monthlySales, topCategories, tablesSummary } = store;
  const { excludeExtremeMonths, categoryLimit } = state;

  const filteredSales = excludeExtremeMonths
    ? monthlySales.filter(m => !m.isExtreme)
    : monthlySales;

  const totalSalesFiltered = filteredSales.reduce((acc, item) => acc + item.salesBRL, 0);
  const peakMonth = [...filteredSales].sort((a, b) => b.salesBRL - a.salesBRL)[0] || monthlySales[14];

  const visibleCategories = topCategories.slice(0, categoryLimit);
  const top5Sum = topCategories.slice(0, 5).reduce((acc, c) => acc + c.salesBRL, 0);

  return `
    <div class="tabs-bar" style="justify-content:flex-end; margin-bottom:0.5rem;">
      <button class="btn" data-action="export-kpis">⬇ Exportar KPIs</button>
      <button class="btn btn-primary" data-action="navigate" data-view="models">Ir a modelos</button>
    </div>

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
          <div class="kpi-sub"><span>${kpi.definition}</span></div>
        </article>
      `
        )
        .join('')}
    </section>

    <section class="grid-asymmetric">
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>Ventas mensuales</h3>
            <p>Máximo: ${peakMonth.monthLabel} (${formatBRL(peakMonth.salesBRL)})</p>
          </div>
          <div class="tabs-bar">
            <button class="tab-pill ${!excludeExtremeMonths ? 'active' : ''}" data-action="toggle-extreme-months" data-value="false">
              Completa
            </button>
            <button class="tab-pill ${excludeExtremeMonths ? 'active' : ''}" data-action="toggle-extreme-months" data-value="true">
              Sin extremos
            </button>
            <button class="btn" data-action="export-monthly-sales" title="Exportar serie mensual">CSV</button>
          </div>
        </div>

        <div class="svg-chart-container">${renderMonthlySalesSVG(filteredSales)}</div>

        <div class="chart-summary">
          <span>Acumulado: <span class="mono">${formatBRL(totalSalesFiltered)}</span></span>
          <span>Pico: <span class="mono">${formatBRL(peakMonth.salesBRL)}</span></span>
        </div>
      </article>

      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>Estados de pedido</h3>
          </div>
          <span class="chip chip-emerald">${formatPct(orderStatus[0]?.pct ?? 0, 2)} entregados</span>
        </div>

        <div class="bar-list">
          ${orderStatus
            .map(st => {
              const visualWidth = Math.max(st.pct, st.count > 100 ? 3.5 : 1.2);
              return `
              <div class="bar-row">
                <div class="bar-row-label">
                  <span>
                    <strong aria-hidden="true" style="color:${st.color}">${st.marker}</strong>
                    ${st.label}
                  </span>
                  <span class="mono"><strong>${formatInt(st.count)}</strong> (${formatPct(st.pct)})</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" style="width:${visualWidth}%; background:${st.color};"></div>
                </div>
              </div>
            `;
            })
            .join('')}
        </div>
      </article>
    </section>

    <section class="grid-2">
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>Categorías con mayores ventas</h3>
            <p>Top 5: ${formatBRL(top5Sum, 0)} (${formatPct(topCategories.slice(0, 5).reduce((acc, c) => acc + c.sharePct, 0))})</p>
          </div>
          <div class="tabs-bar">
            <button class="tab-pill ${categoryLimit === 5 ? 'active' : ''}" data-action="set-category-limit" data-limit="5">Top 5</button>
            <button class="tab-pill ${categoryLimit === 10 ? 'active' : ''}" data-action="set-category-limit" data-limit="10">Top 10</button>
          </div>
        </div>

        <div class="bar-list">
          ${visibleCategories
            .map(cat => {
              const widthPct = (cat.salesBRL / topCategories[0].salesBRL) * 100;
              const isTop5 = cat.rank <= 5;
              return `
              <div class="bar-row">
                <div class="bar-row-label">
                  <span>
                    <span class="mono muted">#${cat.rank}</span>
                    <strong>${cat.nameEs}</strong>
                  </span>
                  <span class="mono"><strong>${formatBRL(cat.salesBRL, 0)}</strong> (${formatPct(cat.sharePct)})</span>
                </div>
                <div class="bar-track">
                  <div class="bar-fill" style="width:${widthPct.toFixed(1)}%; background:${isTop5 ? 'var(--chart-primary)' : 'var(--chart-secondary)'};"></div>
                </div>
              </div>
            `;
            })
            .join('')}
        </div>
      </article>

      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>Tablas de Olist</h3>
          </div>
          <button class="btn" data-action="navigate" data-view="dictionary">Ver diccionario →</button>
        </div>

        <div class="table-wrap">
          <table class="data-table">
            <thead>
              <tr>
                <th>Tabla</th>
                <th>Filas</th>
                <th>Cols</th>
                <th>Nulos</th>
                <th>Duplicados</th>
                <th>Estado</th>
              </tr>
            </thead>
            <tbody>
              ${tablesSummary
                .map(
                  t => `
                <tr>
                  <td><strong>${t.table}</strong></td>
                  <td class="mono">${formatInt(t.rows)}</td>
                  <td class="mono">${t.cols}</td>
                  <td class="mono">${formatInt(t.nullCells)}</td>
                  <td class="mono">${formatInt(t.exactDuplicates)}</td>
                  <td>
                    <span class="chip ${
                      t.exactDuplicates > 0 ? 'chip-rose' : t.nullCells > 0 ? 'chip-amber' : 'chip-emerald'
                    }">
                      ${t.exactDuplicates > 0 ? 'Deduplicar' : t.nullCells > 0 ? 'Revisar' : 'Limpio'}
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

    <section class="card">
      <div class="card-header"><div class="card-title-group"><h3>Gráficos</h3></div></div>
      <div class="grid-3">
        <div class="card" style="padding:0.9rem; background:var(--bg-secondary);">
          <div style="font-size:0.82rem; font-weight:600; margin-bottom:0.4rem;">Pedidos por estado</div>
          <img
            src="/resultados/graficos/01_pedidos_por_estado.png"
            alt="Pedidos según su estado"
            style="width:100%; border-radius:8px; border:1px solid var(--border-subtle); background:var(--off-white);"
            onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
          />
          <div style="display:none; font-size:0.76rem; color:var(--text-muted); padding:1rem; text-align:center;">Gráfico no disponible.</div>
        </div>
        <div class="card" style="padding:0.9rem; background:var(--bg-secondary);">
          <div style="font-size:0.82rem; font-weight:600; margin-bottom:0.4rem;">Ventas mensuales</div>
          <img
            src="/resultados/graficos/02_ventas_mensuales.png"
            alt="Ventas mensuales de artículos"
            style="width:100%; border-radius:8px; border:1px solid var(--border-subtle); background:var(--off-white);"
            onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
          />
          <div style="display:none; font-size:0.76rem; color:var(--text-muted); padding:1rem; text-align:center;">Gráfico no disponible.</div>
        </div>
        <div class="card" style="padding:0.9rem; background:var(--bg-secondary);">
          <div style="font-size:0.82rem; font-weight:600; margin-bottom:0.4rem;">Top categorías</div>
          <img
            src="/resultados/graficos/03_top_categorias.png"
            alt="Las 10 categorías con mayores ventas"
            style="width:100%; border-radius:8px; border:1px solid var(--border-subtle); background:var(--off-white);"
            onerror="this.style.display='none'; this.nextElementSibling.style.display='block';"
          />
          <div style="display:none; font-size:0.76rem; color:var(--text-muted); padding:1rem; text-align:center;">Gráfico no disponible.</div>
        </div>
      </div>
    </section>
  `;
}
