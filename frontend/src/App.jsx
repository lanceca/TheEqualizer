import { useEffect, useState } from 'react'
import AdviserAnalytics from './AdviserAnalytics.jsx'
import ArticleMediaEnhancer from './ArticleMediaEnhancer.jsx'
import './App.css'

function App() {
  const [progress, setProgress] = useState(0)
  const [showBackToTop, setShowBackToTop] =
    useState(false)

  useEffect(() => {
    function updateReaderTools() {
      const documentElement =
        document.documentElement

      const scrollTop =
        window.scrollY ||
        documentElement.scrollTop

      const scrollableHeight =
        documentElement.scrollHeight -
        window.innerHeight

      const nextProgress =
        scrollableHeight > 0
          ? (scrollTop / scrollableHeight) * 100
          : 0

      setProgress(
        Math.min(
          100,
          Math.max(0, nextProgress),
        ),
      )

      setShowBackToTop(scrollTop > 420)
    }

    updateReaderTools()

    window.addEventListener(
      'scroll',
      updateReaderTools,
      { passive: true },
    )

    window.addEventListener(
      'resize',
      updateReaderTools,
    )

    return () => {
      window.removeEventListener(
        'scroll',
        updateReaderTools,
      )

      window.removeEventListener(
        'resize',
        updateReaderTools,
      )
    }
  }, [])

  function scrollToTop() {
    window.scrollTo({
      top: 0,
      behavior: 'smooth',
    })
  }

  return (
    <>
      <AdviserAnalytics />
      <ArticleMediaEnhancer />

      <div
        className="react-reading-progress"
        aria-hidden="true"
      >
        <div
          className="react-reading-progress__bar"
          style={{
            width: `${progress}%`,
          }}
        />
      </div>

      <button
        type="button"
        className={[
          'react-back-to-top',
          showBackToTop ? 'is-visible' : '',
        ].join(' ')}
        onClick={scrollToTop}
        aria-label="Back to top"
        title="Back to top"
      >
        ↑
      </button>
    </>
  )
}

export default App
