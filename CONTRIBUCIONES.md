# Contribuciones

El proyecto se hizo de forma individual: un solo integrante cubrió los cuatro roles sugeridos por la guía. Por eso no hay pull requests revisados por otro integrante; el trabajo quedó en commits separados por funcionalidad sobre `main`.

| Integrante | Rol | Qué hizo | Commits |
|---|---|---|---|
| Diego Saavedra | Datos y NLP | Extracción sin datos personales, tabla variante → práctica oficial con reglas de similitud y palabras exactas del dominio, fusiones manuales, prueba manual, pipeline de preprocesamiento (normalización, stop words del dominio, Snowball y spaCy), notebook de análisis exploratorio | `feat(data): extraer…`, `feat(nlp): pipeline…`, `feat(data): tabla variante…`, `fix(data): incluir en el catálogo…`, `docs(notebook)…` |
| Diego Saavedra | Modelado | Comparación de stemming/lematización y n-gramas, regresión logística y Naive Bayes con validación cruzada agrupada, `GridSearchCV`, líneas base (clase más frecuente y regla de similitud), análisis de errores | `feat(models): entrenar…` |
| Diego Saavedra | Backend | API FastAPI (`/salud`, `/predecir`, `/preprocesar`, `/metricas`, `/practicas`), validaciones, regla de confirmación por margen, pruebas con pytest, versiones fijadas | `feat(api)…`, `build: fijar versiones…` |
| Diego Saavedra | Frontend | Interfaz React: predicción con probabilidades y reactivos sugeridos, preprocesamiento paso a paso, panel de métricas, carga de archivo con varios nombres | `feat(frontend)…` |

La lista completa está en `git log --oneline`.

Uso de asistentes de IA: declarado en la sección 8 de [`docs/informe.md`](docs/informe.md).
