"""
Servidor de desarrollo y API ligera para el Frontend de DataSmart.
Sirve la aplicacion web de `frontend/` y expone los resultados generados
por `src/eda_olist.py` desde la carpeta `../resultados/`.

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


class DataSmartHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        req_path = parsed.path

        # Endpoint JSON en vivo leyendo los CSV generados en ../resultados/
        if req_path == "/api/resultados":
            payload = {
                "status": "ok",
                "source": "resultados/ (Olist Brazilian E-Commerce Dataset)",
                "indicadores_kpi": read_csv_as_dicts(RESULTADOS_DIR / "indicadores_kpi.csv"),
                "resumen_tablas": read_csv_as_dicts(RESULTADOS_DIR / "resumen_tablas.csv"),
                "ventas_mensuales": read_csv_as_dicts(RESULTADOS_DIR / "ventas_mensuales.csv"),
                "diccionario_perfilado": read_csv_as_dicts(RESULTADOS_DIR / "diccionario_perfilado.csv"),
            }
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)
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
