import { useEffect } from 'react'
import './DashboardEnhancer.css'

const numberFormatter =
  new Intl.NumberFormat('en-US')

const ICONS = {
  status: '<circle cx="12" cy="12" r="8"/><path d="m8.5 12 2.2 2.2 4.8-5"/>',
  mail: '<rect x="3" y="5" width="18" height="14" rx="2"/><path d="m4 7 8 6 8-6"/>',
  phone: '<rect x="7" y="2.5" width="10" height="19" rx="2"/><path d="M10 5h4M11 18.5h2"/>',
  download: '<path d="M12 3v11"/><path d="m8 10 4 4 4-4"/><path d="M5 19h14"/>',
  notice: '<path d="M4 13v-2l12-5v12Z"/><path d="M7 14v5h4v-6"/><path d="M19 9v6"/>',
  shield: '<path d="M12 3 5 6v5c0 4.6 2.8 8 7 10 4.2-2 7-5.4 7-10V6Z"/><path d="m9 12 2 2 4-4"/>',
  clock: '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
  article: '<path d="M6 3h9l3 3v15H6Z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
  edit: '<path d="M4 20h4l11-11-4-4L4 16Z"/><path d="m13.5 6.5 4 4"/>',
  alert: '<path d="M12 3 3.5 19h17Z"/><path d="M12 9v4M12 16h.01"/>',
  users: '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3.5 19c.5-3.5 2.4-5.5 5.5-5.5s5 2 5.5 5.5"/><path d="M14.5 14.5c3.4-.4 5.5 1.1 6 4.5"/>',
  chart: '<path d="M4 20V11M10 20V5M16 20v-7M22 20V8"/>',
  directory: '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  activity: '<path d="M3 12h4l2-5 4 10 2-5h6"/>',
  settings: '<circle cx="12" cy="12" r="3"/><path d="M19 12a7 7 0 0 0-.1-1l2-1.5-2-3.4-2.4 1a7 7 0 0 0-1.7-1L14.5 3h-5l-.4 3.1a7 7 0 0 0-1.7 1l-2.4-1-2 3.4L5 11a7 7 0 0 0 0 2l-2 1.5 2 3.4 2.4-1a7 7 0 0 0 1.7 1l.4 3.1h5l.4-3.1a7 7 0 0 0 1.7-1l2.4 1 2-3.4L19 13a7 7 0 0 0 0-1Z"/>',
  archive: '<rect x="3" y="5" width="18" height="4" rx="1"/><path d="M5 9v11h14V9M10 13h4"/>',
  draft: '<path d="M6 3h9l3 3v15H6Z"/><path d="M14 3v4h4M9 12h6M9 16h4"/>',
  repeat: '<path d="m17 2 4 4-4 4"/><path d="M3 11V9a3 3 0 0 1 3-3h15"/><path d="m7 22-4-4 4-4"/><path d="M21 13v2a3 3 0 0 1-3 3H3"/>',
  bell: '<path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9"/><path d="M10 21h4"/>',
}

function normalizedText(value) {
  return String(value || '')
    .replace(/\s+/g, ' ')
    .trim()
    .toLowerCase()
}

function toneForText(value) {
  const text = normalizedText(value)

  if (
    text.includes('approved')
    || text.includes('resolved')
  ) return 'green'

  if (
    text.includes('rejected')
    || text.includes('cancelled')
    || text.includes('deactivated')
  ) return 'red'

  if (
    text.includes('report')
    || text.includes('removal')
    || text.includes('archive request')
  ) return 'red'

  if (
    text.includes('pending')
    || text.includes('revision')
    || text.includes('edit request')
    || text.includes('request')
  ) return 'gold'

  if (
    text.includes('analytics')
    || text.includes('notification')
    || text.includes('last login')
    || text.includes('mobile')
    || text.includes('install')
  ) return 'blue'

  if (
    text.includes('system')
    || text.includes('accountability')
    || text.includes('action log')
    || text.includes('role scope')
    || text.includes('showcase')
  ) return 'purple'

  if (
    text.includes('staff')
    || text.includes('people')
    || text.includes('directory')
    || text.includes('tracking')
  ) return 'teal'

  if (
    text.includes('published')
    || text.includes('active')
    || text.includes('verified')
    || text.includes('account status')
  ) return 'green'

  if (text.includes('archive')) return 'slate'

  return 'role'
}

function iconForText(value) {
  const text = normalizedText(value)

  if (text.includes('approved') || text.includes('resolved')) return 'status'
  if (text.includes('rejected') || text.includes('cancelled') || text.includes('deactivated')) return 'alert'
  if (text.includes('email')) return 'mail'
  if (text.includes('install')) return 'download'
  if (text.includes('mobile') || text.includes('release')) return 'phone'
  if (text.includes('notice') || text.includes('update notice')) return 'notice'
  if (text.includes('analytics')) return 'chart'
  if (text.includes('directory') || text.includes('people')) return 'directory'
  if (text.includes('action log') || text.includes('activity')) return 'activity'
  if (text.includes('report')) return 'alert'
  if (text.includes('archive') || text.includes('removal')) return 'archive'
  if (text.includes('revision') || text.includes('resubmission')) return 'repeat'
  if (text.includes('draft') || text.includes('writing')) return 'draft'
  if (text.includes('edit') || text.includes('changes')) return 'edit'
  if (text.includes('submission') || text.includes('review') || text.includes('pending')) return 'clock'
  if (text.includes('staff') || text.includes('account')) return 'users'
  if (text.includes('system') || text.includes('settings') || text.includes('administration')) return 'settings'
  if (text.includes('published') || text.includes('article')) return 'article'
  if (text.includes('notification')) return 'bell'
  if (text.includes('active') || text.includes('verified')) return 'status'

  return 'shield'
}

function createIcon(iconName, modifier = '') {
  const icon = document.createElement('span')
  icon.className = [
    'workspace-card-icon',
    modifier,
  ].filter(Boolean).join(' ')
  icon.setAttribute('aria-hidden', 'true')
  icon.innerHTML = `
    <svg viewBox="0 0 24 24" focusable="false">
      ${ICONS[iconName] || ICONS.shield}
    </svg>
  `
  return icon
}

function decorateMetricCards(dashboard) {
  dashboard
    .querySelectorAll('.workspace-metric-card')
    .forEach((card) => {
      const label = card.querySelector(
        '.workspace-metric-label',
      )?.textContent || ''

      card.dataset.dashboardTone =
        toneForText(label)

      if (
        !card.querySelector(
          '.workspace-card-icon--metric',
        )
      ) {
        card.appendChild(
          createIcon(
            iconForText(label),
            'workspace-card-icon--metric',
          ),
        )
      }
    })
}

function decorateActionCards(dashboard) {
  dashboard
    .querySelectorAll('.workspace-action-card')
    .forEach((card) => {
      const kicker = card.querySelector(
        '.workspace-action-kicker',
      )?.textContent || ''
      const title = card.querySelector('h3')?.textContent || ''
      const combined = `${kicker} ${title}`

      card.dataset.dashboardTone =
        toneForText(combined)

      const content = Array.from(card.children)
        .find((child) => child.tagName === 'DIV')

      if (
        content
        && !content.querySelector(
          '.workspace-card-icon--action',
        )
      ) {
        content.prepend(
          createIcon(
            iconForText(combined),
            'workspace-card-icon--action',
          ),
        )
      }
    })
}

function decorateSections(dashboard) {
  dashboard
    .querySelectorAll(
      '.workspace-dashboard-section, .workspace-account-panel, .workspace-management-panel',
    )
    .forEach((panel) => {
      const heading = panel.querySelector(
        '.workspace-section-heading h2',
      )?.textContent || ''

      if (
        panel.classList.contains(
          'workspace-account-panel',
        )
      ) {
        panel.dataset.dashboardTone = 'slate'
        return
      }

      panel.dataset.dashboardTone =
        toneForText(heading)
    })
}

function setupLiveMetricHighlights(dashboard) {
  if (!('MutationObserver' in window)) {
    return () => {}
  }

  const metrics = Array.from(
    dashboard.querySelectorAll(
      '[data-dashboard-metric-value]',
    ),
  )

  if (!metrics.length) {
    return () => {}
  }

  let ready = false
  let readyTimer = window.setTimeout(() => {
    ready = true
  }, 700)

  const highlightTimers = new Map()

  const observer = new MutationObserver(
    (mutations) => {
      if (!ready) return

      mutations.forEach((mutation) => {
        const metric = mutation.target
        const card = metric.closest(
          '.workspace-metric-card',
        )

        if (!card) return

        card.classList.remove(
          'is-live-updated',
        )

        // Force reflow so repeated live changes replay the highlight.
        void card.offsetWidth

        card.classList.add(
          'is-live-updated',
        )

        const oldTimer =
          highlightTimers.get(card)

        if (oldTimer) {
          window.clearTimeout(oldTimer)
        }

        const timer = window.setTimeout(
          () => {
            card.classList.remove(
              'is-live-updated',
            )
            highlightTimers.delete(card)
          },
          1200,
        )

        highlightTimers.set(card, timer)
      })
    },
  )

  metrics.forEach((metric) => {
    observer.observe(metric, {
      childList: true,
      characterData: true,
      subtree: true,
    })
  })

  return () => {
    observer.disconnect()
    window.clearTimeout(readyTimer)
    highlightTimers.forEach((timer) => {
      window.clearTimeout(timer)
    })
  }
}

function DashboardEnhancer() {
  useEffect(() => {
    const dashboard =
      document.querySelector(
        '.workspace-dashboard',
      )

    if (!dashboard) {
      return undefined
    }

    const isControlRoom =
      dashboard.classList.contains(
        'workspace-dashboard--control-room',
      )

    if (isControlRoom) {
      decorateMetricCards(dashboard)
      decorateActionCards(dashboard)
      decorateSections(dashboard)
    }

    const reducedMotion =
      window.matchMedia(
        '(prefers-reduced-motion: reduce)',
      ).matches

    const counters =
      Array.from(
        dashboard.querySelectorAll(
          '[data-dashboard-metric-value]',
        ),
      )

    const animationFrames = []

    counters.forEach((counter) => {
      const target =
        Number(counter.dataset.value)

      if (!Number.isFinite(target)) {
        return
      }

      const safeTarget =
        Math.max(0, target)

      if (
        reducedMotion
        || safeTarget === 0
      ) {
        counter.textContent =
          numberFormatter.format(safeTarget)
        return
      }

      const duration = 520
      const startTime =
        performance.now()

      const tick = (currentTime) => {
        const progress =
          Math.min(
            1,
            (currentTime - startTime)
              / duration,
          )

        const eased =
          1 - ((1 - progress) ** 3)

        const currentValue =
          Math.round(
            safeTarget * eased,
          )

        counter.textContent =
          numberFormatter.format(
            currentValue,
          )

        if (progress < 1) {
          const frame =
            window.requestAnimationFrame(
              tick,
            )

          animationFrames.push(frame)
        }
      }

      const frame =
        window.requestAnimationFrame(
          tick,
        )

      animationFrames.push(frame)
    })

    const revealTargets =
      Array.from(
        dashboard.querySelectorAll(
          [
            '.workspace-metric-grid',
            '.workspace-dashboard-section',
            '.workspace-account-panel',
            '.workspace-management-panel',
            '.workspace-analytics-filter',
          ].join(','),
        ),
      )

    revealTargets.forEach((element) => {
      element.setAttribute(
        'data-dashboard-reveal',
        '',
      )
    })

    let observer = null

    if (
      reducedMotion
      || !('IntersectionObserver' in window)
    ) {
      revealTargets.forEach((element) => {
        element.classList.add(
          'is-revealed',
        )
      })
    } else {
      observer =
        new IntersectionObserver(
          (entries) => {
            entries.forEach((entry) => {
              if (!entry.isIntersecting) {
                return
              }

              entry.target.classList.add(
                'is-revealed',
              )

              observer.unobserve(
                entry.target,
              )
            })
          },
          {
            threshold: 0.08,
            rootMargin:
              '0px 0px -24px 0px',
          },
        )

      revealTargets.forEach((element) => {
        observer.observe(element)
      })
    }

    const cleanupMetricHighlights =
      isControlRoom
        ? setupLiveMetricHighlights(dashboard)
        : () => {}

    return () => {
      animationFrames.forEach(
        (frame) => {
          window.cancelAnimationFrame(
            frame,
          )
        },
      )

      if (observer) {
        observer.disconnect()
      }

      cleanupMetricHighlights()
    }
  }, [])

  return null
}

export default DashboardEnhancer
