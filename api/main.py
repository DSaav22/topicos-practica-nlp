"""API REST del modelo de práctica oficial.

Levantar: uvicorn api.main:app --reload
Documentación interactiva: http://localhost:8000/docs
"""
import json
from pathlib import Path

import joblib
import pandas as pd
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, field_validator

from src.nlp.preprocesamiento import pasos

RAIZ = Path(__file__).resolve().parents[1]
MAX_CARACTERES = 500
# Con cientos de clases la probabilidad absoluta queda baja aunque acierte; se pide confirmar
# cuando la primera opción no llega al doble de la segunda.
MARGEN_CONFIRMAR = 2.0

pipeline = joblib.load(RAIZ / "models" / "pipeline.joblib")
metricas = json.loads((RAIZ / "models" / "metricas.json").read_text(encoding="utf-8"))
reactivos = pd.read_csv(RAIZ / "data" / "processed" / "reactivos_por_practica.csv")
catalogo = pd.read_csv(RAIZ / "data" / "processed" / "catalogo.csv")
MODO = pipeline.named_steps["preprocesamiento"].modo
CLASES = list(pipeline.classes_)

app = FastAPI(
    title="BioFarm — práctica oficial a partir del nombre escrito",
    description="Recibe el nombre de una práctica como lo escribió el docente o el auxiliar "
                "y devuelve la práctica oficial del catálogo con su probabilidad.",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class EntradaTexto(BaseModel):
    texto: str = Field(..., description="Nombre de la práctica tal como se escribió", examples=["prep. de soluciones a un pH determinado"])

    @field_validator("texto")
    @classmethod
    def validar_texto(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("el texto está vacío")
        if len(v) > MAX_CARACTERES:
            raise ValueError(f"el texto supera {MAX_CARACTERES} caracteres")
        if not any(c.isalpha() for c in v):
            raise ValueError("el texto no tiene letras")
        return v


class EntradaPrediccion(EntradaTexto):
    top_k: int = Field(3, ge=1, le=10, description="Cuántas alternativas devolver")
    candidatas: list[str] | None = Field(
        None, description="Prácticas de los grupos del auxiliar; si se envían, solo se elige entre ellas"
    )


class EntradaPreprocesar(EntradaTexto):
    modo: str | None = Field(None, pattern="^(stem|lemma)$", description="Por defecto, el del modelo en producción")


@app.exception_handler(RequestValidationError)
async def errores_validacion(_: Request, exc: RequestValidationError):
    mensajes = []
    for e in exc.errors():
        campo = ".".join(str(p) for p in e["loc"] if p != "body")
        mensajes.append(f"{campo}: {e['msg'].removeprefix('Value error, ')}" if campo else e["msg"])
    return JSONResponse(status_code=422, content={"error": "entrada inválida", "detalle": mensajes})


@app.get("/salud")
def salud():
    return {
        "estado": "ok",
        "modelo": metricas["modelo_produccion"],
        "preprocesamiento": MODO,
        "practicas": len(CLASES),
        "entrenado": metricas["fecha"],
    }


@app.post("/predecir")
def predecir(entrada: EntradaPrediccion):
    proba = pipeline.predict_proba([entrada.texto])[0]
    pares = list(zip(CLASES, proba))
    if entrada.candidatas:
        validas = set(entrada.candidatas) & set(CLASES)
        if not validas:
            return JSONResponse(status_code=422, content={"error": "entrada inválida",
                                                          "detalle": ["candidatas: ninguna está en el catálogo"]})
        pares = [(c, p) for c, p in pares if c in validas]
        total = sum(p for _, p in pares) or 1.0
        pares = [(c, p / total) for c, p in pares]
    pares.sort(key=lambda x: x[1], reverse=True)
    elegida, probabilidad = pares[0]
    segunda = pares[1][1] if len(pares) > 1 else 0.0
    sugeridos = reactivos[reactivos["practica"] == elegida]
    return {
        "texto": entrada.texto,
        "practica": elegida,
        "probabilidad": round(float(probabilidad), 4),
        "confirmar": bool(probabilidad < MARGEN_CONFIRMAR * segunda),
        "alternativas": [{"practica": c, "probabilidad": round(float(p), 4)} for c, p in pares[: entrada.top_k]],
        "reactivos_sugeridos": [
            {"reactivo": r.reactivo, "proporcion": float(r.proporcion), "sesiones": int(r.sesiones)}
            for r in sugeridos.itertuples()
        ],
        "nota_reactivos": "La lista sale por conteo del kardex para la práctica elegida; el modelo solo elige la práctica.",
    }


@app.post("/preprocesar")
def preprocesar(entrada: EntradaPreprocesar):
    return pasos(entrada.texto, entrada.modo or MODO)


@app.get("/metricas")
def obtener_metricas():
    return {k: metricas[k] for k in ("fecha", "modelo_produccion", "datos", "tfidf", "modelos", "experimentos",
                                     "errores", "errores_prueba_manual", "semilla")}


@app.get("/practicas")
def practicas():
    return catalogo.to_dict("records")
