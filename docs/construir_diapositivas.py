"""Genera docs/diapositivas.pptx a partir de models/metricas.json.

Uso: python docs/construir_diapositivas.py
"""
import json
from pathlib import Path

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.util import Inches, Pt

RAIZ = Path(__file__).resolve().parents[1]
AZUL = RGBColor(0x12, 0x35, 0x5B)
GRIS = RGBColor(0x5F, 0x6B, 0x7A)
m = json.loads((RAIZ / "models" / "metricas.json").read_text(encoding="utf-8"))
mod = m["modelos"]

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
VACIA = prs.slide_layouts[6]


def titulo(slide, texto, sub=None):
    barra = slide.shapes.add_shape(1, 0, 0, prs.slide_width, Inches(1.1))
    barra.fill.solid()
    barra.fill.fore_color.rgb = AZUL
    barra.line.fill.background()
    tf = barra.text_frame
    tf.text = texto
    tf.paragraphs[0].runs[0].font.size = Pt(30)
    tf.paragraphs[0].runs[0].font.bold = True
    tf.paragraphs[0].runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    if sub:
        caja = slide.shapes.add_textbox(Inches(0.6), Inches(1.2), Inches(12), Inches(0.5))
        caja.text_frame.text = sub
        caja.text_frame.paragraphs[0].runs[0].font.size = Pt(16)
        caja.text_frame.paragraphs[0].runs[0].font.color.rgb = GRIS


def vinetas(slide, lineas, x=0.6, y=1.8, ancho=12.1, alto=5.3, tam=20):
    caja = slide.shapes.add_textbox(Inches(x), Inches(y), Inches(ancho), Inches(alto))
    tf = caja.text_frame
    tf.word_wrap = True
    for i, linea in enumerate(lineas):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        sangria = linea.startswith("  ")
        marca = "" if linea.strip().startswith("→") else ("– " if sangria else "• ")
        p.text = marca + linea.strip()
        p.level = 1 if sangria else 0
        p.space_after = Pt(8)
        for r in p.runs:
            r.font.size = Pt(tam - 3 if sangria else tam)


def tabla(slide, filas, x=0.6, y=1.9, ancho=12.1, tam=15, anchos=None):
    t = slide.shapes.add_table(len(filas), len(filas[0]), Inches(x), Inches(y), Inches(ancho), Inches(0.45 * len(filas))).table
    for i, fila in enumerate(filas):
        for j, valor in enumerate(fila):
            celda = t.cell(i, j)
            celda.text = str(valor)
            for p in celda.text_frame.paragraphs:
                for r in p.runs:
                    r.font.size = Pt(tam)
                    r.font.bold = i == 0
    if anchos:
        for j, w in enumerate(anchos):
            t.columns[j].width = Inches(w)


def nueva(texto, sub=None):
    s = prs.slides.add_slide(VACIA)
    titulo(s, texto, sub)
    return s


def f3(v):
    return "—" if v is None else f"{v:.3f}".replace(".", ",")


# 1. Portada
s = prs.slides.add_slide(VACIA)
fondo = s.shapes.add_shape(1, 0, 0, prs.slide_width, prs.slide_height)
fondo.fill.solid()
fondo.fill.fore_color.rgb = AZUL
fondo.line.fill.background()
caja = s.shapes.add_textbox(Inches(0.8), Inches(2.2), Inches(11.5), Inches(3))
tf = caja.text_frame
tf.word_wrap = True
for i, (texto, tam, negrita) in enumerate([
    ("Práctica oficial a partir del nombre escrito", 40, True),
    ("Clasificación de texto con NLP para el Laboratorio Académico FCFB — UAGRM", 22, False),
    ("Tópicos y Programación Avanzada · Proyecto integrador · Diego Saavedra · 3 de noviembre de 2026", 16, False),
]):
    p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
    p.text = texto
    p.space_after = Pt(14)
    p.runs[0].font.size = Pt(tam)
    p.runs[0].font.bold = negrita
    p.runs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

# 2. Problema
s = nueva("Problema", "El mismo trabajo, escrito de muchas formas en las planillas del laboratorio")
vinetas(s, [
    "Cada sesión se registra a mano en atenciones y kardex: 3.655 nombres distintos en 7.994 atenciones",
    "«Preparación de soluciones a un pH determinado» tiene más de 20 escrituras:",
    "  de un ph determinado · con un ph determinado · de un phdeterminado · LAB 4 … · oreparacion …",
    "Sin un nombre oficial, BioFarm no puede saber qué reactivos suele llevar una práctica",
    "Tarea: dado el nombre escrito → práctica oficial del catálogo + probabilidad",
])

# 3. Qué hace el modelo
s = nueva("Qué hace el modelo y qué no")
tabla(s, [
    ["Pieza", "Quién", "Qué hace"],
    ["Carrera y grupos", "Sesión del auxiliar en BioFarm", "Ya se conocen: el modelo no los adivina"],
    ["Nombre escrito → práctica", "Modelo (NLP + ML)", "Práctica oficial con probabilidad y alternativas"],
    ["Reactivos sugeridos", "Conteo del kardex", "Los que salen en ≥ 50 % de las sesiones de esa práctica"],
    ["Gramos", "Auxiliar y pesaje", "No se predicen: varían demasiado entre sesiones"],
], anchos=[3.2, 3.6, 5.3], tam=17)
vinetas(s, ["Descartado: predecir FAR/BQM (la sesión ya lo trae) y regresión de gramos"], y=4.8, tam=18)

# 4. Datos
d = m["datos"]
s = nueva("Datos", "Planillas internas del laboratorio, obtenidas el 25/10/2026 · uso académico, no públicas")
vinetas(s, [
    "Atenciones marzo–octubre 2026 (FAR/BQM) y dos kardex de reactivos (controlados y no controlados)",
    "Se quitan docente, auxiliar, registros y firmas: al repo solo van práctica, carrera, sigla, grupo, reactivo",
    f"{d['filas']:,} filas etiquetadas · {d['practicas']} prácticas oficiales · mediana 13 filas por práctica".replace(",", "."),
    "Desbalance fuerte → métrica principal macro-F1 y class_weight='balanced'",
    "677 nombres de una sola palabra («bioseguridad», «alcanos»)",
])

# 5. Etiquetado
s = nueva("Etiquetado: no había columna con la práctica oficial")
vinetas(s, [
    "Clave = nombre normalizado, sin stop words ni tildes",
    "Claves frecuentes (≥ 4) → candidatas a práctica oficial",
    "Una variante se une solo si TODAS sus palabras coinciden (rapidfuzz ≥ 84 por palabra)",
    "  «unidades fisecas» = «unidades físicas» · «unidades físicas» ≠ «unidades químicas»",
    "Palabras del dominio que difieren en una letra deben ser exactas",
    "  alquenos/alquinos · mitosis/meiosis · éter/éster · colorimetría/calorimetría",
    "15 fusiones manuales + prueba manual de 78 escrituras que la regla no unió",
    "Lo dudoso queda fuera: mejor perder filas que meter etiquetas falsas",
])

# 6. NLP
s = nueva("Pipeline de NLP", "normalizar → tokenizar → stop words → stem / lemma → quitar tildes")
tabla(s, [
    ["Paso", "Resultado"],
    ["Original", "LAB 4 PREPARACIÓN DE SOLUCIONES DE UN PH DETERMINADO"],
    ["Normalizado", "lab preparación de soluciones de un ph determinado"],
    ["Stop words quitadas", "lab · de · de · un   (spaCy + dominio: lab, practica, nro)"],
    ["Stemming (Snowball)", "prepar solucion ph determin"],
    ["Lematización (spaCy)", "preparacion solucion ph determinado"],
], anchos=[3.4, 8.7], tam=17)
vinetas(s, [
    "Tildes se quitan al final: spaCy las necesita · se corrige la tilde grave (INTRODUCCÌON)",
    "Se conservan simple(s), medio(s), general: cambian la práctica",
], y=5.0, tam=17)

# 7. Experimentos
exp = {(e["modo"], e["ngramas"], e["modelo"]): e["f1_macro_cv"] for e in m["experimentos"]}
s = nueva("Experimentos de preprocesamiento", "Validación cruzada de 5 particiones · macro-F1")
filas = [["Preproc.", "n-gramas", "Logística", "Complement NB", "Multinomial NB"]]
for modo in ("stem", "lemma"):
    for ng in ("uni", "uni+bi", "uni+bi+car"):
        filas.append([modo, ng] + [f3(exp[(modo, ng, mo)]) for mo in ("logistica", "complement_nb", "multinomial_nb")])
tabla(s, filas, tam=16)
vinetas(s, [
    "Palabras solas: stemming > lematización (spaCy falla con términos técnicos)",
    "N-gramas de caracteres 3–5: lo que más sube, absorben errores de tipeo",
], y=5.4, tam=17)

# 8. Validación
s = nueva("Modelos y validación")
vinetas(s, [
    "Regresión logística (softmax, class_weight balanced) y Naive Bayes Complement",
    "Las formas oficiales siempre entrenan (son el catálogo de BioFarm)",
    f"Prueba: formas alternativas con StratifiedGroupKFold agrupado por clave · {d['prueba']} textos, {d['escrituras_prueba']} escrituras nunca vistas",
    "CV de 5 particiones con el mismo esquema · GridSearchCV de C y alpha",
    "Problema: la prueba automática la etiquetó la misma regla de similitud",
    f"  → prueba manual: {d['prueba_manual']} textos que la regla NO supo unir, etiquetados a mano",
    "Elección del modelo en producción: solo por validación cruzada",
])

# 9. Resultados
s = nueva("Resultados")
nombres = [("logistica", "Regresión logística"), ("complement_nb", "Naive Bayes (Complement)"),
           ("regla_similitud", "Regla de similitud"), ("linea_base", "Clase más frecuente")]
filas = [["Modelo", "Config.", "F1 CV", "F1 prueba", "Exact. prueba", "F1 manual", "Exact. manual"]]
for k, n in nombres:
    r = mod[k]
    cfg = f"{r['modo']} · {r['ngramas']} · {list(r['hiperparametros'].items())[0][0]}={r['hiperparametros'][list(r['hiperparametros'])[0]]}" if r.get("modo") else "—"
    filas.append([n, cfg, f3(r.get("f1_macro_cv")), f3(r["prueba"]["f1_macro"]), f3(r["prueba"]["exactitud"]),
                  f3(r["prueba_manual"]["f1_macro"]), f3(r["prueba_manual"]["exactitud"])])
tabla(s, filas, tam=15, anchos=[2.6, 3.0, 1.1, 1.3, 1.4, 1.3, 1.4])
vinetas(s, [
    "En producción: regresión logística",
    f"Prueba manual: {f3(mod['logistica']['prueba_manual']['exactitud'])} frente a {f3(mod['regla_similitud']['prueba_manual']['exactitud'])} de la regla → el modelo aporta",
], y=4.6, tam=18)

# 10. Errores
s = nueva("Análisis de errores")
vinetas(s, [
    "Genérica contra específica: «…de un PHDETERMINADO» → «Preparación de soluciones»",
    "El catálogo tiene casi duplicados: «Uso de la micropipeta» / «Uso y control de la micripipeta»",
    "  → el laboratorio debe fusionarlas al cerrar el catálogo",
    "Sinónimos no vistos: «buffer» (en los datos se dice «tampón») → la API pide confirmar",
    "Una palabra con errores: «BIOSEFURIDAD», «MICROSCOPIO»",
    f"Probabilidades bajas con 266 clases (media {f3(m['errores']['probabilidad_media_aciertos'])} en aciertos)",
    "  → confirmar cuando la 1.ª opción no duplica a la 2.ª",
])

# 11. Arquitectura
s = nueva("Arquitectura", "El backend carga el pipeline; no reimplementa el preprocesamiento")
tabla(s, [
    ["Capa", "Archivo", "Qué hace"],
    ["Datos", "src/data/extraer.py · etiquetar.py", "Excel → CSV sin personas → dataset etiquetado"],
    ["NLP", "src/nlp/preprocesamiento.py", "PreprocesadorTexto (paso de sklearn)"],
    ["Modelo", "src/models/entrenar.py", "Un comando → pipeline.joblib + metricas.json"],
    ["Backend", "api/main.py (FastAPI)", "/salud · /predecir · /preprocesar · /metricas"],
    ["Frontend", "frontend/ (React + Vite)", "Predicción, pasos, métricas, archivo con varios"],
], anchos=[1.8, 4.5, 5.8], tam=16)
vinetas(s, ["Semilla 42 · versiones fijadas · 16 pruebas con pytest"], y=5.2, tam=18)

# 12. Demo
s = nueva("Demostración")
s.shapes.add_picture(str(RAIZ / "docs" / "img" / "prediccion.png"), Inches(0.6), Inches(1.3), height=Inches(6))
s.shapes.add_picture(str(RAIZ / "docs" / "img" / "metricas.png"), Inches(6.9), Inches(1.3), height=Inches(6))

# 13. BioFarm
s = nueva("Encaje en BioFarm y límites")
vinetas(s, [
    "BioFarm manda el texto y las prácticas de los grupos del auxiliar (candidatas)",
    "Recibe la práctica; muestra los reactivos por conteo; el auxiliar confirma y carga gramos",
    "Requerimientos nuevos guardan practica_id → el conteo se actualiza solo",
    "Límites: etiquetas por regla + revisión parcial · prueba manual pequeña · catálogo aún no oficial",
    "Uso de IA declarado en el informe (Cursor); el código fue revisado y probado por el autor",
])

prs.save(RAIZ / "docs" / "diapositivas.pptx")
print("docs/diapositivas.pptx")
