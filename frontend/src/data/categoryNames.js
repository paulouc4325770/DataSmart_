/**
 * Nombres en español de las categorías de producto de Olist (original en portugués).
 * Las categorías sin traducción conservan su nombre original, con guiones bajos
 * reemplazados por espacios.
 */

export const CATEGORY_NAMES_ES = {
  automotivo: 'Automotriz',
  bebes: 'Bebés',
  beleza_saude: 'Belleza y salud',
  brinquedos: 'Juguetes',
  cama_mesa_banho: 'Cama, mesa y baño',
  casa_conforto: 'Casa y confort',
  casa_construcao: 'Casa y construcción',
  construcao_ferramentas_iluminacao: 'Construcción, herramientas e iluminación',
  cool_stuff: 'Artículos originales (cool stuff)',
  eletronicos: 'Electrónicos',
  esporte_lazer: 'Deportes y ocio',
  ferramentas_jardim: 'Herramientas de jardín',
  informatica_acessorios: 'Accesorios de informática',
  moveis_decoracao: 'Muebles y decoración',
  moveis_escritorio: 'Muebles de oficina',
  papelaria: 'Papelería',
  perfumaria: 'Perfumería',
  relogios_presentes: 'Relojes y regalos',
  telefonia: 'Telefonía',
  utilidades_domesticas: 'Utilidades domésticas',
};

const SEPARADOR = ' + ';

export function categoryLabel(original) {
  if (CATEGORY_NAMES_ES[original]) return CATEGORY_NAMES_ES[original];
  const texto = String(original || '').replace(/_/g, ' ').trim();
  return texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : '';
}

/** Etiqueta para un conjunto de categorías unidas con " + ". */
export function categorySetLabel(unidas) {
  return String(unidas || '')
    .split(SEPARADOR)
    .map(categoryLabel)
    .join(SEPARADOR);
}
