// Ejecutar desde la raíz del proyecto:  node --test frontend/tests/asociacion.test.mjs
import assert from 'node:assert/strict';
import test from 'node:test';
import { loadDataSmartStore, parseCsv, aplicarKpisEnVivo } from '../src/services/dataService.js';
import { renderAssociationTab, bonferroniThreshold, formatPValue } from '../src/views/associationView.js';
import { categorySetLabel } from '../src/data/categoryNames.js';

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
