import { useEffect } from 'react'
import './SystemUpdatesEnhancer.css'

export default function SystemUpdatesEnhancer({ mode = '' }) {
  useEffect(() => {
    const root = document.querySelector('[data-system-updates-root]')
    if (!root) return undefined

    root.dataset.enhanced = 'true'
    root.dataset.mode = mode

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const targets = Array.from(root.querySelectorAll('[data-system-update-reveal]'))
    let observer = null

    if (reducedMotion || !('IntersectionObserver' in window)) {
      targets.forEach((item) => item.classList.add('is-revealed'))
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return
            entry.target.classList.add('is-revealed')
            observer.unobserve(entry.target)
          })
        },
        { threshold: 0.08, rootMargin: '0px 0px -20px 0px' },
      )
      targets.forEach((item) => observer.observe(item))
    }

    const actionForms = Array.from(root.querySelectorAll('[data-update-action-form], [data-system-update-form]'))
    const submitHandlers = []

    actionForms.forEach((form) => {
      const handler = (event) => {
        const button =
          event.submitter
          || form.querySelector('button[type="submit"]')

        if (!button) return

        /*
         * A disabled submit button is not included in the browser's
         * submitted form data. System Update management buttons use
         * name="action" / value="publish|hide_popup", so preserve the
         * clicked button's name/value before disabling it for the
         * loading state.
         */
        const buttonName = button.getAttribute('name')

        if (buttonName) {
          const preservedValue = document.createElement('input')
          preservedValue.type = 'hidden'
          preservedValue.name = buttonName
          preservedValue.value = button.value
          preservedValue.dataset.preservedSubmitter = 'true'
          form.appendChild(preservedValue)
        }

        button.disabled = true
        button.classList.add('is-loading')
        button.dataset.originalLabel = button.textContent
        button.textContent = button.dataset.loadingLabel || 'Saving…'
      }

      form.addEventListener('submit', handler)
      submitHandlers.push([form, handler])
    })

    const audienceFieldset = root.querySelector('.system-update-audience-fieldset')
    const audienceSummary = root.querySelector('[data-update-audience-summary]')
    const audienceInputs = audienceFieldset ? Array.from(audienceFieldset.querySelectorAll('input[type="checkbox"]')) : []

    function updateAudienceSummary() {
      if (!audienceSummary) return
      const selected = audienceInputs
        .filter((input) => input.checked)
        .map((input) => input.closest('label')?.innerText.trim())
        .filter(Boolean)

      audienceSummary.textContent = selected.length ? `Audience: ${selected.join(', ')}` : 'Audience: All Staff'
    }

    audienceInputs.forEach((input) => input.addEventListener('change', updateAudienceSummary))
    updateAudienceSummary()

    return () => {
      observer?.disconnect()
      submitHandlers.forEach(([form, handler]) => form.removeEventListener('submit', handler))
      audienceInputs.forEach((input) => input.removeEventListener('change', updateAudienceSummary))
    }
  }, [mode])

  return null
}
