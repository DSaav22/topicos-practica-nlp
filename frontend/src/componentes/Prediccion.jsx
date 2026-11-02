import { useEffect, useState } from 'react'
import { api } from '../api'

const pct = (p) => `${(p * 100).toFixed(1)} %`
const ancho = (p) => `${(p * 100).toFixed(1)}%`

export default function Prediccion({ texto }) {
  const [res, setRes] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api.predecir(texto, 5).then(setRes).catch((e) => setError(e.message))
  }, [texto])

  if (error) return <section className="tarjeta error">{error}</section>
  if (!res) return <section className="tarjeta">Prediciendo…</section>

  return (
    <section className="tarjeta">
      <h2>Práctica sugerida</h2>
      <p className="practica">{res.practica}</p>
      <div className="barra grande">
        <span style={{ width: ancho(res.probabilidad) }} />
      </div>
      <p className="prob">{pct(res.probabilidad)}</p>
      {res.confirmar && (
        <p className="aviso">⚠ La segunda opción está cerca: el auxiliar debe confirmar entre las alternativas.</p>
      )}

      <h3>Alternativas</h3>
      <ul className="alternativas">
        {res.alternativas.map((a) => (
          <li key={a.practica}>
            <span className="nombre">{a.practica}</span>
            <div className="barra">
              <span style={{ width: ancho(a.probabilidad) }} />
            </div>
            <span className="valor">{pct(a.probabilidad)}</span>
          </li>
        ))}
      </ul>

      <h3>Reactivos que suelen salir con esta práctica</h3>
      {res.reactivos_sugeridos.length === 0 ? (
        <p className="nota">El kardex no tiene salidas suficientes para esta práctica.</p>
      ) : (
        <table className="tabla">
          <thead>
            <tr>
              <th>Reactivo</th>
              <th>Sesiones en que salió</th>
            </tr>
          </thead>
          <tbody>
            {res.reactivos_sugeridos.map((r) => (
              <tr key={r.reactivo}>
                <td>{r.reactivo}</td>
                <td>{pct(r.proporcion)} de {r.sesiones}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      <p className="nota">{res.nota_reactivos}</p>
    </section>
  )
}
