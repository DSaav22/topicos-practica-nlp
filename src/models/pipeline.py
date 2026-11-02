"""Construcción del pipeline completo: preprocesamiento + TF-IDF + modelo."""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB, MultinomialNB
from sklearn.pipeline import FeatureUnion, Pipeline

from src.nlp.preprocesamiento import PreprocesadorTexto

SEMILLA = 42

# Parámetros de TF-IDF documentados en el informe.
TFIDF = {
    "min_df": 1,          # una variante con error de tipeo puede aparecer una sola vez
    "max_df": 0.5,        # palabras en más de la mitad de los nombres no distinguen prácticas
    "max_features": 5000,
    "sublinear_tf": True,
}
NGRAMAS = {
    "uni": {"palabras": (1, 1)},
    "uni+bi": {"palabras": (1, 2)},
    "uni+bi+car": {"palabras": (1, 2), "caracteres": (3, 5)},
}


def vectorizador(ngramas: str):
    config = NGRAMAS[ngramas]
    palabras = TfidfVectorizer(ngram_range=config["palabras"], **TFIDF)
    if "caracteres" not in config:
        return palabras
    caracteres = TfidfVectorizer(analyzer="char_wb", ngram_range=config["caracteres"], **TFIDF)
    return FeatureUnion([("palabras", palabras), ("caracteres", caracteres)])


def clasificador(nombre: str, **params):
    if nombre == "logistica":
        return LogisticRegression(max_iter=3000, class_weight="balanced", random_state=SEMILLA, **params)
    if nombre == "complement_nb":
        return ComplementNB(**params)
    if nombre == "multinomial_nb":
        return MultinomialNB(**params)
    raise ValueError(f"modelo desconocido: {nombre}")


def construir(modelo: str, modo: str = "lemma", ngramas: str = "uni+bi", **params) -> Pipeline:
    return Pipeline([
        ("preprocesamiento", PreprocesadorTexto(modo=modo)),
        ("tfidf", vectorizador(ngramas)),
        ("modelo", clasificador(modelo, **params)),
    ])
