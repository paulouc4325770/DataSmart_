/**
 * Controlador Principal y Router SPA de DataSmart Frontend
 * Arquitectura Modular Senior Frontend — UNMSM FISI Minería de Datos
 */

import { loadDataSmartStore } from './services/dataService.js';
import { renderExecutiveDashboardView } from './views/executiveDashboardView.js';
import { renderDataQualityView } from './views/dataQualityView.js';
import { renderDataDictionaryView } from './views/dataDictionaryView.js';
import { renderBusinessModelsView } from './views/businessModelsView.js';
import { renderCrispDmRoadmapView } from './views/crispDmRoadmapView.js';
import { exportToCSV } from './utils/formatters.js';

const appState = {
  currentView: 'dashboard', // 'dashboard' | 'quality' | 'dictionary' | 'models' | 'roadmap'
  theme: 'dark',
  globalSearch: '',
  // Dashboard state
  excludeExtremeMonths: false,
  categoryLimit: 10,
  // Data Quality state
  severityFilter: 'ALL',
  // Data Dictionary state
  dictTableFilter: 'ALL',
  dictSearchQuery: '',
  dictOnlyNulls: false,
  // Business Models Workbench state
  activeLabTab: 'rfm',
  minLift: 1.8,
  forecastHorizon: 4,
  simDistanceKm: 650,
  simWeightGrams: 1800,
  simInterstate: true,
  selectedGraphNode: 'SP',
};

let dataStore = null;

const VIEW_METADATA = {
  dashboard: {
    section: 'Comprensión de los Datos & KPIs (Secciones 1, 6, 7 y 8)',
    title: 'Dashboard Ejecutivo & Análisis Exploratorio (EDA)',
  },
  quality: {
    section: 'Auditoría de Datos & Preprocesamiento (Sección 9)',
    title: 'Evaluación de Calidad de Datos y Plan de Tratamiento',
  },
  dictionary: {
    section: 'Gobierno de Datos & Esquema SQL (Secciones 6 y 10)',
    title: 'Diccionario de Datos (53 Columnas) & Modelo Relacional',
  },
  models: {
    section: 'Modelado & Explicabilidad (Sección 5 — PN-01 a PN-10)',
    title: 'Laboratorio de Preguntas de Negocio y Modelos Predictivos',
  },
  roadmap: {
    section: 'Metodología & Arquitectura (Secciones 11, 12 y 13)',
    title: 'Ciclo CRISP-DM, Stack Tecnológico y Hoja de Ruta',
  },
};

function renderActiveView() {
  switch (appState.currentView) {
    case 'dashboard':
      return renderExecutiveDashboardView(dataStore, appState);
    case 'quality':
      return renderDataQualityView(dataStore, appState);
    case 'dictionary':
      return renderDataDictionaryView(dataStore, appState);
    case 'models':
      return renderBusinessModelsView(dataStore, appState);
    case 'roadmap':
      return renderCrispDmRoadmapView(dataStore, appState);
    default:
      return renderExecutiveDashboardView(dataStore, appState);
  }
}

function renderAppShell() {
  const root = document.getElementById('app');
  if (!root || !dataStore) return;

  const activeMeta = VIEW_METADATA[appState.currentView] || VIEW_METADATA.dashboard;

  root.innerHTML = `
    <div class="app-shell">
      <!-- Sidebar de Navegación Principal -->
      <aside class="sidebar">
        <div class="sidebar-brand">
          <div class="brand-logo">DS</div>
          <div class="brand-text">
            <h1>DataSmart <span class="brand-badge">v1.0</span></h1>
            <p>Olist E-Commerce • UNMSM FISI</p>
          </div>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-section-label">Módulos Analíticos</div>
          <ul class="nav-list">
            <li>
              <button
                class="nav-btn ${appState.currentView === 'dashboard' ? 'active' : ''}"
                data-action="navigate"
                data-view="dashboard"
              >
                <span class="nav-btn-left">
                  <span class="nav-icon">📊</span>
                  <span>Dashboard & EDA</span>
                </span>
                <span class="nav-pill">8 KPIs</span>
              </button>
            </li>
            <li>
              <button
                class="nav-btn ${appState.currentView === 'quality' ? 'active' : ''}"
                data-action="navigate"
                data-view="quality"
              >
                <span class="nav-btn-left">
                  <span class="nav-icon">🛡️</span>
                  <span>Calidad de Datos</span>
                </span>
                <span class="nav-pill">7 Reglas</span>
              </button>
            </li>
            <li>
              <button
                class="nav-btn ${appState.currentView === 'dictionary' ? 'active' : ''}"
                data-action="navigate"
                data-view="dictionary"
              >
                <span class="nav-btn-left">
                  <span class="nav-icon">📖</span>
                  <span>Diccionario & SQL</span>
                </span>
                <span class="nav-pill">53 Cols</span>
              </button>
            </li>
            <li>
              <button
                class="nav-btn ${appState.currentView === 'models' ? 'active' : ''}"
                data-action="navigate"
                data-view="models"
              >
                <span class="nav-btn-left">
                  <span class="nav-icon">🧠</span>
                  <span>Modelos (PN-01..10)</span>
                </span>
                <span class="nav-pill">10 PN</span>
              </button>
            </li>
            <li>
              <button
                class="nav-btn ${appState.currentView === 'roadmap' ? 'active' : ''}"
                data-action="navigate"
                data-view="roadmap"
              >
                <span class="nav-btn-left">
                  <span class="nav-icon">🔄</span>
                  <span>Hoja de Ruta CRISP-DM</span>
                </span>
                <span class="nav-pill">Sem 7–16</span>
              </button>
            </li>
          </ul>
        </div>

        <div class="sidebar-section">
          <div class="sidebar-section-label">Accesos Directos por Técnica</div>
          <ul class="nav-list">
            <li>
              <button class="nav-btn" data-action="quick-lab" data-tab="rfm">
                <span class="nav-btn-left"><span class="nav-icon">👥</span><span>Segmentación RFM</span></span>
                <span class="nav-pill">PN-01</span>
              </button>
            </li>
            <li>
              <button class="nav-btn" data-action="quick-lab" data-tab="association">
                <span class="nav-btn-left"><span class="nav-icon">🛒</span><span>Reglas Asociación</span></span>
                <span class="nav-pill">PN-05</span>
              </button>
            </li>
            <li>
              <button class="nav-btn" data-action="quick-lab" data-tab="logistics">
                <span class="nav-btn-left"><span class="nav-icon">🚚</span><span>Logística & SHAP</span></span>
                <span class="nav-pill">PN-07</span>
              </button>
            </li>
            <li>
              <button class="nav-btn" data-action="quick-lab" data-tab="nlp">
                <span class="nav-btn-left"><span class="nav-icon">💬</span><span>Minería Texto NLP</span></span>
                <span class="nav-pill">PN-10</span>
              </button>
            </li>
          </ul>
        </div>

        <div class="sidebar-footer">
          <div class="crisp-status-box">
            <div class="crisp-status-header">
              <span><span class="status-dot"></span>Dataset Olist</span>
              <span class="mono">99.441 filas</span>
            </div>
            <div class="progress-bar-track">
              <div class="progress-bar-fill" style="width: 100%;"></div>
            </div>
            <div style="color:var(--text-secondary); font-size:0.72rem; display:flex; justify-content:space-between;">
              <span>9 archivos CSV</span>
              <span>R$ 13,22M</span>
            </div>
          </div>
        </div>
      </aside>

      <!-- Contenedor Principal -->
      <div class="main-wrapper">
        <header class="top-header">
          <div class="header-left">
            <div class="header-breadcrumb">
              <span class="crumb-top">${activeMeta.section}</span>
              <span class="crumb-title">${activeMeta.title}</span>
            </div>
          </div>

          <div class="header-actions">
            <div class="search-input-wrap">
              <span class="search-icon">🔍</span>
              <input
                type="text"
                class="search-input"
                placeholder="Buscar columna en diccionario..."
                value="${appState.dictSearchQuery}"
                data-action="global-search"
              />
            </div>

            <button class="btn" data-action="toggle-theme" title="Cambiar tema Oscuro / Claro">
              ${appState.theme === 'dark' ? '☀️ Modo Claro' : '🌙 Modo Oscuro'}
            </button>

            <a
              class="btn"
              href="${dataStore.meta.repoUrl}"
              target="_blank"
              rel="noopener noreferrer"
              title="Abrir repositorio en GitHub"
            >
              GitHub ↗
            </a>
          </div>
        </header>

        <main class="main-content">
          ${renderActiveView()}
        </main>
      </div>
    </div>
  `;
}

function attachGlobalListeners() {
  const root = document.getElementById('app');
  if (!root) return;

  root.addEventListener('click', event => {
    const graphNode = event.target.closest('.graph-node');
    if (graphNode) {
      const nodeId = graphNode.getAttribute('data-node-id');
      if (nodeId) {
        appState.selectedGraphNode = nodeId;
        renderAppShell();
        return;
      }
    }

    const target = event.target.closest('[data-action]');
    if (!target) return;

    const action = target.getAttribute('data-action');

    switch (action) {
      case 'navigate': {
        const view = target.getAttribute('data-view');
        if (view) {
          appState.currentView = view;
          window.scrollTo({ top: 0, behavior: 'smooth' });
          renderAppShell();
        }
        break;
      }

      case 'quick-lab': {
        const tab = target.getAttribute('data-tab');
        if (tab) {
          appState.currentView = 'models';
          appState.activeLabTab = tab;
          window.scrollTo({ top: 0, behavior: 'smooth' });
          renderAppShell();
        }
        break;
      }

      case 'toggle-theme': {
        appState.theme = appState.theme === 'dark' ? 'light' : 'dark';
        document.documentElement.classList.toggle('light', appState.theme === 'light');
        document.documentElement.classList.toggle('dark', appState.theme === 'dark');
        renderAppShell();
        break;
      }

      case 'toggle-extreme-months': {
        appState.excludeExtremeMonths = target.getAttribute('data-value') === 'true';
        renderAppShell();
        break;
      }

      case 'set-category-limit': {
        appState.categoryLimit = Number(target.getAttribute('data-limit')) || 10;
        renderAppShell();
        break;
      }

      case 'set-quality-severity': {
        appState.severityFilter = target.getAttribute('data-severity') || 'ALL';
        renderAppShell();
        break;
      }

      case 'select-dict-table': {
        appState.dictTableFilter = target.getAttribute('data-table') || 'ALL';
        renderAppShell();
        break;
      }

      case 'toggle-dict-only-nulls': {
        appState.dictOnlyNulls = !appState.dictOnlyNulls;
        renderAppShell();
        break;
      }

      case 'set-lab-tab': {
        appState.activeLabTab = target.getAttribute('data-tab') || 'rfm';
        renderAppShell();
        break;
      }

      case 'set-forecast-horizon': {
        appState.forecastHorizon = Number(target.getAttribute('data-horizon')) || 4;
        renderAppShell();
        break;
      }

      case 'toggle-sim-interstate': {
        appState.simInterstate = !appState.simInterstate;
        renderAppShell();
        break;
      }

      case 'select-graph-node': {
        appState.selectedGraphNode = target.getAttribute('data-node') || 'SP';
        renderAppShell();
        break;
      }

      case 'export-kpis': {
        exportToCSV('datasmart_indicadores_kpi.csv', dataStore.kpis);
        break;
      }

      case 'export-monthly-sales': {
        exportToCSV('datasmart_ventas_mensuales.csv', dataStore.monthlySales);
        break;
      }

      case 'export-dictionary': {
        exportToCSV('datasmart_diccionario_perfilado.csv', dataStore.dictionary);
        break;
      }

      default:
        break;
    }
  });

  root.addEventListener('input', event => {
    const target = event.target;
    const action = target.getAttribute('data-action');
    if (!action) return;

    if (action === 'dict-search-input') {
      appState.dictSearchQuery = target.value;
      const cursorPos = target.selectionStart;
      renderAppShell();
      const newInput = root.querySelector('[data-action="dict-search-input"]');
      if (newInput) {
        newInput.focus();
        newInput.setSelectionRange(cursorPos, cursorPos);
      }
    } else if (action === 'global-search') {
      appState.dictSearchQuery = target.value;
      appState.currentView = 'dictionary';
      const cursorPos = target.selectionStart;
      renderAppShell();
      const newInput = root.querySelector('[data-action="global-search"]');
      if (newInput) {
        newInput.focus();
        newInput.setSelectionRange(cursorPos, cursorPos);
      }
    } else if (action === 'change-min-lift') {
      appState.minLift = Number(target.value);
      renderAppShell();
    } else if (action === 'sim-distance') {
      appState.simDistanceKm = Number(target.value);
      renderAppShell();
    } else if (action === 'sim-weight') {
      appState.simWeightGrams = Number(target.value);
      renderAppShell();
    }
  });
}

async function bootstrap() {
  dataStore = await loadDataSmartStore();
  renderAppShell();
  attachGlobalListeners();
}

bootstrap();
