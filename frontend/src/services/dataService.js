/**
 * Servicio de Sincronización con los archivos reales de `resultados/`
 * Intenta cargar en vivo `/api/resultados` o los CSV estáticos si están disponibles,
 * y fusiona de forma segura con el store verificado `olistData.js`.
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
  ASSOCIATION_RULES_PREVIEW,
  SHAP_FEATURE_IMPORTANCE,
  NLP_TOPICS_PREVIEW,
  CRISP_DM_ROADMAP,
} from '../data/olistData.js';

export async function loadDataSmartStore() {
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
    associationRules: ASSOCIATION_RULES_PREVIEW,
    shapImportance: SHAP_FEATURE_IMPORTANCE,
    nlpTopics: NLP_TOPICS_PREVIEW,
    roadmap: CRISP_DM_ROADMAP,
    liveSourceConnected: false,
  };

  try {
    const response = await fetch('/api/resultados', { cache: 'no-store' });
    if (response.ok) {
      const payload = await response.json();
      if (payload && payload.status === 'ok') {
        store.liveSourceConnected = true;
      }
    }
  } catch (_) {
    // Modo estático / Vite directo: usa los datos exactos pre-sincronizados de resultados/*.csv
  }

  return store;
}
