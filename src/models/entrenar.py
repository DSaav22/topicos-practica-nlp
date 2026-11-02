"""Entrena, compara y guarda el modelo en producción.

Uso (un solo comando desde los CSV sin personas):
    python -m src.models.entrenar
Con las planillas crudas en data/raw:
    python -m src.models.entrenar --desde-crudos
"""
import argparse
import json
import platform
from datetime import datetime
from pathlib import Path

import joblib
import numpy as np
import pandas as pd
import sklearn
from sklearn.dummy import DummyClassifier
from sklearn.metrics import accuracy_score, classification_report, f1_score
from sklearn.model_selection import GridSearchCV, StratifiedGroupKFold, cross_val_score
from sklearn.pipeline import Pipeline

from src.models.pipeline import NGRAMAS, SEMILLA, TFIDF, clasificador, construir, vectorizador
from src.nlp.preprocesamiento import PreprocesadorTexto

RAIZ = Path(__file__).resolve().parents[2]
DATASET = RAIZ / "data" / "processed" / "dataset.csv"
VARIANTES = RAIZ / "data" / "etiquetas" / "variantes.csv"
SALIDA = RAIZ / "models"

MODELOS = ["logistica", "complement_nb", "multinomial_nb"]
MODOS = ["stem", "lemma"]
GRILLAS = {
    "logistica": {"modelo__C": [0.3, 1, 3, 10, 30, 100]},
    "complement_nb": {"modelo__alpha": [0.01, 0.05, 0.1, 0.3, 1.0]},
}


def cargar_prueba_manual() -> pd.DataFrame:
    """Escrituras que la regla no unió, etiquetadas a mano. Se recuperan los textos originales."""
    from src.data.etiquetar import clave

    manual = pd.read_csv(RAIZ / "data" / "etiquetas" / "prueba_manual.csv", comment="#")
    procesados = RAIZ / "data" / "processed"
    textos = pd.concat([
        pd.read_csv(procesados / "atenciones.csv")["nombre"],
        pd.read_csv(procesados / "kardex.csv")["nombre"],
    ]).dropna().str.strip().drop_duplicates()
    df = pd.DataFrame({"texto": textos})
    df["clave"] = df["texto"].map(clave)
    return df.merge(manual, on="clave").reset_index(drop=True)


def claves_oficiales() -> set[str]:
    return set(pd.read_csv(VARIANTES).query("metodo == 'oficial'")["clave"])


def dividir(datos: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """La forma oficial de cada práctica siempre entrena (es el catálogo).
    Prueba: la mitad de las formas alternativas, agrupadas por clave y estratificadas por práctica."""
    alternativas = datos[~datos["clave"].isin(claves_oficiales())]
    divisor = StratifiedGroupKFold(n_splits=2, shuffle=True, random_state=SEMILLA)
    _, idx_prueba = next(divisor.split(alternativas, alternativas["practica"], alternativas["clave"]))
    prueba = alternativas.iloc[idx_prueba]
    entrenamiento = datos.drop(index=prueba.index)
    assert not set(prueba["clave"]) & set(entrenamiento["clave"])
    return entrenamiento.reset_index(drop=True), prueba.reset_index(drop=True)


def particiones_cv(entrenamiento: pd.DataFrame, n: int = 5) -> list[tuple[np.ndarray, np.ndarray]]:
    """Mismo esquema que la prueba: las formas oficiales están en todas las particiones de
    entrenamiento y se valida con formas alternativas agrupadas por clave."""
    es_oficial = entrenamiento["clave"].isin(claves_oficiales()).to_numpy()
    idx_oficial = np.flatnonzero(es_oficial)
    idx_alt = np.flatnonzero(~es_oficial)
    alt = entrenamiento.iloc[idx_alt]
    divisor = StratifiedGroupKFold(n_splits=n, shuffle=True, random_state=SEMILLA)
    particiones = []
    for tr, va in divisor.split(alt, alt["practica"], alt["clave"]):
        particiones.append((np.concatenate([idx_oficial, idx_alt[tr]]), idx_alt[va]))
    return particiones


def experimentos(entrenamiento: pd.DataFrame, textos_pre: dict, cv) -> pd.DataFrame:
    """Compara stemming/lematización y n-gramas con validación cruzada (macro-F1).
    El preprocesamiento no aprende nada de los datos, por eso se calcula una sola vez por modo."""
    y = entrenamiento["practica"]
    filas = []
    for modo in MODOS:
        for ngramas in NGRAMAS:
            for modelo in MODELOS:
                pipe = Pipeline([("tfidf", vectorizador(ngramas)), ("modelo", clasificador(modelo))])
                puntajes = cross_val_score(pipe, textos_pre[modo], y, cv=cv, scoring="f1_macro")
                filas.append({"modo": modo, "ngramas": ngramas, "modelo": modelo,
                              "f1_macro_cv": round(puntajes.mean(), 4), "desvio": round(puntajes.std(), 4)})
                print(f"  {modo:5} {ngramas:11} {modelo:15} {puntajes.mean():.3f}")
    return pd.DataFrame(filas).sort_values("f1_macro_cv", ascending=False)


def ajustar(modelo: str, modo: str, ngramas: str, entrenamiento: pd.DataFrame, textos_pre: dict, cv) -> GridSearchCV:
    pipe = Pipeline([("tfidf", vectorizador(ngramas)), ("modelo", clasificador(modelo))])
    busqueda = GridSearchCV(pipe, GRILLAS[modelo], scoring="f1_macro", cv=cv, n_jobs=1)
    busqueda.fit(textos_pre[modo], entrenamiento["practica"])
    return busqueda


class ReglaSimilitud:
    """Línea base fuerte: la práctica cuya forma oficial se parece más (rapidfuzz) al texto.
    Es la misma regla que armó las etiquetas, así que mide qué aporta el modelo sobre ella."""

    def fit(self, entrenamiento: pd.DataFrame):
        from src.data.etiquetar import clave

        self._clave = clave
        oficiales = entrenamiento[entrenamiento["clave"].isin(claves_oficiales())]
        self.mapa = oficiales.drop_duplicates("clave").set_index("clave")["practica"].to_dict()
        return self

    def predict(self, textos) -> np.ndarray:
        from rapidfuzz import fuzz, process

        claves = list(self.mapa)
        return np.array([self.mapa[process.extractOne(self._clave(t), claves, scorer=fuzz.token_sort_ratio)[0]] for t in textos])


def evaluar(pipe, X, y) -> dict:
    pred = pipe.predict(X)
    return {
        "f1_macro": round(f1_score(y, pred, average="macro", zero_division=0), 4),
        "f1_ponderado": round(f1_score(y, pred, average="weighted", zero_division=0), 4),
        "exactitud": round(accuracy_score(y, pred), 4),
    }


def analisis_errores(pipe, prueba: pd.DataFrame) -> dict:
    proba = pipe.predict_proba(prueba["texto"])
    clases = pipe.classes_
    pred = clases[proba.argmax(axis=1)]
    df = prueba.assign(prediccion=pred, probabilidad=proba.max(axis=1).round(3))
    errores = df[df["prediccion"] != df["practica"]].drop_duplicates(subset=["texto"])
    n_palabras = df["texto"].str.split().str.len()
    confusiones = errores.groupby(["practica", "prediccion"]).size().sort_values(ascending=False).head(15)
    return {
        "ejemplos": errores[["texto", "practica", "prediccion", "probabilidad"]].head(40).to_dict("records"),
        "confusiones_frecuentes": [
            {"real": r, "predicha": p, "veces": int(n)} for (r, p), n in confusiones.items()
        ],
        "exactitud_una_palabra": round(float((df["prediccion"] == df["practica"])[n_palabras == 1].mean()), 4)
        if (n_palabras == 1).any() else None,
        "exactitud_varias_palabras": round(float((df["prediccion"] == df["practica"])[n_palabras > 1].mean()), 4),
        "probabilidad_media_aciertos": round(float(df.loc[df["prediccion"] == df["practica"], "probabilidad"].mean()), 3),
        "probabilidad_media_errores": round(float(errores["probabilidad"].mean()), 3) if len(errores) else None,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--desde-crudos", action="store_true", help="regenera los CSV desde data/raw")
    args = parser.parse_args()
    if args.desde_crudos:
        from src.data import etiquetar, extraer
        extraer.main()
        etiquetar.main()

    np.random.seed(SEMILLA)
    SALIDA.mkdir(exist_ok=True)
    datos = pd.read_csv(DATASET)
    entrenamiento, prueba = dividir(datos)
    manual = cargar_prueba_manual()
    print(f"entrenamiento: {len(entrenamiento)} filas | prueba: {len(prueba)} filas ({prueba['clave'].nunique()} escrituras nunca vistas)"
          f" | prueba manual: {len(manual)} textos")

    textos_pre = {m: PreprocesadorTexto(m).transform(entrenamiento["texto"]) for m in MODOS}

    cv = particiones_cv(entrenamiento)
    print("experimentos (CV 5 particiones agrupadas, macro-F1):")
    tabla = experimentos(entrenamiento, textos_pre, cv)
    tabla.to_csv(SALIDA / "experimentos.csv", index=False)

    resultados, finales = {}, {}
    for modelo in GRILLAS:
        mejor = tabla[tabla["modelo"] == modelo].iloc[0]
        busqueda = ajustar(modelo, mejor["modo"], mejor["ngramas"], entrenamiento, textos_pre, cv)
        params = {k.replace("modelo__", ""): v for k, v in busqueda.best_params_.items()}
        pipe = construir(modelo, mejor["modo"], mejor["ngramas"], **params).fit(entrenamiento["texto"], entrenamiento["practica"])
        finales[modelo] = pipe
        resultados[modelo] = {
            "modo": mejor["modo"], "ngramas": mejor["ngramas"], "hiperparametros": params,
            "f1_macro_cv": round(busqueda.best_score_, 4),
            "grilla": {str(p): round(s, 4) for p, s in zip(busqueda.cv_results_["params"], busqueda.cv_results_["mean_test_score"])},
            "prueba": evaluar(pipe, prueba["texto"], prueba["practica"]),
            "prueba_manual": evaluar(pipe, manual["texto"], manual["practica"]),
        }
        print(f"{modelo}: {params} cv={busqueda.best_score_:.3f} prueba={resultados[modelo]['prueba']} manual={resultados[modelo]['prueba_manual']}")

    base = DummyClassifier(strategy="most_frequent").fit(entrenamiento["texto"], entrenamiento["practica"])
    regla = ReglaSimilitud().fit(entrenamiento)
    for nombre, modelo in [("linea_base", base), ("regla_similitud", regla)]:
        resultados[nombre] = {
            "prueba": evaluar(modelo, prueba["texto"], prueba["practica"]),
            "prueba_manual": evaluar(modelo, manual["texto"], manual["practica"]),
        }
        print(f"{nombre}: prueba={resultados[nombre]['prueba']} manual={resultados[nombre]['prueba_manual']}")

    # Se elige por validación cruzada: la prueba no decide nada.
    produccion = max(GRILLAS, key=lambda m: resultados[m]["f1_macro_cv"])
    pipe = finales[produccion]
    joblib.dump(pipe, SALIDA / "pipeline.joblib")

    reporte = classification_report(prueba["practica"], pipe.predict(prueba["texto"]), output_dict=True, zero_division=0)
    por_clase = {k: {m: round(v[m], 3) for m in ("precision", "recall", "f1-score", "support")}
                 for k, v in reporte.items() if isinstance(v, dict) and k not in ("macro avg", "weighted avg")}

    metricas = {
        "fecha": datetime.now().isoformat(timespec="seconds"),
        "semilla": SEMILLA,
        "modelo_produccion": produccion,
        "datos": {
            "filas": len(datos), "practicas": int(datos["practica"].nunique()),
            "entrenamiento": len(entrenamiento), "prueba": len(prueba),
            "escrituras_prueba": int(prueba["clave"].nunique()),
            "practicas_en_prueba": int(prueba["practica"].nunique()),
            "prueba_manual": len(manual),
        },
        "tfidf": {**TFIDF, "ngramas": resultados[produccion]["ngramas"],
                  "vocabulario": vocabulario(pipe)},
        "modelos": resultados,
        "experimentos": tabla.to_dict("records"),
        "por_clase": por_clase,
        "errores": analisis_errores(pipe, prueba),
        "errores_prueba_manual": analisis_errores(pipe, manual),
        "versiones": {"python": platform.python_version(), "scikit-learn": sklearn.__version__},
    }
    (SALIDA / "metricas.json").write_text(json.dumps(metricas, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"en producción: {produccion} -> models/pipeline.joblib")


def vocabulario(pipe) -> int:
    tfidf = pipe.named_steps["tfidf"]
    if hasattr(tfidf, "vocabulary_"):
        return len(tfidf.vocabulary_)
    return sum(len(v.vocabulary_) for _, v in tfidf.transformer_list)


if __name__ == "__main__":
    main()
