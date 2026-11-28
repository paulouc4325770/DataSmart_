/**
 * Laboratorio de modelos: preguntas de negocio y resultados analíticos.
 */

import { renderSeriesTestSVG, renderOlistSubgraphSVG } from '../components/svgCharts.js';
import { formatBRL, formatInt, formatPct } from '../utils/formatters.js';
import { renderAssociationTab } from './associationView.js';

/** Color del chip de estado según lo realmente implementado. */
function statusChipClass(status) {
  if (/^(Disponible|Resultados reales|Completado)/.test(status)) return 'chip-emerald';
  return 'chip-amber';
}

function moduleRows(modules, modulo, archivo) {
  return modules?.[modulo]?.resultados?.[archivo]?.filas || [];
}

function fmtNumber(value, digits = 2) {
  if (value === null || value === undefined || String(value).trim() === '') return '—';
  const number = Number(value);
  return Number.isFinite(number) ? number.toLocaleString('es-ES', { maximumFractionDigits: digits }) : '—';
}

function escapeHtml(value) {
  return String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
}

function statusPregunta(id, modules, association) {
  if (id === 'PN-05') return association?.status === 'ok' ? 'Disponible' : 'Sin resultados';
  if (id === 'PN-02') return modules?.clustering?.status === 'ok'
    ? 'RFM disponible; la curva de Pareto y sus métricas siguen pendientes.'
    : 'Sin resultados';
  const modulo = ({ 'PN-01': 'clustering', 'PN-02': 'clustering', 'PN-04': 'series', 'PN-07': 'regresion', 'PN-08': 'clasificacion', 'PN-09': 'grafos', 'PN-10': 'nlp' })[id];
  if (!modulo) return null;
  return modules?.[modulo]?.status === 'ok' ? 'Disponible' : 'Sin resultados';
}

export function renderBusinessModelsView(store, state) {
  const {
    businessQuestions,
    association,
    monthlySales,
  } = store;

  const { activeLabTab, selectedGraphNode } = state;

  const modules = store.modules || {};
  const clusterRows = moduleRows(modules, 'clustering', 'perfiles_clusters');
  const clusterEvaluation = moduleRows(modules, 'clustering', 'evaluacion_clustering');
  const dbscanRows = moduleRows(modules, 'clustering', 'perfiles_clusters_dbscan');
  const dbscanEvaluation = moduleRows(modules, 'clustering', 'evaluacion_clustering_dbscan');
  const temporalForecasts = moduleRows(modules, 'series', 'pronosticos_ventas');
  const temporalEvaluation = moduleRows(modules, 'series', 'evaluacion_series');
  const regressionEvaluation = moduleRows(modules, 'regresion', 'evaluacion_regresion');
  const classificationEvaluation = moduleRows(modules, 'clasificacion', 'evaluacion_clasificacion');
  const classificationMetadata = modules.clasificacion?.resultados?.clasificacion_metadata || {};
  const globalExplanations = moduleRows(modules, 'explicabilidad', 'importancia_variables');
  const localExplanations = moduleRows(modules, 'explicabilidad', 'explicaciones_locales');
  const explanationClasses = [...new Set(globalExplanations.map(row => row.clase))];
  const explainedReviewIds = [...new Set(localExplanations.map(row => row.review_id))].slice(0, 3);
  const monitoringMetrics = moduleRows(modules, 'monitoring', 'monitoring_metrics');
  const driftRows = moduleRows(modules, 'monitoring', 'data_drift_report');
  const modelRegistry = modules.monitoring?.resultados?.model_registry || {};
  const nlpTerms = moduleRows(modules, 'nlp', 'nlp_terminos_frecuentes');
  const nlpSentiments = moduleRows(modules, 'nlp', 'nlp_sentimientos');
  const graphMetadata = modules.grafos?.resultados?.grafos_metadata || modules.grafos?.resultados?.grafo_metadata || {};
  const subgraph = modules.grafos?.resultados?.grafo_subgrafo;
  const moduleTitles = {
    clustering: 'Segmentación RFM', series: 'Series temporales', grafos: 'Grafo vendedor–producto',
    regresion: 'Regresión de entrega', clasificacion: 'Clasificación', nlp: 'Minería de texto',
    explicabilidad: 'Explicabilidad', monitoring: 'Monitoreo', modelos: 'Evaluación consolidada',
  };
  const actualResultsPanel = `
    <section class="card">
      <div class="card-header"><div class="card-title-group"><h3>Resultados disponibles</h3></div></div>
      <div class="grid-3">${Object.entries(moduleTitles).map(([key, title]) => {
        const result = modules[key] || { status: 'sin_resultados' };
        const available = result.status === 'ok' && !result.faltantes?.length;
        const partial = result.status === 'parcial' || (result.status === 'ok' && result.faltantes?.length);
        const label = available ? 'Disponible' : partial ? 'Parcial' : (result.status === 'sin_resultados' || result.status === 'sin_api') ? 'Sin resultados' : 'Error de carga';
        return `<article class="card" style="padding:.85rem"><strong>${title}</strong><p class="chip ${available ? 'chip-emerald' : 'chip-amber'}">${label}</p></article>`;
      }).join('')}</div>
    </section>`;

  const cleanHistory = monthlySales.filter(m => !m.isExtreme);

  return `
    ${actualResultsPanel}
    <section class="card">
      <div class="card-header">
        <div class="card-title-group"><h3>Preguntas de negocio</h3></div>
        <span class="chip chip-purple">10 preguntas</span>
      </div>

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Área</th>
              <th>Pregunta</th>
              <th>Técnica</th>
              <th>Métricas</th>
              <th>Estado</th>
            </tr>
          </thead>
          <tbody>
            ${businessQuestions
              .map(
                bq => `
              <tr>
                <td class="mono"><strong>${bq.id}</strong></td>
                <td><span class="chip chip-blue">${bq.area}</span></td>
                <td>
                  <strong>${bq.question}</strong>
                  <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:0.15rem;">${escapeHtml(statusPregunta(bq.id, modules, association) || bq.summary)}</div>
                </td>
                <td class="mono" style="color:var(--accent-cyan);">${bq.technique}</td>
                 <td style="font-size:0.77rem; color:var(--text-secondary);">${bq.metrics}</td>
                 <td><span class="chip ${statusChipClass(statusPregunta(bq.id, modules, association) || bq.status)}">${escapeHtml(statusPregunta(bq.id, modules, association) || bq.status)}</span></td>
              </tr>
            `
              )
              .join('')}
          </tbody>
        </table>
      </div>
    </section>

    <!-- Selector de Laboratorio Analítico Interactivo -->
    <section class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h3>Resultados analíticos</h3>
        </div>
        <div class="tabs-bar">
          <button class="tab-pill ${activeLabTab === 'rfm' ? 'active' : ''}" data-action="set-lab-tab" data-tab="rfm">Segmentación RFM</button>
          <button class="tab-pill ${activeLabTab === 'association' ? 'active' : ''}" data-action="set-lab-tab" data-tab="association">Asociación</button>
          <button class="tab-pill ${activeLabTab === 'forecast' ? 'active' : ''}" data-action="set-lab-tab" data-tab="forecast">Pronóstico de ventas</button>
          <button class="tab-pill ${activeLabTab === 'logistics' ? 'active' : ''}" data-action="set-lab-tab" data-tab="logistics">Regresión de entrega</button>
          <button class="tab-pill ${activeLabTab === 'explainability' ? 'active' : ''}" data-action="set-lab-tab" data-tab="explainability">Explicabilidad</button>
          <button class="tab-pill ${activeLabTab === 'nlp' ? 'active' : ''}" data-action="set-lab-tab" data-tab="nlp">Clasificación y NLP</button>
          <button class="tab-pill ${activeLabTab === 'graphs' ? 'active' : ''}" data-action="set-lab-tab" data-tab="graphs">Grafos</button>
          <button class="tab-pill ${activeLabTab === 'monitoring' ? 'active' : ''}" data-action="set-lab-tab" data-tab="monitoring">Monitoreo</button>
        </div>
      </div>

      ${
        activeLabTab === 'rfm'
          ? `
        <!-- TAB 1: RFM + CLUSTERING (PN-01 & PN-02) -->
        <div class="grid-asymmetric" style="margin-top:0.5rem;">
          <div style="display:flex; flex-direction:column; gap:0.85rem;">
          <h4 style="font-size:0.95rem;">Segmentación RFM</h4>
            <div class="table-wrap">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Cluster / Segmento</th>
                    <th>Clientes</th>
                    <th>% Base</th>
                    <th>Recencia Media</th>
                    <th>Frecuencia</th>
                    <th>Ticket / Monto</th>
                    <th>Acción Comercial</th>
                  </tr>
                </thead>
                <tbody>
                  ${clusterRows.length ? clusterRows.map(seg => `
                    <tr>
                      <td>
                        <strong>Cluster ${escapeHtml(seg.cluster)}</strong>
                        <div class="muted">${escapeHtml(seg.segment || '')}</div>
                      </td>
                      <td class="mono">${formatInt(Number(seg.cantidad_clientes) || 0)}</td>
                      <td class="mono">${formatPct(Number(seg.porcentaje) || 0)}</td>
                      <td class="mono">${fmtNumber(seg.recencia_promedio)} días</td>
                      <td class="mono">${fmtNumber(seg.frecuencia_promedio)} pedidos</td>
                      <td class="mono"><strong>${formatBRL(Number(seg.monto_promedio) || 0)}</strong></td>
                      <td style="font-size:0.76rem; color:var(--text-secondary);">${escapeHtml(seg.accion_sugerida)}</td>
                    </tr>
                  `).join('') : `<tr><td colspan="7">${modules.clustering?.mensaje || 'Sin perfiles reales disponibles. Ejecuta src/clustering.py.'}</td></tr>`}
                </tbody>
              </table>
            </div>
            <div class="method-note"><strong>DBSCAN (muestra fija)</strong>${dbscanEvaluation.length ? `<p>${formatInt(dbscanEvaluation[0].n_clusters_sin_ruido)} clusters, ${formatPct(Number(dbscanEvaluation[0].porcentaje_ruido) || 0)} de ruido; Silhouette: ${fmtNumber(dbscanEvaluation[0].silhouette_sin_ruido)}. Muestra: ${formatInt(dbscanEvaluation[0].n_muestra)}. Sin extrapolación.</p><div class="table-wrap"><table class="data-table"><thead><tr><th>Grupo DBSCAN</th><th>Compradores en muestra</th><th>Recencia media</th><th>Frecuencia media</th><th>Monto medio</th></tr></thead><tbody>${dbscanRows.map(row => `<tr><td>${escapeHtml(row.segmento)}</td><td>${formatInt(row.cantidad_clientes)}</td><td>${fmtNumber(row.recencia_promedio)}</td><td>${fmtNumber(row.frecuencia_promedio)}</td><td>${formatBRL(row.monto_promedio)}</td></tr>`).join('')}</tbody></table></div>` : '<p>DBSCAN aún no se ha ejecutado en esta versión. Ejecuta src/clustering.py para generar su evaluación muestral.</p>'}</div>
          </div>

          <div style="display:flex; flex-direction:column; gap:0.85rem; background:var(--bg-secondary); padding:1.1rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
            <h4 style="font-size:0.92rem;">Resumen</h4>
            <p style="font-size:0.8rem; color:var(--text-secondary);">Segmentación descriptiva de compradores con pedidos entregados.</p>
            <div class="bar-row">
              <div class="bar-row-label">
                <span>Compradores en los perfiles cargados</span>
                <span class="mono">${formatInt(clusterRows.reduce((sum, row) => sum + (Number(row.cantidad_clientes) || 0), 0))}</span>
              </div>
              <div class="bar-track"><div class="bar-fill" style="width:${clusterRows.length ? 100 : 0}%; background:var(--chart-primary);"></div></div>
            </div>
            <div class="bar-row">
              <div class="bar-row-label">
                <span>Silhouette del K seleccionado</span>
                <span class="mono">${fmtNumber(clusterEvaluation.find(row => row.seleccionado === 'True' || row.seleccionado === true)?.silhouette)}</span>
              </div>
              <div class="bar-track"><div class="bar-fill" style="width:${clusterEvaluation.length ? 100 : 0}%; background:var(--chart-secondary);"></div></div>
            </div>
            <div class="method-note" style="margin-top:auto;">
              <strong>Criterio:</strong>
              ${modules.clustering?.resultados?.clustering_metadata?.criterio_seleccion || 'RFM no debe interpretarse como churn; Olist no incluye una etiqueta de abandono.'}
            </div>
          </div>
        </div>
      `
          : ''
      }

      ${
        activeLabTab === 'association'
          ? `
        ${renderAssociationTab(association, state)}
      `
          : ''
      }

      ${
        activeLabTab === 'forecast'
          ? `
        <!-- TAB 3: evaluación cronológica con pronósticos exportados por Python -->
        <div style="display:flex; flex-direction:column; gap:1rem; margin-top:0.5rem;">
          <div class="method-note">Evaluación cronológica sobre el periodo de prueba; sin extrapolación.</div>
          ${temporalForecasts.length ? `<div class="svg-chart-container">${renderSeriesTestSVG(temporalForecasts)}</div>` : `<div class="method-note">${escapeHtml(modules.series?.mensaje || 'Ejecuta src/series_temporales.py para generar pronósticos reales.')}</div>`}
          <div class="table-wrap"><table class="data-table"><thead><tr><th>Modelo</th><th>Frecuencia</th><th>Train / test</th><th>MAE (BRL)</th><th>RMSE (BRL)</th><th>n test</th></tr></thead><tbody>
            ${temporalEvaluation.length ? temporalEvaluation.map(row => `<tr><td><strong>${escapeHtml(row.modelo)}</strong></td><td>${escapeHtml(row.frecuencia)}</td><td>${escapeHtml(row.train_inicio)}–${escapeHtml(row.train_fin)} / ${escapeHtml(row.test_inicio)}–${escapeHtml(row.test_fin)}</td><td>${formatBRL(row.mae_brl)}</td><td>${formatBRL(row.rmse_brl)}</td><td>${formatInt(row.n_test)}</td></tr>`).join('') : '<tr><td colspan="6">Sin métricas de series disponibles.</td></tr>'}
          </tbody></table></div>
        </div>
      `
          : ''
      }

      ${
        activeLabTab === 'logistics'
          ? `
        <div style="display:flex;flex-direction:column;gap:1rem;margin-top:.5rem">
          <div class="method-note">Predicción de días de entrega con partición cronológica.</div>
          <div class="grid-3">${regressionEvaluation.length ? regressionEvaluation.map(row => `<article class="card" style="padding:.9rem"><strong>${escapeHtml(row.modelo)}</strong><p>MAE: ${fmtNumber(row.mae_dias, 4)} días</p><p>RMSE: ${fmtNumber(row.rmse_dias, 4)} días</p><p>R²: ${fmtNumber(row.r2, 4)}</p><p class="muted">${formatInt(row.n_test)} pedidos de test</p></article>`).join('') : `<div class="method-note">${escapeHtml(modules.regresion?.mensaje || 'Sin evaluación real. Ejecuta src/regresion.py.')}</div>`}</div>
        </div>
      `
          : activeLabTab === 'logistics-preview-disabled'
          ? `
        <!-- TAB 4: REGRESIÓN LOGÍSTICA DE TIEMPOS DE ENTREGA & EXPLICABILIDAD SHAP (PN-07) -->
        <div class="grid-2" style="margin-top:0.5rem;">
          <!-- Simulador Interactivo What-If -->
          <div style="background:var(--bg-secondary); padding:1.15rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle); display:flex; flex-direction:column; gap:1rem;">
            <h4 style="font-size:0.94rem;">🚚 Simulador Predictivo de Tiempo de Entrega y SLA Logístico (PN-07)</h4>
            <p style="font-size:0.78rem; color:var(--text-secondary);">
              Ajusta los parámetros físicos y geográficos del pedido para estimar el tiempo de entrega y la probabilidad de superar la fecha prometida (tasa base Olist: 6,77%).
            </p>

            <div class="control-group">
              <label>
                <span>Distancia Vendedor ↔ Comprador (km):</span>
                <span class="mono">${formatInt(simDistanceKm)} km</span>
              </label>
              <input
                type="range"
                class="range-slider"
                min="50"
                max="3000"
                step="50"
                value="${simDistanceKm}"
                data-action="sim-distance"
              />
            </div>

            <div class="control-group">
              <label>
                <span>Peso del Producto (<code>product_weight_g</code>):</span>
                <span class="mono">${formatInt(simWeightGrams)} g</span>
              </label>
              <input
                type="range"
                class="range-slider"
                min="200"
                max="15000"
                step="200"
                value="${simWeightGrams}"
                data-action="sim-weight"
              />
            </div>

            <div style="display:flex; align-items:center; justify-content:space-between; padding:0.55rem 0.75rem; background:var(--bg-surface); border-radius:var(--radius-sm);">
              <span style="font-size:0.8rem; font-weight:600;">Ruta Interestatal (<code>seller_state ≠ customer_state</code>)</span>
              <button
                class="tab-pill ${simInterstate ? 'active' : ''}"
                data-action="toggle-sim-interstate"
              >
                ${simInterstate ? 'Sí (Interestatal)' : 'No (Mismo Estado)'}
              </button>
            </div>

            <div class="grid-3" style="margin-top:auto;">
              <div style="padding:0.8rem; background:var(--bg-surface); border-radius:var(--radius-sm); text-align:center;">
                <div style="font-size:0.72rem; color:var(--text-secondary);">Tiempo Estimado</div>
                <div class="mono" style="font-size:1.25rem; font-weight:800; color:var(--accent-primary);">
                  ${estimatedDays.toFixed(1)} días
                </div>
              </div>
              <div style="padding:0.8rem; background:var(--bg-surface); border-radius:var(--radius-sm); text-align:center;">
                <div style="font-size:0.72rem; color:var(--text-secondary);">Riesgo Entrega Tardía</div>
                <div class="mono" style="font-size:1.25rem; font-weight:800; color:${
                  lateRiskPct > 15 ? 'var(--accent-rose)' : 'var(--accent-emerald)'
                };">
                  ${lateRiskPct.toFixed(1)}%
                </div>
              </div>
              <div style="padding:0.8rem; background:var(--bg-surface); border-radius:var(--radius-sm); text-align:center;">
                <div style="font-size:0.72rem; color:var(--text-secondary);">Score Esperado (PN-08)</div>
                <div class="mono" style="font-size:1.25rem; font-weight:800; color:var(--accent-amber);">
                  ★ ${expectedReviewScore}
                </div>
              </div>
            </div>
          </div>

          <!-- Importancia Global de Variables SHAP -->
          <div style="background:var(--bg-secondary); padding:1.15rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle); display:flex; flex-direction:column; gap:0.85rem;">
            <h4 style="font-size:0.94rem;">🔍 Explicabilidad del Modelo: Importancia Global SHAP (Semana 16)</h4>
            <p style="font-size:0.78rem; color:var(--text-secondary);">
              Contribución media absoluta (<code>|SHAP value|</code>) sobre la predicción de días de entrega.
            </p>

            ${shapImportance
              .map(item => {
                const widthPct = (item.shapValue / 0.38) * 100;
                return `
                <div class="bar-row">
                  <div class="bar-row-label">
                    <span class="mono" style="font-size:0.77rem;"><strong>${item.feature}</strong></span>
                    <span class="mono" style="color:var(--accent-cyan);">SHAP: ${item.shapValue.toFixed(2)}</span>
                  </div>
                  <div class="bar-track">
                    <div class="bar-fill" style="width:${widthPct.toFixed(1)}%; background:var(--chart-primary);"></div>
                  </div>
                  <div style="font-size:0.73rem; color:var(--text-muted);">${item.impact}</div>
                </div>
              `;
              })
              .join('')}
          </div>
        </div>
      `
          : ''
      }

      ${
        activeLabTab === 'explainability'
          ? `
        <div style="display:flex;flex-direction:column;gap:1rem;margin-top:.5rem">
          <div class="method-note">Regresión logística TF-IDF sobre etiquetas proxy de review_score. Coeficientes y contribuciones en escala logit; no se calcula SHAP.</div>
          ${globalExplanations.length ? `<section class="card"><h4>Importancia global por clase</h4><div class="grid-3">${explanationClasses.map(clase => `<div><strong>${escapeHtml(clase)}</strong><div class="table-wrap"><table class="data-table"><thead><tr><th>Término</th><th>Coef.</th><th>Dirección</th></tr></thead><tbody>${globalExplanations.filter(row => row.clase === clase).slice(0, 10).map(row => `<tr><td>${escapeHtml(row.termino)}</td><td class="mono">${fmtNumber(row.coeficiente_logit, 4)}</td><td>${escapeHtml(row.direccion)}</td></tr>`).join('')}</tbody></table></div></div>`).join('')}</div></section>` : `<div class="method-note">${escapeHtml(modules.explicabilidad?.mensaje || 'Sin coeficientes globales. Ejecuta clasificación y luego explicabilidad.')}</div>`}
          ${explainedReviewIds.length ? `<section class="card"><h4>Explicaciones locales de predicciones reales del test</h4><p class="muted">Se muestran términos con contribución positiva y negativa al logit de la clase predicha; el comentario original no se expone.</p><div class="grid-3">${explainedReviewIds.map(id => { const rows = localExplanations.filter(row => row.review_id === id); const first = rows[0] || {}; return `<article class="card" style="padding:.8rem"><strong>Reseña ${escapeHtml(String(id).slice(0, 8))}</strong><p>Real: ${escapeHtml(first.clase_real)} · Predicha: ${escapeHtml(first.clase_predicha)} · Probabilidad: ${formatPct(100 * Number(first.probabilidad_predicha || 0))}</p><div class="table-wrap"><table class="data-table"><thead><tr><th>Token</th><th>Contribución logit</th><th>Dirección</th></tr></thead><tbody>${rows.map(row => `<tr><td>${escapeHtml(row.termino)}</td><td class="mono">${fmtNumber(row.contribucion_logit, 4)}</td><td>${escapeHtml(row.direccion)}</td></tr>`).join('')}</tbody></table></div></article>`; }).join('')}</div></section>` : ''}
        </div>
      `
          : ''
      }

      ${
        activeLabTab === 'nlp'
          ? `
        <div style="display:flex;flex-direction:column;gap:1rem;margin-top:.5rem">
          <div class="method-note">Etiquetas derivadas de review_score, separadas de la polaridad calculada desde el texto.</div>
          <div class="grid-2">
            <article class="card" style="padding:1rem">
              <h4>Clasificación de reseñas</h4>
              <p class="chip ${modules.clasificacion?.status === 'ok' ? 'chip-emerald' : 'chip-amber'}">${modules.clasificacion?.status === 'ok' ? 'Evaluación real disponible' : 'Pendiente de implementación'}</p>
              <p>Etiquetas de referencia derivadas de review_score; no son anotaciones humanas independientes.</p>
              <div class="table-wrap">
                <table class="data-table" aria-label="Evaluación de clasificación de reseñas">
                  <thead><tr><th scope="col">Métrica</th><th scope="col">Valor</th></tr></thead>
                  <tbody>
                    ${classificationEvaluation.length ? `
                      <tr><td>Accuracy</td><td class="mono">${formatPct(100 * Number(classificationEvaluation[0].accuracy || 0))}</td></tr>
                      <tr><td>Precisión macro</td><td class="mono">${formatPct(100 * Number(classificationEvaluation[0].precision_macro || 0))}</td></tr>
                      <tr><td>Recall macro</td><td class="mono">${formatPct(100 * Number(classificationEvaluation[0].recall_macro || 0))}</td></tr>
                      <tr><td>F1 macro</td><td class="mono">${formatPct(100 * Number(classificationEvaluation[0].f1_macro || 0))}</td></tr>
                      <tr><td>ROC-AUC OVR</td><td class="mono">${fmtNumber(classificationEvaluation[0].roc_auc_ovr_macro)}</td></tr>
                      <tr><td>PR-AUC macro</td><td class="mono">${fmtNumber(classificationEvaluation[0].pr_auc_macro_ovr)}</td></tr>
                      <tr><td>Reseñas de entrenamiento</td><td class="mono">${formatInt(classificationEvaluation[0].n_train)}</td></tr>
                      <tr><td>Reseñas de prueba</td><td class="mono">${formatInt(classificationEvaluation[0].n_test)}</td></tr>
                      <tr><td>Fecha de corte cronológico</td><td class="mono">${escapeHtml(classificationMetadata.fecha_corte_test || classificationEvaluation[0].fecha_corte_test || '—')}</td></tr>
                      <tr><td>Matriz de confusión [negativo, neutral, positivo]</td><td class="mono">${escapeHtml(classificationEvaluation[0].matriz_confusion_json || '—')}</td></tr>
                    ` : `<tr><td colspan="2">${escapeHtml(modules.clasificacion?.mensaje || 'Sin evaluación de clasificación generada.')}</td></tr>`}
                  </tbody>
                </table>
              </div>
            </article>
            <article class="card" style="padding:1rem">
              <h4>Análisis de sentimiento desde texto</h4>
              <p class="chip ${modules.nlp?.status === 'ok' ? 'chip-emerald' : 'chip-amber'}">${modules.nlp?.status === 'ok' ? 'Resultados descriptivos disponibles' : 'Pendiente de implementación'}</p>
              <p>${escapeHtml(modules.nlp?.mensaje || 'La polaridad léxica procede del comentario; las etiquetas derivadas de puntuación se informan por separado.')}</p>
              ${nlpSentiments.length ? `<div class="table-wrap"><table class="data-table"><thead><tr><th>Origen de etiqueta</th><th>Clase</th><th>Reseñas</th><th>%</th></tr></thead><tbody>${nlpSentiments.map(row => `<tr><td>${escapeHtml(row.origen_etiqueta)}</td><td>${escapeHtml(row.clase)}</td><td>${formatInt(row.cantidad)}</td><td>${fmtNumber(row.porcentaje)}%</td></tr>`).join('')}</tbody></table></div>` : ''}
            </article>
          </div>
          ${nlpTerms.length ? `
            <div class="card">
              <h4>Términos TF-IDF por clase de puntuación (no son tópicos modelados)</h4>
              <div class="grid-3">
                ${['negativo_score', 'neutral_score', 'positivo_score'].map(clase => `
                  <div style="display:flex;flex-direction:column;gap:.5rem">
                    <strong>${clase.replace('_score', '')}</strong>
                    <div class="table-wrap">
                      <table class="data-table" aria-label="Términos TF-IDF: ${clase.replace('_score', '')}">
                        <thead><tr><th scope="col">Término</th><th scope="col">TF-IDF medio</th></tr></thead>
                        <tbody>
                          ${nlpTerms.filter(row => row.referencia_sentimiento_score === clase).slice(0, 10).map(row => `
                            <tr><td>${escapeHtml(row.termino)}</td><td class="mono">${fmtNumber(row.tfidf_medio, 4)}</td></tr>
                          `).join('') || '<tr><td colspan="2">Sin términos disponibles.</td></tr>'}
                        </tbody>
                      </table>
                    </div>
                  </div>
                `).join('')}
              </div>
            </div>
          ` : ''}
        </div>
      `
          : activeLabTab === 'nlp-preview-disabled'
          ? `
        <!-- TAB 5: CLASIFICACIÓN DE VALORACIONES & MINERÍA DE TEXTOS NLP (PN-08 & PN-10) -->
        <div style="display:flex; flex-direction:column; gap:1rem; margin-top:0.5rem;">
          <div class="method-note">
            <strong>Universo Textual (Sección 9 y PN-10):</strong>
            De las 99.224 reseñas en <code>olist_order_reviews_dataset.csv</code> (calificación promedio <strong>4,09 / 5</strong>),
            exactamente <strong>40.977 opiniones contienen comentario textual</strong> (<code>review_comment_message</code> no nulo)
            para el modelado de tópicos y análisis de sentimiento en portugués.
          </div>

          <div class="grid-2">
            ${nlpTopics
              .map(
                t => `
              <div style="padding:1.1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border:1px solid var(--border-subtle); display:flex; flex-direction:column; gap:0.6rem;">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                  <strong>${t.topicId}: ${t.name}</strong>
                  <span class="chip ${t.sentiment === 'Positivo' ? 'chip-emerald' : 'chip-rose'}">
                    ${t.sentiment} • ★ ${t.avgScore} (${t.sharePct}%)
                  </span>
                </div>
                <div style="display:flex; gap:0.4rem; flex-wrap:wrap;">
                  ${t.keywords
                    .map(kw => `<span class="chip mono" style="font-size:0.71rem;">${kw}</span>`)
                    .join('')}
                </div>
                <blockquote style="font-size:0.79rem; font-style:italic; color:var(--text-secondary); border-left:2px solid var(--accent-primary); padding-left:0.65rem; margin-top:0.2rem;">
                  ${t.sampleQuote}
                </blockquote>
              </div>
            `
              )
              .join('')}
          </div>
        </div>
      `
          : ''
      }

      ${
        activeLabTab === 'monitoring'
          ? `
        <div style="display:flex;flex-direction:column;gap:1rem;margin-top:.5rem">
          <div class="method-note">Comparación histórica de train/test; no es monitoreo en vivo. PSI orienta revisión.</div>
          <div class="grid-2"><div class="table-wrap"><h4>Historial de métricas</h4><table class="data-table"><thead><tr><th>Modelo</th><th>Métrica</th><th>Valor</th><th>n</th></tr></thead><tbody>${monitoringMetrics.slice(-12).map(row => `<tr><td>${escapeHtml(row.modelo)}</td><td>${escapeHtml(row.metrica)}</td><td>${fmtNumber(row.valor, 4)}</td><td>${formatInt(row.n_evaluacion)}</td></tr>`).join('') || '<tr><td colspan="4">Sin métricas registradas.</td></tr>'}</tbody></table></div><div class="table-wrap"><h4>Drift de train a test</h4><table class="data-table"><thead><tr><th>Variable</th><th>PSI</th><th>Estado</th></tr></thead><tbody>${driftRows.map(row => `<tr><td>${escapeHtml(row.variable)}</td><td>${fmtNumber(row.psi, 4)}</td><td>${escapeHtml(row.estado)}</td></tr>`).join('') || '<tr><td colspan="3">Sin reporte de drift.</td></tr>'}</tbody></table></div></div>
          <p class="muted">Criterio registrado: ${escapeHtml(modelRegistry.criterio_revision || 'Consultar documentación del módulo.')}</p>
        </div>
      `
          : ''
      }

      ${
        activeLabTab === 'graphs'
          ? `
        <div class="grid-asymmetric" style="margin-top:.5rem">
          <div class="card"><h4>Red bipartita real vendedor–producto</h4><p class="muted">${escapeHtml(subgraph?.criterio_seleccion || 'Subgrafo real generado por el análisis de grafos.')}</p><div class="svg-chart-container">${renderOlistSubgraphSVG(subgraph, selectedGraphNode)}</div></div>
          <div class="card" style="padding:1rem">
            <h4>Resumen de la red completa</h4>
            <div class="table-wrap">
              <table class="data-table" aria-label="Resumen de la red completa">
                <thead><tr><th scope="col">Indicador</th><th scope="col">Total</th></tr></thead>
                <tbody>
                  <tr><td>Nodos</td><td class="mono">${formatInt(graphMetadata.nodos ?? graphMetadata.total_nodos)}</td></tr>
                  <tr><td>Aristas</td><td class="mono">${formatInt(graphMetadata.aristas ?? graphMetadata.total_aristas)}</td></tr>
                  <tr><td>Vendedores</td><td class="mono">${formatInt(graphMetadata.vendedores ?? graphMetadata.total_vendedores)}</td></tr>
                  <tr><td>Productos</td><td class="mono">${formatInt(graphMetadata.productos ?? graphMetadata.total_productos)}</td></tr>
                  <tr><td>Componentes</td><td class="mono">${formatInt(graphMetadata.componentes ?? graphMetadata.componentes_conexas)}</td></tr>
                </tbody>
              </table>
            </div>
            <p class="muted">Vista acotada; métricas de la red completa.</p>
            ${modules.grafos?.status !== 'ok' ? `<p>${escapeHtml(modules.grafos?.mensaje || 'No se encontraron archivos del grafo.')}</p>` : ''}
          </div>
        </div>
      `
          : activeLabTab === 'graphs-preview-disabled'
          ? `
        <!-- TAB 6: GRAFOS DE RELACIONES CLIENTES - PRODUCTOS - VENDEDORES (PN-09) -->
        <div class="grid-asymmetric" style="margin-top:0.5rem;">
          <div style="background:var(--bg-secondary); padding:1rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
              <strong style="font-size:0.88rem;">Topología NetworkX: Nodos Regionales y Categorías Líderes</strong>
              <span class="chip chip-blue">Nodo Activo: ${selectedGraphNode}</span>
            </div>
            ${renderEntityNetworkSVG(selectedGraphNode)}
            <div class="chart-legend" aria-label="Leyenda del grafo">
              <span>○ Región</span><span>◇ Polo vendedor</span><span>□ Categoría</span>
              <span>Contorno doble: nodo seleccionado</span>
            </div>
          </div>

          <div style="background:var(--bg-secondary); padding:1.1rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle); display:flex; flex-direction:column; gap:0.8rem;">
            <h4 style="font-size:0.92rem;">Métricas de Centralidad de Red (PN-09)</h4>
            <p style="font-size:0.79rem; color:var(--text-secondary);">
              Haz clic en cualquier nodo del grafo o usa los botones inferiores para inspeccionar su rol estructural entre los
              <strong>3.095 vendedores</strong> (23 estados) y <strong>96.096 clientes</strong> (27 estados).
            </p>
            <div class="tabs-bar">
              ${['SP', 'RJ', 'MG', 'PR', 'RS', 'CAT_BS', 'CAT_CM']
                .map(
                  nid => `
                <button
                  class="tab-pill ${selectedGraphNode === nid ? 'active' : ''}"
                  data-action="select-graph-node"
                  data-node="${nid}"
                >
                  ${nid}
                </button>
              `
                )
                .join('')}
            </div>
            <div style="padding:0.85rem; background:var(--bg-surface); border-radius:var(--radius-sm); font-size:0.8rem; color:var(--text-secondary);">
              <p><strong>Centralidad de Grado (São Paulo - SP):</strong> 0,84 (Mayor emisor logístico de Brasil).</p>
              <p style="margin-top:0.35rem;"><strong>Comunidad Textil Detectada:</strong> El municipio de Ibitinga (SP) concentra el clúster más denso de vendedores de <em>Cama, mesa y baño</em>.</p>
            </div>
          </div>
        </div>
      `
          : ''
      }
    </section>
  `;
}
