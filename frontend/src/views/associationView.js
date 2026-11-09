/**
 * Pestaña PN-05: reglas de asociación reales (Apriori y FP-Growth).
 * Muestra solo lo calculado por `src/asociacion.py`; cada regla declara su población
 * de referencia y se puede rastrear hasta los pedidos que la sustentan.
 */

import { formatInt } from '../utils/formatters.js';
import { categorySetLabel } from '../data/categoryNames.js';

const MAX_PEDIDOS_VISIBLES = 12;
const SEPARADOR = ' + ';

const esc = valor =>
  String(valor ?? '').replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[c]);

const pct = (valor, decimales = 2) => (valor === null || valor === undefined ? '—' : `${(valor * 100).toFixed(decimales)}%`);

export function formatPValue(p) {
  if (p === null || p === undefined) return '—';
  return p < 0.001 ? p.toExponential(1) : p.toFixed(4);
}

export function pairKey(regla) {
  return [...regla.antecedente.split(SEPARADOR), ...regla.consecuente.split(SEPARADOR)].sort().join('|');
}

/** Umbral de Bonferroni: 0,05 dividido por el número de conjuntos de categorías evaluados. */
export function bonferroniThreshold(reglas) {
  const conjuntos = new Set(reglas.map(pairKey)).size;
  return { conjuntos, umbral: conjuntos ? 0.05 / conjuntos : 0.05 };
}

function renderEmptyState(association) {
  const comandos = (association && association.comandos) || [];
  const faltantes = (association && association.faltantes) || [];
  return `
    <div style="margin-top:0.5rem; padding:1.1rem 1.25rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-amber);">
      <strong>Aún no hay resultados de asociación para mostrar.</strong>
      <p style="font-size:0.8rem; color:var(--text-secondary); margin:0.4rem 0;">
        ${esc((association && association.mensaje) || 'No se encontraron los archivos de resultados.')}
        ${faltantes.length ? `Faltan: <span class="mono">${faltantes.map(esc).join(', ')}</span>.` : ''}
      </p>
      <p style="font-size:0.8rem; color:var(--text-secondary); margin:0.4rem 0;">Para generarlos, ejecuta desde la raíz del proyecto:</p>
      ${comandos.map(c => `<div class="mono" style="font-size:0.8rem;">${esc(c)}</div>`).join('')}
    </div>`;
}

function composicionDe(association, concepto) {
  return (association.composicion || []).find(f => f.concepto === concepto) || null;
}

function renderComposition(association) {
  const total = composicionDe(association, 'pedidos_entregados');
  const universo = composicionDe(association, 'universo_total');
  const unitarias = composicionDe(association, 'unitarias_una_categoria');
  const multi = composicionDe(association, 'multicategoria_dos_o_mas');
  const sinCategoria = composicionDe(association, 'sin_categoria_conocida');
  const vacias = composicionDe(association, 'vacias_sin_items');
  if (!total || !universo) return '';
  const tarjeta = (titulo, valor, detalle) => `
    <div style="flex:1; min-width:170px; padding:0.7rem 0.9rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
      <div style="font-size:0.72rem; color:var(--text-secondary);">${titulo}</div>
      <div class="mono" style="font-size:1.05rem; font-weight:600;">${formatInt(valor)}</div>
      <div style="font-size:0.72rem; color:var(--text-muted);">${detalle}</div>
    </div>`;
  return `
    <div>
      <strong style="font-size:0.84rem;">Composición de las cestas (pedidos entregados)</strong>
      <div style="display:flex; gap:0.6rem; flex-wrap:wrap; margin-top:0.5rem;">
        ${tarjeta('Pedidos entregados', total.pedidos, 'Total de referencia')}
        ${tarjeta('Universo de análisis', universo.pedidos, 'Entregados con categoría conocida')}
        ${unitarias ? tarjeta('Unitarias', unitarias.pedidos, `${(unitarias.pctUniverso ?? 0).toFixed(2)}% del universo (1 categoría)`) : ''}
        ${multi ? tarjeta('Multicategoría', multi.pedidos, `${(multi.pctUniverso ?? 0).toFixed(2)}% del universo (2 o más)`) : ''}
        ${sinCategoria ? tarjeta('Fuera: solo categoría desconocida', sinCategoria.pedidos, 'No forman cesta de categorías conocidas') : ''}
        ${vacias ? tarjeta('Fuera: sin ítems', vacias.pedidos, 'Entregados sin ítems') : ''}
      </div>
    </div>`;
}

function renderPopulationBox(association, poblacion) {
  const p = poblacion.parametros || {};
  const verificacion = poblacion.verificacion || {};
  const total = poblacion.reglas.length;
  const verificadas = total - (verificacion.reglasInconsistentes || []).length;
  const chipTraza = verificacion.trazabilidadCompleta
    ? `<span class="chip chip-emerald">Trazabilidad verificada: ${verificadas}/${total} reglas</span>`
    : `<span class="chip chip-rose">Trazabilidad incompleta: ${esc((verificacion.reglasInconsistentes || []).join(', '))}</span>`;
  const chipAlgoritmos = poblacion.algoritmosCoinciden
    ? '<span class="chip chip-emerald">Apriori y FP-Growth coinciden</span>'
    : '<span class="chip chip-rose">Apriori y FP-Growth no coinciden</span>';
  return `
    <div style="padding:0.85rem 1.05rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-primary);">
      <div style="font-size:0.72rem; color:var(--text-secondary);">POBLACIÓN DE REFERENCIA</div>
      <div style="font-size:0.84rem; margin:0.15rem 0 0.45rem;"><strong>${esc(poblacion.poblacionReferencia)}</strong></div>
      <div style="font-size:0.77rem; color:var(--text-secondary);">
        Umbral: al menos <span class="mono">${formatInt(p.min_pedidos)}</span> pedidos
        (soporte <span class="mono">${p.min_soporte !== undefined ? (p.min_soporte * 100).toFixed(4) : '—'}%</span>) ·
        confianza mínima <span class="mono">${p.min_confianza ?? '—'}</span> ·
        longitud máxima <span class="mono">${p.max_len ?? '—'}</span> categorías ·
        ${formatInt(poblacion.paresObservados)} pares observados.
      </div>
      <div style="display:flex; gap:0.5rem; flex-wrap:wrap; margin-top:0.5rem;">${chipTraza}${chipAlgoritmos}</div>
    </div>`;
}

function renderRuleDetail(poblacion, regla) {
  const pedidos = poblacion.trazabilidad[regla.id] || [];
  const visibles = pedidos.slice(0, MAX_PEDIDOS_VISIBLES);
  const restantes = pedidos.length - visibles.length;
  const ant = categorySetLabel(regla.antecedente);
  const cons = categorySetLabel(regla.consecuente);
  const coincide = pedidos.length === regla.nPedidos;
  return `
    <div style="padding:0.95rem 1.1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border:1px solid var(--accent-primary);">
      <strong>${esc(regla.id)}: ${esc(ant)} → ${esc(cons)}</strong>
      <p style="font-size:0.8rem; color:var(--text-secondary); margin:0.45rem 0;">
        Entre los <strong>${formatInt(regla.totalCestas)}</strong> pedidos de la población de referencia,
        <strong>${formatInt(regla.nPedidosAntecedente)}</strong> incluyen «${esc(ant)}». De ellos,
        <strong>${formatInt(regla.nPedidos)}</strong> incluyen también «${esc(cons)}» (confianza ${pct(regla.confianza, 1)}).
        «${esc(cons)}» aparece en ${pct(regla.soporteConsecuente, 2)} de los pedidos de la población (lift ${regla.lift.toFixed(2)}x).
        Probabilidad de observar al menos ${formatInt(regla.nPedidos)} pedidos por azar, bajo independencia:
        <span class="mono">p = ${formatPValue(regla.pValor)}</span>.
      </p>
      <div style="font-size:0.78rem;">
        <strong>Pedidos que sustentan la regla:</strong>
        <span class="chip ${coincide ? 'chip-emerald' : 'chip-rose'}">${formatInt(pedidos.length)} rastreados · n_pedidos = ${formatInt(regla.nPedidos)}</span>
      </div>
      <div class="mono" style="font-size:0.72rem; color:var(--text-secondary); margin-top:0.4rem; word-break:break-all;">
        ${visibles.map(esc).join(' · ')}${restantes > 0 ? ` · … y ${formatInt(restantes)} más` : ''}
      </div>
    </div>`;
}

function renderComparison(poblacion) {
  if (!poblacion.comparacion.length) return '';
  return `
    <div>
      <strong style="font-size:0.84rem;">Comparación de algoritmos (mismos parámetros y mismas cestas)</strong>
      <div class="table-wrap" style="margin-top:0.45rem;">
        <table class="data-table">
          <thead><tr>
            <th>Algoritmo</th><th>Conjuntos frecuentes</th><th>Reglas obtenidas</th>
            <th>Reglas en común</th><th>Tiempo mínimo</th><th>Tiempo mediana</th><th>Coincide</th>
          </tr></thead>
          <tbody>
            ${poblacion.comparacion
              .map(
                c => `
              <tr>
                <td><strong>${esc(c.algoritmo)}</strong></td>
                <td class="mono">${formatInt(c.conjuntosFrecuentes)}</td>
                <td class="mono">${formatInt(c.reglas)}</td>
                <td class="mono">${formatInt(c.reglasEnComun)}</td>
                <td class="mono">${(c.tiempoMinimoS * 1000).toFixed(2)} ms</td>
                <td class="mono">${(c.tiempoMedianaS * 1000).toFixed(2)} ms</td>
                <td><span class="chip ${c.coincide ? 'chip-emerald' : 'chip-rose'}">${c.coincide ? 'Sí' : 'No'}</span></td>
              </tr>`
              )
              .join('')}
          </tbody>
        </table>
      </div>
      <p style="font-size:0.74rem; color:var(--text-muted); margin-top:0.35rem;">
        Tiempo de minado de conjuntos frecuentes (mejor y mediana de ${formatInt(poblacion.comparacion[0].repeticiones)} repeticiones).
        Con conjuntos de a lo sumo ${poblacion.parametros.max_len ?? 2} categorías, FP-Growth no tiene por qué ser más rápido que Apriori.
      </p>
    </div>`;
}

function renderThresholds(poblacion) {
  if (!poblacion.umbrales.length) return '';
  return `
    <div>
      <strong style="font-size:0.84rem;">Justificación del umbral (pares de categorías según pedidos mínimos)</strong>
      <div class="table-wrap" style="margin-top:0.45rem;">
        <table class="data-table">
          <thead><tr><th>Umbral (pedidos)</th><th>Soporte equivalente</th><th>Pares frecuentes</th><th>Pares con lift &gt; 1</th></tr></thead>
          <tbody>
            ${poblacion.umbrales
              .map(
                u => `
              <tr style="${u.elegido ? 'background:var(--bg-secondary);' : ''}">
                <td class="mono">${u.elegido ? '<strong>' : ''}${formatInt(u.umbralPedidos)}${u.elegido ? ' (elegido)</strong>' : ''}</td>
                <td class="mono">${pct(u.soporteEquivalente, 4)}</td>
                <td class="mono">${formatInt(u.paresFrecuentes)}</td>
                <td class="mono">${formatInt(u.paresLiftMayor1)}</td>
              </tr>`
              )
              .join('')}
          </tbody>
        </table>
      </div>
    </div>`;
}

function renderReading(association, clave, bonferroni) {
  const multi = composicionDe(association, 'multicategoria_dos_o_mas');
  const nota =
    clave === 'multicategoria'
      ? 'Todas las cestas de esta población tienen 2 o más categorías, por lo que las categorías no son independientes por construcción: los lift mayores que 1 y los p-valores pequeños son conclusiones conservadoras, y un lift menor que 1 no indica rechazo entre categorías.'
      : `${multi ? `Solo el ${(multi.pctUniverso ?? 0).toFixed(2)}% de las cestas` : 'La mayoría de las cestas'} combina 2 o más categorías; el resto no puede contener ningún par. Por eso, medido sobre todas las cestas, casi cualquier par tiene lift menor que 1, lo cual no indica rechazo entre categorías.`;
  return `
    <div style="padding:0.8rem 1rem; background:var(--bg-secondary); border-radius:var(--radius-sm); border-left:3px solid var(--accent-amber); font-size:0.78rem; color:var(--text-secondary);">
      <strong>Cómo leer esta tabla.</strong> ${nota}
      Con ${formatInt(bonferroni.conjuntos)} pares evaluados, la corrección de Bonferroni exige p &lt; ${bonferroni.umbral.toFixed(5)}.
      Las reglas son descriptivas, históricas (2016–2018) y no implican causalidad.
    </div>`;
}

export function renderAssociationTab(association, state) {
  if (!association || association.status !== 'ok') return renderEmptyState(association);

  const claves = Object.keys(association.poblaciones);
  const clave = association.poblaciones[state.assocPopulation] ? state.assocPopulation : 'principal';
  const poblacion = association.poblaciones[clave];
  const sufijo = clave === 'multicategoria' ? '_multicategoria' : '';
  const base = association.csvBase || '/resultados/';
  const bonferroni = bonferroniThreshold(poblacion.reglas);
  const reglas = poblacion.reglas.filter(r => r.lift >= state.minLift);
  const seleccionada = poblacion.reglas.find(r => r.id === state.selectedRuleId) || null;

  return `
    <div style="display:flex; flex-direction:column; gap:1rem; margin-top:0.5rem;">
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:1rem;">
        <div>
          <strong style="font-size:0.88rem;">Reglas de asociación entre categorías (Apriori y FP-Growth)</strong>
          <p style="font-size:0.77rem; color:var(--text-secondary);">
            Resultados calculados por <code>src/asociacion.py</code> sobre pedidos reales de Olist. Cada fila declara su población de referencia.
          </p>
        </div>
        <div style="display:flex; flex-direction:column; gap:0.4rem; align-items:flex-end;">
          <div class="tabs-bar">
            ${claves
              .map(
                k => `
              <button class="tab-pill ${k === clave ? 'active' : ''}" data-action="set-assoc-population" data-population="${k}">
                ${esc(association.poblaciones[k].etiqueta)}
              </button>`
              )
              .join('')}
          </div>
          ${
            claves.length < 2
              ? `<span style="font-size:0.72rem; color:var(--text-muted);">Análisis complementario no generado: <span class="mono">py src/asociacion.py --poblacion multicategoria</span></span>`
              : ''
          }
        </div>
      </div>

      ${renderPopulationBox(association, poblacion)}
      ${renderComposition(association)}

      <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:1rem; background:var(--bg-secondary); padding:0.85rem 1.15rem; border-radius:var(--radius-sm); border:1px solid var(--border-subtle);">
        <div>
          <strong style="font-size:0.84rem;">${formatInt(reglas.length)} de ${formatInt(poblacion.reglas.length)} reglas</strong>
          <p style="font-size:0.75rem; color:var(--text-secondary);">Filtra por lift mínimo. Haz clic en una regla para ver los pedidos que la sustentan.</p>
        </div>
        <div class="control-group" style="min-width:260px;">
          <label>
            <span>Lift mínimo:</span>
            <span class="mono" style="color:var(--accent-primary);">${state.minLift.toFixed(1)}x</span>
          </label>
          <input type="range" class="range-slider" min="0" max="5" step="0.1" value="${state.minLift}" data-action="change-min-lift" />
        </div>
      </div>

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Regla</th>
              <th>Antecedente (si compra...)</th>
              <th>Consecuente (también lleva...)</th>
              <th>Soporte</th>
              <th>Confianza</th>
              <th>Lift</th>
              <th>p-valor</th>
              <th>Pedidos (de ${formatInt(poblacion.totalCestas)})</th>
            </tr>
          </thead>
          <tbody>
            ${
              reglas.length
                ? reglas
                    .map(r => {
                      const significativa = r.lift > 1 && r.pValor !== null && r.pValor < bonferroni.umbral;
                      const elegida = seleccionada && seleccionada.id === r.id;
                      return `
              <tr data-action="select-rule" data-rule-id="${esc(r.id)}" style="cursor:pointer; ${elegida ? 'background:var(--bg-secondary);' : ''}">
                <td class="mono"><strong>${esc(r.id)}</strong></td>
                <td><strong>${esc(categorySetLabel(r.antecedente))}</strong><div class="mono" style="font-size:0.68rem; color:var(--text-muted);">${esc(r.antecedente)}</div></td>
                <td style="color:var(--accent-emerald);"><strong>→ ${esc(categorySetLabel(r.consecuente))}</strong><div class="mono" style="font-size:0.68rem; color:var(--text-muted);">${esc(r.consecuente)}</div></td>
                <td class="mono">${pct(r.soporte, 3)}</td>
                <td class="mono">${pct(r.confianza, 1)}</td>
                <td><span class="chip ${r.lift > 1 ? 'chip-purple' : 'chip-amber'} mono">${r.lift.toFixed(2)}x</span></td>
                <td class="mono">${formatPValue(r.pValor)}${significativa ? ' <span class="chip chip-emerald">Bonferroni</span>' : ''}</td>
                <td class="mono">${formatInt(r.nPedidos)}</td>
              </tr>`;
                    })
                    .join('')
                : '<tr><td colspan="8" style="text-align:center; color:var(--text-secondary);">Ninguna regla alcanza el lift mínimo seleccionado.</td></tr>'
            }
          </tbody>
        </table>
      </div>

      ${seleccionada ? renderRuleDetail(poblacion, seleccionada) : ''}
      ${renderReading(association, clave, bonferroni)}
      ${renderComparison(poblacion)}
      ${renderThresholds(poblacion)}

      <div style="font-size:0.76rem; color:var(--text-secondary);">
        Archivos:
        <a class="mono" href="${base}reglas_asociacion${sufijo}.csv" download>reglas_asociacion${sufijo}.csv</a> ·
        <a class="mono" href="${base}reglas_asociacion_trazabilidad${sufijo}.csv" download>reglas_asociacion_trazabilidad${sufijo}.csv</a> ·
        <a class="mono" href="${base}comparacion_asociacion${sufijo}.csv" download>comparacion_asociacion${sufijo}.csv</a>
      </div>
    </div>`;
}

