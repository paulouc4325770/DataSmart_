/**
 * Servicio de Sincronización con los archivos reales de `resultados/`.
 *
 * - Reglas de asociación: se cargan de `/api/asociacion` (servidor Python). Si la API no
 *   está disponible (por ejemplo, Vite directo), se leen los CSV de `resultados/`.
 *   Si no hay resultados, el estado queda explícito y no se muestran datos inventados.
 * - Indicadores: se actualizan desde `/api/resultados` cuando la API responde y, si no,
 *   se usan los valores verificados de `olistData.js`.
 */

import {
  PROJECT_METADATA,
  OFFICIAL_KPIS,
  ORDER_STATUS_DISTRIBUTION,
  MONTHLY_SALES,
  TOP_CATEGORIES,
  TABLES_SUMMARY,
  DATA_QUALITY_ISSUES,
  TREATMENT_PLAN_STEPS,
  DATA_DICTIONARY,
  BUSINESS_QUESTIONS,
  RFM_SEGMENTS_PREVIEW,
  SHAP_FEATURE_IMPORTANCE,
  NLP_TOPICS_PREVIEW,
  CRISP_DM_ROADMAP,
} from '../data/olistData.js';

const POBLACIONES = {
  principal: { sufijo: '', etiqueta: 'Todas las cestas (análisis principal)' },
  multicategoria: {
    sufijo: '_multicategoria',
    etiqueta: 'Solo cestas multicategoría (análisis complementario)',
  },
};
const COMANDOS_ASOCIACION = [
  'py src/asociacion.py',
  'py src/asociacion.py --poblacion multicategoria',
];
const PREFIJOS_CSV = ['/resultados/', '/'];

// ---------------------------------------------------------------------------
// Lectura de CSV (modo estático)
// ---------------------------------------------------------------------------

export function parseCsv(texto) {
  const limpio = String(texto || '').replace(/^\uFEFF/, '');
  const filas = [];
  let fila = [];
  let campo = '';
  let entreComillas = false;
  for (let i = 0; i < limpio.length; i += 1) {
    const c = limpio[i];
    if (entreComillas) {
      if (c === '"' && limpio[i + 1] === '"') {
        campo += '"';
        i += 1;
      } else if (c === '"') {
        entreComillas = false;
      } else {
        campo += c;
      }
    } else if (c === '"') {
      entreComillas = true;
    } else if (c === ',') {
      fila.push(campo);
      campo = '';
    } else if (c === '\n' || c === '\r') {
      if (c === '\r' && limpio[i + 1] === '\n') i += 1;
      fila.push(campo);
      campo = '';
      if (fila.some(valor => valor !== '')) filas.push(fila);
      fila = [];
    } else {
      campo += c;
    }
  }
  if (campo !== '' || fila.length) {
    fila.push(campo);
    if (fila.some(valor => valor !== '')) filas.push(fila);
  }
  if (!filas.length) return [];
  const [encabezado, ...datos] = filas;
  return datos.map(valores =>
    Object.fromEntries(encabezado.map((nombre, idx) => [nombre, valores[idx] ?? '']))
  );
}

const num = valor => (valor === undefined || valor === null || String(valor).trim() === '' ? null : Number(valor));
const entero = valor => (num(valor) === null ? null : Math.round(num(valor)));

function reglaDesdeFila(f) {
  return {
    id: f.regla_id,
    antecedente: f.antecedente,
    consecuente: f.consecuente,
    soporte: num(f.soporte),
    confianza: num(f.confianza),
    lift: num(f.lift),
    conviccion: num(f.conviccion),
    pValor: num(f.p_valor),
    nPedidos: entero(f.n_pedidos),
    nPedidosAntecedente: entero(f.n_pedidos_antecedente),
    nPedidosConsecuente: entero(f.n_pedidos_consecuente),
    soporteAntecedente: num(f.soporte_antecedente),
    soporteConsecuente: num(f.soporte_consecuente),
    asociacionPositiva: f.asociacion_positiva === 'True',
    totalCestas: entero(f.total_cestas),
    poblacionReferencia: f.poblacion_referencia,
  };
}

function poblacionDesdeCsv(clave, textos) {
  const reglas = parseCsv(textos.reglas).map(reglaDesdeFila);
  const metadata = JSON.parse(String(textos.metadata).replace(/^\uFEFF/, ''));
  const trazabilidad = {};
  for (const f of parseCsv(textos.trazabilidad)) {
    (trazabilidad[f.regla_id] ||= []).push(f.order_id);
  }
  const inconsistentes = reglas
    .filter(r => (trazabilidad[r.id] || []).length !== r.nPedidos)
    .map(r => r.id);
  return {
    clave,
    etiqueta: POBLACIONES[clave].etiqueta,
    poblacionReferencia: metadata.poblacion_referencia || '',
    totalCestas: metadata.total_cestas_analisis ?? null,
    parametros: metadata.parametros || {},
    paresObservados: metadata.pares_de_categorias_observados ?? null,
    algoritmosCoinciden: Boolean(metadata.algoritmos_coinciden),
    reglas,
    comparacion: parseCsv(textos.comparacion).map(f => ({
      algoritmo: f.algoritmo,
      conjuntosFrecuentes: entero(f.conjuntos_frecuentes),
      reglas: entero(f.reglas),
      reglasEnComun: entero(f.reglas_en_comun),
      coincide: f.coincide_con_el_otro === 'True',
      tiempoMinimoS: num(f.tiempo_minimo_s),
      tiempoMedianaS: num(f.tiempo_mediana_s),
      repeticiones: entero(f.repeticiones),
    })),
    umbrales: parseCsv(textos.umbrales || '').map(f => ({
      umbralPedidos: entero(f.umbral_pedidos),
      soporteEquivalente: num(f.soporte_equivalente),
      paresFrecuentes: entero(f.pares_frecuentes),
      paresLiftMayor1: entero(f.pares_lift_mayor_1),
      elegido: f.umbral_elegido === 'True',
    })),
    trazabilidad,
    verificacion: { trazabilidadCompleta: inconsistentes.length === 0, reglasInconsistentes: inconsistentes },
  };
}

async function leerTexto(doFetch, baseUrl, prefijo, archivo) {
  const respuesta = await doFetch(`${baseUrl}${prefijo}${archivo}`, { cache: 'no-store' });
  if (!respuesta.ok) throw new Error(`${archivo}: ${respuesta.status}`);
  const texto = await respuesta.text();
  // Vite devuelve index.html cuando el archivo no existe.
  if (/^\s*<(!doctype|html)/i.test(texto)) throw new Error(`${archivo}: no encontrado`);
  return texto;
}

async function cargarAsociacionDesdeCsv(doFetch, baseUrl) {
  for (const prefijo of PREFIJOS_CSV) {
    const poblaciones = {};
    for (const [clave, { sufijo }] of Object.entries(POBLACIONES)) {
      try {
        const [reglas, comparacion, trazabilidad, metadata, umbrales] = await Promise.all([
          leerTexto(doFetch, baseUrl, prefijo, `reglas_asociacion${sufijo}.csv`),
          leerTexto(doFetch, baseUrl, prefijo, `comparacion_asociacion${sufijo}.csv`),
          leerTexto(doFetch, baseUrl, prefijo, `reglas_asociacion_trazabilidad${sufijo}.csv`),
          leerTexto(doFetch, baseUrl, prefijo, `asociacion_metadata${sufijo}.json`),
          leerTexto(doFetch, baseUrl, prefijo, `umbrales_asociacion${sufijo}.csv`).catch(() => ''),
        ]);
        poblaciones[clave] = poblacionDesdeCsv(clave, { reglas, comparacion, trazabilidad, metadata, umbrales });
      } catch (_) {
        // Falta esta población en este prefijo.
      }
    }
    if (poblaciones.principal) {
      let composicion = [];
      try {
        composicion = parseCsv(await leerTexto(doFetch, baseUrl, prefijo, 'composicion_cestas.csv')).map(f => ({
          concepto: f.concepto,
          pedidos: entero(f.pedidos),
          pctPedidosEntregados: num(f.pct_pedidos_entregados),
          pctUniverso: num(f.pct_universo),
          enUniverso: f.en_universo === 'True',
        }));
      } catch (_) {
        composicion = [];
      }
      return {
        status: 'ok',
        source: 'resultados/ (CSV estáticos)',
        csvBase: prefijo,
        composicion,
        poblaciones,
        faltantesOpcionales: poblaciones.multicategoria ? [] : ['reglas_asociacion_multicategoria.csv'],
      };
    }
  }
  return null;
}

async function cargarAsociacion(doFetch, baseUrl) {
  try {
    const respuesta = await doFetch(`${baseUrl}/api/asociacion`, { cache: 'no-store' });
    if (respuesta.ok) {
      const payload = await respuesta.json();
      if (payload && payload.status === 'ok') return { ...payload, csvBase: '/resultados/' };
      if (payload && payload.status === 'sin_resultados') return { ...payload, csvBase: '/resultados/' };
    }
  } catch (_) {
    // Sin API: se intenta con los CSV estáticos.
  }
  try {
    const desdeCsv = await cargarAsociacionDesdeCsv(doFetch, baseUrl);
    if (desdeCsv) return desdeCsv;
  } catch (_) {
    // Se informa más abajo que no hay resultados.
  }
  return {
    status: 'sin_resultados',
    mensaje: 'No se encontraron los resultados de asociación.',
    faltantes: ['reglas_asociacion.csv'],
    comandos: COMANDOS_ASOCIACION,
    csvBase: '/resultados/',
  };
}

// ---------------------------------------------------------------------------
// Indicadores desde /api/resultados
// ---------------------------------------------------------------------------

const formatoEs = (valor, decimales = 0) =>
  Number(valor).toLocaleString('de-DE', { minimumFractionDigits: decimales, maximumFractionDigits: decimales });

function aMapa(filas) {
  const mapa = {};
  for (const f of filas || []) mapa[f.indicador] = Number(f.valor);
  return mapa;
}

/** Actualiza los KPI con los valores de los CSV; conserva los verificados si falta alguno. */
export function aplicarKpisEnVivo(kpis, payload) {
  const base = aMapa(payload.indicadores_kpi);
  const prep = aMapa(payload.indicadores_preparacion);
  const tiene = (...claves) => claves.every(k => Number.isFinite(base[k]) || Number.isFinite(prep[k]));
  const dato = k => (Number.isFinite(base[k]) ? base[k] : prep[k]);

  return kpis.map(kpi => {
    const k = { ...kpi };
    if (k.id === 'pedidos_totales' && tiene('pedidos_totales')) {
      k.value = dato('pedidos_totales');
      k.formatted = formatoEs(k.value);
    } else if (k.id === 'clientes_unicos' && tiene('clientes_unicos')) {
      k.value = dato('clientes_unicos');
      k.formatted = formatoEs(k.value);
      if (Number.isFinite(prep.porcentaje_clientes_recurrentes)) {
        k.badge = `Tasa recompra ${formatoEs(prep.porcentaje_clientes_recurrentes, 2)}%`;
      }
    } else if (k.id === 'pedidos_entregados' && tiene('pedidos_entregados')) {
      k.value = dato('pedidos_entregados');
      k.formatted = formatoEs(k.value);
      if (Number.isFinite(base.pedidos_totales)) {
        k.badge = `${formatoEs((100 * k.value) / base.pedidos_totales, 2)}% tasa entrega`;
      }
    } else if (k.id === 'ventas_articulos_entregados_BRL' && tiene('ventas_articulos_entregados_BRL')) {
      k.value = dato('ventas_articulos_entregados_BRL');
      k.formatted = `R$ ${formatoEs(k.value, 2)}`;
    } else if (k.id === 'ticket_promedio_entregado_BRL' && tiene('ticket_promedio_entregado_BRL')) {
      k.value = dato('ticket_promedio_entregado_BRL');
      k.formatted = `R$ ${formatoEs(k.value, 2)}`;
    } else if (
      k.id === 'tasa_entregas_tardias' &&
      tiene('tasa_entregas_tardias_calendario_pct', 'entregas_tardias_calendario')
    ) {
      k.value = Number(prep.tasa_entregas_tardias_calendario_pct.toFixed(2));
      k.formatted = `${formatoEs(k.value, 2)} %`;
      k.unit = `${formatoEs(prep.entregas_tardias_calendario)} tardíos`;
      if (Number.isFinite(prep.pedidos_entregados) && Number.isFinite(prep.entregados_sin_fecha)) {
        k.definition = `${formatoEs(prep.entregas_tardias_calendario)} entregas tardías (por día calendario) sobre ${formatoEs(
          prep.pedidos_entregados - prep.entregados_sin_fecha
        )} entregados con ambas fechas`;
      }
    }
    return k;
  });
}

// ---------------------------------------------------------------------------
// Store principal
// ---------------------------------------------------------------------------

export async function loadDataSmartStore({ baseUrl = '', fetchImpl } = {}) {
  const doFetch = fetchImpl || ((...args) => fetch(...args));
  const store = {
    meta: PROJECT_METADATA,
    kpis: OFFICIAL_KPIS,
    orderStatus: ORDER_STATUS_DISTRIBUTION,
    monthlySales: MONTHLY_SALES,
    topCategories: TOP_CATEGORIES,
    tablesSummary: TABLES_SUMMARY,
    qualityIssues: DATA_QUALITY_ISSUES,
    treatmentPlan: TREATMENT_PLAN_STEPS,
    dictionary: DATA_DICTIONARY,
    businessQuestions: BUSINESS_QUESTIONS,
    rfmSegments: RFM_SEGMENTS_PREVIEW,
    association: null,
    shapImportance: SHAP_FEATURE_IMPORTANCE,
    nlpTopics: NLP_TOPICS_PREVIEW,
    roadmap: CRISP_DM_ROADMAP,
    liveSourceConnected: false,
  };

  try {
    const response = await doFetch(`${baseUrl}/api/resultados`, { cache: 'no-store' });
    if (response.ok) {
      const payload = await response.json();
      if (payload && payload.status === 'ok') {
        store.liveSourceConnected = true;
        store.kpis = aplicarKpisEnVivo(store.kpis, payload);
      }
    }
  } catch (_) {
    // Modo estático / Vite directo: usa los valores verificados de olistData.js.
  }

  store.association = await cargarAsociacion(doFetch, baseUrl);
  return store;
}
