/**
 * Utilidades de formato numérico, monetario (BRL R$) y porcentajes
 * Alineado con las funciones `moneda_br` y `entero_es` de `src/eda_olist.py`.
 */

export function formatBRL(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return 'R$ 0,00';
  const num = Number(value);
  return 'R$ ' + num.toLocaleString('es-PE', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });
}

export function formatBRLCompact(value) {
  const num = Number(value) || 0;
  if (num >= 1_000_000) {
    return `R$ ${(num / 1_000_000).toFixed(2)}M`;
  }
  if (num >= 1_000) {
    return `R$ ${(num / 1_000).toFixed(1)}K`;
  }
  return formatBRL(num, 0);
}

export function formatInt(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '0';
  return Math.round(Number(value)).toLocaleString('es-PE');
}

export function formatPct(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '0%';
  return `${Number(value).toFixed(decimals)}%`;
}

export function exportToCSV(filename, rows) {
  if (!rows || !rows.length) return;
  const headers = Object.keys(rows[0]);
  const csvContent = [
    headers.join(','),
    ...rows.map(row =>
      headers
        .map(fieldName => {
          const val = row[fieldName] ?? '';
          const escaped = String(val).replace(/"/g, '""');
          return `"${escaped}"`;
        })
        .join(',')
    ),
  ].join('\n');

  const blob = new Blob(['\uFEFF' + csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', filename);
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
}
