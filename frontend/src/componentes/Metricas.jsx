import { useEffect, useState } from 'react'
import { api } from '../api'

const NOMBRES = {
  logistica: 'Regresión logística',
  complement_nb: 'Naive Bayes (Complement)',
  multinomial_nb: 'Naive Bayes (Multinomial)',
  linea_base: 'Línea base: clase más frecuente',
  regla_similitud: 'Línea base: regla de similitud',
}
const n3 = (v) => (v === undefined || v === null ? '—' : Number(v).toFixed(3))

export default function Metricas() {
  const [m, setM] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.metricas().then(setM).catch((e) => setError(e.message))
  }, [])

  if (error) return <section className="tarjeta error">{error}</section>
  if (!m) return <section className="tarjeta">Cargando métricas…</section>

  const filas = ['logistica', 'complement_nb', 'regla_similitud', 'linea_base']
  const maxExp = Math.max(...m.experimentos.map((e) => e.f1_macro_cv))

  return (
    <main className="rejilla">
      <section className="tarjeta ancho">
        <h2>Comparación de modelos</h2>
        <p className="nota">
          En producción: <strong>{NOMBRES[m.modelo_produccion]}</strong>, elegido por validación cruzada.
          Ni la prueba ni la prueba manual se usaron para ajustar nada.
        </p>
        <table className="tabla">
          <thead>
            <tr>
              <th>Modelo</th>
              <th>Config.</th>
              <th>macro-F1 CV</th>
              <th>macro-F1 prueba</th>
              <th>Exactitud prueba</th>
              <th>macro-F1 manual</th>
              <th>Exactitud manual</th>
            </tr>
          </thead>
          <tbody>
            {filas.map((k) => {
              const r = m.modelos[k]
              return (
                <tr key={k} className={k === m.modelo_produccion ? 'destacada' : ''}>
                  <td>{NOMBRES[k]}</td>
                  <td>
                    {r.modo ? `${r.modo} · ${r.ngramas} · ${JSON.stringify(r.hiperparametros)}` : '—'}
                  </td>
                  <td>{n3(r.f1_macro_cv)}</td>
                  <td>{n3(r.prueba.f1_macro)}</td>
                  <td>{n3(r.prueba.exactitud)}</td>
                  <td>{n3(r.prueba_manual?.f1_macro)}</td>
                  <td>{n3(r.prueba_manual?.exactitud)}</td>
                </tr>
              )
            })}
          </tbody>
        </table>
        <p className="nota">
          Prueba: {m.datos.prueba} textos ({m.datos.escrituras_prueba} escrituras nunca vistas), unidos por la
          regla de similitud. Prueba manual: {m.datos.prueba_manual} textos que la regla no supo unir, etiquetados
          a mano.
        </p>
      </section>

      <section className="tarjeta">
        <h2>Experimentos de preprocesamiento (CV, macro-F1)</h2>
        <ul className="alternativas">
          {m.experimentos.map((e) => (
            <li key={`${e.modo}-${e.ngramas}-${e.modelo}`}>
              <span className="nombre">
                {e.modo} · {e.ngramas} · {NOMBRES[e.modelo]}
              </span>
              <div className="barra">
                <span style={{ width: `${(e.f1_macro_cv / maxExp) * 100}%` }} />
              </div>
              <span className="valor">{n3(e.f1_macro_cv)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="tarjeta">
        <h2>Datos y TF-IDF</h2>
        <table className="tabla">
          <tbody>
            <tr><td>Filas etiquetadas</td><td>{m.datos.filas}</td></tr>
            <tr><td>Prácticas oficiales (clases)</td><td>{m.datos.practicas}</td></tr>
            <tr><td>Entrenamiento / prueba</td><td>{m.datos.entrenamiento} / {m.datos.prueba}</td></tr>
            <tr><td>n-gramas</td><td>{m.tfidf.ngramas}</td></tr>
            <tr><td>min_df / max_df</td><td>{m.tfidf.min_df} / {m.tfidf.max_df}</td></tr>
            <tr><td>max_features</td><td>{m.tfidf.max_features}</td></tr>
            <tr><td>Vocabulario final</td><td>{m.tfidf.vocabulario}</td></tr>
            <tr><td>Semilla</td><td>{m.semilla}</td></tr>
          </tbody>
        </table>

        <h3>Errores en la prueba manual</h3>
        {m.errores_prueba_manual.ejemplos.length === 0 ? (
          <p className="nota">Sin errores.</p>
        ) : (
          <table className="tabla">
            <thead>
              <tr><th>Texto</th><th>Real</th><th>Predicha</th><th>Prob.</th></tr>
            </thead>
            <tbody>
              {m.errores_prueba_manual.ejemplos.map((e) => (
                <tr key={e.texto}>
                  <td>{e.texto}</td><td>{e.practica}</td><td>{e.prediccion}</td><td>{n3(e.probabilidad)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        <h3>Errores en la prueba</h3>
        <table className="tabla">
          <thead>
            <tr><th>Texto</th><th>Real</th><th>Predicha</th><th>Prob.</th></tr>
          </thead>
          <tbody>
            {m.errores.ejemplos.map((e) => (
              <tr key={e.texto}>
                <td>{e.texto}</td><td>{e.practica}</td><td>{e.prediccion}</td><td>{n3(e.probabilidad)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </main>
  )
}
