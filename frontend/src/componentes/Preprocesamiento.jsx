import { useEffect, useState } from 'react'
import { api } from '../api'

function Tokens({ lista, tipo = '' }) {
  if (!lista.length) return <span className="nota">(ninguna)</span>
  return (
    <div className="tokens">
      {lista.map((t, i) => (
        <span key={`${t}-${i}`} className={`token ${tipo}`}>{t}</span>
      ))}
    </div>
  )
}

export default function Preprocesamiento({ texto, modoModelo }) {
  const [modo, setModo] = useState(modoModelo ?? 'stem')
  const [pasos, setPasos] = useState(null)
  const [error, setError] = useState('')

  useEffect(() => {
    api
      .preprocesar(texto, modo)
      .then((p) => {
        setPasos(p)
        setError('')
      })
      .catch((e) => setError(e.message))
  }, [texto, modo])

  return (
    <section className="tarjeta">
      <div className="titulo-fila">
        <h2>Preprocesamiento paso a paso</h2>
        <div className="selector">
          {['stem', 'lemma'].map((m) => (
            <button key={m} className={modo === m ? 'activa' : ''} onClick={() => setModo(m)}>
              {m === 'stem' ? 'Stemming' : 'Lematización'}
              {m === modoModelo ? ' (modelo)' : ''}
            </button>
          ))}
        </div>
      </div>
      {error && <p className="error">{error}</p>}
      {pasos && (
        <ol className="pasos">
          <li>
            <strong>Original</strong>
            <code>{pasos.original}</code>
          </li>
          <li>
            <strong>Normalizado</strong>
            <span className="nota">minúsculas, sin URLs, emojis, puntuación ni números</span>
            <code>{pasos.normalizado}</code>
          </li>
          <li>
            <strong>Tokens</strong>
            <Tokens lista={pasos.tokens} />
          </li>
          <li>
            <strong>Stop words eliminadas</strong>
            <Tokens lista={pasos.stop_words_eliminadas} tipo="quitada" />
          </li>
          <li>
            <strong>{pasos.modo === 'stem' ? 'Raíces (Snowball)' : 'Lemas (spaCy)'}</strong>
            <Tokens lista={pasos.raices_o_lemas} tipo="raiz" />
          </li>
          <li>
            <strong>Texto que entra a TF-IDF</strong>
            <code>{pasos.texto_final || '(vacío)'}</code>
          </li>
        </ol>
      )}
    </section>
  )
}
