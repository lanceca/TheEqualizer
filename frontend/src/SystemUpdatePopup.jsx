import { useEffect, useMemo, useRef, useState } from 'react'
import './SystemUpdatePopup.css'

const TYPE_LABELS = new Set(['NEW', 'IMPROVED', 'FIXED', 'IMPORTANT', 'MAINTENANCE'])

function csrfToken() {
  const input = document.querySelector('input[name="csrfmiddlewaretoken"]')
  if (input?.value) return input.value

  const match = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

function parseNotes(value) {
  return String(value || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => {
      const cleaned = line.replace(/^[-•]\s*/, '')
      const match = cleaned.match(/^(NEW|IMPROVED|FIXED|IMPORTANT|MAINTENANCE)\s*:?\s*(.*)$/i)
      if (!match) return { label: '', text: cleaned }
      const label = match[1].toUpperCase()
      return {
        label: TYPE_LABELS.has(label) ? label : '',
        text: match[2] || '',
      }
    })
}

export default function SystemUpdatePopup({ apiUrl }) {
  const [update, setUpdate] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const dialog = useRef(null)

  const notes = useMemo(() => parseNotes(update?.changeNotes), [update])

  useEffect(() => {
    const controller = new AbortController()

    fetch(apiUrl, {
      credentials: 'same-origin',
      signal: controller.signal,
      headers: { Accept: 'application/json' },
    })
      .then((response) => (response.ok ? response.json() : { update: null }))
      .then((data) => setUpdate(data.update))
      .catch(() => {})

    return () => controller.abort()
  }, [apiUrl])

  useEffect(() => {
    if (!update || !dialog.current) return undefined

    const previous = document.activeElement
    const modal = dialog.current
    modal.showModal()

    return () => {
      if (modal.open) modal.close()
      previous?.focus?.()
    }
  }, [update])

  async function acknowledge() {
    setBusy(true)
    setError('')

    try {
      const response = await fetch(update.ackUrl, {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'X-CSRFToken': csrfToken(),
          Accept: 'application/json',
        },
      })

      if (!response.ok) throw new Error('Acknowledgement failed')

      setUpdate(null)

      document.querySelectorAll('[data-update-attention]').forEach((badge) => {
        const current = Number(badge.dataset.pendingCount || '0')
        const remaining = Math.max(0, current - 1)

        badge.dataset.pendingCount = String(remaining)
        badge.hidden = remaining === 0
      })
    } catch {
      setError('Could not save acknowledgement. Please try again.')
    } finally {
      setBusy(false)
    }
  }

  function dismiss() {
    if (!update?.required) setUpdate(null)
  }

  if (!update) return null

  return (
    <dialog
      ref={dialog}
      className={`system-update-dialog system-update-dialog--${String(update.type || 'improved').toLowerCase()}`}
      aria-labelledby="system-update-title"
      aria-describedby="system-update-summary"
      onCancel={(event) => {
        event.preventDefault()
        dismiss()
      }}
    >
      <div className="system-update-popup-frame">
        <div className="system-update-popup-topbar">
          <div className="system-update-popup-brand">
            <span className="system-update-popup-seal" aria-hidden="true">EQ</span>
            <span>
              <strong>THE EQUALIZER</strong>
              <small>Editorial Workspace</small>
            </span>
          </div>

          <div className="system-update-popup-version">
            <span>{update.version || 'Update'}</span>
            {!update.required && (
              <button
                type="button"
                className="system-update-popup-close"
                onClick={dismiss}
                aria-label="Dismiss update for now"
              >
                ×
              </button>
            )}
          </div>
        </div>

        <div className="system-update-popup-hero">
          <span className="system-update-popup-eyebrow">What's New</span>
          <span className={`system-update-popup-type system-update-popup-type--${String(update.type || '').toLowerCase()}`}>
            {update.type}
          </span>
          <h2 id="system-update-title">{update.title}</h2>
          <p id="system-update-summary">{update.summary}</p>
        </div>

        <div className="system-update-popup-scroll">
          <div className="system-update-popup-notes" aria-label="Release notes">
            {notes.length ? (
              <ul>
                {notes.map((note, index) => (
                  <li key={`${note.label}-${note.text}-${index}`}>
                    {note.label && (
                      <span className={`system-update-note-label system-update-note-label--${note.label.toLowerCase()}`}>
                        {note.label}
                      </span>
                    )}
                    <span>{note.text || note.label}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p>No additional release notes were provided.</p>
            )}
          </div>

          {update.required && (
            <div className="system-update-popup-required">
              <span aria-hidden="true">!</span>
              <p>
                <strong>Acknowledgement required</strong>
                <small>Please confirm this update after reviewing the release notes.</small>
              </p>
            </div>
          )}

          {error && <p className="system-update-popup-error" role="alert">{error}</p>}
        </div>

        <div className="system-update-popup-footer">
          <div className="system-update-popup-date">
            <span>Published</span>
            <strong>{update.published}</strong>
          </div>

          <div className="system-update-popup-actions">
            <a className="system-update-popup-secondary" href={update.url}>
              View Full Update
            </a>
            <button
              type="button"
              className="system-update-popup-primary"
              disabled={busy}
              onClick={acknowledge}
            >
              {busy ? 'Saving…' : 'Got it'}
            </button>
          </div>
        </div>
      </div>
    </dialog>
  )
}
