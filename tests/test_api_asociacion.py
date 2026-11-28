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
    def test_modulo_real_lee_contrato_csv_y_json(self):
        with TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            escribir(carpeta / 'perfiles_clusters.csv', 'cluster,cantidad\n0,12\n')
            (carpeta / 'clustering_metadata.json').write_text('{"k_seleccionado": 2}', encoding='utf-8')
            resultado = servidor.cargar_modulo(carpeta, 'clustering')
        self.assertEqual(resultado['status'], 'ok')
        self.assertEqual(resultado['resultados']['perfiles_clusters']['total'], 1)
        self.assertEqual(resultado['resultados']['clustering_metadata']['k_seleccionado'], 2)

    def test_modulo_ausente_no_inventa_resultados(self):
        with TemporaryDirectory() as tmp:
            resultado = servidor.cargar_modulo(Path(tmp), 'nlp')
        self.assertEqual(resultado['status'], 'sin_resultados')
        self.assertIn('nlp_metadata.json', resultado['faltantes'])

    def test_grafos_usa_metadatos_actuales_y_subgrafo(self):
        with TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            escribir(carpeta / 'grafo_metricas.csv', 'pagerank\n0.2\n')
            escribir(carpeta / 'grafo_aristas.csv', 'peso\n3\n')
            run_id = 'run-valid'
            when = '2026-11-27T12:00:00+00:00'
            meta = {'run_id': run_id, 'sha256_entrada': 'sha-items', 'ejecutado_en_utc': when,
                    'nodos': 2, 'aristas': 1, 'visualizacion': {'run_id': run_id, 'nodos': 2, 'aristas': 1}}
            subgrafo = {'run_id': run_id, 'sha256_entrada': 'sha-items', 'ejecutado_en_utc': when,
                        'total_nodos': 2, 'total_enlaces': 1, 'total_grafo_nodos': 2,
                        'total_grafo_aristas': 1,
                        'nodes': [{'id': 'p:p1'}, {'id': 'v:v1'}],
                        'links': [{'source': 'p:p1', 'target': 'v:v1', 'weight': 3}]}
            (carpeta / 'grafos_metadata.json').write_text(json.dumps(meta), encoding='utf-8')
            (carpeta / 'grafo_metadata.json').write_text('{"total_nodos": 99}', encoding='utf-8')
            (carpeta / 'grafo_subgrafo.json').write_text(json.dumps(subgrafo), encoding='utf-8')
            resultado = servidor.cargar_modulo(carpeta, 'grafos')
        self.assertEqual(resultado['status'], 'ok')
        self.assertIn('grafos_metadata', resultado['resultados'])
        self.assertNotIn('grafo_metadata', resultado['resultados'])
        self.assertEqual(resultado['resultados']['grafo_subgrafo']['total_nodos'], 2)

    def test_rechaza_subgrafo_de_otra_ejecucion(self):
        with TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            meta = {'run_id': 'run-new', 'sha256_entrada': 'sha-new',
                    'ejecutado_en_utc': '2026-11-27T12:00:00+00:00', 'nodos': 2, 'aristas': 1,
                    'visualizacion': {'run_id': 'run-new', 'nodos': 2, 'aristas': 1}}
            old = {'run_id': 'run-old', 'sha256_entrada': 'sha-old',
                   'ejecutado_en_utc': '2026-11-26T12:00:00+00:00', 'total_nodos': 2,
                   'total_enlaces': 1, 'total_grafo_nodos': 2, 'total_grafo_aristas': 1,
                   'nodes': [{'id': 'p:p1'}, {'id': 'v:v1'}],
                   'links': [{'source': 'p:p1', 'target': 'v:v1', 'weight': 1}]}
            (carpeta / 'grafo_metricas.csv').write_text('pagerank\n0.2\n', encoding='utf-8')
            (carpeta / 'grafos_metadata.json').write_text(json.dumps(meta), encoding='utf-8')
            (carpeta / 'grafo_subgrafo.json').write_text(json.dumps(old), encoding='utf-8')
            resultado = servidor.cargar_modulo(carpeta, 'grafos')
        self.assertEqual(resultado['status'], 'parcial')
        self.assertNotIn('grafo_subgrafo', resultado['resultados'])
        self.assertIn('run_id', resultado['advertencias'][0])

    def test_carga_contratos_reales_de_clasificacion_y_nlp(self):
        with TemporaryDirectory() as tmp:
            carpeta = Path(tmp)
            escribir(carpeta / 'evaluacion_clasificacion.csv', 'f1_macro\n0.65\n')
            escribir(carpeta / 'predicciones_clasificacion.csv', 'etiqueta_texto_predicha\npositivo\n')
            (carpeta / 'clasificacion_metadata.json').write_text('{"n_test": 1}', encoding='utf-8')
            escribir(carpeta / 'nlp_terminos_frecuentes.csv', 'termino\nprazo\n')
            escribir(carpeta / 'nlp_coocurrencias.csv', 'termino_1,termino_2\nantes,prazo\n')
            escribir(carpeta / 'nlp_sentimientos.csv', 'origen_etiqueta,clase\nderivado_de_review_score,positivo_score\n')
            (carpeta / 'nlp_metadata.json').write_text('{"resenas_con_texto_util": 20}', encoding='utf-8')
            clasificacion = servidor.cargar_modulo(carpeta, 'clasificacion')
            nlp = servidor.cargar_modulo(carpeta, 'nlp')
        self.assertEqual(clasificacion['status'], 'ok')
        self.assertEqual(clasificacion['resultados']['clasificacion_metadata']['n_test'], 1)
        self.assertEqual(nlp['status'], 'ok')
        self.assertEqual(nlp['resultados']['nlp_metadata']['resenas_con_texto_util'], 20)

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
    def test_resultados_entrega_perfil_calidad_y_diccionarios_generados(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / 'calidad').mkdir()
            escribir(tmp / 'resumen_tablas.csv', 'tabla,filas,columnas,celdas_nulas,filas_duplicadas_exactas\nopiniones,10,7,4,0\n')
            escribir(tmp / 'diccionario_perfilado.csv', 'tabla,columna,tipo_pandas,nulos,porcentaje_nulos,valores_distintos\nopiniones,review_comment_message,object,4,40.0,6\n')
            escribir(tmp / 'diccionario_datos.csv', 'tabla,columna,descripcion\nopiniones,review_comment_message,Mensaje de reseña\n')
            escribir(tmp / 'diccionario_procesados.csv', 'tabla,columna\npedidos,order_id\n')
            escribir(tmp / 'diccionario_variables_derivadas.csv', 'columna,descripcion\ndias_entrega,Días observados\n')
            escribir(tmp / 'calidad' / 'perfil_antes.csv', 'tabla,columna,nulos,porcentaje_nulos\nopiniones,review_comment_message,4,40.0\n')
            escribir(tmp / 'calidad' / 'perfil_despues.csv', 'tabla,columna,nulos,porcentaje_nulos\nopiniones,review_comment_message,4,40.0\n')
            escribir(tmp / 'calidad' / 'validaciones.csv', 'control,resultado\nclave,OK\n')
            escribir(tmp / 'calidad' / 'indicadores_preparacion.csv', 'indicador,valor\nentregados_sin_fecha,2\n')
            escribir(tmp / 'calidad' / 'incidencias.csv', 'tabla,columna,regla,afectados,tratamiento\nopiniones,review_comment_message,texto_vacio,2,limpiar\nopiniones,review_comment_message,texto_vacio,3,limpiar\n')
            (tmp / 'calidad' / 'metadata.json').write_text('{"sha256_origen": "ziphash"}', encoding='utf-8')
            original = servidor.RESULTADOS_DIR
            servidor.RESULTADOS_DIR = tmp
            httpd = ThreadingHTTPServer(('127.0.0.1', 0), servidor.DataSmartHandler)
            hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
            hilo.start()
            try:
                url = f'http://127.0.0.1:{httpd.server_address[1]}/api/resultados'
                with urllib.request.urlopen(url, timeout=10) as respuesta:
                    payload = json.loads(respuesta.read().decode('utf-8'))
            finally:
                httpd.shutdown()
                httpd.server_close()
                servidor.RESULTADOS_DIR = original
        self.assertEqual(payload['calidad_validaciones'][0]['resultado'], 'OK')
        self.assertEqual(payload['calidad_incidencias_resumen']['grupos'][0]['afectados'], 5)
        self.assertEqual(payload['diccionario_datos'][0]['descripcion'], 'Mensaje de reseña')
        self.assertEqual(payload['calidad_metadata']['sha256_origen'], 'ziphash')

    def test_endpoint_modulo_publica_artefactos_json(self):
        with TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            escribir(tmp / 'nlp_sentimientos.csv', 'clase,cantidad\npositivo,3\n')
            (tmp / 'nlp_metadata.json').write_text('{"resenas_con_texto_util": 3}', encoding='utf-8')
            original = servidor.RESULTADOS_DIR
            servidor.RESULTADOS_DIR = tmp
            httpd = ThreadingHTTPServer(('127.0.0.1', 0), servidor.DataSmartHandler)
            hilo = threading.Thread(target=httpd.serve_forever, daemon=True)
            hilo.start()
            try:
                url = f'http://127.0.0.1:{httpd.server_address[1]}/api/nlp'
                with urllib.request.urlopen(url, timeout=10) as respuesta:
                    datos = json.loads(respuesta.read().decode('utf-8'))
            finally:
                httpd.shutdown()
                httpd.server_close()
                servidor.RESULTADOS_DIR = original
        self.assertEqual(datos['status'], 'ok')
        self.assertEqual(datos['resultados']['nlp_sentimientos']['filas'][0]['cantidad'], '3')
        self.assertEqual(datos['resultados']['nlp_metadata']['resenas_con_texto_util'], 3)

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
