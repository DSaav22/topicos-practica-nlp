import { useEffect, useState } from 'react'
import { api } from './api'
import Prediccion from './componentes/Prediccion'
import Preprocesamiento from './componentes/Preprocesamiento'
import Metricas from './componentes/Metricas'
import Lote from './componentes/Lote'

const VISTAS = [
  { id: 'prediccion', nombre: 'Predicción' },
  { id: 'lote', nombre: 'Archivo con varios' },
  { id: 'metricas', nombre: 'Métricas' },
]

export default function App() {
  const [vista, setVista] = useState('prediccion')
  const [salud, setSalud] = useState(null)
  const [errorSalud, setErrorSalud] = useState('')
  const [texto, setTexto] = useState('')
  const [enviado, setEnviado] = useState('')

  useEffect(() => {
    api.salud().then(setSalud).catch(() => setErrorSalud('La API no responde en http://localhost:8000'))
  }, [])

  return (
    <div className="pagina">
      <header className="cabecera">
        <div>
          <h1>Práctica oficial a partir del nombre escrito</h1>
          <p className="sub">Laboratorio Académico FCFB — UAGRM · Tópicos y Programación Avanzada</p>
        </div>
        <div className={`estado ${salud ? 'ok' : 'mal'}`}>
          {salud
            ? `API ok · ${salud.modelo} · ${salud.practicas} prácticas · ${salud.preprocesamiento}`
            : errorSalud || 'conectando…'}
        </div>
      </header>

      <nav className="pestanas">
        {VISTAS.map((v) => (
          <button key={v.id} className={vista === v.id ? 'activa' : ''} onClick={() => setVista(v.id)}>
            {v.nombre}
          </button>
        ))}
      </nav>

      {vista === 'prediccion' && (
        <main className="rejilla">
          <section className="tarjeta ancho">
            <form
              className="entrada"
              onSubmit={(e) => {
                e.preventDefault()
                setEnviado(texto)
              }}
            >
              <label htmlFor="texto">Título de la práctica, como lo escribe el auxiliar</label>
              <div className="fila">
                <input
                  id="texto"
                  value={texto}
                  maxLength={500}
                  placeholder="ej. preparacion de soluciones de un phdeterminado"
                  onChange={(e) => setTexto(e.target.value)}
                />
                <button type="submit" disabled={!texto.trim()}>Analizar</button>
              </div>
              <div className="ejemplos">
                {[
                  'PREPARACION DE SOLUCIONES BUFFER',
                  'oreparacion de soluciones unidades fisecas',
                  'LAB 4 cromatografia',
                  'lab 2 alcanos',
                  'genero staphylococcus',
                  'formacion de precipitados',
                ].map((e) => (
                  <button
                    type="button"
                    key={e}
                    className="chip"
                    onClick={() => {
                      setTexto(e)
                      setEnviado(e)
                    }}
                  >
                    {e}
                  </button>
                ))}
              </div>
            </form>
          </section>
          {enviado && (
            <>
              <Prediccion key={enviado} texto={enviado} />
              <Preprocesamiento
                key={`${enviado}-${salud?.preprocesamiento}`}
                texto={enviado}
                modoModelo={salud?.preprocesamiento}
              />
            </>
          )}
        </main>
      )}
      {vista === 'lote' && <Lote />}
      {vista === 'metricas' && <Metricas />}
    </div>
  )
}
