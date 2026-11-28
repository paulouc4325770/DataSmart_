// Ejecutar desde la raíz del proyecto:  node --test frontend/tests/asociacion.test.mjs
import assert from 'node:assert/strict';
import test from 'node:test';
import { loadDataSmartStore, parseCsv, aplicarKpisEnVivo, aplicarCalidadEnVivo, aplicarDiccionarioEnVivo } from '../src/services/dataService.js';
import { renderAssociationTab, bonferroniThreshold, formatPValue } from '../src/views/associationView.js';
import { categorySetLabel } from '../src/data/categoryNames.js';
import { renderOlistSubgraphSVG, renderSeriesTestSVG } from '../src/components/svgCharts.js';
import { renderBusinessModelsView } from '../src/views/businessModelsView.js';
import { renderDataQualityView } from '../src/views/dataQualityView.js';
import { renderDataDictionaryView } from '../src/views/dataDictionaryView.js';

const ENC = 'regla_id,antecedente,consecuente,soporte,confianza,lift,conviccion,p_valor,n_pedidos,n_pedidos_antecedente,n_pedidos_consecuente,soporte_antecedente,soporte_consecuente,asociacion_positiva,total_cestas,poblacion_referencia';
const POB = 'Poblacion de prueba; N=100';
const ARCHIVOS = {
  'reglas_asociacion.csv': `\uFEFF${ENC}\nAR-001,cama_mesa_banho,casa_conforto,0.03,0.3,2.5,1.2,0.001,3,10,12,0.1,0.12,True,100,${POB}\nAR-002,casa_conforto,cama_mesa_banho,0.03,0.25,2.5,,0.001,3,12,10,0.12,0.1,True,100,${POB}\n`,
  'reglas_asociacion_trazabilidad.csv': 'regla_id,order_id\nAR-001,o1\nAR-001,o2\nAR-001,o3\nAR-002,o1\nAR-002,o2\nAR-002,o3\n',
  'comparacion_asociacion.csv': 'algoritmo,poblacion,conjuntos_frecuentes,reglas,reglas_en_comun,reglas_con_metricas_iguales,coincide_con_el_otro,tiempo_minimo_s,tiempo_mediana_s,repeticiones,min_pedidos,min_soporte,min_confianza,max_len,total_cestas\nApriori,todas,5,2,2,2,True,0.01,0.012,5,3,0.03,0.0,2,100\nFP-Growth,todas,5,2,2,2,True,0.02,0.022,5,3,0.03,0.0,2,100\n',
  'umbrales_asociacion.csv': 'umbral_pedidos,soporte_equivalente,pares_frecuentes,pares_lift_mayor_1,umbral_elegido\n1,0.01,5,2,False\n3,0.03,1,1,True\n',
  'asociacion_metadata.json': JSON.stringify({ poblacion_referencia: POB, total_cestas_analisis: 100, parametros: { min_pedidos: 3, min_soporte: 0.03, min_confianza: 0, max_len: 2 }, pares_de_categorias_observados: 5, algoritmos_coinciden: true }),
  'composicion_cestas.csv': 'concepto,pedidos,pct_pedidos_entregados,pct_universo,en_universo\npedidos_entregados,110,100.0,,False\nuniverso_total,100,90.9,100.0,True\nmulticategoria_dos_o_mas,8,7.2,8.0,True\n',
};

const fetchDeArchivos = archivos => async url => {
  if (url.startsWith('/api/')) return { ok: false, status: 404, json: async () => ({}), text: async () => '' };
  const nombre = url.split('/').pop();
  if (!(nombre in archivos)) return { ok: true, status: 200, text: async () => '<!doctype html><html></html>' };
  return { ok: true, status: 200, text: async () => archivos[nombre] };
};

test('parseCsv maneja BOM, comillas y saltos de línea', () => {
  const filas = parseCsv('\uFEFFa,b\r\n1,"x, y"\r\n2,"z ""q"""\r\n');
  assert.deepEqual(filas, [{ a: '1', b: 'x, y' }, { a: '2', b: 'z "q"' }]);
});

test('sin resultados: estado explícito con comandos, sin reglas inventadas', async () => {
  const store = await loadDataSmartStore({ fetchImpl: fetchDeArchivos({}) });
  assert.equal(store.association.status, 'sin_resultados');
  const html = renderAssociationTab(store.association, { minLift: 0 });
  assert.ok(html.includes('py src/asociacion.py'));
  assert.ok(!html.includes('data-action="select-rule"'));
});

test('lee los CSV, muestra la población de referencia y verifica la trazabilidad', async () => {
  const store = await loadDataSmartStore({ fetchImpl: fetchDeArchivos(ARCHIVOS) });
  const a = store.association;
  assert.equal(a.status, 'ok');
  assert.equal(a.poblaciones.principal.reglas.length, 2);
  assert.equal(a.poblaciones.principal.reglas[1].conviccion, null);
  assert.equal(a.poblaciones.principal.verificacion.trazabilidadCompleta, true);
  assert.equal(a.poblaciones.multicategoria, undefined);
  const html = renderAssociationTab(a, { assocPopulation: 'principal', minLift: 0, selectedRuleId: 'AR-001' });
  assert.ok(html.includes(POB));
  assert.ok(html.includes('Cama, mesa y baño'));
  assert.ok(html.includes('3 rastreados · n_pedidos = 3'));
  assert.ok(html.includes('--poblacion multicategoria'));
});

test('detecta trazabilidad incompleta', async () => {
  const archivos = { ...ARCHIVOS, 'reglas_asociacion_trazabilidad.csv': 'regla_id,order_id\nAR-001,o1\n' };
  const store = await loadDataSmartStore({ fetchImpl: fetchDeArchivos(archivos) });
  const v = store.association.poblaciones.principal.verificacion;
  assert.equal(v.trazabilidadCompleta, false);
  assert.deepEqual(v.reglasInconsistentes, ['AR-001', 'AR-002']);
});

test('Bonferroni, p-valor y nombres de categorías', () => {
  const reglas = [
    { antecedente: 'a', consecuente: 'b' }, { antecedente: 'b', consecuente: 'a' },
    { antecedente: 'a', consecuente: 'c' }, { antecedente: 'c', consecuente: 'a' },
  ];
  const { conjuntos, umbral } = bonferroniThreshold(reglas);
  assert.equal(conjuntos, 2);
  assert.equal(umbral, 0.025);
  assert.equal(formatPValue(2.27e-19), '2.3e-19');
  assert.equal(formatPValue(0.00237075), '0.0024');
  assert.equal(categorySetLabel('bebes + categoria_rara'), 'Bebés + Categoria rara');
});

test('los KPI se actualizan con los CSV y conservan los valores si faltan', () => {
  const kpis = [
    { id: 'tasa_entregas_tardias', value: 0, formatted: '', unit: '', definition: '' },
    { id: 'calificacion_promedio', value: 4.09, formatted: '4,09 / 5,0' },
  ];
  const payload = {
    indicadores_kpi: [],
    indicadores_preparacion: [
      { indicador: 'tasa_entregas_tardias_calendario_pct', valor: '6.77309' },
      { indicador: 'entregas_tardias_calendario', valor: '6534' },
      { indicador: 'pedidos_entregados', valor: '96478' },
      { indicador: 'entregados_sin_fecha', valor: '8' },
    ],
  };
  const [tardias, calificacion] = aplicarKpisEnVivo(kpis, payload);
  assert.equal(tardias.formatted, '6,77 %');
  assert.equal(tardias.unit, '6.534 tardíos');
  assert.ok(tardias.definition.includes('96.470'));
  assert.equal(calificacion.formatted, '4,09 / 5,0');
});

test('la API reemplaza la serie mensual local con los resultados disponibles', async () => {
  const fetchImpl = async url => {
    if (url.endsWith('/api/resultados')) return { ok: true, json: async () => ({ status: 'ok', indicadores_kpi: [], indicadores_preparacion: [], ventas_mensuales: [] }) };
    if (url.endsWith('/api/series')) return { ok: true, json: async () => ({
      status: 'ok', resultados: { ventas_mensuales: { total: 1, filas: [{ order_purchase_timestamp: '2018-08-01', ventas_articulos_BRL: '1234.5' }] } },
    }) };
    if (url.endsWith('/api/asociacion')) return { ok: true, json: async () => ({ status: 'sin_resultados' }) };
    return { ok: true, json: async () => ({ status: 'sin_resultados' }) };
  };
  const store = await loadDataSmartStore({ fetchImpl });
  assert.equal(store.monthlySales.length, 1);
  assert.equal(store.monthlySales[0].date, '2018-08-01');
  assert.equal(store.monthlySales[0].salesBRL, 1234.5);
});

test('las visualizaciones temporales y de grafos usan filas y nodos reales recibidos', () => {
  const serie = renderSeriesTestSVG([
    { fecha: '2018-06-03', modelo: 'baseline', venta_real: '100', venta_predicha: '90' },
  ]);
  assert.ok(serie.includes('2018-06-03'));
  const grafo = renderOlistSubgraphSVG({
    total_nodos: 2, total_enlaces: 1,
    nodes: [
      { id: 'p1', label: 'Producto real', tipo: 'producto', grado_ponderado: 3 },
      { id: 'v1', label: 'Vendedor real', tipo: 'vendedor', grado_ponderado: 3 },
    ],
    links: [{ source: 'p1', target: 'v1', weight: 3 }],
  });
  assert.ok(grafo.includes('Producto real'));
  assert.ok(grafo.includes('Vendedor real'));
  assert.ok(grafo.includes('2 nodos'));
});

test('la vista de clasificación comunica métricas reales y el origen proxy de etiquetas', () => {
  const html = renderBusinessModelsView({
    businessQuestions: [], monthlySales: [], association: { status: 'sin_resultados' }, modules: {
      clasificacion: { status: 'ok', resultados: {
        evaluacion_clasificacion: { total: 1, filas: [{ accuracy: '0.8', precision_macro: '0.7', recall_macro: '0.6', f1_macro: '0.65', roc_auc_ovr_macro: '0.88', pr_auc_macro_ovr: '0.68', n_train: '100', n_test: '25', fecha_corte_test: '2020-01-01', matriz_confusion_json: '[[1,0,0],[0,1,0],[0,0,1]]' }] },
        clasificacion_metadata: { fecha_corte_test: '2020-01-01' },
      } }, nlp: { status: 'ok', resultados: {
        nlp_sentimientos: { total: 2, filas: [
          { origen_etiqueta: 'derivado_de_review_score', clase: 'positivo_score', cantidad: '7', porcentaje: '70' },
          { origen_etiqueta: 'calculado_desde_texto_lexico', clase: 'positivo_lexico', cantidad: '5', porcentaje: '50' },
        ] },
        nlp_terminos_frecuentes: { total: 1, filas: [{ referencia_sentimiento_score: 'positivo_score', termino: 'prazo', tfidf_medio: '0.2' }] },
      } },
    },
  }, { activeLabTab: 'nlp', selectedGraphNode: '' });
  assert.ok(html.includes('F1 macro'));
  assert.ok(html.includes('65.00%'));
  assert.ok(html.includes('derivadas de review_score'));
  assert.ok(html.includes('calculado_desde_texto_lexico'));
  assert.ok(html.includes('prazo'));
  assert.ok(!html.includes('chegou muito antes do prazo'));
});

test('la vista de monitoreo declara explícitamente su carácter retrospectivo', () => {
  const html = renderBusinessModelsView({
    businessQuestions: [], monthlySales: [], association: { status: 'sin_resultados' }, modules: {
      monitoring: { status: 'ok', resultados: {
        model_registry: { modo: 'retrospectivo_academico', tiempo_real: false, version_activa: 'sha-123', versiones: [], criterio_revision: 'PSI >= 0.25 revisar.' },
        model_history: { total: 1, filas: [{ model_version: 'sha-123' }] },
        monitoring_metrics: { total: 1, filas: [{ modelo: 'logistic', metrica: 'f1_macro', valor: '0.66', n_evaluacion: '100' }] },
        data_drift_report: { total: 1, filas: [{ variable: 'tokens', psi: '0.12', estado: 'cambio_moderado_revision' }] },
      } },
    },
  }, { activeLabTab: 'monitoring', selectedGraphNode: '' });
  assert.ok(html.includes('no es monitoreo en vivo'));
  assert.ok(html.includes('0,12'));
  assert.ok(html.includes('f1_macro'));
});

test('explicabilidad está separada de regresión y muestra contribuciones locales por clase', () => {
  const data = {
    businessQuestions: [], monthlySales: [], association: { status: 'sin_resultados' },
    modules: {
      regresion: { status: 'ok', resultados: { evaluacion_regresion: { total: 1, filas: [{ modelo: 'rf', mae_dias: '4.1', rmse_dias: '5.6', r2: '0.07', n_test: '100' }] } } },
      explicabilidad: { status: 'ok', resultados: {
        importancia_variables: { total: 3, filas: ['negativo', 'neutral', 'positivo'].map(clase => ({ clase, termino: `token_${clase}`, coeficiente_logit: '0.8', direccion: 'a_favor_de_clase' })) },
        explicaciones_locales: { total: 2, filas: [
          { review_id: 'review-1', clase_real: 'negativo', clase_predicha: 'negativo', probabilidad_predicha: '0.9', termino: 'atraso', contribucion_logit: '1.2', direccion: 'a_favor' },
          { review_id: 'review-1', clase_real: 'negativo', clase_predicha: 'negativo', probabilidad_predicha: '0.9', termino: 'rapido', contribucion_logit: '-0.3', direccion: 'en_contra' },
        ] },
      } },
    },
  };
  const reg = renderBusinessModelsView(data, { activeLabTab: 'logistics', selectedGraphNode: '' });
  assert.ok(reg.includes('random forest') || reg.includes('<strong>rf</strong>'));
  assert.ok(!reg.includes('Importancia global por clase'));
  assert.ok(!reg.includes('Explicabilidad del clasificador TF-IDF'));
  const explain = renderBusinessModelsView(data, { activeLabTab: 'explainability', selectedGraphNode: '' });
  assert.ok(explain.includes('Importancia global por clase'));
  assert.ok(explain.includes('token_negativo'));
  assert.ok(explain.includes('token_neutral'));
  assert.ok(explain.includes('token_positivo'));
  assert.ok(explain.includes('atraso'));
  assert.ok(explain.includes('no se calcula SHAP'));
  assert.ok(explain.includes('Reseña review-1'));
});

test('calidad y diccionario aceptan perfilado, incidencias y contrato generado', () => {
  const dictionary = [{ table: 'opiniones', column: 'review_comment_message', pandasType: 'object', sqlType: 'TEXT', nulls: 0, nullPct: 0, distinct: 0, meaning: 'fallback' }];
  const payload = {
    diccionario_perfilado: [{ tabla: 'opiniones', columna: 'review_comment_message', tipo_pandas: 'object', nulos: '2', porcentaje_nulos: '20', valores_distintos: '7' }],
    diccionario_datos: [{ tabla: 'opiniones', columna: 'review_comment_message', descripcion: 'Descripción calculada desde el contrato.' }],
    resumen_tablas: [{ tabla: 'opiniones', filas: '10', columnas: '7', celdas_nulas: '2', filas_duplicadas_exactas: '0' }],
    calidad_perfil_antes: [{ tabla: 'opiniones', columna: 'review_comment_title', nulos: '4', porcentaje_nulos: '40' }],
    calidad_validaciones: [{ resultado: 'OK' }, { resultado: 'ERROR' }],
    calidad_incidencias_resumen: { total_registros: 1, grupos: [{ tabla: 'opiniones', columna: 'review_comment_message', regla: 'comentario_invalido', afectados: 1, tratamiento: 'Verificar texto.' }] },
  };
  const liveDictionary = aplicarDiccionarioEnVivo(dictionary, payload);
  assert.equal(liveDictionary[0].nulls, 2);
  assert.equal(liveDictionary[0].distinct, 7);
  assert.equal(liveDictionary[0].meaning, 'Descripción calculada desde el contrato.');
  const quality = aplicarCalidadEnVivo([
    { table: 'opiniones', rows: 10, cols: 7, nullCells: 0, exactDuplicates: 0, file: 'reviews.csv' },
  ], [
    { id: 'DQ-01', table: 'opiniones', column: 'review_comment_title', nullCount: 0, pctRows: 0, severity: 'Media', treatment: 'respaldo' },
    { id: 'DQ-02', table: 'opiniones', column: 'review_comment_message', nullCount: 0, pctRows: 0, severity: 'Media', treatment: 'respaldo' },
  ], payload);
  assert.equal(quality.tablesSummary[0].nullCells, 2);
  assert.equal(quality.qualityIssues.find(issue => issue.id === 'DQ-01').nullCount, 4);
  assert.ok(quality.qualityIssues.some(issue => issue.id.startsWith('DQ-AUTO-')));
  const html = renderDataQualityView({
    tablesSummary: quality.tablesSummary, qualityIssues: quality.qualityIssues,
    treatmentPlan: [{ step: 7, title: 'Anti-leakage', description: 'Split temporal', status: 'Implementado' }],
    qualityValidations: payload.calidad_validaciones, qualityMetrics: { entregados_sin_fecha: 3 },
    liveQualityConnected: true,
  }, { severityFilter: 'ALL' });
  assert.ok(html.includes('70'));
  assert.ok(html.includes('3 pedidos'));
  assert.ok(html.includes('1 con resultado distinto de OK'));
  const dictionaryHtml = renderDataDictionaryView({ dictionary: liveDictionary, tablesSummary: quality.tablesSummary }, {
    dictTableFilter: 'ALL', dictSearchQuery: '', dictOnlyNulls: false,
  });
  assert.ok(dictionaryHtml.includes('Descripción calculada desde el contrato.'));
  assert.ok(dictionaryHtml.includes('7'));
});

test('PN-02 no presenta Pareto como terminado solo por tener RFM', () => {
  const html = renderBusinessModelsView({
    businessQuestions: [{ id: 'PN-02', area: 'Clientes', question: 'Pareto', technique: 'RFM', metrics: 'Pareto', targetWeek: 'Semana 16', summary: 'legacy', status: 'legacy' }],
    monthlySales: [], association: { status: 'sin_resultados' },
    modules: { clustering: { status: 'ok', resultados: { perfiles_clusters: { total: 2, filas: [] } } } },
  }, { activeLabTab: 'rfm', selectedGraphNode: '' });
  assert.ok(html.toLowerCase().includes('rfm disponible; la curva de pareto y sus métricas siguen pendientes.'));
});
