import { useState } from 'react'
import { api } from '../api'

const MAX_LINEAS = 200

export default function Lote() {
  const [filas, setFilas] = useState([])
  const [estado, setEstado] = useState('')

  async function procesar(archivo) {
    const lineas = (await archivo.text())
      .split(/\r?\n/)
      .map((l) => l.trim())
      .filter(Boolean)
      .slice(0, MAX_LINEAS)
    setFilas([])
    setEstado(`Procesando ${lineas.length} nombres…`)
    const resultados = []
    for (const texto of lineas) {
      try {
        const r = await api.predecir(texto, 1)
        resultados.push({ texto, practica: r.practica, probabilidad: r.probabilidad, confirmar: r.confirmar })
      } catch (e) {
        resultados.push({ texto, error: e.message })
      }
    }
    setFilas(resultados)
    setEstado(`${resultados.length} nombres procesados`)
  }

  return (
    <main className="rejilla">
      <section className="tarjeta ancho">
        <h2>Archivo con varios nombres</h2>
        <p className="nota">Un nombre de práctica por línea (.txt o .csv de una columna). Máximo {MAX_LINEAS} líneas.</p>
        <input type="file" accept=".txt,.csv" onChange={(e) => e.target.files[0] && procesar(e.target.files[0])} />
        {estado && <p className="nota">{estado}</p>}
        {filas.length > 0 && (
          <table className="tabla">
            <thead>
              <tr><th>Texto</th><th>Práctica oficial</th><th>Probabilidad</th></tr>
            </thead>
            <tbody>
              {filas.map((f, i) => (
                <tr key={i} className={f.confirmar ? 'dudosa' : ''}>
                  <td>{f.texto}</td>
                  <td>{f.error ? <span className="error">{f.error}</span> : f.practica}</td>
                  <td>{f.error ? '—' : `${(f.probabilidad * 100).toFixed(1)} %${f.confirmar ? ' ⚠' : ''}`}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </main>
  )
}
