/**
 * Motor de Visualización Vectorial SVG de Alta Precisión para DataSmart
 * Cero dependencias externas pesadas: funciona instantáneamente en navegador, Vite y servidor Python.
 */

import { formatBRL, formatBRLCompact, formatInt, formatPct } from '../utils/formatters.js';

/**
 * Gráfico de Serie Temporal Mensual (Ventas de Artículos Entregados BRL)
 */
export function renderMonthlySalesSVG(series, options = {}) {
  const { showForecast = false, forecastMonths = [] } = options;
  const allPoints = showForecast ? [...series, ...forecastMonths] : series;

  if (!allPoints.length) return '<p>Sin datos para graficar.</p>';

  const width = 880;
  const height = 310;
  const pad = { top: 28, right: 28, bottom: 54, left: 74 };
  const plotW = width - pad.left - pad.right;
  const plotH = height - pad.top - pad.bottom;

  const maxVal = Math.max(...allPoints.map(d => d.upperBound || d.salesBRL), 1050000) * 1.08;
  const minVal = 0;

  const getX = idx => pad.left + (idx / Math.max(allPoints.length - 1, 1)) * plotW;
  const getY = val => pad.top + plotH - ((val - minVal) / (maxVal - minVal)) * plotH;

  // Líneas de grilla horizontal
  const yTicks = [0, 250000, 500000, 750000, 1000000];
  const gridLines = yTicks
    .map(tick => {
      const y = getY(tick);
      return `
        <line x1="${pad.left}" y1="${y}" x2="${width - pad.right}" y2="${y}" stroke="var(--chart-grid)" stroke-dasharray="4 4" />
        <text x="${pad.left - 10}" y="${y + 4}" text-anchor="end" fill="var(--text-secondary)" font-size="11" font-family="JetBrains Mono, monospace">
          ${formatBRLCompact(tick)}
        </text>
      `;
    })
    .join('');

  // Puntos históricos reales
  const histCoords = series.map((d, i) => ({ x: getX(i), y: getY(d.salesBRL), d, i }));
  const linePath = histCoords
    .map((pt, idx) => `${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`)
    .join(' ');

  const areaPath = `${linePath} L ${histCoords[histCoords.length - 1].x.toFixed(1)} ${(pad.top + plotH).toFixed(1)} L ${histCoords[0].x.toFixed(1)} ${(pad.top + plotH).toFixed(1)} Z`;

  // Pronóstico si está activo
  let forecastElements = '';
  if (showForecast && forecastMonths.length > 0 && histCoords.length > 0) {
    const startIdx = series.length - 1;
    const fCoords = [
      histCoords[startIdx],
      ...forecastMonths.map((d, idx) => ({
        x: getX(series.length + idx),
        y: getY(d.salesBRL),
        yUp: getY(d.upperBound || d.salesBRL * 1.1),
        yLow: getY(d.lowerBound || d.salesBRL * 0.9),
        d,
      })),
    ];

    const fLine = fCoords
      .map((pt, idx) => `${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.y.toFixed(1)}`)
      .join(' ');

    const bandTop = fCoords
      .slice(1)
      .map((pt, idx) => `${idx === 0 ? 'M' : 'L'} ${pt.x.toFixed(1)} ${pt.yUp.toFixed(1)}`)
      .join(' ');
    const bandBottom = [...fCoords.slice(1)]
      .reverse()
      .map(pt => `L ${pt.x.toFixed(1)} ${pt.yLow.toFixed(1)}`)
      .join(' ');

    forecastElements = `
      <path d="${bandTop} ${bandBottom} Z" fill="var(--chart-band)" />
      <path d="${fLine}" fill="none" stroke="var(--chart-secondary)" stroke-width="2.5" stroke-dasharray="6 4" />
      ${fCoords
        .slice(1)
        .map(
          pt => `
        <rect x="${(pt.x - 4).toFixed(1)}" y="${(pt.y - 4).toFixed(1)}" width="8" height="8" fill="var(--lavender)" stroke="var(--chart-secondary)" stroke-width="2">
          <title>${pt.d.monthLabel} (Pronóstico): ${formatBRL(pt.d.salesBRL)}</title>
        </rect>
      `
        )
        .join('')}
    `;
  }

  // Etiquetas eje X y puntos interactivos
  const pointsMarkup = histCoords
    .map((pt, idx) => {
      const isPeak = pt.d.date === '2017-11-01';
      const showLabel = idx % 2 === 0 || idx === histCoords.length - 1;
      return `
        ${
          showLabel
            ? `<text x="${pt.x.toFixed(1)}" y="${height - 16}" text-anchor="middle" fill="var(--text-secondary)" font-size="10.5" transform="rotate(-22 ${pt.x.toFixed(1)} ${height - 16})">${pt.d.monthLabel}</text>`
            : ''
        }
        <g class="svg-point-group">
          ${pt.d.isExtreme ? `
          <rect
            x="${(pt.x - 4).toFixed(1)}" y="${(pt.y - 4).toFixed(1)}" width="8" height="8"
            transform="rotate(45 ${pt.x.toFixed(1)} ${pt.y.toFixed(1)})"
            fill="var(--bg-surface)" stroke="var(--chart-primary)" stroke-width="2"
          >
            <title>${pt.d.monthLabel}: ${formatBRL(pt.d.salesBRL)} (${pt.d.note})</title>
          </rect>` : `<circle
            cx="${pt.x.toFixed(1)}"
            cy="${pt.y.toFixed(1)}"
            r="${isPeak ? 6.5 : 4.2}"
            fill="${isPeak ? 'var(--chart-tertiary)' : 'var(--chart-primary)'}"
            stroke="var(--bg-surface)"
            stroke-width="2"
          >
            <title>${pt.d.monthLabel}: ${formatBRL(pt.d.salesBRL)} (${pt.d.note})</title>
          </circle>`}
          ${
            isPeak
              ? `<rect x="${(pt.x - 68).toFixed(1)}" y="${(pt.y - 30).toFixed(1)}" width="136" height="20" rx="5" fill="var(--accent-rose)" />
                 <text x="${pt.x.toFixed(1)}" y="${(pt.y - 16).toFixed(1)}" text-anchor="middle" fill="var(--text-on-accent)" font-size="10" font-weight="700">Pico: R$ 987.765</text>`
              : ''
          }
        </g>
      `;
    })
    .join('');

  return `
    <svg viewBox="0 0 ${width} ${height}" width="100%" height="auto" role="img" aria-label="Evolución mensual de ventas Olist">
      <defs>
        <linearGradient id="salesAreaGrad" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="var(--chart-primary)" stop-opacity="0.18" />
          <stop offset="100%" stop-color="var(--chart-primary)" stop-opacity="0.0" />
        </linearGradient>
      </defs>
      ${gridLines}
      <path d="${areaPath}" fill="url(#salesAreaGrad)" />
      <path d="${linePath}" fill="none" stroke="var(--chart-primary)" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round" />
      ${forecastElements}
      ${pointsMarkup}
    </svg>
  `;
}

/**
 * Grafo Interactivo SVG para PN-09 (Relaciones Clientes – Categorías – Vendedores en Brasil)
 */
export function renderEntityNetworkSVG(selectedNode = 'SP') {
  const nodes = [
    { id: 'SP', label: 'São Paulo (SP)', sub: '70.4% Vendedores | 41.9% Clientes', x: 360, y: 155, r: 34, shape: 'circle', type: 'Hub Principal' },
    { id: 'RJ', label: 'Rio de Janeiro (RJ)', sub: '12.9% Clientes | Receptor Neto', x: 165, y: 85, r: 24, shape: 'circle', type: 'Nodo Cliente' },
    { id: 'MG', label: 'Minas Gerais (MG)', sub: '11.7% Clientes | 8.2% Vendedores', x: 565, y: 85, r: 24, shape: 'circle', type: 'Nodo Mixto' },
    { id: 'PR', label: 'Paraná (PR)', sub: '7.4% Vendedores | Polo Sur', x: 580, y: 235, r: 22, shape: 'diamond', type: 'Polo Vendedor' },
    { id: 'RS', label: 'Rio Grande do Sul (RS)', sub: '5.5% Clientes | Alta Distancia', x: 160, y: 235, r: 21, shape: 'circle', type: 'Nodo Cliente' },
    { id: 'CAT_BS', label: 'Belleza y Salud', sub: 'R$ 1,23M (Top 1)', x: 360, y: 42, r: 20, shape: 'square', type: 'Categoría' },
    { id: 'CAT_CM', label: 'Cama, Mesa y Baño', sub: 'R$ 1,02M (Top 3)', x: 360, y: 270, r: 20, shape: 'square', type: 'Categoría' },
  ];

  const edges = [
    { from: 'SP', to: 'RJ', weight: 'Flujo #1: 18.420 envíos', width: 5 },
    { from: 'SP', to: 'MG', weight: 'Flujo #2: 14.890 envíos', width: 4.5 },
    { from: 'SP', to: 'RS', weight: 'Flujo #3: 7.310 envíos', width: 3 },
    { from: 'PR', to: 'SP', weight: 'Flujo Sur→SP: 5.120 envíos', width: 3 },
    { from: 'PR', to: 'RJ', weight: 'Flujo Sur→RJ: 2.640 envíos', width: 2 },
    { from: 'SP', to: 'CAT_BS', weight: 'Concentra 68% despachos Belleza', width: 3.5 },
    { from: 'SP', to: 'CAT_CM', weight: 'Polo Textil Ibitinga-SP (81%)', width: 4 },
    { from: 'MG', to: 'CAT_BS', weight: '14% demanda regional', width: 2 },
    { from: 'RJ', to: 'CAT_CM', weight: '16% demanda hogar', width: 2.2 },
  ];

  const byId = Object.fromEntries(nodes.map(n => [n.id, n]));

  const edgesSvg = edges
    .map(e => {
      const a = byId[e.from];
      const b = byId[e.to];
      const highlighted = e.from === selectedNode || e.to === selectedNode;
      return `
        <g>
          <line
            x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}"
            stroke="${highlighted ? 'var(--chart-primary)' : 'var(--chart-muted)'}"
            stroke-dasharray="${highlighted ? 'none' : '4 4'}"
            stroke-width="${highlighted ? e.width + 1 : e.width}"
          >
            <title>${a.label} ↔ ${b.label}: ${e.weight}</title>
          </line>
        </g>
      `;
    })
    .join('');

  const nodesSvg = nodes
    .map(n => {
      const isSelected = n.id === selectedNode;
      const radius = isSelected ? n.r + 4 : n.r;
      const fill = n.id === 'SP' ? 'var(--petrol)'
        : n.shape === 'square' ? 'var(--lavender)'
        : n.shape === 'diamond' || n.id === 'MG' ? 'var(--pink)'
        : 'var(--chart-node-fill)';
      const shape = (size, fill, stroke, strokeWidth) => {
        const attrs = `fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}"`;
        if (n.shape === 'square') {
          return `<rect x="${n.x - size}" y="${n.y - size}" width="${size * 2}" height="${size * 2}" rx="5" ${attrs} />`;
        }
        if (n.shape === 'diamond') {
          return `<polygon points="${n.x},${n.y - size} ${n.x + size},${n.y} ${n.x},${n.y + size} ${n.x - size},${n.y}" ${attrs} />`;
        }
        return `<circle cx="${n.x}" cy="${n.y}" r="${size}" ${attrs} />`;
      };
      return `
        <g class="graph-node" data-node-id="${n.id}" role="button" tabindex="0" aria-label="${n.label}: ${n.type}" aria-pressed="${isSelected}" style="cursor:pointer">
          <title>${n.label} — ${n.type}</title>
          ${isSelected ? shape(radius + 5, 'none', 'var(--chart-primary)', 1.5) : ''}
          ${shape(radius, fill, isSelected ? 'var(--chart-primary)' : 'var(--chart-muted)', isSelected ? 3 : 2)}
          <text x="${n.x}" y="${n.y + 4}" text-anchor="middle" fill="${n.id === 'SP' ? 'var(--text-on-accent)' : 'var(--chart-node-text)'}" font-size="11" font-weight="700">
            ${n.id.replace('CAT_', '')}
          </text>
          <text x="${n.x}" y="${n.y + n.r + 15}" text-anchor="middle" fill="var(--text-primary)" font-size="11" font-weight="600">
            ${n.label}
          </text>
          <text x="${n.x}" y="${n.y + n.r + 28}" text-anchor="middle" fill="var(--text-secondary)" font-size="9.5">
            ${n.sub}
          </text>
        </g>
      `;
    })
    .join('');

  return `
    <svg viewBox="0 0 720 320" width="100%" height="auto" role="group" aria-label="Grafo NetworkX de Olist">
      ${edgesSvg}
      ${nodesSvg}
    </svg>
  `;
}

/** Red bipartita real acotada procedente del artefacto grafo_subgrafo.json. */
export function renderOlistSubgraphSVG(subgraph, selectedNode = '') {
  const nodes = Array.isArray(subgraph?.nodes) ? subgraph.nodes : [];
  const links = Array.isArray(subgraph?.links) ? subgraph.links : [];
  if (!nodes.length || !links.length) return '<p>El subgrafo real no está disponible.</p>';

  const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
  })[char]);
  const idOf = value => typeof value === 'object' ? value.id : value;
  const top = [...nodes]
    .sort((a, b) => Number(b.grado_ponderado || 0) - Number(a.grado_ponderado || 0) || String(a.id).localeCompare(String(b.id)))
    .slice(0, 24);
  const ids = new Set(top.map(node => node.id));
  const visibleLinks = links.filter(link => ids.has(idOf(link.source)) && ids.has(idOf(link.target)));
  const byId = new Map(top.map(node => [node.id, node]));
  const sellers = top.filter(node => node.tipo === 'vendedor');
  const products = top.filter(node => node.tipo === 'producto');
  const positions = new Map();
  const place = (list, x) => list.forEach((node, index) => positions.set(node.id, {
    x, y: 28 + (index + 1) * (320 / (list.length + 1)),
  }));
  place(products, 170);
  place(sellers, 550);
  const maxWeight = Math.max(1, ...visibleLinks.map(link => Number(link.weight) || 0));
  const edgeSvg = visibleLinks.map(link => {
    const source = idOf(link.source), target = idOf(link.target);
    const a = positions.get(source), b = positions.get(target);
    if (!a || !b) return '';
    return `<line x1="${a.x}" y1="${a.y}" x2="${b.x}" y2="${b.y}" stroke="var(--chart-muted)" stroke-opacity=".58" stroke-width="${1 + 4 * (Number(link.weight || 0) / maxWeight)}"><title>${escape(byId.get(source)?.label)} ↔ ${escape(byId.get(target)?.label)}: ${formatInt(link.weight)} ítems</title></line>`;
  }).join('');
  const nodeSvg = top.map(node => {
    const p = positions.get(node.id);
    const selected = node.id === selectedNode;
    const radius = Math.max(6, Math.min(14, 5 + Math.log1p(Number(node.grado_ponderado || 0))));
    const fill = node.tipo === 'vendedor' ? 'var(--chart-primary)' : 'var(--lavender)';
    const label = escape(node.label || node.id);
    return `<g class="graph-node" data-node-id="${escape(node.id)}" role="button" tabindex="0" aria-label="${label}, ${escape(node.tipo)}" aria-pressed="${selected}"><circle cx="${p.x}" cy="${p.y}" r="${radius + (selected ? 4 : 0)}" fill="${fill}" stroke="${selected ? 'var(--chart-tertiary)' : 'var(--chart-muted)'}" stroke-width="${selected ? 3 : 1}"><title>${label}; ${formatInt(node.grado_ponderado)} ítems</title></circle><text x="${p.x + (node.tipo === 'producto' ? -12 : 12)}" y="${p.y + 3}" text-anchor="${node.tipo === 'producto' ? 'end' : 'start'}" fill="var(--text-primary)" font-size="9">${label}</text></g>`;
  }).join('');
  return `<svg viewBox="0 0 720 380" width="100%" height="auto" role="group" aria-label="Subgrafo bipartito real vendedor-producto"><text x="170" y="18" text-anchor="middle" fill="var(--text-secondary)" font-size="12">Productos</text><text x="550" y="18" text-anchor="middle" fill="var(--text-secondary)" font-size="12">Vendedores</text>${edgeSvg}${nodeSvg}</svg><p class="muted">Visualización acotada a ${top.length} nodos y ${visibleLinks.length} relaciones del artefacto real (${formatInt(subgraph.total_nodos)} nodos, ${formatInt(subgraph.total_enlaces)} enlaces).</p>`;
}

/** Compara valores observados y pronósticos de la partición temporal de test. */
export function renderSeriesTestSVG(rows) {
  const valid = (Array.isArray(rows) ? rows : []).filter(row =>
    Number.isFinite(Number(row.venta_real)) && Number.isFinite(Number(row.venta_predicha))
  );
  if (!valid.length) return '<p>Sin predicciones temporales disponibles.</p>';
  const byDate = new Map();
  for (const row of valid) {
    const entry = byDate.get(row.fecha) || { fecha: row.fecha, real: Number(row.venta_real), predicciones: [] };
    entry.predicciones.push(Number(row.venta_predicha));
    byDate.set(row.fecha, entry);
  }
  const points = [...byDate.values()].sort((a, b) => a.fecha.localeCompare(b.fecha));
  const values = points.flatMap(point => [point.real, ...point.predicciones]);
  const max = Math.max(1, ...values) * 1.08;
  const width = 880, height = 300, left = 74, right = 24, top = 20, bottom = 48;
  const x = index => left + index * (width - left - right) / Math.max(1, points.length - 1);
  const y = value => top + (height - top - bottom) * (1 - value / max);
  const observed = points.map((point, index) => `${index ? 'L' : 'M'} ${x(index).toFixed(1)} ${y(point.real).toFixed(1)}`).join(' ');
  const predicted = points.map((point, index) => {
    const average = point.predicciones.reduce((sum, value) => sum + value, 0) / point.predicciones.length;
    return `${index ? 'L' : 'M'} ${x(index).toFixed(1)} ${y(average).toFixed(1)}`;
  }).join(' ');
  const grid = [0, .25, .5, .75, 1].map(ratio => {
    const yy = y(max * ratio);
    return `<line x1="${left}" y1="${yy}" x2="${width - right}" y2="${yy}" stroke="var(--chart-grid)" stroke-dasharray="4 4"/><text x="${left - 8}" y="${yy + 4}" text-anchor="end" fill="var(--text-secondary)" font-size="10">${formatBRLCompact(max * ratio)}</text>`;
  }).join('');
  const first = points[0].fecha, last = points[points.length - 1].fecha;
  return `<svg viewBox="0 0 ${width} ${height}" width="100%" height="auto" role="img" aria-label="Ventas reales y pronósticos en test temporal">${grid}<path d="${observed}" fill="none" stroke="var(--chart-primary)" stroke-width="2.5"/><path d="${predicted}" fill="none" stroke="var(--chart-secondary)" stroke-width="2.5" stroke-dasharray="6 4"/><text x="${left}" y="${height - 12}" fill="var(--text-secondary)" font-size="10">${first}</text><text x="${width - right}" y="${height - 12}" text-anchor="end" fill="var(--text-secondary)" font-size="10">${last}</text></svg><div class="chart-legend"><span>Ventas reales (test)</span><span>Promedio de modelos evaluados</span></div>`;
}
