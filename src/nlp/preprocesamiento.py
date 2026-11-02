"""Pipeline de NLP para nombres de práctica de laboratorio.

Orden: normalizar -> tokenizar -> quitar stop words -> stemming o lematización
-> quitar tildes. Las tildes se quitan al final porque el lematizador de spaCy
las necesita para reconocer la palabra ("preparación" sí, "preparacion" no siempre).
"""
from __future__ import annotations

import re
import unicodedata
from functools import lru_cache

from nltk.stem.snowball import SnowballStemmer
from sklearn.base import BaseEstimator, TransformerMixin
from spacy.lang.es.stop_words import STOP_WORDS

MODELO_SPACY = "es_core_news_sm"

# En las planillas se escribe la tilde grave por error (INTRODUCCÌON, TITULACIÒN).
_GRAVES = str.maketrans({"à": "á", "è": "é", "ì": "í", "ò": "ó", "ù": "ú"})
_URL = re.compile(r"(https?://\S+|www\.\S+)")
_EMOJI = re.compile(
    "[\U0001F300-\U0001FAFF\U00002700-\U000027BF\U0001F000-\U0001F2FF\U00002600-\U000026FF]"
)
_NO_LETRA = re.compile(r"[^a-záéíóúüñ\s]")
_ESPACIOS = re.compile(r"\s+")
_TOKEN = re.compile(r"[a-záéíóúüñ]+")

# Palabras de las planillas que no distinguen una práctica de otra:
# "lab 4", "práctica 3", "nro", "parte 1", "tema"; las letras sueltas salen
# de numeraciones como "1) a) b)".
STOP_DOMINIO = {"lab", "practica", "práctica", "practicas", "prácticas", "nro", "parte", "tema", "temas"}
# spaCy trae como stop words palabras que aquí sí cambian la práctica.
CONSERVAR = {"general", "simple", "simples", "medio", "medios", "total", "primera", "segunda"}
STOP_WORDS_ES = (set(STOP_WORDS) | STOP_DOMINIO) - CONSERVAR


def quitar_tildes(texto: str) -> str:
    """Quita tildes y diéresis; la ñ se conserva porque cambia la palabra (año / ano)."""
    texto = texto.replace("ñ", "\0")
    descompuesto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in descompuesto if not unicodedata.combining(c)).replace("\0", "ñ")


def normalizar(texto: str) -> str:
    """Minúsculas, quita URLs, emojis, puntuación y números. Conserva tildes y ñ."""
    texto = unicodedata.normalize("NFC", str(texto)).lower().translate(_GRAVES)
    texto = _URL.sub(" ", texto)
    texto = _EMOJI.sub(" ", texto)
    texto = _NO_LETRA.sub(" ", texto)
    return _ESPACIOS.sub(" ", texto).strip()


def tokenizar(texto_normalizado: str) -> list[str]:
    return _TOKEN.findall(texto_normalizado)


def es_stop_word(token: str) -> bool:
    return len(token) == 1 or token in STOP_WORDS_ES or quitar_tildes(token) in STOP_WORDS_ES


def quitar_stop_words(tokens: list[str]) -> list[str]:
    return [t for t in tokens if not es_stop_word(t)]


@lru_cache(maxsize=1)
def _stemmer() -> SnowballStemmer:
    return SnowballStemmer("spanish")


@lru_cache(maxsize=1)
def _spacy():
    import spacy

    return spacy.load(MODELO_SPACY, disable=["parser", "ner"])


def stemizar(tokens: list[str]) -> list[str]:
    st = _stemmer()
    return [st.stem(t) for t in tokens]


def lematizar(tokens: list[str]) -> list[str]:
    if not tokens:
        return []
    doc = _spacy()(" ".join(tokens))
    return [t.lemma_.lower() for t in doc if not t.is_space]


def lematizar_lote(lista_tokens: list[list[str]]) -> list[list[str]]:
    textos = [" ".join(t) for t in lista_tokens]
    return [[t.lemma_.lower() for t in doc if not t.is_space] for doc in _spacy().pipe(textos, batch_size=256)]


def pasos(texto: str, modo: str = "lemma") -> dict:
    """Cada etapa por separado, para mostrarla en la API y en el frontend."""
    normalizado = normalizar(texto)
    tokens = tokenizar(normalizado)
    sin_stop = quitar_stop_words(tokens)
    eliminadas = [t for t in tokens if es_stop_word(t)]
    raices = stemizar(sin_stop) if modo == "stem" else lematizar(sin_stop)
    final = [quitar_tildes(r) for r in raices]
    return {
        "original": texto,
        "normalizado": normalizado,
        "tokens": tokens,
        "stop_words_eliminadas": eliminadas,
        "sin_stop_words": sin_stop,
        "modo": modo,
        "raices_o_lemas": raices,
        "texto_final": " ".join(final),
    }


def preprocesar(texto: str, modo: str = "lemma") -> str:
    return pasos(texto, modo)["texto_final"]


class PreprocesadorTexto(BaseEstimator, TransformerMixin):
    """Paso de sklearn: queda dentro del pipeline guardado, así la API no lo reimplementa."""

    def __init__(self, modo: str = "lemma"):
        self.modo = modo

    def fit(self, X, y=None):
        return self

    def transform(self, X):
        sin_stop = [quitar_stop_words(tokenizar(normalizar(t))) for t in X]
        if self.modo == "stem":
            raices = [stemizar(t) for t in sin_stop]
        elif self.modo == "lemma":
            raices = lematizar_lote(sin_stop)
        else:
            raices = sin_stop
        return [" ".join(quitar_tildes(r) for r in fila) for fila in raices]
