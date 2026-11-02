"""Lee las planillas originales y deja dos CSV sin datos de personas.

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
CARRERAS = {"FAR", "BQM"}


def _limpiar_str(serie: pd.Series) -> pd.Series:
    return serie.astype("string").str.strip().replace("", pd.NA)


def leer_atenciones() -> pd.DataFrame:
    df = pd.read_excel(RAW / ATENCIONES, sheet_name="ATENCION 2026")
    df.columns = [str(c).strip() for c in df.columns]
    columnas = {
        "NOMBRE DE PRACTICAS DESARROLLADAS": "nombre",
        "CARRERA (FAR / BQM/POSG/EXTRA/EXTENCION)": "carrera",
        "ASIGNATURA": "asignatura",
        "SIGLA (MAYUSCULA CON GUION)": "sigla",
        "GRUPO  (MAYUSCULA)": "grupo",
        "MES": "mes",
    }
    df = df[list(columnas)].rename(columns=columnas)
    for c in df.columns:
        df[c] = _limpiar_str(df[c])
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


def main() -> None:
    warnings.filterwarnings("ignore", category=UserWarning)
    SALIDA.mkdir(parents=True, exist_ok=True)
    atenciones = leer_atenciones()
    kardex = leer_kardex()
    atenciones.to_csv(SALIDA / "atenciones.csv", index=False, encoding="utf-8")
    kardex.to_csv(SALIDA / "kardex.csv", index=False, encoding="utf-8")
    print(f"atenciones FAR/BQM: {len(atenciones)} filas ({atenciones['nombre'].notna().sum()} con nombre)")
    print(f"kardex: {len(kardex)} salidas, {kardex['reactivo'].nunique()} reactivos, {kardex['nombre'].nunique()} nombres")


if __name__ == "__main__":
    main()
