"""
Servidor de desarrollo y API ligera para el Frontend de DataSmart.
Sirve la aplicacion web de `frontend/` y expone los resultados generados
por `src/eda_olist.py` y `src/asociacion.py` desde la carpeta `../resultados/`.

Endpoints:
    /api/resultados   indicadores del EDA y de la preparacion de datos.
    /api/asociacion   reglas de asociacion reales, comparacion de algoritmos,
                      composicion de cestas y pedidos que sustentan cada regla.

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
                "indicadores_preparacion": read_csv_as_dicts(
                    RESULTADOS_DIR / "calidad" / "indicadores_preparacion.csv"
                ),
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
