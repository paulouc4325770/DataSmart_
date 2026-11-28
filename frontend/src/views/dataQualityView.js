/**
 * Calidad de datos y plan de tratamiento.
 */

import { formatInt, formatPct } from '../utils/formatters.js';

export function renderDataQualityView(store, state) {
  const { qualityIssues, treatmentPlan, tablesSummary, qualityValidations = [], qualityMetrics = {}, liveQualityConnected = false } = store;
  const { severityFilter } = state;

  const filteredIssues =
    severityFilter === 'ALL'
      ? qualityIssues
      : qualityIssues.filter(i => i.severity === severityFilter);

  const totalNullCells = tablesSummary.reduce((acc, t) => acc + t.nullCells, 0);
  const totalDuplicates = tablesSummary.reduce((acc, t) => acc + t.exactDuplicates, 0);
  const totalCells = tablesSummary.reduce((acc, table) => acc + table.rows * table.cols, 0);
  const geo = tablesSummary.find(table => table.table === 'geolocalizacion');
  const geoDuplicatePct = geo?.rows ? 100 * geo.exactDuplicates / geo.rows : 0;
  const opinionNulls = qualityIssues.filter(issue => issue.table === 'opiniones' && String(issue.issueType || '').includes('Completitud'))
    .reduce((sum, issue) => sum + issue.nullCount, 0);
  const opinionsNullPct = totalNullCells ? 100 * opinionNulls / totalNullCells : 0;
  const deliveredMissingDate = Number(qualityMetrics.entregados_sin_fecha ?? 0);
  const validationFailures = qualityValidations.filter(row => row.resultado && row.resultado !== 'OK');

  return `
    <!-- Resumen Ejecutivo de Calidad de Datos -->
    <section class="kpi-grid">
      <article class="kpi-card">
        <div class="kpi-card-top">
          <span>Total Celdas Analizadas</span>
          <span class="chip ${liveQualityConnected ? 'chip-emerald' : 'chip-amber'}">${tablesSummary.length} Tablas CSV · ${liveQualityConnected ? 'perfilado API' : 'respaldo local'}</span>
        </div>
        <div class="kpi-value">${formatInt(totalCells)}</div>
        <div class="kpi-sub"><span>${formatInt(tablesSummary.reduce((sum, table) => sum + table.rows, 0))} filas totales en las tablas perfiladas</span></div>
      </article>

      <article class="kpi-card">
        <div class="kpi-card-top">
          <span>Celdas Nulas Detectadas</span>
          <span class="chip chip-amber">Completitud</span>
        </div>
        <div class="kpi-value">${formatInt(totalNullCells)}</div>
        <div class="kpi-sub"><span>${formatPct(opinionsNullPct)} concentradas en campos de Opiniones</span></div>
      </article>

      <article class="kpi-card">
        <div class="kpi-card-top">
          <span>Filas Duplicadas Exactas</span>
          <span class="chip chip-rose">Unicidad</span>
        </div>
        <div class="kpi-value">${formatInt(totalDuplicates)}</div>
        <div class="kpi-sub"><span>${formatPct(geoDuplicatePct)} de filas exactas en Geolocalización</span></div>
      </article>

      <article class="kpi-card">
        <div class="kpi-card-top">
          <span>Pedidos Entregados sin Fecha</span>
          <span class="chip chip-purple">Consistencia</span>
        </div>
        <div class="kpi-value">${formatInt(deliveredMissingDate)} pedidos</div>
        <div class="kpi-sub"><span>order_status = delivered con fecha nula</span></div>
      </article>
    </section>

    ${qualityValidations.length ? `<p class="muted">Validaciones: ${formatInt(qualityValidations.length - validationFailures.length)} OK / ${formatInt(validationFailures.length)} con resultado distinto de OK.</p>` : ''}

    <!-- Tabla de Incidencias de Calidad + Plan de Tratamiento -->
    <section class="grid-asymmetric">
      <!-- Incidencias por Tabla y Columna -->
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>Incidencias de calidad</h3>
            <p>Conteo sobre los archivos originales.</p>
          </div>
          <div class="tabs-bar">
            ${['ALL', 'Alta', 'Media', 'Baja']
              .map(
                sev => `
              <button
                class="tab-pill ${severityFilter === sev ? 'active' : ''}"
                data-action="set-quality-severity"
                data-severity="${sev}"
              >
                ${sev === 'ALL' ? 'Todas' : `Severidad ${sev}`}
              </button>
            `
              )
              .join('')}
          </div>
        </div>

        <div class="table-wrap quality-issues-table-wrap">
          <p class="muted">Desplázate para ver todas las columnas.</p>
          <table class="data-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>Tabla / Campo</th>
                <th>Dimensión</th>
                <th>Registros Afectados</th>
                <th>% Filas</th>
                <th>Severidad</th>
                <th>Estrategia de Tratamiento</th>
              </tr>
            </thead>
            <tbody>
              ${filteredIssues
                .map(
                  issue => `
                <tr>
                  <td class="mono"><strong>${issue.id}</strong></td>
                  <td>
                    <strong>${issue.table}</strong>
                    <div class="mono" style="color:var(--accent-primary); font-size:0.75rem;">${issue.column}</div>
                  </td>
                  <td>${issue.issueType}</td>
                  <td class="mono">${formatInt(issue.nullCount)}</td>
                  <td>
                    <div class="mono" style="font-weight:700;">${formatPct(issue.pctRows)}</div>
                    <div class="bar-track" style="height:5px; margin-top:4px;">
                      <div
                        class="bar-fill"
                        style="width:${Math.min(issue.pctRows, 100)}%; background:${
                          issue.severity === 'Alta'
                            ? 'var(--accent-rose)'
                            : issue.severity === 'Media'
                            ? 'var(--accent-amber)'
                            : 'var(--accent-primary)'
                        };"
                      ></div>
                    </div>
                  </td>
                  <td>
                    <span class="chip ${
                      issue.severity === 'Alta'
                        ? 'chip-rose'
                        : issue.severity === 'Media'
                        ? 'chip-amber'
                        : 'chip-blue'
                    }">
                      ${issue.severity}
                    </span>
                  </td>
                  <td style="font-size:0.78rem; color:var(--text-secondary); max-width:290px;">
                    ${issue.treatment}
                  </td>
                </tr>
              `
                )
                .join('')}
            </tbody>
          </table>
        </div>
      </article>

      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>Plan de tratamiento</h3>
            <p>Reglas aplicadas a los datos procesados.</p>
          </div>
        </div>

        <div style="display:flex; flex-direction:column; gap:0.75rem;">
          ${treatmentPlan
            .map(
              item => `
            <div style="padding:0.8rem 0.95rem; border-radius:var(--radius-sm); background:var(--bg-secondary); border:1px solid var(--border-subtle); display:flex; flex-direction:column; gap:0.3rem;">
              <div style="display:flex; justify-content:space-between; align-items:center; gap:0.5rem;">
                <strong style="font-size:0.84rem; color:var(--text-primary);">
                  <span class="mono" style="color:var(--accent-primary);">#0${item.step}</span> ${item.title}
                </strong>
                <span class="chip ${item.status === 'Implementado' ? 'chip-emerald' : 'chip-blue'}">
                  ${item.status}
                </span>
              </div>
              <p style="font-size:0.78rem; color:var(--text-secondary);">
                ${item.description}
              </p>
            </div>
          `
            )
            .join('')}
        </div>
      </article>
    </section>

    <section class="card">
      <div class="card-header"><div class="card-title-group"><h3>Integridad referencial</h3></div></div>
      <div class="grid-3">
        <div style="padding:1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-rose);">
          <h4 style="font-size:0.88rem; margin-bottom:0.35rem;">Geolocalización</h4>
          <p style="font-size:0.79rem; color:var(--text-secondary);">
            261.831 filas duplicadas (26,18%); agrupar por prefijo postal antes de unir.
          </p>
        </div>
        <div style="padding:1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-amber);">
          <h4 style="font-size:0.88rem; margin-bottom:0.35rem;">Reseñas</h4>
          <p style="font-size:0.79rem; color:var(--text-secondary);">
            98.410 <code>review_id</code> distintos en 99.224 reseñas; agregar por <code>order_id</code>.
          </p>
        </div>
        <div style="padding:1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-primary);">
          <h4 style="font-size:0.88rem; margin-bottom:0.35rem;">Clientes</h4>
          <p style="font-size:0.79rem; color:var(--text-secondary);">
            <code>customer_id</code> identifica el pedido; <code>customer_unique_id</code>, al comprador. Agrupar por este último.
          </p>
        </div>
      </div>
    </section>
  `;
}
