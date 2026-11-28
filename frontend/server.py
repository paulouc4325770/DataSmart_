"""
Servidor de desarrollo y API ligera para el Frontend de DataSmart.
Sirve la aplicacion web de `frontend/` y expone los resultados generados
por `src/eda_olist.py` y `src/asociacion.py` desde la carpeta `../resultados/`.

Endpoints:
    /api/resultados   indicadores del EDA y de la preparacion de datos.
    /api/asociacion   reglas reales, comparación de Apriori/FP-Growth/ECLAT y trazabilidad.
    /api/{clustering,series,grafos,regresion,clasificacion,nlp,explicabilidad,monitoring,modelos}
                      contratos de resultados precalculados desde resultados/.

Ejecucion:
    py frontend/server.py
"""

from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import json
import csv
import mimetypes
import urllib.parse

FRONTEND_DIR = Path(__file__).resolve().parent
ROOT_DIR = FRONTEND_DIR.parent
RESULTADOS_DIR = ROOT_DIR / "resultados"
PORT = 8080


def read_csv_as_dicts(csv_path: Path):
    if not csv_path.exists():
        return []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def resumir_incidencias_calidad(csv_path: Path):
    """Agrega incidencias por regla sin enviar miles de registros a la UI."""
    if not csv_path.is_file():
        return {"total_registros": 0, "grupos": []}
    grupos = {}
    total = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as archivo:
        for fila in csv.DictReader(archivo):
            clave = (fila.get("tabla", ""), fila.get("columna", ""), fila.get("regla", ""))
            item = grupos.setdefault(clave, {
                "tabla": clave[0], "columna": clave[1], "regla": clave[2],
                "afectados": 0, "tratamiento": fila.get("tratamiento", ""),
            })
            try:
                item["afectados"] += int(float(fila.get("afectados") or 0))
            except (TypeError, ValueError):
                pass
            total += 1
    return {"total_registros": total, "grupos": sorted(
        grupos.values(), key=lambda item: (-item["afectados"], item["tabla"], item["regla"]),
    )}


def _read_json(path: Path):
    if not path.is_file():
        raise FileNotFoundError(path.name)
    return json.loads(path.read_text(encoding="utf-8-sig"))


def validar_procedencia_subgrafo(metadata, subgrafo):
    """Evita servir el subgrafo si no corresponde al último artefacto de grafo."""
    if not isinstance(metadata, dict) or not isinstance(subgrafo, dict):
        return False, "Falta metadata o grafo_subgrafo.json."
    run_id = metadata.get("run_id")
    visualizacion = metadata.get("visualizacion") or {}
    if not run_id or run_id != subgrafo.get("run_id") or run_id != visualizacion.get("run_id"):
        return False, "run_id ausente o distinto entre grafo y subgrafo."
    if not metadata.get("sha256_entrada") or metadata.get("sha256_entrada") != subgrafo.get("sha256_entrada"):
        return False, "El hash de entrada del subgrafo no corresponde a la ejecución actual."
    if not metadata.get("ejecutado_en_utc") or metadata.get("ejecutado_en_utc") != subgrafo.get("ejecutado_en_utc"):
        return False, "La fecha de ejecución del subgrafo no corresponde a la metadata actual."
    nodos = subgrafo.get("nodes")
    enlaces = subgrafo.get("links")
    if not isinstance(nodos, list) or not isinstance(enlaces, list):
        return False, "El subgrafo no contiene listas nodes y links válidas."
    esperados = visualizacion
    if len(nodos) != esperados.get("nodos") or len(enlaces) != esperados.get("aristas"):
        return False, "Los conteos nodes/links no concilian con metadata.visualizacion."
    if subgrafo.get("total_nodos") != len(nodos) or subgrafo.get("total_enlaces") != len(enlaces):
        return False, "Los totales declarados no concilian con nodes/links."
    if subgrafo.get("total_grafo_nodos") != metadata.get("nodos") or subgrafo.get("total_grafo_aristas") != metadata.get("aristas"):
        return False, "El subgrafo refiere a una red completa distinta de la metadata."
    ids = {nodo.get("id") for nodo in nodos if isinstance(nodo, dict)}
    if len(ids) != len(nodos):
        return False, "Hay identificadores de nodo ausentes o duplicados."
    if any(not isinstance(link, dict) or link.get("source") not in ids or link.get("target") not in ids for link in enlaces):
        return False, "Hay enlaces cuyo origen o destino no pertenece a la muestra de nodos."
    return True, "ok"


def cargar_modulo(resultados_dir: Path, modulo: str):
    """Carga resultados reales con tamaños acotados para la interfaz."""
    contratos = {
        "clustering": {"csv": ["perfiles_clusters.csv", "evaluacion_clustering.csv", "rfm_distribuciones.csv", "perfiles_clusters_dbscan.csv", "evaluacion_clustering_dbscan.csv"], "json": ["clustering_metadata.json", "clustering_dbscan_metadata.json"]},
        "series": {"csv": ["ventas_mensuales.csv", "pronosticos_ventas.csv", "evaluacion_series.csv"], "json": ["series_temporales_metadata.json"]},
        "regresion": {"csv": ["evaluacion_regresion.csv", "predicciones_entrega.csv"], "json": ["regresion_metadata.json"]},
        # `grafos.py` publica grafos_metadata.json; el cargador contempla el
        # nombre histórico grafo_metadata.json como fallback, no como duplicado.
        "grafos": {"csv": ["grafo_aristas.csv", "grafo_metricas.csv", "grafo_componentes.csv"], "json": ["grafo_subgrafo.json", "grafos_metadata.json"]},
        "modelos": {"csv": ["evaluacion_comparativa.csv"], "json": ["evaluacion_comparativa_resumen.json"]},
        "clasificacion": {"csv": ["evaluacion_clasificacion.csv", "predicciones_clasificacion.csv"], "json": ["clasificacion_metadata.json"]},
        "nlp": {"csv": ["nlp_terminos_frecuentes.csv", "nlp_coocurrencias.csv", "nlp_sentimientos.csv"], "json": ["nlp_metadata.json"]},
        "explicabilidad": {"csv": ["importancia_variables.csv", "explicaciones_locales.csv"], "json": ["explicabilidad_metadata.json"]},
        "monitoring": {"csv": ["monitoring_metrics.csv", "data_drift_report.csv", "audit_log.csv", "model_history.csv"], "json": ["model_registry.json"]},
    }
    if modulo not in contratos:
        return {"status": "no_encontrado", "mensaje": "Módulo desconocido."}
    contrato = contratos[modulo]
    json_files = list(contrato["json"])
    if modulo == "grafos" and not (resultados_dir / "grafos_metadata.json").is_file():
        json_files.append("grafo_metadata.json")
    # Algunos contratos admiten salidas parciales (p. ej. no hay modelo supervisado).
    existentes = [n for n in contrato["csv"] + json_files if (resultados_dir / n).is_file()]
    if not existentes:
        return {"status": "sin_resultados", "modulo": modulo,
                "mensaje": "Los resultados de este módulo aún no se han generado.",
                "faltantes": contrato["csv"] + json_files}
    datos = {"status": "ok", "source": "resultados/", "modulo": modulo, "resultados": {}}
    for nombre in contrato["csv"]:
        ruta = resultados_dir / nombre
        if ruta.is_file():
            filas = read_csv_as_dicts(ruta)
            # Las predicciones/metricas de grafos pueden ser grandes; la UI recibe muestra y N.
            datos["resultados"][ruta.stem] = {"total": len(filas), "filas": filas[:1000]}
    for nombre in json_files:
        ruta = resultados_dir / nombre
        if ruta.is_file():
            datos["resultados"][ruta.stem] = _read_json(ruta)
    datos["faltantes"] = [n for n in contrato["csv"] + json_files if not (resultados_dir / n).is_file()]
    if modulo == "grafos":
        metadata = datos["resultados"].get("grafos_metadata") or datos["resultados"].get("grafo_metadata")
        subgrafo = datos["resultados"].get("grafo_subgrafo")
        valido, motivo = validar_procedencia_subgrafo(metadata, subgrafo)
        if not valido:
            datos["resultados"].pop("grafo_subgrafo", None)
            datos["status"] = "parcial"
            datos["advertencias"] = [motivo]
            if "grafo_subgrafo.json" not in datos["faltantes"]:
                datos["faltantes"].append("grafo_subgrafo.json (obsoleto o incompatible)")
    return datos


POBLACIONES_ASOCIACION = {
    "principal": {
        "sufijo": "",
        "etiqueta": "Todas las cestas (análisis principal)",
    },
    "multicategoria": {
        "sufijo": "_multicategoria",
        "etiqueta": "Solo cestas multicategoría (análisis complementario)",
    },
}
COMANDOS_ASOCIACION = [
    "py src/asociacion.py",
    "py src/asociacion.py --poblacion multicategoria",
]


def _a_numero(valor, tipo=float):
    """Convierte texto de CSV a numero; devuelve None si esta vacio."""
    if valor is None or str(valor).strip() == "":
        return None
    return tipo(float(valor)) if tipo is int else tipo(valor)


def _regla_desde_fila(fila):
    return {
        "id": fila["regla_id"],
        "antecedente": fila["antecedente"],
        "consecuente": fila["consecuente"],
        "soporte": _a_numero(fila["soporte"]),
        "confianza": _a_numero(fila["confianza"]),
        "lift": _a_numero(fila["lift"]),
        "conviccion": _a_numero(fila.get("conviccion")),
        "pValor": _a_numero(fila.get("p_valor")),
        "nPedidos": _a_numero(fila["n_pedidos"], int),
        "nPedidosAntecedente": _a_numero(fila["n_pedidos_antecedente"], int),
        "nPedidosConsecuente": _a_numero(fila["n_pedidos_consecuente"], int),
        "soporteAntecedente": _a_numero(fila["soporte_antecedente"]),
        "soporteConsecuente": _a_numero(fila["soporte_consecuente"]),
        "asociacionPositiva": fila["asociacion_positiva"] == "True",
        "totalCestas": _a_numero(fila["total_cestas"], int),
        "poblacionReferencia": fila["poblacion_referencia"],
    }


def _comparacion_desde_fila(fila):
    return {
        "algoritmo": fila["algoritmo"],
        "conjuntosFrecuentes": _a_numero(fila["conjuntos_frecuentes"], int),
        "reglas": _a_numero(fila["reglas"], int),
        "reglasEnComun": _a_numero(fila["reglas_en_comun"], int),
        "coincide": fila["coincide_con_el_otro"] == "True",
        "tiempoMinimoS": _a_numero(fila["tiempo_minimo_s"]),
        "tiempoMedianaS": _a_numero(fila["tiempo_mediana_s"]),
        "repeticiones": _a_numero(fila["repeticiones"], int),
    }


def _umbral_desde_fila(fila):
    return {
        "umbralPedidos": _a_numero(fila["umbral_pedidos"], int),
        "soporteEquivalente": _a_numero(fila["soporte_equivalente"]),
        "paresFrecuentes": _a_numero(fila["pares_frecuentes"], int),
        "paresLiftMayor1": _a_numero(fila["pares_lift_mayor_1"], int),
        "elegido": fila["umbral_elegido"] == "True",
    }


def cargar_poblacion_asociacion(resultados_dir: Path, clave: str):
    """Carga una poblacion de analisis (principal o multicategoria).

    Devuelve ``(datos, faltantes)``. Si falta algun archivo, ``datos`` es None.
    """
    sufijo = POBLACIONES_ASOCIACION[clave]["sufijo"]
    rutas = {
        "reglas": resultados_dir / f"reglas_asociacion{sufijo}.csv",
        "comparacion": resultados_dir / f"comparacion_asociacion{sufijo}.csv",
        "trazabilidad": resultados_dir / f"reglas_asociacion_trazabilidad{sufijo}.csv",
        "metadata": resultados_dir / f"asociacion_metadata{sufijo}.json",
    }
    faltantes = [ruta.name for ruta in rutas.values() if not ruta.is_file()]
    if faltantes:
        return None, faltantes

    reglas = [_regla_desde_fila(f) for f in read_csv_as_dicts(rutas["reglas"])]
    trazabilidad = {}
    for fila in read_csv_as_dicts(rutas["trazabilidad"]):
        trazabilidad.setdefault(fila["regla_id"], []).append(fila["order_id"])
    metadata = json.loads(rutas["metadata"].read_text(encoding="utf-8-sig"))

    # Criterio de cierre: cada regla se rastrea hasta sus cestas originales.
    inconsistentes = [
        r["id"] for r in reglas if len(trazabilidad.get(r["id"], [])) != r["nPedidos"]
    ]
    umbrales = [
        _umbral_desde_fila(f)
        for f in read_csv_as_dicts(resultados_dir / f"umbrales_asociacion{sufijo}.csv")
    ]
    return {
        "clave": clave,
        "etiqueta": POBLACIONES_ASOCIACION[clave]["etiqueta"],
        "poblacionReferencia": metadata.get("poblacion_referencia", ""),
        "totalCestas": metadata.get("total_cestas_analisis"),
        "parametros": metadata.get("parametros", {}),
        "paresObservados": metadata.get("pares_de_categorias_observados"),
        "algoritmosCoinciden": bool(metadata.get("algoritmos_coinciden")),
        "reglas": reglas,
        "comparacion": [_comparacion_desde_fila(f) for f in read_csv_as_dicts(rutas["comparacion"])],
        "umbrales": umbrales,
        "trazabilidad": trazabilidad,
        "verificacion": {
            "trazabilidadCompleta": not inconsistentes,
            "reglasInconsistentes": inconsistentes,
        },
    }, []


def cargar_asociacion(resultados_dir: Path):
    """Arma la respuesta de /api/asociacion a partir de los CSV de resultados/."""
    principal, faltantes = cargar_poblacion_asociacion(resultados_dir, "principal")
    if principal is None:
        return {
            "status": "sin_resultados",
            "mensaje": "Aún no se generaron los resultados de asociación.",
            "faltantes": faltantes,
            "comandos": COMANDOS_ASOCIACION,
        }
    poblaciones = {"principal": principal}
    opcionales = []
    complementaria, faltantes_comp = cargar_poblacion_asociacion(resultados_dir, "multicategoria")
    if complementaria is None:
        opcionales = faltantes_comp
    else:
        poblaciones["multicategoria"] = complementaria

    composicion = []
    for fila in read_csv_as_dicts(resultados_dir / "composicion_cestas.csv"):
        composicion.append({
            "concepto": fila["concepto"],
            "pedidos": _a_numero(fila["pedidos"], int),
            "pctPedidosEntregados": _a_numero(fila["pct_pedidos_entregados"]),
            "pctUniverso": _a_numero(fila["pct_universo"]),
            "enUniverso": fila["en_universo"] == "True",
        })
    return {
        "status": "ok",
        "source": "resultados/ (src/asociacion.py)",
        "composicion": composicion,
        "poblaciones": poblaciones,
        "faltantesOpcionales": opcionales,
    }


class DataSmartHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def end_headers(self):
        # Servidor local de desarrollo: cada visita debe cargar los recursos actuales.
        self.send_header("Cache-Control", "no-store, no-cache, max-age=0, must-revalidate")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_head(self):
        # Evitar respuestas 304 al recargar HTML, CSS y módulos durante el desarrollo.
        if "If-Modified-Since" in self.headers:
            del self.headers["If-Modified-Since"]
        return super().send_head()

    def send_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        req_path = parsed.path

        if req_path.startswith("/api/") and req_path[5:] in {
            "clustering", "series", "grafos", "regresion", "clasificacion",
            "nlp", "explicabilidad", "monitoring", "modelos",
        }:
            try:
                self.send_json(cargar_modulo(RESULTADOS_DIR, req_path[5:]))
            except (OSError, ValueError, csv.Error) as error:
                self.send_json({"status": "error", "mensaje": "No se pudieron leer los resultados.",
                                "detalle": str(error)}, status=500)
            return

        # Reglas de asociacion reales (src/asociacion.py) con trazabilidad.
        if req_path == "/api/asociacion":
            try:
                self.send_json(cargar_asociacion(RESULTADOS_DIR))
            except (OSError, ValueError, KeyError) as error:
                self.send_json({
                    "status": "error",
                    "mensaje": f"No se pudieron leer los resultados de asociación: {error}",
                    "comandos": COMANDOS_ASOCIACION,
                }, status=500)
            return

        # Endpoint JSON en vivo leyendo los CSV generados en ../resultados/
        if req_path == "/api/resultados":
            payload = {
                "status": "ok",
                "source": "resultados/ (Olist Brazilian E-Commerce Dataset)",
                "indicadores_kpi": read_csv_as_dicts(RESULTADOS_DIR / "indicadores_kpi.csv"),
                "resumen_tablas": read_csv_as_dicts(RESULTADOS_DIR / "resumen_tablas.csv"),
                "ventas_mensuales": read_csv_as_dicts(RESULTADOS_DIR / "ventas_mensuales.csv"),
                "diccionario_perfilado": read_csv_as_dicts(RESULTADOS_DIR / "diccionario_perfilado.csv"),
                "diccionario_datos": read_csv_as_dicts(RESULTADOS_DIR / "diccionario_datos.csv"),
                "diccionario_procesados": read_csv_as_dicts(RESULTADOS_DIR / "diccionario_procesados.csv"),
                "diccionario_variables_derivadas": read_csv_as_dicts(RESULTADOS_DIR / "diccionario_variables_derivadas.csv"),
                "indicadores_preparacion": read_csv_as_dicts(
                    RESULTADOS_DIR / "calidad" / "indicadores_preparacion.csv"
                ),
                "calidad_perfil_antes": read_csv_as_dicts(RESULTADOS_DIR / "calidad" / "perfil_antes.csv"),
                "calidad_perfil_despues": read_csv_as_dicts(RESULTADOS_DIR / "calidad" / "perfil_despues.csv"),
                "calidad_validaciones": read_csv_as_dicts(RESULTADOS_DIR / "calidad" / "validaciones.csv"),
                "calidad_incidencias_resumen": resumir_incidencias_calidad(
                    RESULTADOS_DIR / "calidad" / "incidencias.csv"
                ),
                "calidad_metadata": _read_json(RESULTADOS_DIR / "calidad" / "metadata.json")
                if (RESULTADOS_DIR / "calidad" / "metadata.json").is_file() else {},
            }
            self.send_json(payload)
            return

        # Servir archivos estaticos de ../resultados/ (CSV y graficos PNG)
        if req_path.startswith("/resultados/"):
            rel = req_path[len("/resultados/"):]
            target = (RESULTADOS_DIR / rel).resolve()
            if str(target).startswith(str(RESULTADOS_DIR.resolve())) and target.is_file():
                ctype, _ = mimetypes.guess_type(str(target))
                data = target.read_bytes()
                self.send_response(200)
                self.send_header("Content-Type", ctype or "application/octet-stream")
                self.send_header("Content-Length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)
                return

        return super().do_GET()


def main():
    server = ThreadingHTTPServer(("127.0.0.1", PORT), DataSmartHandler)
    print("=" * 64)
    print(" DataSmart Frontend & Analytics Server")
    print(f" URL Local : http://localhost:{PORT}")
    print(f" API Datos : http://localhost:{PORT}/api/resultados")
    print(f" API Reglas: http://localhost:{PORT}/api/asociacion")
    print(f" Graficos  : {RESULTADOS_DIR / 'graficos'}")
    print("=" * 64)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nServidor detenido.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
