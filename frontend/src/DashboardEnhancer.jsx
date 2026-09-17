import { useEffect } from 'react'
import './DashboardEnhancer.css'

const numberFormatter =
  new Intl.NumberFormat('en-US')

function DashboardEnhancer() {
  useEffect(() => {
    const dashboard =
      document.querySelector(
        '.workspace-dashboard',
      )

    if (!dashboard) {
      return undefined
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
    }
  }, [])

  return null
}

export default DashboardEnhancer
