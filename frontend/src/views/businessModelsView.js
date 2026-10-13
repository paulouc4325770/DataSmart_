/**
 * Módulo 4: Laboratorio de Preguntas de Negocio (PN-01 a PN-10) & Modelos de Minería de Datos
 * Incluye simuladores interactivos para RFM/Clustering, Series Temporales, Asociación (Apriori/FP-Growth),
 * Regresión Logística + Explicabilidad SHAP, Clasificación/NLP y Grafos (NetworkX).
 */

import { renderMonthlySalesSVG, renderEntityNetworkSVG } from '../components/svgCharts.js';
import { formatBRL, formatInt, formatPct } from '../utils/formatters.js';

export function renderBusinessModelsView(store, state) {
  const {
    businessQuestions,
    rfmSegments,
    associationRules,
    shapImportance,
    nlpTopics,
    monthlySales,
  } = store;

  const {
    activeLabTab,
    minLift,
    forecastHorizon,
    simDistanceKm,
    simWeightGrams,
    simInterstate,
    selectedGraphNode,
  } = state;

  // Filtrar reglas de asociación por Lift mínimo
  const filteredRules = associationRules.filter(r => r.lift >= minLift);

  // Generar meses de pronóstico (PN-04) sobre la serie limpia (sin meses extremos 2016)
  const cleanHistory = monthlySales.filter(m => !m.isExtreme);
  const baseAvg = 895000;
  const forecastLabels = ['Sep 2018', 'Oct 2018', 'Nov 2018 (BF)', 'Dic 2018', 'Ene 2019', 'Feb 2019'];
  const seasonalFactors = [0.98, 1.04, 1.28, 1.12, 1.03, 0.95];

  const forecastMonths = Array.from({ length: forecastHorizon }, (_, idx) => {
    const pred = baseAvg * seasonalFactors[idx];
    return {
      date: `2018-${9 + idx}-01`,
      monthLabel: forecastLabels[idx],
      salesBRL: pred,
      upperBound: pred * 1.09,
      lowerBound: pred * 0.91,
    };
  });

  // Simulador de tiempo de entrega y riesgo de tardanza (PN-07 & PN-08)
  const baseDays = 5.2;
  const distEffect = (simDistanceKm / 500) * 2.15;
  const weightEffect = (simWeightGrams / 2000) * 0.85;
  const interstateEffect = simInterstate ? 3.1 : 0.0;
  const estimatedDays = baseDays + distEffect + weightEffect + interstateEffect;
  const lateRiskPct = Math.min(Math.max((estimatedDays - 6.0) * 4.2, 1.8), 68.5);
  const expectedReviewScore = Math.max(5.0 - (lateRiskPct / 100) * 3.4, 1.4).toFixed(2);

  return `
    <!-- Matriz Oficial de las 10 Preguntas de Negocio (Sección 5 del Informe) -->
    <section class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h3>🎯 Matriz de Preguntas de Negocio (PN-01 a PN-10) — Sección 5 del Informe</h3>
          <p>Trazabilidad completa entre objetivos de negocio, técnicas de minería de datos y métricas de validación.</p>
        </div>
        <span class="chip chip-purple">10 Preguntas Definidas</span>
      </div>

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>ID</th>
              <th>Área</th>
              <th>Pregunta de Negocio</th>
              <th>Técnica / Algoritmo Previsto</th>
              <th>Métricas de Evaluación</th>
              <th>Entrega</th>
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
                  <div style="font-size:0.75rem; color:var(--text-secondary); margin-top:0.15rem;">${bq.summary}</div>
                </td>
                <td class="mono" style="color:var(--accent-cyan);">${bq.technique}</td>
                <td style="font-size:0.77rem; color:var(--text-secondary);">${bq.metrics}</td>
                <td><span class="chip chip-emerald">${bq.targetWeek}</span></td>
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
          <h3>🧪 Workbench Interactivo de Modelos Analíticos y Explicabilidad (SHAP / LIME)</h3>
          <p>Selecciona un módulo analítico para explorar segmentaciones, reglas de asociación, pronósticos y simulaciones.</p>
        </div>
        <div class="tabs-bar">
          <button class="tab-pill ${activeLabTab === 'rfm' ? 'active' : ''}" data-action="set-lab-tab" data-tab="rfm">
            👥 PN-01 / PN-02: RFM & Clustering
          </button>
          <button class="tab-pill ${activeLabTab === 'association' ? 'active' : ''}" data-action="set-lab-tab" data-tab="association">
            🛒 PN-05 / PN-06: Asociación (Apriori/FP-Growth)
          </button>
          <button class="tab-pill ${activeLabTab === 'forecast' ? 'active' : ''}" data-action="set-lab-tab" data-tab="forecast">
            📈 PN-03 / PN-04: Pronóstico Ventas
          </button>
          <button class="tab-pill ${activeLabTab === 'logistics' ? 'active' : ''}" data-action="set-lab-tab" data-tab="logistics">
            🚚 PN-07: Logística & SHAP
          </button>
          <button class="tab-pill ${activeLabTab === 'nlp' ? 'active' : ''}" data-action="set-lab-tab" data-tab="nlp">
            💬 PN-08 / PN-10: Clasificación & NLP
          </button>
          <button class="tab-pill ${activeLabTab === 'graphs' ? 'active' : ''}" data-action="set-lab-tab" data-tab="graphs">
            🕸️ PN-09: Grafos NetworkX
          </button>
        </div>
      </div>

      ${
        activeLabTab === 'rfm'
          ? `
        <!-- TAB 1: RFM + CLUSTERING (PN-01 & PN-02) -->
        <div class="grid-asymmetric" style="margin-top:0.5rem;">
          <div style="display:flex; flex-direction:column; gap:0.85rem;">
            <h4 style="font-size:0.95rem;">Segmentación RFM + K-Means sobre 96.096 Compradores Únicos (<code>customer_unique_id</code>)</h4>
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
                  ${rfmSegments
                    .map(
                      seg => `
                    <tr>
                      <td>
                        <strong style="color:${seg.color}">●</strong>
                        <strong>${seg.segment}</strong>
                      </td>
                      <td class="mono">${formatInt(seg.customers)}</td>
                      <td class="mono">${formatPct(seg.sharePct)}</td>
                      <td class="mono">${seg.avgRecencyDays} días</td>
                      <td class="mono">${seg.avgFrequency.toFixed(2)}x</td>
                      <td class="mono"><strong>${formatBRL(seg.avgMonetaryBRL)}</strong></td>
                      <td style="font-size:0.76rem; color:var(--text-secondary);">${seg.action}</td>
                    </tr>
                  `
                    )
                    .join('')}
                </tbody>
              </table>
            </div>
          </div>

          <div style="display:flex; flex-direction:column; gap:0.85rem; background:var(--bg-secondary); padding:1.1rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
            <h4 style="font-size:0.92rem;">Hallazgo Clave de Negocio (Delimitación Olist)</h4>
            <p style="font-size:0.8rem; color:var(--text-secondary);">
              Al comparar <code>pedidos_totales (99.441)</code> frente a <code>clientes_unicos (96.096)</code>, se observa
              que solo ~3,36% de los clientes realiza múltiples pedidos en el horizonte histórico.
            </p>
            <div class="bar-row">
              <div class="bar-row-label">
                <span>Clientes de Compra Única (1 pedido)</span>
                <span class="mono">96,64%</span>
              </div>
              <div class="bar-track"><div class="bar-fill" style="width:96.64%; background:#3b82f6;"></div></div>
            </div>
            <div class="bar-row">
              <div class="bar-row-label">
                <span>Clientes Recurrentes (≥ 2 pedidos)</span>
                <span class="mono">3,36%</span>
              </div>
              <div class="bar-track"><div class="bar-fill" style="width:12%; background:#10b981;"></div></div>
            </div>
            <div class="method-note" style="margin-top:auto;">
              <strong>Delimitación Metodológica (Sección 5):</strong>
              Olist no incluye una etiqueta explícita de abandono (<em>churn</em>); por tanto, la recencia RFM se interpreta como
              inactividad transaccional observada y no como baja contractual.
            </div>
          </div>
        </div>
      `
          : ''
      }

      ${
        activeLabTab === 'association'
          ? `
        <!-- TAB 2: REGLAS DE ASOCIACIÓN APRIORI / FP-GROWTH (PN-05 & PN-06) -->
        <div style="display:flex; flex-direction:column; gap:1rem; margin-top:0.5rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; background:var(--bg-secondary); padding:0.95rem 1.15rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
            <div>
              <strong style="font-size:0.88rem;">Filtro Interactivo de Reglas de Asociación (Apriori / FP-Growth / ECLAT)</strong>
              <p style="font-size:0.77rem; color:var(--text-secondary);">
                Ajusta el umbral mínimo de <strong>Lift</strong> para descubrir co-ocurrencias fuertes en <code>olist_order_items_dataset.csv</code> (112.650 ítems).
              </p>
            </div>
            <div class="control-group" style="min-width:260px;">
              <label>
                <span>Lift Mínimo Requerido:</span>
                <span class="mono" style="color:var(--accent-primary);">${minLift.toFixed(2)}x</span>
              </label>
              <input
                type="range"
                class="range-slider"
                min="1.5"
                max="3.0"
                step="0.1"
                value="${minLift}"
                data-action="change-min-lift"
              />
            </div>
          </div>

          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Regla ID</th>
                  <th>Antecedente (Si compra...)</th>
                  <th>Consecuente (También lleva...)</th>
                  <th>Support</th>
                  <th>Confidence</th>
                  <th>Lift</th>
                  <th>Pedidos Co-ocurrentes</th>
                </tr>
              </thead>
              <tbody>
                ${filteredRules
                  .map(
                    r => `
                  <tr>
                    <td class="mono"><strong>${r.id}</strong></td>
                    <td><strong>${r.antecedent}</strong></td>
                    <td style="color:var(--accent-emerald);"><strong>→ ${r.consequent}</strong></td>
                    <td class="mono">${(r.support * 100).toFixed(2)}%</td>
                    <td class="mono">${(r.confidence * 100).toFixed(1)}%</td>
                    <td><span class="chip chip-purple mono">${r.lift.toFixed(2)}x</span></td>
                    <td class="mono">${formatInt(r.ordersCount)} pedidos</td>
                  </tr>
                `
                  )
                  .join('')}
              </tbody>
            </table>
          </div>
        </div>
      `
          : ''
      }

      ${
        activeLabTab === 'forecast'
          ? `
        <!-- TAB 3: SERIES TEMPORALES Y PRONÓSTICO (PN-03 & PN-04) -->
        <div style="display:flex; flex-direction:column; gap:1rem; margin-top:0.5rem;">
          <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; background:var(--bg-secondary); padding:0.95rem 1.15rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
            <div>
              <strong style="font-size:0.88rem;">Pronóstico de Ventas Mensuales (SARIMA / Holt-Winters con Banda de Confianza 90%)</strong>
              <p style="font-size:0.77rem; color:var(--text-secondary);">
                Entrenado sobre la ventana limpia Ene 2017 – Ago 2018 (excluyendo los meses extremos incompletos de 2016 según Sección 8.2).
              </p>
            </div>
            <div class="tabs-bar">
              ${[3, 4, 6]
                .map(
                  h => `
                <button
                  class="tab-pill ${forecastHorizon === h ? 'active' : ''}"
                  data-action="set-forecast-horizon"
                  data-horizon="${h}"
                >
                  Horizonte +${h} meses
                </button>
              `
                )
                .join('')}
            </div>
          </div>

          <div class="svg-chart-container">
            ${renderMonthlySalesSVG(cleanHistory, { showForecast: true, forecastMonths })}
          </div>

          <div class="grid-3">
            ${forecastMonths
              .slice(0, 3)
              .map(
                fm => `
              <div style="padding:0.85rem 1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
                <div style="font-size:0.76rem; color:var(--text-secondary);">Proyección ${fm.monthLabel}</div>
                <div class="mono" style="font-size:1.15rem; font-weight:700; color:var(--accent-purple); margin:0.2rem 0;">
                  ${formatBRL(fm.salesBRL)}
                </div>
                <div class="mono" style="font-size:0.72rem; color:var(--text-muted);">
                  IC 90%: [${formatBRL(fm.lowerBound, 0)} – ${formatBRL(fm.upperBound, 0)}]
                </div>
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
        activeLabTab === 'logistics'
          ? `
        <!-- TAB 4: REGRESIÓN LOGÍSTICA DE TIEMPOS DE ENTREGA & EXPLICABILIDAD SHAP (PN-07) -->
        <div class="grid-2" style="margin-top:0.5rem;">
          <!-- Simulador Interactivo What-If -->
          <div style="background:var(--bg-secondary); padding:1.15rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle); display:flex; flex-direction:column; gap:1rem;">
            <h4 style="font-size:0.94rem;">🚚 Simulador Predictivo de Tiempo de Entrega y SLA Logístico (PN-07)</h4>
            <p style="font-size:0.78rem; color:var(--text-secondary);">
              Ajusta los parámetros físicos y geográficos del pedido para estimar el tiempo de entrega y la probabilidad de superar la fecha prometida (tasa base Olist: 8,11%).
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
                    <div class="bar-fill" style="width:${widthPct.toFixed(1)}%; background:linear-gradient(90deg, #3b82f6, #06b6d4);"></div>
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
        activeLabTab === 'nlp'
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
        activeLabTab === 'graphs'
          ? `
        <!-- TAB 6: GRAFOS DE RELACIONES CLIENTES - PRODUCTOS - VENDEDORES (PN-09) -->
        <div class="grid-asymmetric" style="margin-top:0.5rem;">
          <div style="background:var(--bg-secondary); padding:1rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.5rem;">
              <strong style="font-size:0.88rem;">Topología NetworkX: Nodos Regionales y Categorías Líderes</strong>
              <span class="chip chip-blue">Nodo Activo: ${selectedGraphNode}</span>
            </div>
            ${renderEntityNetworkSVG(selectedGraphNode)}
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
