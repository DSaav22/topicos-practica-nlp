const BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'

async function pedir(ruta, opciones = {}) {
  const r = await fetch(`${BASE}${ruta}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opciones,
  })
  const cuerpo = await r.json()
  if (!r.ok) {
    throw new Error(cuerpo.detalle?.join(' · ') ?? cuerpo.error ?? `error ${r.status}`)
  }
  return cuerpo
}

export const api = {
  salud: () => pedir('/salud'),
  metricas: () => pedir('/metricas'),
  predecir: (texto, topK = 3) =>
    pedir('/predecir', { method: 'POST', body: JSON.stringify({ texto, top_k: topK }) }),
  preprocesar: (texto, modo) =>
    pedir('/preprocesar', { method: 'POST', body: JSON.stringify({ texto, modo }) }),
}
