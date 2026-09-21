import { useEffect, useRef, useState } from 'react'
import './PublicationInteractions.css'

function filenameFrom(response, fallback) {
  const disposition = response.headers.get('Content-Disposition') || ''
  const encoded = disposition.match(/filename\*=UTF-8''([^;]+)/i)
  const regular = disposition.match(/filename=(?:"([^"]+)"|([^;]+))/i)

  let name = regular?.[1] || regular?.[2] || fallback

  if (encoded) {
    try {
      name = decodeURIComponent(encoded[1])
    } catch {
      // Keep the plain filename when decoding is not possible.
    }
  }

  return Array.from(
    (name || 'article.pdf').trim(),
    (char) => (
      char.charCodeAt(0) < 32 || '/\\'.includes(char)
        ? '_'
        : char
    ),
  ).join('')
}

function DownloadIcon({ phase }) {
  if (phase === 'success') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="m6.8 12.4 3.2 3.2 7.2-7.2" />
      </svg>
    )
  }

  if (phase === 'error') {
    return (
      <svg viewBox="0 0 24 24" aria-hidden="true">
        <path d="M12 7.2v5.6M12 16.6h.01" />
        <circle cx="12" cy="12" r="8.3" />
      </svg>
    )
  }

  if (phase === 'preparing' || phase === 'downloading') {
    return <span className="inline-pdf-spinner" aria-hidden="true" />
  }

  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M12 4.8v9.4m0 0 3.5-3.5M12 14.2l-3.5-3.5M5.2 18.5h13.6" />
    </svg>
  )
}

export default function InlineDownloadButton({ url, filename }) {
  const [phase, setPhase] = useState('idle')
  const [progress, setProgress] = useState(null)
  const controller = useRef(null)
  const resetTimer = useRef(null)

  const busy = phase === 'preparing' || phase === 'downloading'

  useEffect(
    () => () => {
      controller.current?.abort()
      clearTimeout(resetTimer.current)
    },
    [],
  )

  function resetLater(delay = 3800) {
    clearTimeout(resetTimer.current)
    resetTimer.current = setTimeout(() => {
      setPhase('idle')
      setProgress(null)
    }, delay)
  }

  async function download() {
    if (controller.current) return

    clearTimeout(resetTimer.current)

    const active = new AbortController()
    controller.current = active

    setPhase('preparing')
    setProgress(null)

    try {
      const response = await fetch(
        url,
        {
          credentials: 'same-origin',
          signal: active.signal,
        },
      )

      if (!response.ok) {
        throw new Error('Download failed')
      }

      const contentLength = Number(
        response.headers.get('Content-Length'),
      )

      setPhase('downloading')

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

          if (contentLength > 0) {
            setProgress(
              Math.min(
                100,
                Math.round(
                  (received / contentLength) * 100,
                ),
              ),
            )
          }
        }

        blob = new Blob(
          chunks,
          { type: 'application/pdf' },
        )
      } else {
        blob = await response.blob()
      }

      if (active.signal.aborted) {
        return
      }

      const objectUrl = URL.createObjectURL(blob)
      const anchor = document.createElement('a')

      anchor.href = objectUrl
      anchor.download = filenameFrom(
        response,
        filename,
      )

      document.body.append(anchor)
      anchor.click()
      anchor.remove()

      setTimeout(
        () => URL.revokeObjectURL(objectUrl),
        10000,
      )

      setProgress(100)
      setPhase('success')
      resetLater()
    } catch (error) {
      if (error.name === 'AbortError') {
        setPhase('idle')
        setProgress(null)
      } else {
        setPhase('error')
        setProgress(null)
        resetLater(5200)
      }
    } finally {
      controller.current = null
    }
  }

  function cancel() {
    controller.current?.abort()
  }

  const label = {
    idle: 'Download PDF',
    preparing: 'Preparing PDF…',
    downloading: progress === null
      ? 'Downloading PDF…'
      : `Downloading ${progress}%`,
    success: 'PDF downloaded',
    error: 'Retry download',
  }[phase]

  const assistiveStatus = {
    idle: '',
    preparing: 'Preparing PDF download.',
    downloading: progress === null
      ? 'Downloading PDF.'
      : `PDF download ${progress} percent complete.`,
    success: 'PDF downloaded successfully.',
    error: 'PDF download failed. Press the button to retry.',
  }[phase]

  return (
    <span
      className={`inline-pdf-download inline-pdf-download--${phase}`}
      data-pdf-state={phase}
    >
      <button
        type="button"
        className="reader-action-button inline-pdf-download-button"
        onClick={download}
        disabled={busy}
        aria-busy={busy}
      >
        <span className="inline-pdf-download-icon">
          <DownloadIcon phase={phase} />
        </span>

        <span className="inline-pdf-download-label">
          {label}
        </span>

        {busy && progress !== null && (
          <span
            className="inline-pdf-download-percent"
            aria-hidden="true"
          >
            {progress}%
          </span>
        )}

        {busy && (
          <span
            className={`inline-pdf-progress-track ${
              progress === null
                ? 'is-indeterminate'
                : ''
            }`}
            aria-hidden="true"
          >
            <span
              className="inline-pdf-progress-value"
              style={
                progress === null
                  ? undefined
                  : {
                    width: `${progress}%`,
                  }
              }
            />
          </span>
        )}
      </button>

      {busy && (
        <button
          type="button"
          className="inline-pdf-cancel"
          onClick={cancel}
          aria-label="Cancel PDF download"
          title="Cancel PDF download"
        >
          <span aria-hidden="true">×</span>
        </button>
      )}

      <span
        className="inline-pdf-live-status"
        role="status"
        aria-live="polite"
      >
        {assistiveStatus}
      </span>
    </span>
  )
}
