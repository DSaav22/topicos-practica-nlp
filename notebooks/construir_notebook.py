"""Genera notebooks/01_eda_y_experimentos.ipynb. Ejecutar luego con:
jupyter nbconvert --to notebook --execute --inplace notebooks/01_eda_y_experimentos.ipynb
"""
from pathlib import Path

import nbformat as nbf

celdas = [
    ("md", "# Análisis exploratorio y experimentos\n\nDatos: atenciones del Laboratorio Académico FCFB — UAGRM (marzo a octubre 2026) y kardex de reactivos. "
           "Los CSV de `data/processed/` ya no tienen datos de personas."),
    ("code", "import sys, json\nsys.path.insert(0, '..')\nimport pandas as pd\nimport matplotlib.pyplot as plt\nfrom collections import Counter\n"
             "pd.set_option('display.max_colwidth', 90)\n"
             "atenciones = pd.read_csv('../data/processed/atenciones.csv')\nkardex = pd.read_csv('../data/processed/kardex.csv')\n"
             "datos = pd.read_csv('../data/processed/dataset.csv')\nvariantes = pd.read_csv('../data/etiquetas/variantes.csv')\n"
             "print(len(atenciones), 'atenciones FAR/BQM |', len(kardex), 'salidas de kardex |', len(datos), 'filas etiquetadas')"),
    ("md", "## 1. Valores faltantes"),
    ("code", "pd.DataFrame({'atenciones': atenciones.isna().sum(), 'kardex': kardex.isna().sum()})"),
    ("md", "## 2. Variantes: el mismo trabajo escrito de muchas formas"),
    ("code", "from src.data.etiquetar import clave\n"
             "crudos = atenciones['nombre'].dropna()\n"
             "print('nombres crudos distintos:', crudos.nunique())\n"
             "print('claves distintas (normalizado, sin stop words ni tildes):', crudos.map(clave).nunique())\n"
             "variantes[variantes.clave_oficial == 'preparacion soluciones ph determinado'][['clave', 'n', 'metodo', 'puntaje']]"),
    ("code", "print(variantes.metodo.value_counts())\n"
             "frecuencia = variantes.n\n"
             "for umbral in (1, 2, 5, 10):\n    print(f'claves con n >= {umbral}:', int((frecuencia >= umbral).sum()))"),
    ("md", "## 3. Distribución de clases\n\nHay muchas prácticas con pocos ejemplos: por eso la métrica principal es macro-F1 y la regresión logística usa `class_weight='balanced'`."),
    ("code", "conteo = datos['practica'].value_counts()\nprint(conteo.describe())\n"
             "fig, ax = plt.subplots(1, 2, figsize=(13, 4))\n"
             "conteo.head(20).iloc[::-1].plot.barh(ax=ax[0], title='20 prácticas con más filas')\n"
             "ax[1].hist(conteo, bins=40)\nax[1].set_title('Filas por práctica (266 clases)')\nax[1].set_xlabel('filas')\nplt.tight_layout()"),
    ("md", "## 4. Longitud de los textos\n\nMuchos nombres tienen una o dos palabras («bioseguridad», «alcanos»): la API los acepta."),
    ("code", "palabras = datos['texto'].str.split().str.len()\ncaracteres = datos['texto'].str.len()\n"
             "print(palabras.describe())\nprint('una sola palabra:', int((palabras == 1).sum()))\n"
             "fig, ax = plt.subplots(1, 2, figsize=(12, 3.5))\nax[0].hist(palabras, bins=range(1, 25))\nax[0].set_title('Palabras por nombre')\n"
             "ax[1].hist(caracteres, bins=40)\nax[1].set_title('Caracteres por nombre')\nplt.tight_layout()"),
    ("md", "## 5. Palabras más frecuentes, antes y después de quitar stop words"),
    ("code", "from src.nlp.preprocesamiento import normalizar, tokenizar, quitar_stop_words\n"
             "tokens = [t for x in datos['texto'] for t in tokenizar(normalizar(x))]\n"
             "sin_stop = [t for x in datos['texto'] for t in quitar_stop_words(tokenizar(normalizar(x)))]\n"
             "pd.DataFrame({'con stop words': [f'{w} ({n})' for w, n in Counter(tokens).most_common(15)],\n"
             "              'sin stop words': [f'{w} ({n})' for w, n in Counter(sin_stop).most_common(15)]})"),
    ("md", "## 6. Reactivos que salen en casi todas las prácticas\n\nPor eso la sugerencia de reactivos usa la proporción de sesiones **de esa práctica**, no «todo lo que alguna vez la acompañó»."),
    ("code", "sesiones = kardex.groupby('reactivo')['nombre'].nunique().sort_values(ascending=False)\nsesiones.head(10).rename('prácticas distintas')"),
    ("md", "## 7. Preprocesamiento antes / después"),
    ("code", "from src.nlp.preprocesamiento import pasos\n"
             "ejemplos = ['PREPARACIÓN DE SOLUCIONES DE UN PH DETERMINADO', 'LAB 4 PREPARACION DE SOLUCIONES UNIDADES FISICAS',\n"
             "            'INTRODUCCIÒN A LA BIOTECNOLOGÌA', 'preparacion de soluciones de un phdeterminado', 'Observación de células animales 🔬']\n"
             "pd.DataFrame([{**{k: pasos(e, 'stem')[k] for k in ('original', 'normalizado')},\n"
             "               'stem': pasos(e, 'stem')['texto_final'], 'lemma': pasos(e, 'lemma')['texto_final']} for e in ejemplos])"),
    ("md", "Casos difíciles de tokenización: `phdeterminado` (dos palabras pegadas), `ac` por «ácido», `e coli` (la `e` suelta se descarta como letra sola), "
           "`lab 4` (el número se quita y `lab` es stop word del dominio). La lematización de spaCy falla con términos técnicos (`biotecnología` → `biotecnologio`)."),
    ("md", "## 8. Experimentos (validación cruzada, macro-F1)"),
    ("code", "exp = pd.read_csv('../models/experimentos.csv')\nexp.pivot_table(index=['modo', 'ngramas'], columns='modelo', values='f1_macro_cv')"),
    ("md", "Los n-gramas de caracteres son los que más suben: absorben errores de tipeo (`fisecas`, `prepraracion`) que con palabras completas quedan fuera del vocabulario. "
           "Los bigramas de palabras solos no ayudan a la regresión logística; sí a Naive Bayes."),
    ("code", "m = json.load(open('../models/metricas.json', encoding='utf-8'))\n"
             "filas = []\nfor k in ('logistica', 'complement_nb', 'regla_similitud', 'linea_base'):\n"
             "    r = m['modelos'][k]\n"
             "    filas.append({'modelo': k, 'f1_cv': r.get('f1_macro_cv'), 'f1_prueba': r['prueba']['f1_macro'], 'exactitud_prueba': r['prueba']['exactitud'],\n"
             "                  'f1_manual': r['prueba_manual']['f1_macro'], 'exactitud_manual': r['prueba_manual']['exactitud']})\n"
             "pd.DataFrame(filas)"),
    ("md", "## 9. Análisis de errores (prueba manual)"),
    ("code", "pd.DataFrame(m['errores_prueba_manual']['ejemplos'])"),
    ("code", "pd.DataFrame(m['errores']['confusiones_frecuentes'])"),
]

nb = nbf.v4.new_notebook()
nb["cells"] = [nbf.v4.new_markdown_cell(c) if t == "md" else nbf.v4.new_code_cell(c) for t, c in celdas]
nb["metadata"]["kernelspec"] = {"name": "python3", "display_name": "Python 3", "language": "python"}
nbf.write(nb, Path(__file__).with_name("01_eda_y_experimentos.ipynb"))
