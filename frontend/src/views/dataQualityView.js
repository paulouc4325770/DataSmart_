/**
 * Módulo 2: Evaluación de Calidad de Datos & Plan de Tratamiento
 * Cubre la Sección 9 y Sección 9.1 del Informe de Avance (Semana 7).
 */

import { formatInt, formatPct } from '../utils/formatters.js';

export function renderDataQualityView(store, state) {
  const { qualityIssues, treatmentPlan, tablesSummary } = store;
  const { severityFilter } = state;

  const filteredIssues =
    severityFilter === 'ALL'
      ? qualityIssues
      : qualityIssues.filter(i => i.severity === severityFilter);

  const totalNullCells = tablesSummary.reduce((acc, t) => acc + t.nullCells, 0);
  const totalDuplicates = tablesSummary.reduce((acc, t) => acc + t.exactDuplicates, 0);

  return `
    <!-- Resumen Ejecutivo de Calidad de Datos -->
    <section class="kpi-grid">
      <article class="kpi-card">
        <div class="kpi-card-top">
          <span>Total Celdas Analizadas</span>
          <span class="chip chip-blue">9 Tablas CSV</span>
        </div>
        <div class="kpi-value">8.264.113</div>
        <div class="kpi-sub"><span>1.547.848 filas totales en Olist</span></div>
      </article>

      <article class="kpi-card">
        <div class="kpi-card-top">
          <span>Celdas Nulas Detectadas</span>
          <span class="chip chip-amber">Completitud</span>
        </div>
        <div class="kpi-value">${formatInt(totalNullCells)}</div>
        <div class="kpi-sub"><span>Concentradas 95,2% en textos de Opiniones</span></div>
      </article>

      <article class="kpi-card">
        <div class="kpi-card-top">
          <span>Filas Duplicadas Exactas</span>
          <span class="chip chip-rose">Unicidad</span>
        </div>
        <div class="kpi-value">${formatInt(totalDuplicates)}</div>
        <div class="kpi-sub"><span>100% en tabla Geolocalización (26,18%)</span></div>
      </article>

      <article class="kpi-card">
        <div class="kpi-card-top">
          <span>Pedidos Entregados sin Fecha</span>
          <span class="chip chip-purple">Consistencia</span>
        </div>
        <div class="kpi-value">8 pedidos</div>
        <div class="kpi-sub"><span>order_status = delivered con fecha nula</span></div>
      </article>
    </section>

    <div class="method-note">
      <strong>Criterio de Auditoría (Sección 9):</strong>
      Se evaluaron cuatro dimensiones sobre los CSV originales sin imputación previa:
      <strong>Completitud</strong> (valores nulos), <strong>Unicidad</strong> (duplicados de filas y claves),
      <strong>Consistencia Referencial</strong> (relaciones 1:N en pagos, reseñas y códigos postales) y
      <strong>Validez de Rangos</strong> (secuencia temporal de marcas de tiempo).
    </div>

    <!-- Tabla de Incidencias de Calidad + Plan de Tratamiento -->
    <section class="grid-asymmetric">
      <!-- Incidencias por Tabla y Columna -->
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>🔍 Matriz de Incidencias de Calidad de Datos (Sección 9)</h3>
            <p>Estadísticas exactas calculadas sobre los archivos originales de la zona <code>data/raw/</code></p>
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

        <div class="table-wrap">
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

      <!-- Sección 9.1: Plan de Tratamiento (7 Reglas) -->
      <article class="card">
        <div class="card-header">
          <div class="card-title-group">
            <h3>🛡️ Plan de Tratamiento (Sección 9.1)</h3>
            <p>7 reglas de ingeniería de datos para la zona <code>data/processed/</code></p>
          </div>
          <span class="chip chip-emerald">CRISP-DM Fase 3</span>
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

    <!-- Diagnóstico de Integridad Referencial y Claves -->
    <section class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h3>🔗 Reglas Críticas de Integridad Referencial y Prevención de Multiplicación en Joins</h3>
          <p>Hallazgos estructurales documentados en las Secciones 6, 9 y 10 del Informe</p>
        </div>
      </div>

      <div class="grid-3">
        <div style="padding:1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-rose);">
          <h4 style="font-size:0.88rem; margin-bottom:0.35rem;">1. Geolocalización (1.000.163 filas)</h4>
          <p style="font-size:0.79rem; color:var(--text-secondary);">
            Presenta <strong>261.831 filas duplicadas exactas (26,18%)</strong> y múltiples coordenadas por cada
            <code>geolocation_zip_code_prefix</code> (19.015 prefijos distintos). Hacer un <code>JOIN</code> directo sin
            agrupar previamente por prefijo postal multiplica artificialmente las filas de pedidos y ventas.
          </p>
        </div>

        <div style="padding:1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-amber);">
          <h4 style="font-size:0.88rem; margin-bottom:0.35rem;">2. Opiniones y Review ID Repetidos</h4>
          <p style="font-size:0.79rem; color:var(--text-secondary);">
            De las 99.224 reseñas, existen <strong>98.410 <code>review_id</code> distintos</strong> y
            <strong>98.673 <code>order_id</code> distintos</strong>. Un pedido puede tener más de una reseña; por ello se
            recomienda clave surrogate interna y agregación previa por <code>order_id</code>.
          </p>
        </div>

        <div style="padding:1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-primary);">
          <h4 style="font-size:0.88rem; margin-bottom:0.35rem;">3. Customer ID vs Customer Unique ID</h4>
          <p style="font-size:0.79rem; color:var(--text-secondary);">
            <code>customer_id</code> (99.441 valores) es un identificador transaccional por pedido, mientras que
            <code>customer_unique_id</code> (96.096 valores) identifica al comprador real. Todo modelo RFM y clustering
            (PN-01 y PN-02) debe agrupar por <code>customer_unique_id</code>.
          </p>
        </div>
      </div>
    </section>
  `;
}
