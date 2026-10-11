import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import './RegretActionGuard.css'

const COUNTDOWN_MS = 10000

function getSubmitter(target) {
  if (!target?.closest) return null
  const button = target.closest('button[type="submit"], input[type="submit"]')
  return button?.form ? button : null
}

function getRegretSource(form, submitter) {
  if (submitter?.hasAttribute('data-regret-action')) return submitter
  if (form?.hasAttribute('data-regret-action')) return form
  return null
}

function labelFor(submitter, source) {
  return (
    source?.dataset.regretButton
    || submitter?.textContent
    || submitter?.value
    || 'Send Now'
  ).trim()
}

export default function RegretActionGuard() {
  const [pending, setPending] = useState(null)
  const [remainingMs, setRemainingMs] = useState(COUNTDOWN_MS)
  const [sending, setSending] = useState(false)
  const deadlineRef = useRef(0)
  const sourceRef = useRef(null)
  const submitLockRef = useRef(false)

  const close = useCallback(() => {
    if (sending) return
    const source = sourceRef.current
    setPending(null)
    setRemainingMs(COUNTDOWN_MS)
    deadlineRef.current = 0
    sourceRef.current = null
    document.body.classList.remove('regret-action-open')
    window.setTimeout(() => source?.focus?.(), 0)
  }, [sending])

  const performSubmit = useCallback((payload) => {
    if (!payload || submitLockRef.current) return

    const { form, submitter, source } = payload
    submitLockRef.current = true
    setSending(true)

    form.dataset.regretBypass = 'true'
    if (submitter) submitter.dataset.regretBypass = 'true'

    const confirmationAttributes = [
      'data-confirm',
      'data-confirm-title',
      'data-confirm-button',
    ]
    const savedConfirmationAttributes = new Map()

    if (source) {
      confirmationAttributes.forEach((attribute) => {
        if (source.hasAttribute(attribute)) {
          savedConfirmationAttributes.set(attribute, source.getAttribute(attribute))
          source.removeAttribute(attribute)
        }
      })
    }

    setPending(null)
    setRemainingMs(COUNTDOWN_MS)
    deadlineRef.current = 0
    sourceRef.current = null
    document.body.classList.remove('regret-action-open')

    try {
      if (submitter && typeof form.requestSubmit === 'function') {
        form.requestSubmit(submitter)
      } else if (typeof form.requestSubmit === 'function') {
        form.requestSubmit()
      } else {
        HTMLFormElement.prototype.submit.call(form)
      }
    } finally {
      window.setTimeout(() => {
        delete form.dataset.regretBypass
        if (submitter) delete submitter.dataset.regretBypass
        if (source) {
          savedConfirmationAttributes.forEach((value, attribute) => {
            source.setAttribute(attribute, value)
          })
        }
        submitLockRef.current = false
        setSending(false)
      }, 1000)
    }
  }, [])

  const open = useCallback((form, submitter, source) => {
    if (!form || !source || sending) return

    if (!form.checkValidity()) {
      form.reportValidity()
      return
    }

    sourceRef.current = source
    deadlineRef.current = performance.now() + COUNTDOWN_MS
    setRemainingMs(COUNTDOWN_MS)
    setPending({
      form,
      submitter,
      source,
      title:
        source.dataset.regretTitle
        || source.dataset.confirmTitle
        || 'Confirm action',
      message:
        source.dataset.regretMessage
        || source.dataset.confirm
        || 'You still have a few seconds to change your mind.',
      buttonLabel: labelFor(submitter, source),
      tone: source.dataset.regretTone || 'default',
    })
    document.body.classList.add('regret-action-open')
  }, [sending])

  useEffect(() => {
    const markSourcesReady = () => {
      document.querySelectorAll('[data-regret-action]').forEach((source) => {
        source.dataset.regretReady = 'true'
      })
    }

    markSourcesReady()

    const observer = new MutationObserver(markSourcesReady)
    observer.observe(document.body, { childList: true, subtree: true })

    const onClick = (event) => {
      const submitter = getSubmitter(event.target)
      if (!submitter) return

      const form = submitter.form
      if (
        form.dataset.regretBypass === 'true'
        || submitter.dataset.regretBypass === 'true'
      ) return

      const source = getRegretSource(form, submitter)
      if (!source) return

      event.preventDefault()
      event.stopImmediatePropagation()
      open(form, submitter, source)
    }

    const onSubmit = (event) => {
      const form = event.target
      if (!form || form.tagName !== 'FORM') return

      const submitter = event.submitter || null
      if (
        form.dataset.regretBypass === 'true'
        || submitter?.dataset.regretBypass === 'true'
      ) return

      const source = getRegretSource(form, submitter)
      if (!source) return

      event.preventDefault()
      event.stopImmediatePropagation()
      open(form, submitter, source)
    }

    const onDelegatedRegret = (event) => {
      const { form, submitter, source } = event.detail || {}
      if (!form || !source) return
      if (
        form.dataset.regretBypass === 'true'
        || submitter?.dataset.regretBypass === 'true'
      ) return
      open(form, submitter || null, source)
    }

    window.addEventListener('equalizer:regret-action', onDelegatedRegret)
    document.addEventListener('click', onClick, true)
    document.addEventListener('submit', onSubmit, true)

    return () => {
      observer.disconnect()
      window.removeEventListener('equalizer:regret-action', onDelegatedRegret)
      document.removeEventListener('click', onClick, true)
      document.removeEventListener('submit', onSubmit, true)
    }
  }, [open])

  useEffect(() => {
    if (!pending || sending) return undefined

    let frame = 0

    const tick = (now) => {
      const remaining = Math.max(0, deadlineRef.current - now)
      setRemainingMs(remaining)

      if (remaining <= 0) {
        performSubmit(pending)
        return
      }

      frame = window.requestAnimationFrame(tick)
    }

    frame = window.requestAnimationFrame(tick)
    return () => window.cancelAnimationFrame(frame)
  }, [pending, performSubmit, sending])

  useEffect(() => {
    if (!pending) return undefined

    const onKeyDown = (event) => {
      if (event.key === 'Escape') {
        event.preventDefault()
        close()
      }
    }

    document.addEventListener('keydown', onKeyDown)
    return () => document.removeEventListener('keydown', onKeyDown)
  }, [close, pending])

  const seconds = Math.max(0, Math.ceil(remainingMs / 1000))
  const progress = useMemo(
    () => Math.max(0, Math.min(1, remainingMs / COUNTDOWN_MS)),
    [remainingMs],
  )

  if (!pending) return null

  return (
    <div
      className={`regret-action-overlay regret-action-overlay--${pending.tone}`}
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) close()
      }}
    >
      <section
        className="regret-action-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="regret-action-title"
        aria-describedby="regret-action-message"
      >
        <div className="regret-action-meter" aria-hidden="true">
          <svg viewBox="0 0 56 56">
            <circle className="regret-action-meter-track" cx="28" cy="28" r="23" />
            <circle
              className="regret-action-meter-progress"
              cx="28"
              cy="28"
              r="23"
              pathLength="1"
              style={{ strokeDashoffset: 1 - progress }}
            />
          </svg>
          <strong>{seconds}</strong>
        </div>

        <div className="regret-action-copy">
          <p className="regret-action-kicker">Decision window</p>
          <h2 id="regret-action-title">{pending.title}</h2>
          <p id="regret-action-message">{pending.message}</p>
          <span className="regret-action-auto-copy">
            {sending ? 'Sending now…' : `Automatically continues in ${seconds}s`}
          </span>
        </div>

        <div className="regret-action-actions">
          <button
            type="button"
            className="regret-action-cancel"
            onClick={close}
            disabled={sending}
          >
            Cancel
          </button>
          <button
            type="button"
            className="regret-action-send"
            onClick={() => performSubmit(pending)}
            disabled={sending}
            autoFocus
          >
            {sending ? 'Sending…' : pending.buttonLabel}
          </button>
        </div>
      </section>
    </div>
  )
}
