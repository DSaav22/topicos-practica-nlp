import { useEffect, useState } from 'react'
import { api } from '../api'

const pct = (p) => `${(p * 100).toFixed(1)} %`
const ancho = (p) => `${(p * 100).toFixed(1)}%`
const POCAS_SESIONES = 3
const TIPOS = [
  { id: 'reactivo', nombre: 'Reactivos' },
  { id: 'medio de cultivo', nombre: 'Medios de cultivo' },
]

function Reactivos({ res }) {
  if (res.reactivos_sugeridos.length === 0) {
    return <p className="nota">{res.nota_reactivos}</p>
  }
  const titulo =
    res.base_reactivos === 'asignatura'
      ? `Reactivos más usados en ${res.siglas_base.join(', ')}`
      : 'Reactivos que probablemente usará'
  return (
    <div className="reactivos">
      <h3>{titulo}</h3>
      {TIPOS.map(({ id, nombre }) => {
        const lista = res.reactivos_sugeridos.filter((r) => r.tipo === id)
        if (lista.length === 0) return null
        const sesiones = lista[0].sesiones
        return (
          <div key={id}>
            <p className="subtitulo">
              {nombre} · según {sesiones} {sesiones === 1 ? 'sesión registrada' : 'sesiones registradas'}
            </p>
            {sesiones < POCAS_SESIONES && (
              <p className="aviso">⚠ Pocas sesiones registradas: tómelo como referencia.</p>
            )}
            <ul className="alternativas">
              {lista.map((r) => (
                <li key={r.reactivo}>
                  <span className="nombre">{r.reactivo}</span>
                  <div className="barra verde">
                    <span style={{ width: ancho(r.proporcion) }} />
                  </div>
                  <span className="valor">{pct(r.proporcion)}</span>
                </li>
              ))}
            </ul>
          </div>
        )
      })}
      <p className="nota">{res.nota_reactivos} El porcentaje es la parte de las sesiones en que salió cada uno.</p>
    </div>
  )
}

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

      <Reactivos res={res} />

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
    </section>
  )
}
