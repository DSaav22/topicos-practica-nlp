"""Arma la tabla variante -> práctica oficial y el dataset etiquetado.

1. Cada nombre se reduce a una clave: normalizado, sin stop words y sin tildes.
2. Las claves que aparecen 5 veces o más son candidatas a práctica oficial.
3. Una clave se une a una práctica oficial solo si todas sus palabras coinciden
   con las de la oficial, palabra por palabra, admitiendo errores de tipeo.
   Así "unidades fisecas" se une a "unidades fisicas", pero "unidades fisicas"
   no se une a "unidades quimicas".
4. `data/etiquetas/fusiones_manuales.csv` corrige a mano lo que el paso 3 deja
   separado y es la misma práctica.

Uso: python -m src.data.etiquetar
"""
from pathlib import Path

import pandas as pd
from rapidfuzz import fuzz, process

from src.nlp.preprocesamiento import normalizar, quitar_stop_words, quitar_tildes, tokenizar

RAIZ = Path(__file__).resolve().parents[2]
PROCESADOS = RAIZ / "data" / "processed"
ETIQUETAS = RAIZ / "data" / "etiquetas"

MIN_CANDIDATA = 4
UMBRAL_PALABRA = 84
# Difieren en una letra de otra palabra del dominio y no son errores de tipeo:
# alquenos / alquinos, mitosis / meiosis, éter / éster, metanol / etanol.
PALABRAS_EXACTAS = {
    "alcano", "alqueno", "alquino", "mitosis", "meiosis", "antibiotico", "antipsicotico",
    "eter", "ester", "metanol", "etanol", "hexano", "hexeno", "etano", "eteno", "etino",
    "nitrato", "nitrito", "sulfato", "sulfito", "fosfato", "fosfito",
    "colorimetria", "calorimetria", "disolucion", "disoluciones", "dilucion", "diluciones",
}
MIN_FILAS_CLASE = 8
# Una práctica escrita siempre igual también es del catálogo: entra al entrenamiento
# aunque no aporte escrituras alternativas a la prueba.
MIN_VARIANTES_CLASE = 1
MIN_PROPORCION_REACTIVO = 0.25
MAX_REACTIVOS = 12
# Respaldo para prácticas sin salidas propias: lo más usado en sus asignaturas.
MIN_SESIONES_ASIGNATURA = 5
MIN_PROPORCION_ASIGNATURA = 0.10
MAX_REACTIVOS_ASIGNATURA = 8
TIPO_POR_FUENTE = {"kardex": "reactivo", "microbiologia": "medio de cultivo"}
CLAVES_EXCLUIDAS = {"", "nombre"}  # "sin nombre" queda en "nombre"


def clave(texto: str) -> str:
    return " ".join(quitar_tildes(t) for t in quitar_stop_words(tokenizar(normalizar(texto))))


def texto_grupo(texto: str) -> str:
    return quitar_tildes(normalizar(texto))


def _singular(palabra: str) -> str:
    return palabra[:-1] if palabra.endswith("s") else palabra


def _es_exacta(palabra: str) -> bool:
    return palabra in PALABRAS_EXACTAS or _singular(palabra) in PALABRAS_EXACTAS


def _palabra_coincide(x: str, y: str) -> bool:
    if _es_exacta(x) or _es_exacta(y):
        return x == y or _singular(x) == _singular(y)
    return fuzz.ratio(x, y) >= UMBRAL_PALABRA


def _palabras_coinciden(a: list[str], b: list[str]) -> bool:
    return all(any(_palabra_coincide(x, y) for y in b) for x in a)


def misma_practica(variante: str, oficial: str) -> bool:
    a, b = variante.split(), oficial.split()
    return _palabras_coinciden(a, b) and _palabras_coinciden(b, a)


def asignar_claves(conteo: pd.Series) -> pd.DataFrame:
    oficiales: list[str] = []
    filas = []
    for k, n in conteo.sort_values(ascending=False).items():
        destino, puntaje = None, 0.0
        if oficiales:
            for cand, p, _ in process.extract(k, oficiales, scorer=fuzz.token_sort_ratio, limit=5, score_cutoff=70):
                if misma_practica(k, cand):
                    destino, puntaje = cand, p
                    break
        if destino is not None:
            metodo = "auto"
        elif n >= MIN_CANDIDATA:
            oficiales.append(k)
            destino, puntaje, metodo = k, 100.0, "oficial"
        else:
            metodo = "sin_asignar"
        filas.append({"clave": k, "n": int(n), "clave_oficial": destino, "puntaje": round(puntaje, 1), "metodo": metodo})
    return pd.DataFrame(filas)


def aplicar_fusiones(tabla: pd.DataFrame) -> pd.DataFrame:
    ruta = ETIQUETAS / "fusiones_manuales.csv"
    if not ruta.exists():
        return tabla
    fusiones = pd.read_csv(ruta, comment="#").dropna(subset=["clave_origen", "clave_destino"])
    mapa = dict(zip(fusiones["clave_origen"].str.strip(), fusiones["clave_destino"].str.strip()))
    oficiales = set(tabla.loc[tabla["metodo"] == "oficial", "clave"])
    for origen, destino in mapa.items():
        if destino not in oficiales:
            print(f"aviso: fusión '{origen}' -> '{destino}': el destino no es una práctica oficial")
    tabla = tabla.copy()
    afectadas = tabla["clave_oficial"].isin(mapa) | tabla["clave"].isin(mapa)
    origen = tabla["clave_oficial"].where(tabla["clave_oficial"].isin(mapa), tabla["clave"])
    tabla.loc[afectadas, "clave_oficial"] = origen[afectadas].map(mapa)
    tabla.loc[afectadas, "metodo"] = "manual"
    return tabla


def nombre_visible(nombres: pd.Series) -> str:
    texto = nombres.str.strip().str.replace(r"\s+", " ", regex=True).value_counts().index[0]
    texto = texto.lower().translate(str.maketrans({"ì": "í", "ò": "ó"}))
    return texto[:1].upper() + texto[1:]


def main() -> None:
    ETIQUETAS.mkdir(parents=True, exist_ok=True)
    atenciones = pd.read_csv(PROCESADOS / "atenciones.csv").dropna(subset=["nombre"])
    kardex = pd.read_csv(PROCESADOS / "kardex.csv")
    sesiones_kardex = kardex.drop_duplicates(subset=["formulario", "nombre"])[["nombre", "carrera", "sigla", "grupo"]].copy()
    sesiones_kardex["fuente"] = "kardex"
    textos = pd.concat([atenciones[["nombre", "carrera", "sigla", "grupo", "fuente"]], sesiones_kardex], ignore_index=True)
    textos["clave"] = textos["nombre"].map(clave)
    textos = textos[~textos["clave"].isin(CLAVES_EXCLUIDAS)]

    tabla = aplicar_fusiones(asignar_claves(textos["clave"].value_counts()))

    nombres = textos.merge(tabla[["clave", "clave_oficial"]], on="clave")
    oficiales = (
        nombres[nombres["clave"] == nombres["clave_oficial"]]
        .groupby("clave_oficial")["nombre"].apply(nombre_visible).rename("practica")
    )
    tabla = tabla.merge(oficiales, left_on="clave_oficial", right_index=True, how="left")
    tabla.sort_values(["clave_oficial", "n"], ascending=[True, False]).to_csv(
        ETIQUETAS / "variantes.csv", index=False, encoding="utf-8"
    )

    datos = textos.merge(tabla[["clave", "clave_oficial", "practica", "metodo"]], on="clave")
    datos = datos.dropna(subset=["practica"])
    datos["grupo_texto"] = datos["nombre"].map(texto_grupo)
    resumen = datos.groupby("practica").agg(filas=("nombre", "size"), variantes=("clave", "nunique"))
    validas = resumen[(resumen["filas"] >= MIN_FILAS_CLASE) & (resumen["variantes"] >= MIN_VARIANTES_CLASE)].index
    datos = datos[datos["practica"].isin(validas)]
    datos = datos.rename(columns={"nombre": "texto"})[
        ["texto", "practica", "clave", "grupo_texto", "metodo", "carrera", "sigla", "grupo", "fuente"]
    ]
    datos.to_csv(PROCESADOS / "dataset.csv", index=False, encoding="utf-8")

    catalogo = datos.groupby("practica").agg(
        filas=("texto", "size"),
        variantes=("clave", "nunique"),
        carreras=("carrera", lambda s: ",".join(sorted(s.dropna().unique()))),
        siglas=("sigla", lambda s: ",".join(sorted(s.dropna().unique())[:8])),
    ).sort_values("filas", ascending=False)
    catalogo.to_csv(PROCESADOS / "catalogo.csv", encoding="utf-8")

    microbiologia = pd.read_csv(PROCESADOS / "microbiologia.csv")
    nombre_atencion = atenciones.drop_duplicates("formulario").set_index("formulario")["nombre"]
    kardex["nombre_atencion"] = kardex["formulario"].str.upper().map(nombre_atencion)
    salidas = pd.concat([kardex, microbiologia], ignore_index=True)
    por_practica = reactivos_por_practica(salidas, tabla)
    siglas = datos.dropna(subset=["sigla"]).groupby("practica")["sigla"].agg(lambda s: sorted(set(s)))
    por_asignatura = reactivos_por_asignatura(salidas, siglas[~siglas.index.isin(por_practica["practica"])])
    reactivos = pd.concat([por_practica.assign(base="practica", siglas=""), por_asignatura], ignore_index=True)
    reactivos.to_csv(PROCESADOS / "reactivos_por_practica.csv", index=False, encoding="utf-8")

    asignadas = tabla["clave_oficial"].notna()
    print(f"claves: {len(tabla)} | asignadas: {asignadas.sum()} | sin asignar: {(~asignadas).sum()}")
    print(f"dataset: {len(datos)} filas, {datos['practica'].nunique()} prácticas, {datos['clave'].nunique()} variantes")
    base = reactivos[reactivos["practica"].isin(catalogo.index)].drop_duplicates("practica")["base"].value_counts()
    print(f"reactivos sugeridos para {base.sum()} de {len(catalogo)} prácticas del catálogo "
          f"({base.get('practica', 0)} por su propio registro, {base.get('asignatura', 0)} por su asignatura)")


def reactivos_por_practica(salidas: pd.DataFrame, tabla: pd.DataFrame) -> pd.DataFrame:
    """Por conteo: en qué proporción de las sesiones registradas de la práctica salió cada reactivo.

    La proporción se calcula dentro de cada planilla, porque el kardex de reactivos y el de
    microbiología no registran las mismas sesiones. Si el nombre escrito en el kardex no llega
    a una práctica del catálogo, se usa el de la atención con el mismo número de formulario.
    """
    k = salidas.dropna(subset=["formulario", "nombre"]).copy()
    k["tipo"] = k["fuente"].map(TIPO_POR_FUENTE)
    practica_de = tabla.dropna(subset=["practica"]).set_index("clave")["practica"]
    k["practica"] = k["nombre"].map(clave).map(practica_de)
    if "nombre_atencion" in k:
        respaldo = k["nombre_atencion"].dropna().map(clave).map(practica_de)
        k["practica"] = k["practica"].fillna(respaldo)
    k = k.dropna(subset=["practica"])
    sesiones = k.groupby(["practica", "tipo"])["formulario"].nunique().rename("sesiones")
    uso = (k.groupby(["practica", "tipo", "reactivo"])["formulario"].nunique()
           .rename("sesiones_con_reactivo").reset_index().merge(sesiones, on=["practica", "tipo"]))
    uso["proporcion"] = (uso["sesiones_con_reactivo"] / uso["sesiones"]).round(3)
    uso = uso[uso["proporcion"] >= MIN_PROPORCION_REACTIVO]
    uso = uso.sort_values(["practica", "tipo", "proporcion", "sesiones_con_reactivo"], ascending=[True, False, False, False])
    return uso.groupby(["practica", "tipo"]).head(MAX_REACTIVOS).reset_index(drop=True)


def reactivos_por_asignatura(salidas: pd.DataFrame, siglas_por_practica: pd.Series) -> pd.DataFrame:
    """Para prácticas sin salidas propias: reactivos más frecuentes en las sesiones de sus asignaturas."""
    k = salidas.dropna(subset=["formulario", "sigla"]).copy()
    k["tipo"] = k["fuente"].map(TIPO_POR_FUENTE)
    partes = []
    for practica, siglas in siglas_por_practica.items():
        s = k[k["sigla"].isin(siglas)]
        sesiones = s.groupby("tipo")["formulario"].nunique().rename("sesiones")
        sesiones = sesiones[sesiones >= MIN_SESIONES_ASIGNATURA]
        if sesiones.empty:
            continue
        uso = (s[s["tipo"].isin(sesiones.index)].groupby(["tipo", "reactivo"])["formulario"].nunique()
               .rename("sesiones_con_reactivo").reset_index().merge(sesiones, on="tipo"))
        uso["proporcion"] = (uso["sesiones_con_reactivo"] / uso["sesiones"]).round(3)
        uso = uso[uso["proporcion"] >= MIN_PROPORCION_ASIGNATURA]
        uso = uso.sort_values(["tipo", "proporcion"], ascending=[False, False]).groupby("tipo").head(MAX_REACTIVOS_ASIGNATURA)
        presentes = sorted(set(s["sigla"]))
        partes.append(uso.assign(practica=practica, base="asignatura", siglas=",".join(presentes)))
    if not partes:
        return pd.DataFrame()
    return pd.concat(partes, ignore_index=True)


if __name__ == "__main__":
    main()
