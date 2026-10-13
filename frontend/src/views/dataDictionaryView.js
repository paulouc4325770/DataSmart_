/**
 * Módulo 3: Diccionario de Datos (53 Columnas) & Esquema Relacional Olist
 * Cubre la Sección 6 y Sección 10 (10.1 a 10.9) del Informe + `resultados/diccionario_perfilado.csv`.
 */

import { formatInt, formatPct } from '../utils/formatters.js';

export function renderDataDictionaryView(store, state) {
  const { dictionary, tablesSummary } = store;
  const { dictTableFilter, dictSearchQuery, dictOnlyNulls } = state;

  const tablesList = ['ALL', ...tablesSummary.map(t => t.table)];

  const filteredCols = dictionary.filter(col => {
    if (dictTableFilter !== 'ALL' && col.table !== dictTableFilter) return false;
    if (dictOnlyNulls && col.nulls === 0) return false;
    if (dictSearchQuery.trim() !== '') {
      const q = dictSearchQuery.toLowerCase();
      return (
        col.column.toLowerCase().includes(q) ||
        col.table.toLowerCase().includes(q) ||
        col.meaning.toLowerCase().includes(q) ||
        col.sqlType.toLowerCase().includes(q)
      );
    }
    return true;
  });

  const activeTableInfo =
    dictTableFilter !== 'ALL'
      ? tablesSummary.find(t => t.table === dictTableFilter)
      : null;

  return `
    <!-- Esquema Relacional Entidad-Relación de Olist (Sección 6) -->
    <section class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h3>🗺️ Arquitectura Relacional del Dataset Olist (9 Entidades)</h3>
          <p>
            Relaciones de clave primaria y foránea para la futura persistencia en <strong>PostgreSQL</strong> (Sección 6 y 10).
            Haz clic en cualquier entidad para filtrar sus columnas en el diccionario.
          </p>
        </div>
        <button class="btn" data-action="export-dictionary">
          ⬇ Exportar Diccionario Completo (CSV)
        </button>
      </div>

      <div class="grid-3">
        ${tablesSummary
          .map(t => {
            const isSelected = dictTableFilter === t.table;
            return `
            <div
              class="card"
              data-action="select-dict-table"
              data-table="${t.table}"
              style="padding:0.95rem 1.1rem; cursor:pointer; background:${
                isSelected ? 'var(--accent-primary-soft)' : 'var(--bg-secondary)'
              }; border-color:${isSelected ? 'var(--accent-primary)' : 'var(--border-subtle)'}; gap:0.45rem;"
            >
              <div style="display:flex; justify-content:space-between; align-items:center;">
                <strong style="font-size:0.92rem; color:var(--text-primary); text-transform:capitalize;">
                  📁 ${t.table}
                </strong>
                <span class="chip chip-blue">${t.cols} cols • ${formatInt(t.rows)} filas</span>
              </div>
              <div class="mono" style="font-size:0.73rem; color:var(--accent-primary);">
                PK: ${t.primaryKey}
              </div>
              <div style="font-size:0.76rem; color:var(--text-secondary);">
                ${t.grain}
              </div>
            </div>
          `;
          })
          .join('')}
      </div>
    </section>

    <!-- Controles de Búsqueda y Filtrado del Diccionario -->
    <section class="card">
      <div class="card-header">
        <div class="card-title-group">
          <h3>
            📖 Diccionario de Datos y Perfilado de Columnas
            <span class="chip chip-emerald">${filteredCols.length} de ${dictionary.length} columnas</span>
          </h3>
          <p>
            Comparativa entre <code>tipo_pandas</code> (inferido en <code>diccionario_perfilado.csv</code>) y
            <code>Tipo SQL PostgreSQL propuesto</code> (Sección 10 del Informe).
          </p>
        </div>

        <div style="display:flex; align-items:center; gap:0.65rem; flex-wrap:wrap;">
          <input
            type="text"
            class="search-input"
            style="padding-left:0.85rem; width:250px;"
            placeholder="Buscar columna, tabla o significado..."
            value="${dictSearchQuery}"
            data-action="dict-search-input"
          />
          <button
            class="tab-pill ${dictOnlyNulls ? 'active' : ''}"
            data-action="toggle-dict-only-nulls"
          >
            ⚠️ Solo con Nulos
          </button>
          ${
            dictTableFilter !== 'ALL'
              ? `<button class="btn" data-action="select-dict-table" data-table="ALL">Mostrar las 9 tablas</button>`
              : ''
          }
        </div>
      </div>

      <!-- Filtro rápido de tablas -->
      <div class="tabs-bar">
        ${tablesList
          .map(
            tbl => `
          <button
            class="tab-pill ${dictTableFilter === tbl ? 'active' : ''}"
            data-action="select-dict-table"
            data-table="${tbl}"
          >
            ${tbl === 'ALL' ? 'Todas (53)' : tbl}
          </button>
        `
          )
          .join('')}
      </div>

      ${
        activeTableInfo
          ? `
        <div class="method-note">
          <strong>Archivo origen:</strong> <code>${activeTableInfo.file}</code> |
          <strong>Filas:</strong> ${formatInt(activeTableInfo.rows)} |
          <strong>Clave propuesta:</strong> <code>${activeTableInfo.primaryKey}</code> |
          <strong>Estado:</strong> ${activeTableInfo.status}
        </div>
      `
          : ''
      }

      <div class="table-wrap">
        <table class="data-table">
          <thead>
            <tr>
              <th>Tabla</th>
              <th>Columna (Nombre Original)</th>
              <th>Tipo Pandas</th>
              <th>Tipo SQL Propuesto (PostgreSQL)</th>
              <th>Valores Distintos</th>
              <th>Nulos</th>
              <th>% Nulos</th>
              <th>Significado / Definición de Negocio</th>
            </tr>
          </thead>
          <tbody>
            ${
              filteredCols.length === 0
                ? `<tr><td colspan="8" style="text-align:center; padding:2rem; color:var(--text-muted);">No se encontraron columnas con los filtros actuales.</td></tr>`
                : filteredCols
                    .map(
                      col => `
                <tr>
                  <td>
                    <span class="chip chip-blue" style="text-transform:capitalize;">${col.table}</span>
                  </td>
                  <td class="mono"><strong>${col.column}</strong></td>
                  <td class="mono" style="color:var(--text-secondary);">${col.pandasType}</td>
                  <td class="mono" style="color:var(--accent-cyan);">${col.sqlType}</td>
                  <td class="mono">${formatInt(col.distinct)}</td>
                  <td class="mono" style="color:${col.nulls > 0 ? 'var(--accent-amber)' : 'var(--text-muted)'}">
                    ${formatInt(col.nulls)}
                  </td>
                  <td class="mono">
                    ${
                      col.nullPct > 0
                        ? `<span class="chip chip-amber">${formatPct(col.nullPct)}</span>`
                        : `<span style="color:var(--text-muted);">0,00%</span>`
                    }
                  </td>
                  <td style="font-size:0.8rem; color:var(--text-secondary);">${col.meaning}</td>
                </tr>
              `
                    )
                    .join('')
            }
          </tbody>
        </table>
      </div>
    </section>
  `;
}
