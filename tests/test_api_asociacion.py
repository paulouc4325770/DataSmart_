"""Pruebas de /api/asociacion con resultados sintéticos pequeños."""

import importlib.util
import json
import os
from http.server import ThreadingHTTPServer
from pathlib import Path
import threading
from tempfile import TemporaryDirectory
import unittest
import urllib.request

RUTA_SERVIDOR = Path(__file__).resolve().parents[1] / 'frontend' / 'server.py'
spec = importlib.util.spec_from_file_location('datasmart_server', RUTA_SERVIDOR)
servidor = importlib.util.module_from_spec(spec)
spec.loader.exec_module(servidor)

ENCABEZADO_REGLAS = (
    'regla_id,antecedente,consecuente,soporte,confianza,lift,conviccion,p_valor,n_pedidos,'
    'n_pedidos_antecedente,n_pedidos_consecuente,soporte_antecedente,soporte_consecuente,'
    'asociacion_positiva,total_cestas,poblacion_referencia'
)


def escribir(ruta, texto):
    ruta.write_text(texto, encoding='utf-8-sig')


def crear_resultados(carpeta, sufijo='', total=100, inconsistente=False):
    poblacion = f'Poblacion de prueba; N={total}'
    escribir(carpeta / f'reglas_asociacion{sufijo}.csv', '\n'.join([
        ENCABEZADO_REGLAS,
        f'AR-001,cat_a,cat_b,0.03,0.3,2.5,1.2,0.001,3,10,12,0.1,0.12,True,{total},{poblacion}',
        f'AR-002,cat_b,cat_a,0.03,0.25,2.5,,0.001,3,12,10,0.12,0.1,True,{total},{poblacion}',
    ]) + '\n')
    traza = ['regla_id,order_id', 'AR-001,o1', 'AR-001,o2', 'AR-001,o3',
             'AR-002,o1', 'AR-002,o2']
    if not inconsistente:
        traza.append('AR-002,o3')
    escribir(carpeta / f'reglas_asociacion_trazabilidad{sufijo}.csv', '\n'.join(traza) + '\n')
    escribir(carpeta / f'comparacion_asociacion{sufijo}.csv', '\n'.join([
        'algoritmo,poblacion,conjuntos_frecuentes,reglas,reglas_en_comun,reglas_con_metricas_iguales,'
        'coincide_con_el_otro,tiempo_minimo_s,tiempo_mediana_s,repeticiones,min_pedidos,min_soporte,'
        'min_confianza,max_len,total_cestas',
        f'Apriori,todas,5,2,2,2,True,0.01,0.012,5,3,0.03,0.0,2,{total}',
        f'FP-Growth,todas,5,2,2,2,True,0.02,0.022,5,3,0.03,0.0,2,{total}',
    ]) + '\n')
    escribir(carpeta / f'umbrales_asociacion{sufijo}.csv', '\n'.join([
        'umbral_pedidos,soporte_equivalente,pares_frecuentes,pares_lift_mayor_1,umbral_elegido',
        '1,0.01,5,2,False', '3,0.03,1,1,True',
    ]) + '\n')
    (carpeta / f'asociacion_metadata{sufijo}.json').write_text(json.dumps({
        'poblacion_referencia': poblacion, 'total_cestas_analisis': total,
        'parametros': {'min_pedidos': 3, 'min_confianza': 0.0, 'max_len': 2},
        'pares_de_categorias_observados': 5, 'algoritmos_coinciden': True,
    }), encoding='utf-8')


class PruebasCargador(unittest.TestCase):
    def test_sin_resultados_indica_que_ejecutar(self):
        with TemporaryDirectory() as tmp:
            r = servidor.cargar_asociacion(Path(tmp))
        self.assertEqual(r['status'], 'sin_resultados')
        self.assertIn('reglas_asociacion.csv', r['faltantes'])
        self.assertTrue(any('asociacion.py' in c for c in r['comandos']))

    def test_carga_poblacion_principal_con_tipos_numericos(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            crear_resultados(tmp)
            escribir(tmp / 'composicion_cestas.csv', 'concepto,pedidos,pct_pedidos_entregados,'
                     'pct_universo,en_universo\nuniverso_total,100,100.0,100.0,True\n')
            r = servidor.cargar_asociacion(tmp)
        self.assertEqual(r['status'], 'ok')
        self.assertEqual(list(r['poblaciones']), ['principal'])
        self.assertEqual(r['faltantesOpcionales'], ['reglas_asociacion_multicategoria.csv',
                         'comparacion_asociacion_multicategoria.csv',
                         'reglas_asociacion_trazabilidad_multicategoria.csv',
                         'asociacion_metadata_multicategoria.json'])
        p = r['poblaciones']['principal']
        regla = p['reglas'][0]
        self.assertEqual(regla['nPedidos'], 3)
        self.assertIsInstance(regla['nPedidos'], int)
        self.assertEqual(regla['lift'], 2.5)
        self.assertTrue(regla['asociacionPositiva'])
        self.assertIsNone(p['reglas'][1]['conviccion'])
        self.assertEqual(p['trazabilidad']['AR-001'], ['o1', 'o2', 'o3'])
        self.assertTrue(p['verificacion']['trazabilidadCompleta'])
        self.assertEqual(p['totalCestas'], 100)
        self.assertEqual(p['poblacionReferencia'], 'Poblacion de prueba; N=100')
        self.assertTrue(all(c['coincide'] for c in p['comparacion']))
        self.assertEqual(r['composicion'][0]['pedidos'], 100)

    def test_incluye_la_poblacion_complementaria_con_su_propio_n(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            crear_resultados(tmp, total=100)
            crear_resultados(tmp, sufijo='_multicategoria', total=8)
            r = servidor.cargar_asociacion(tmp)
        self.assertEqual(list(r['poblaciones']), ['principal', 'multicategoria'])
        self.assertEqual(r['poblaciones']['multicategoria']['totalCestas'], 8)
        self.assertEqual(r['poblaciones']['principal']['totalCestas'], 100)
        self.assertEqual(r['faltantesOpcionales'], [])

    def test_detecta_trazabilidad_inconsistente(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            crear_resultados(tmp, inconsistente=True)
            r = servidor.cargar_asociacion(tmp)
        v = r['poblaciones']['principal']['verificacion']
        self.assertFalse(v['trazabilidadCompleta'])
        self.assertEqual(v['reglasInconsistentes'], ['AR-002'])


class PruebaHttp(unittest.TestCase):
    def test_endpoint_devuelve_json(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            crear_resultados(tmp)
            original = servidor.RESULTADOS_DIR
            servidor.RESULTADOS_DIR = tmp
            httpd = ThreadingHTTPServer(('127.0.0.1', 0), servidor.DataSmartHandler)
            hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
            hilo.start()
            try:
                url = f'http://127.0.0.1:{httpd.server_address[1]}/api/asociacion'
                with urllib.request.urlopen(url, timeout=10) as respuesta:
                    self.assertEqual(respuesta.status, 200)
                    self.assertIn('application/json', respuesta.headers['Content-Type'])
                    self.assertIn('no-store', respuesta.headers['Cache-Control'])
                    datos = json.loads(respuesta.read().decode('utf-8'))
            finally:
                httpd.shutdown()
                httpd.server_close()
                servidor.RESULTADOS_DIR = original
        self.assertEqual(datos['status'], 'ok')
        self.assertEqual(len(datos['poblaciones']['principal']['reglas']), 2)

    def test_recarga_css_actualizado_aunque_conserve_fecha_y_tamano(self):
        with TemporaryDirectory() as tmp:
            css = Path(tmp) / 'styles.css'
            css.write_text('body { color: #35627A; }', encoding='utf-8')
            fecha = css.stat()
            original = servidor.FRONTEND_DIR
            servidor.FRONTEND_DIR = Path(tmp)
            httpd = ThreadingHTTPServer(('127.0.0.1', 0), servidor.DataSmartHandler)
            hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
            hilo.start()
            try:
                url = f'http://127.0.0.1:{httpd.server_address[1]}/styles.css'
                with urllib.request.urlopen(url, timeout=10) as respuesta:
                    ultima_modificacion = respuesta.headers['Last-Modified']
                    self.assertIn(b'#35627A', respuesta.read())

                # Una edición rápida puede conservar el timestamp HTTP y el tamaño.
                css.write_text('body { color: #B46258; }', encoding='utf-8')
                os.utime(css, ns=(fecha.st_atime_ns, fecha.st_mtime_ns))
                peticion = urllib.request.Request(url, headers={
                    'If-Modified-Since': ultima_modificacion,
                })
                with urllib.request.urlopen(peticion, timeout=10) as respuesta:
                    self.assertEqual(respuesta.status, 200)
                    self.assertIn('no-store', respuesta.headers['Cache-Control'])
                    self.assertIn(b'#B46258', respuesta.read())
            finally:
                httpd.shutdown()
                httpd.server_close()
                servidor.FRONTEND_DIR = original


if __name__ == '__main__':
    unittest.main()
