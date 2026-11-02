from fastapi.testclient import TestClient

from api.main import app

cliente = TestClient(app)


def test_salud():
    r = cliente.get("/salud")
    assert r.status_code == 200
    assert r.json()["estado"] == "ok"


def test_prediccion_conocida():
    r = cliente.post("/predecir", json={"texto": "PREPARACION DE SOLUCIONES DE UN PH DETERMINADO"})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["practica"] == "Preparacion de soluciones a un ph determinado"
    assert 0 <= cuerpo["probabilidad"] <= 1
    assert len(cuerpo["alternativas"]) == 3


def test_prediccion_con_error_de_tipeo():
    r = cliente.post("/predecir", json={"texto": "oreparacion de soluciones unidades fisecas"})
    assert r.json()["practica"] == "Preparacion de soluciones unidades fisicas"


def test_acepta_una_sola_palabra():
    r = cliente.post("/predecir", json={"texto": "bioseguridad"})
    assert r.status_code == 200


def test_rechaza_texto_vacio():
    r = cliente.post("/predecir", json={"texto": "   "})
    assert r.status_code == 422
    assert "vacío" in r.json()["detalle"][0]


def test_rechaza_texto_largo():
    r = cliente.post("/predecir", json={"texto": "a" * 501})
    assert r.status_code == 422
    assert "500" in r.json()["detalle"][0]


def test_rechaza_formato_incorrecto():
    assert cliente.post("/predecir", json={"nombre": "alcanos"}).status_code == 422
    assert cliente.post("/predecir", json={"texto": "12345 ---"}).status_code == 422
    assert cliente.post("/predecir", json={"texto": "alcanos", "top_k": 0}).status_code == 422


def test_candidatas_restringen_la_respuesta():
    candidatas = ["Alcanos", "Bioseguridad"]
    r = cliente.post("/predecir", json={"texto": "preparacion de soluciones", "candidatas": candidatas})
    cuerpo = r.json()
    assert cuerpo["practica"] in candidatas
    assert abs(sum(a["probabilidad"] for a in cuerpo["alternativas"]) - 1) < 0.01


def test_preprocesar_muestra_los_pasos():
    r = cliente.post("/preprocesar", json={"texto": "LAB 4 Preparación de Soluciones", "modo": "stem"})
    cuerpo = r.json()
    assert cuerpo["normalizado"] == "lab preparación de soluciones"
    assert "lab" in cuerpo["stop_words_eliminadas"]
    assert cuerpo["texto_final"] == "prepar solucion"


def test_metricas():
    r = cliente.get("/metricas")
    assert r.status_code == 200
    assert "logistica" in r.json()["modelos"]
