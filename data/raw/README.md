# Datos crudos (no versionados)

Las planillas originales tienen datos personales (docentes, auxiliares, registros, estudiantes), por eso no se suben.

Para regenerar `data/processed/` copiar aquí, con estos nombres:

| Archivo | Origen |
|---|---|
| `ATENCION 2026 JULIO AGOSTO SEPTIEMBRE.xlsx` | Laboratorio Académico FCFB — UAGRM, planilla de atenciones (Lic. Yeraldine), hoja `ATENCION 2026` |
| `KARDEX DE REACTIVOS CONTROLADOS.xlsx` | Kardex de reactivos (Lic. Elizabeth) |
| `KARDEX DE REACTIVOS NO SUSTANCIAS CONTROLADAS.xlsx` | Kardex de reactivos (Lic. Elizabeth) |

Fecha de obtención: 25 de octubre de 2026. Uso: académico, con autorización del laboratorio; los datos no son públicos.

Luego:

```
python -m src.data.extraer
```
