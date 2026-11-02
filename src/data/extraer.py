"""Lee las planillas originales y deja tres CSV sin datos de personas.

El kardex de microbiología no anota el nombre de la práctica: cada salida de medio
se une a la atención del mismo grupo y sigla más cercana en fecha, porque el medio
se prepara entre un día antes y unos días después de registrarse la atención.

Uso: python -m src.data.extraer
"""
from pathlib import Path
import warnings

import pandas as pd

RAIZ = Path(__file__).resolve().parents[2]
RAW = RAIZ / "data" / "raw"
SALIDA = RAIZ / "data" / "processed"

ATENCIONES = "ATENCION 2026 JULIO AGOSTO SEPTIEMBRE.xlsx"
KARDEX = {
    "controlado": "KARDEX DE REACTIVOS CONTROLADOS.xlsx",
    "no_controlado": "KARDEX DE REACTIVOS NO SUSTANCIAS CONTROLADAS.xlsx",
}
MICROBIOLOGIA = "Kardex de Microbiologia 27_08_2026.xlsx"
HOJAS_NO_MEDIOS = {"REACTIVOS INORGANICOS SOLIDOS", "Lista_de_Medios", "BASE_MATERIAS_1"}
MICRO_DIAS_ANTES = 1
MICRO_DIAS_DESPUES = 3
CARRERAS = {"FAR", "BQM"}


def _limpiar_str(serie: pd.Series) -> pd.Series:
    return serie.astype("string").str.strip().replace("", pd.NA)


def leer_atenciones() -> pd.DataFrame:
    df = pd.read_excel(RAW / ATENCIONES, sheet_name="ATENCION 2026")
    df.columns = [str(c).strip() for c in df.columns]
    df = df.rename(columns={"": "formulario", "#REF!": "fecha"})
    df["fecha"] = pd.to_datetime(df["fecha"], errors="coerce")
    columnas = {
        "formulario": "formulario",
        "fecha": "fecha",
        "NOMBRE DE PRACTICAS DESARROLLADAS": "nombre",
        "CARRERA (FAR / BQM/POSG/EXTRA/EXTENCION)": "carrera",
        "ASIGNATURA": "asignatura",
        "SIGLA (MAYUSCULA CON GUION)": "sigla",
        "GRUPO  (MAYUSCULA)": "grupo",
        "MES": "mes",
    }
    df = df[list(columnas)].rename(columns=columnas)
    for c in df.columns.drop("fecha"):
        df[c] = _limpiar_str(df[c])
    df["formulario"] = df["formulario"].str.upper()
    df["carrera"] = df["carrera"].str.upper()
    df["sigla"] = df["sigla"].str.upper()
    df["grupo"] = df["grupo"].str.upper()
    df = df[df["carrera"].isin(CARRERAS)]
    df["fuente"] = "atenciones"
    return df.reset_index(drop=True)


def leer_kardex() -> pd.DataFrame:
    partes = []
    for tipo, archivo in KARDEX.items():
        df = pd.read_excel(RAW / archivo, header=9)
        df.columns = [str(c).strip() for c in df.columns]
        columnas = {
            "COD. FRASC": "reactivo",
            "NOMBRE DE LA PRACTICA": "nombre",
            "SIGLA": "sigla",
            "GRUPO": "grupo",
            "N° FORMULARIO": "formulario",
            "CARRERA": "carrera",
            "Cant. Gastada g": "gastado_g",
        }
        df = df[list(columnas)].rename(columns=columnas)
        for c in ["reactivo", "nombre", "sigla", "grupo", "formulario", "carrera"]:
            df[c] = _limpiar_str(df[c])
        df["reactivo"] = df["reactivo"].str.upper()
        df["carrera"] = df["carrera"].str.upper()
        df["sigla"] = df["sigla"].str.upper()
        df["grupo"] = df["grupo"].str.upper()
        df["gastado_g"] = pd.to_numeric(df["gastado_g"], errors="coerce")
        df["tipo_reactivo"] = tipo
        partes.append(df.dropna(subset=["reactivo", "nombre"]))
    df = pd.concat(partes, ignore_index=True)
    df["fuente"] = "kardex"
    return df


def _hoja_medio(xls: pd.ExcelFile, hoja: str) -> pd.DataFrame:
    crudo = pd.read_excel(xls, sheet_name=hoja, header=None)
    fila = next(i for i in range(min(15, len(crudo)))
                if crudo.iloc[i].astype(str).str.upper().str.contains("SIGLA").any())
    df = crudo.iloc[fila + 1:].copy()
    df.columns = [str(c).strip().upper() for c in crudo.iloc[fila]]
    col_fecha = next(c for c in df.columns if c.startswith("FECHA"))
    if "SIGLA" in df.columns and "GRUPO" in df.columns:
        sigla, grupo = df["SIGLA"], df["GRUPO"]
    else:  # columna única "SIGLA / GRUPO", p. ej. "BQM-407/A1"
        partes = df[next(c for c in df.columns if "SIGLA" in c)].astype("string").str.split("/", n=1, expand=True)
        sigla = partes[0]
        grupo = partes[1] if 1 in partes.columns else pd.Series(pd.NA, index=df.index)
    return pd.DataFrame({
        "reactivo": hoja.strip().upper(),
        "fecha_uso": pd.to_datetime(df[col_fecha], errors="coerce"),
        "sigla": _limpiar_str(sigla.astype("string")).str.upper().str.replace(" ", "-"),
        "grupo": _limpiar_str(grupo.astype("string")).str.upper(),
    })


def leer_microbiologia(atenciones: pd.DataFrame) -> pd.DataFrame:
    xls = pd.ExcelFile(RAW / MICROBIOLOGIA)
    medios = pd.concat([_hoja_medio(xls, h) for h in xls.sheet_names if h not in HOJAS_NO_MEDIOS], ignore_index=True)
    medios = medios.dropna(subset=["fecha_uso", "sigla", "grupo"])
    medios = medios[medios["sigla"].str.fullmatch(r"[A-Z]{3}-\d{3}")].reset_index(names="salida")

    sesiones = atenciones.dropna(subset=["fecha", "nombre"])[["fecha", "sigla", "grupo", "nombre"]]
    unidas = medios.merge(sesiones, on=["sigla", "grupo"])
    dias = (unidas["fecha"] - unidas["fecha_uso"]).dt.days
    unidas = unidas[(dias >= -MICRO_DIAS_ANTES) & (dias <= MICRO_DIAS_DESPUES)].assign(distancia=dias.abs())
    unidas = unidas.sort_values(["distancia", "fecha"]).drop_duplicates("salida")
    unidas["formulario"] = "MIC-" + unidas["sigla"] + "-" + unidas["grupo"] + "-" + unidas["fecha"].dt.strftime("%Y%m%d")
    unidas["fuente"] = "microbiologia"
    print(f"microbiología: {len(unidas)} de {len(medios)} salidas de medios unidas a una atención")
    return unidas[["reactivo", "nombre", "sigla", "grupo", "formulario", "fuente"]].reset_index(drop=True)


def main() -> None:
    warnings.filterwarnings("ignore", category=UserWarning)
    SALIDA.mkdir(parents=True, exist_ok=True)
    atenciones = leer_atenciones()
    kardex = leer_kardex()
    microbiologia = leer_microbiologia(atenciones)
    atenciones.to_csv(SALIDA / "atenciones.csv", index=False, encoding="utf-8")
    kardex.to_csv(SALIDA / "kardex.csv", index=False, encoding="utf-8")
    microbiologia.to_csv(SALIDA / "microbiologia.csv", index=False, encoding="utf-8")
    print(f"atenciones FAR/BQM: {len(atenciones)} filas ({atenciones['nombre'].notna().sum()} con nombre)")
    print(f"kardex: {len(kardex)} salidas, {kardex['reactivo'].nunique()} reactivos, {kardex['nombre'].nunique()} nombres")
    print(f"medios de cultivo: {microbiologia['reactivo'].nunique()}")


if __name__ == "__main__":
    main()
