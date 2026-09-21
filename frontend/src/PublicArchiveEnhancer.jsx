import { useEffect } from 'react'
import './PublicArchiveEnhancer.css'

const FILTER_LABELS = {
  q: 'Search',
  category: 'Category',
  month: 'Month',
  start: 'From',
  end: 'Through',
}

function selectedValue(field) {
  if (!field) return ''
  if (field.tagName === 'SELECT') {
    const option = field.options[field.selectedIndex]
    return option?.value ? option.textContent.trim() : ''
  }
  return field.value?.trim() || ''
}

export default function PublicArchiveEnhancer() {
  useEffect(() => {
    const root = document.querySelector('[data-archive-root]')
    if (!root) return undefined

    const form = root.querySelector('.library-filters')
    const chipHost = root.querySelector('[data-archive-active-filters]')
    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    const revealTargets = Array.from(root.querySelectorAll('[data-archive-reveal]'))
    let observer = null

    if (reducedMotion || !('IntersectionObserver' in window)) {
      revealTargets.forEach((item) => item.classList.add('is-revealed'))
    } else {
      observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (!entry.isIntersecting) return
            entry.target.classList.add('is-revealed')
            observer.unobserve(entry.target)
          })
        },
        { threshold: 0.08, rootMargin: '0px 0px -22px 0px' },
      )
      revealTargets.forEach((item) => observer.observe(item))
    }

    function renderChips() {
      if (!form || !chipHost) return
      chipHost.replaceChildren()

      const active = []
      Object.keys(FILTER_LABELS).forEach((name) => {
        const field = form.elements.namedItem(name)
        const value = selectedValue(field)
        if (value) active.push({ name, value, field })
      })

      if (!active.length) {
        chipHost.hidden = true
        return
      }

      chipHost.hidden = false

      const label = document.createElement('span')
      label.className = 'archive-filter-chip-label'
      label.textContent = 'Active filters'
      chipHost.append(label)

      active.forEach(({ name, value, field }) => {
        const button = document.createElement('button')
        button.type = 'button'
        button.className = 'archive-filter-chip'
        button.innerHTML = `<span>${FILTER_LABELS[name]}: ${value}</span><span aria-hidden="true">×</span>`
        button.setAttribute('aria-label', `Remove ${FILTER_LABELS[name]} filter: ${value}`)
        button.addEventListener('click', () => {
          if (field.tagName === 'SELECT') field.selectedIndex = 0
          else field.value = ''
          form.requestSubmit()
        })
        chipHost.append(button)
      })
    }

    renderChips()

    const onSubmit = () => {
      form?.classList.add('is-submitting')
      const submit = form?.querySelector('button[type="submit"]')
      if (submit) {
        submit.dataset.originalLabel = submit.textContent
        submit.textContent = 'Applying…'
        submit.disabled = true
      }
    }

    form?.addEventListener('submit', onSubmit)

    return () => {
      observer?.disconnect()
      form?.removeEventListener('submit', onSubmit)
    }
  }, [])

  return null
}
