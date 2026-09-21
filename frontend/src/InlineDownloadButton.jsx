import { useEffect, useRef, useState } from 'react'
import './PublicationInteractions.css'

function filenameFrom(response, fallback) {
  const disposition = response.headers.get('Content-Disposition') || ''
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const regular = disposition.match(/filename=(?:"([^"]+)"|([^;]+))/i)
  let name = regular?.[1] || regular?.[2] || fallback
  if (encoded) { try { name = decodeURIComponent(encoded[1]) } catch { /* Keep plain filename. */ } }
  return Array.from(name.trim(), char => char.charCodeAt(0) < 32 || '/\\'.includes(char) ? '_' : char).join('')
}

export default function InlineDownloadButton({ url, filename }) {
  const [label, setLabel] = useState('Download PDF')
  const [busy, setBusy] = useState(false)
  const controller = useRef(null)
  const timer = useRef(null)
  useEffect(() => () => { controller.current?.abort(); clearTimeout(timer.current) }, [])
  async function download() {
    if (controller.current) return
    clearTimeout(timer.current)
    const active = new AbortController()
    controller.current = active
    setBusy(true)
    setLabel('Preparing PDF…')
    try {
      const response = await fetch(url, { credentials: 'same-origin', signal: active.signal })
      if (!response.ok) throw new Error('Download failed')
      const size = Number(response.headers.get('Content-Length'))
      setLabel('Downloading…')
      let blob
      if (response.body?.getReader) {
        const reader = response.body.getReader()
        const chunks = []
        let received = 0
        while (true) {
          const { done, value } = await reader.read()
          if (done) break
          chunks.push(value)
          received += value.length
          if (size > 0) setLabel(`${Math.min(100, Math.round(received / size * 100))}%`)
        }
        blob = new Blob(chunks, { type: 'application/pdf' })
      } else blob = await response.blob()
      if (active.signal.aborted) return
      const objectUrl = URL.createObjectURL(blob)
      const anchor = document.createElement('a')
      anchor.href = objectUrl
      anchor.download = filenameFrom(response, filename)
      document.body.append(anchor)
      anchor.click()
      anchor.remove()
      setTimeout(() => URL.revokeObjectURL(objectUrl), 10000)
      setLabel('✓ Downloaded')
    } catch (error) {
      if (error.name !== 'AbortError') setLabel('Download failed · Retry')
      else setLabel('Download PDF')
    } finally {
      controller.current = null
      setBusy(false)
      if (!active.signal.aborted) timer.current = setTimeout(() => setLabel('Download PDF'), 4000)
    }
  }
  return <span className="inline-pdf-download"><button type="button" className="reader-action-button" onClick={download} disabled={busy} aria-busy={busy}>
    {busy && <span className="inline-spinner" aria-hidden="true"/>}<span role="status">{label}</span>
  </button>{busy && <button type="button" className="inline-pdf-cancel" onClick={() => controller.current?.abort()}>Cancel</button>}</span>
}
