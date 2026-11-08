# DataSmart - EDA y preparación de datos de Olist

## Ejecutar en Windows (PowerShell)
1. Descomprimir este proyecto en una carpeta, por ejemplo `C:\DataSmart_EDA`.
2. Abrir una terminal en la carpeta que contiene `requirements.txt`.
3. Ejecutar `py -m pip install -r requirements.txt`.
4. Ejecutar `py src/eda_olist.py`.

Si `py` no funciona, usa `python` en los comandos.

### Dataset utilizado

Este proyecto utiliza el dataset público **Brazilian E-Commerce Public Dataset by Olist**, disponible en Kaggle:

https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce

Para ejecutar el proyecto:

1. Descargar el dataset desde Kaggle.
2. Crear la carpeta `data/raw/` en caso de que no exista.
3. Colocar el archivo descargado en esa carpeta con el nombre `archive.zip`.
4. Instalar las dependencias mediante `python -m pip install -r requirements.txt`.
5. Ejecutar `python src/eda_olist.py`.

**Nota:** los datos originales no se incluyen en este repositorio. Se deben descargar desde su fuente oficial.

## Resultados
- `resultados/resumen_tablas.csv`: filas, columnas, nulos y duplicados exactos por tabla.
- `resultados/diccionario_perfilado.csv`: columnas, tipos inferidos, nulos, valores distintos.
- `resultados/indicadores_kpi.csv`: métricas descriptivas básicas.
- `resultados/ventas_mensuales.csv`: serie temporal de importes.
- `resultados/graficos/`: tres visualizaciones PNG.

## Notas metodológicas
- El dataset Olist es histórico y no representa ventas actuales.
- Las ventas reportadas suman `price` de artículos de pedidos entregados y excluyen flete.
- El estado `delivered` se utiliza como filtro para un análisis inicial, no como tratamiento final de todos los datos.
- Los tipos en `diccionario_perfilado.csv` son los inferidos por Pandas, no los tipos definitivos de SQL.
- No eliminar faltantes ni duplicados sin revisar su significado y las claves de las tablas.

## Preparación de datos — entrega de Jerson

Con las mismas dependencias y el ZIP original, ejecutar desde la raíz:

```bash
python src/preparar_datos.py
```

En Windows también se puede utilizar `py src/preparar_datos.py`. El script resuelve
las rutas desde su ubicación y puede ejecutarse desde otro directorio.

### Salidas

- `data/processed/pedidos_procesados.csv`: una fila por pedido, con clientes,
  importes y conteos de ítems, pagos y reseñas agregados independientemente.
- `data/processed/items_procesados.csv`: una fila por ítem, con producto,
  categoría, vendedor, comprador, coordenadas y distancia aproximada.
- `data/processed/geolocalizacion_agrupada.csv`: medianas por prefijo postal,
  después de eliminar repeticiones exactas.
- `resultados/calidad/`: perfiles antes/después, incidencias identificadas,
  validaciones, indicadores y metadatos de procedencia con SHA-256 del ZIP.
- `resultados/diccionario_datos.csv`: los **52 campos originales** de las nueve tablas.
- `resultados/diccionario_procesados.csv`: todos los campos de las tres tablas finales.
- `resultados/diccionario_variables_derivadas.csv`: fórmulas, unidades y momento
  de disponibilidad de las variables nuevas.
- [`docs/preparacion_y_calidad.md`](docs/preparacion_y_calidad.md): informe generado
  con los resultados reales de cada ejecución.

La preparación valida claves, referencias, rangos, conversiones y conciliaciones
de filas e importes antes de publicar las tablas procesadas. Conserva todos los
estados de pedido y distingue faltantes de valores cero. La puntualidad se mide
por **día calendario**; esta definición difiere de comparar timestamps completos.

Para una salida aislada:

```bash
python src/preparar_datos.py --output-root /ruta/salida
```

Los datos procesados están excluidos de Git; cada integrante puede regenerarlos
con el mismo ZIP. Consultar la [guía de uso y entrega](docs/guia_preparacion.md)
y las [diapositivas de Jerson](docs/presentacion_jerson.md).

### Pruebas de preparación

Las pruebas utilizan datos pequeños y no requieren descargar Olist:

```bash
python -m unittest discover -s tests -v
```

## Plataforma Web Frontend (`frontend/`)

El repositorio incluye la interfaz web analítica interactiva en la carpeta `frontend/`, con vistas del EDA, diccionario, calidad de datos y las 10 preguntas de negocio (`PN-01` a `PN-10`). El conector actual consulta la API pero las vistas utilizan el store local; Paulo tiene pendiente integrar las salidas calculadas y actualizar las etiquetas y simulaciones del prototipo.

### Ejecutar el Frontend con Python (PowerShell)
1. Desde la raíz del proyecto, ejecutar:
   ```powershell
   py frontend/server.py
   ```
2. Abrir en el navegador `http://localhost:8080`.

### Ejecutar el Frontend con Node.js / Vite (Opcional)
1. Entrar a `frontend/`, instalar dependencias y levantar el servidor de desarrollo:
   ```powershell
   cd frontend
   npm install
   npm run dev
   ```
