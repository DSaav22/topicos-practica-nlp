from src.data.etiquetar import misma_practica
from src.nlp.preprocesamiento import normalizar, preprocesar, quitar_stop_words, tokenizar


def test_normalizar_quita_url_emoji_numeros_y_puntuacion():
    assert normalizar("LAB 4: Alcanos 🔬 https://x.com") == "lab alcanos"


def test_normalizar_corrige_tilde_grave():
    assert normalizar("INTRODUCCIÒN") == "introducción"


def test_stop_words_del_dominio():
    assert quitar_stop_words(tokenizar("practica de la cromatografia en papel")) == ["cromatografia", "papel"]


def test_conserva_palabras_que_cambian_la_practica():
    assert quitar_stop_words(["soluciones", "simples", "medio", "general"]) == ["soluciones", "simples", "medio", "general"]


def test_stemming_une_singular_y_plural():
    assert preprocesar("Tejidos epiteliales", "stem") == preprocesar("tejido epitelial", "stem")


def test_etiquetado_distingue_palabras_del_dominio():
    assert misma_practica("preparacion soluciones unidades fisecas", "preparacion soluciones unidades fisicas")
    assert not misma_practica("preparacion soluciones unidades fisicas", "preparacion soluciones unidades quimicas")
    assert not misma_practica("propiedades alquinos", "propiedades alquenos")
