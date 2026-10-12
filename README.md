# DataSmart - Primera fase: EDA de Olist

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
