import { useEffect, useRef, useState } from 'react'
import './PublicationInteractions.css'

export default function SystemUpdatePopup({ apiUrl }) {
  const [update, setUpdate] = useState(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const dialog = useRef(null)
  useEffect(() => {
    const controller = new AbortController()
    fetch(apiUrl, { credentials: 'same-origin', signal: controller.signal })
      .then(response => response.ok ? response.json() : { update: null })
      .then(data => setUpdate(data.update)).catch(() => {})
    return () => controller.abort()
  }, [apiUrl])
  useEffect(() => {
    if (!update || !dialog.current) return
    const previous = document.activeElement
    const modal = dialog.current
    modal.showModal()
    return () => { modal.close(); previous?.focus() }
  }, [update])
  async function acknowledge() {
    setBusy(true)
    setError('')
    const token = document.querySelector('input[name="csrfmiddlewaretoken"]')?.value || ''
    try {
      const response = await fetch(update.ackUrl, { method: 'POST', credentials: 'same-origin', headers: { 'X-CSRFToken': token, Accept: 'application/json' } })
      if (!response.ok) throw new Error('Acknowledgement failed')
      setUpdate(null)
      // Counts on this page should reflect the acknowledgement immediately.
      document.querySelectorAll('[data-update-count]').forEach(badge => {
        const count = Math.max(0, Number(badge.textContent) - 1)
        badge.textContent = count || ''
        badge.hidden = !count
      })
    } catch { setError('Could not save acknowledgement. Please try again.') }
    finally { setBusy(false) }
  }
  if (!update) return null
  return <dialog ref={dialog} className="system-update-dialog" aria-labelledby="system-update-title" onCancel={event => { event.preventDefault(); if (!update.required) setUpdate(null) }}>
    <p className="system-update-brand">THE EQUALIZER <span>{update.version}</span></p>
    <p className="system-update-eyebrow">WHAT'S NEW</p><h2 id="system-update-title">{update.title}</h2>
    <p>{update.summary}</p><span className="system-update-type">{update.type}</span><div className="system-update-notes">{update.changeNotes}</div>
    <p className="system-update-date">Published: {update.published}</p>
    {update.required && <p>Please acknowledge this update to mark it complete.</p>}
    {error && <p role="alert">{error}</p>}
    <div className="system-update-actions"><a href={update.url}>View Full Update</a><button type="button" className="approve-button" disabled={busy} onClick={acknowledge}>{busy ? 'Saving…' : 'Got it'}</button></div>
  </dialog>
}
