import { useEffect, useLayoutEffect, useRef, useState } from 'react'
import './PeopleOrderManager.css'

function csrfToken() {
  const input = document.querySelector('input[name="csrfmiddlewaretoken"]')
  if (input?.value) return input.value

  const match = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

function readProfiles(sourceId) {
  const source = document.getElementById(sourceId)
  if (!source) return []

  return Array.from(source.querySelectorAll('[data-people-order-item]')).map((node) => ({
    id: Number.parseInt(node.dataset.profileId || '0', 10),
    name: node.dataset.name || 'Profile',
    role: node.dataset.role || '',
    position: node.dataset.position || '',
    imageUrl: node.dataset.imageUrl || '',
    isActive: node.dataset.active === 'true',
    editUrl: node.dataset.editUrl || '#',
    statusUrl: node.dataset.statusUrl || '#',
    deleteUrl: node.dataset.deleteUrl || '#',
  })).filter((profile) => profile.id > 0)
}

function moveItem(items, sourceId, targetId) {
  const from = items.findIndex((item) => item.id === sourceId)
  const to = items.findIndex((item) => item.id === targetId)
  if (from < 0 || to < 0 || from === to) return items

  const next = [...items]
  const [moved] = next.splice(from, 1)
  next.splice(to, 0, moved)
  return next
}

export default function PeopleOrderManager({ apiUrl = '', sourceId = '' }) {
  const [profiles, setProfiles] = useState(() => readProfiles(sourceId))
  const [draggingId, setDraggingId] = useState(null)
  const [status, setStatus] = useState('idle')
  const [revision, setRevision] = useState(0)
  const cardRefs = useRef(new Map())
  const previousRects = useRef(new Map())
  const firstRender = useRef(true)
  const latestProfilesRef = useRef(profiles)
  const savePendingRef = useRef(false)
  const savingRef = useRef(false)

  useEffect(() => {
    const fallback = document.getElementById(sourceId)
    if (!fallback) return undefined

    fallback.hidden = true
    return () => {
      fallback.hidden = false
    }
  }, [sourceId])

  const capturePositions = () => {
    const positions = new Map()
    cardRefs.current.forEach((element, id) => {
      if (element) positions.set(id, element.getBoundingClientRect())
    })
    previousRects.current = positions
  }

  useLayoutEffect(() => {
    if (firstRender.current) {
      firstRender.current = false
      return
    }

    cardRefs.current.forEach((element, id) => {
      const previous = previousRects.current.get(id)
      if (!element || !previous) return

      const current = element.getBoundingClientRect()
      const deltaX = previous.left - current.left
      const deltaY = previous.top - current.top

      if (Math.abs(deltaX) < 1 && Math.abs(deltaY) < 1) return
      if (typeof element.animate !== 'function') return

      element.animate(
        [
          { transform: `translate(${deltaX}px, ${deltaY}px)` },
          { transform: 'translate(0, 0)' },
        ],
        { duration: 230, easing: 'cubic-bezier(.2,.8,.2,1)' },
      )
    })
  }, [profiles])

  useEffect(() => {
    latestProfilesRef.current = profiles
  }, [profiles])

  useEffect(() => {
    if (!revision || !apiUrl) return undefined

    savePendingRef.current = true
    setStatus('saving')

    const timer = window.setTimeout(async () => {
      if (savingRef.current) return

      savingRef.current = true
      let failed = false

      while (savePendingRef.current) {
        savePendingRef.current = false
        const order = latestProfilesRef.current.map((profile) => profile.id)

        try {
          const response = await fetch(apiUrl, {
            method: 'POST',
            credentials: 'same-origin',
            headers: {
              'Content-Type': 'application/json',
              'X-CSRFToken': csrfToken(),
            },
            body: JSON.stringify({ order }),
          })

          if (!response.ok) throw new Error('Unable to save profile order.')
          const payload = await response.json()
          if (!payload.ok) throw new Error(payload.error || 'Unable to save profile order.')
        } catch (error) {
          failed = true
          savePendingRef.current = false
          setStatus('error')
          break
        }
      }

      savingRef.current = false
      if (!failed) setStatus('saved')
    }, 360)

    return () => window.clearTimeout(timer)
  }, [apiUrl, revision])

  const commitOrder = (next) => {
    if (next === profiles) return
    capturePositions()
    setProfiles(next)
    setRevision((value) => value + 1)
  }

  const moveBy = (id, offset) => {
    const index = profiles.findIndex((profile) => profile.id === id)
    const target = profiles[index + offset]
    if (index < 0 || !target) return
    commitOrder(moveItem(profiles, id, target.id))
  }

  if (!profiles.length) {
    return (
      <div className="people-order-empty">
        Add a profile first. New profiles will automatically appear in this ordering workspace.
      </div>
    )
  }

  return (
    <div className="people-order-manager">
      <div className="people-order-status" aria-live="polite">
        <span className={`people-order-status-dot is-${status}`} />
        {status === 'saving' && 'Saving order…'}
        {status === 'saved' && 'Order saved'}
        {status === 'error' && 'Could not save order. Move a profile or refresh to retry.'}
        {status === 'idle' && 'Drag profiles or use the arrow controls.'}
      </div>

      <div className="people-order-list">
        {profiles.map((profile, index) => (
          <article
            key={profile.id}
            ref={(element) => {
              if (element) cardRefs.current.set(profile.id, element)
              else cardRefs.current.delete(profile.id)
            }}
            className={`people-order-card ${draggingId === profile.id ? 'is-dragging' : ''}`}
            draggable
            onDragStart={(event) => {
              setDraggingId(profile.id)
              event.dataTransfer.effectAllowed = 'move'
              event.dataTransfer.setData('text/plain', String(profile.id))
            }}
            onDragEnter={(event) => {
              event.preventDefault()
              if (draggingId && draggingId !== profile.id) {
                commitOrder(moveItem(profiles, draggingId, profile.id))
              }
            }}
            onDragOver={(event) => {
              event.preventDefault()
              event.dataTransfer.dropEffect = 'move'
            }}
            onDrop={(event) => {
              event.preventDefault()
              setDraggingId(null)
            }}
            onDragEnd={() => setDraggingId(null)}
          >
            <div className="people-order-grab" aria-hidden="true" title="Drag to reorder">
              <span />
              <span />
              <span />
            </div>

            <div className="people-order-position" aria-label={`Position ${index + 1}`}>
              {index + 1}
            </div>

            <div className="people-order-avatar">
              {profile.imageUrl ? (
                <img src={profile.imageUrl} alt="" />
              ) : (
                <span>{profile.name.slice(0, 1).toUpperCase()}</span>
              )}
            </div>

            <div className="people-order-copy">
              <strong>{profile.name}</strong>
              {(profile.role || profile.position) && (
                <span>{profile.role || profile.position}</span>
              )}
              <small className={profile.isActive ? 'is-visible' : 'is-hidden'}>
                {profile.isActive ? 'Visible on public page' : 'Hidden from public page'}
              </small>
            </div>

            <div className="people-order-move-controls" aria-label={`Move ${profile.name}`}>
              <button
                type="button"
                onClick={() => moveBy(profile.id, -1)}
                disabled={index === 0}
                aria-label={`Move ${profile.name} up`}
                title="Move up"
              >
                ↑
              </button>
              <button
                type="button"
                onClick={() => moveBy(profile.id, 1)}
                disabled={index === profiles.length - 1}
                aria-label={`Move ${profile.name} down`}
                title="Move down"
              >
                ↓
              </button>
            </div>

            <div className="people-order-actions">
              <a href={profile.editUrl}>Edit</a>

              <form method="post" action={profile.statusUrl}>
                <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
                <input type="hidden" name="is_active" value={profile.isActive ? '0' : '1'} />
                <button
                  type="submit"
                  data-confirm-title={profile.isActive ? 'Hide Profile' : 'Show Profile'}
                  data-confirm={profile.isActive
                    ? `Hide '${profile.name}' from the public People & Teams page?`
                    : `Show '${profile.name}' on the public People & Teams page?`}
                >
                  {profile.isActive ? 'Hide' : 'Show'}
                </button>
              </form>

              <form method="post" action={profile.deleteUrl}>
                <input type="hidden" name="csrfmiddlewaretoken" value={csrfToken()} />
                <button
                  type="submit"
                  className="is-danger"
                  data-regret-action
                  data-regret-tone="danger"
                  data-regret-title="Delete Profile"
                  data-regret-message={`Permanently delete '${profile.name}'? This action cannot be undone.`}
                  data-regret-button="Delete Now"
                  data-confirm-title="Delete Profile"
                  data-confirm={`Permanently delete '${profile.name}'? This cannot be undone.`}
                >
                  Delete
                </button>
              </form>
            </div>
          </article>
        ))}
      </div>
    </div>
  )
}
