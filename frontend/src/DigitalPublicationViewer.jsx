import {
  forwardRef,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'
import HTMLFlipBook from 'react-pageflip'
import {
  Document,
  Page,
  pdfjs,
} from 'react-pdf'
import 'react-pdf/dist/Page/AnnotationLayer.css'
import 'react-pdf/dist/Page/TextLayer.css'
import './DigitalPublicationViewer.css'

pdfjs.GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url,
).toString()

const MIN_ZOOM = 0.8
const MAX_ZOOM = 1.5
const ZOOM_STEP = 0.1
const PAGE_RATIO = 1.414

const FlipPage = forwardRef(function FlipPage(
  {
    pageNumber,
    pageWidth,
    renderTextLayer,
  },
  ref,
) {
  return (
    <div
      ref={ref}
      className="digital-flipbook-page"
    >
      <Page
        pageNumber={pageNumber}
        width={pageWidth}
        renderAnnotationLayer
        renderTextLayer={renderTextLayer}
        loading={
          <div className="digital-flipbook-page-loading">
            Loading page {pageNumber}…
          </div>
        }
      />
    </div>
  )
})

function clamp(
  value,
  minimum,
  maximum,
) {
  return Math.min(
    maximum,
    Math.max(minimum, value),
  )
}

function formatFileSize(bytes) {
  if (!Number.isFinite(bytes) || bytes <= 0) {
    return ''
  }

  const units = [
    'B',
    'KB',
    'MB',
    'GB',
  ]

  let value = bytes
  let unitIndex = 0

  while (
    value >= 1024
    && unitIndex < units.length - 1
  ) {
    value /= 1024
    unitIndex += 1
  }

  const decimals =
    value >= 10 || unitIndex === 0
      ? 0
      : 1

  return `${value.toFixed(decimals)} ${units[unitIndex]}`
}

function DigitalPublicationViewer({
  apiUrl,
}) {
  const shellRef = useRef(null)
  const bookRef = useRef(null)

  const [publication, setPublication] =
    useState(null)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const [numPages, setNumPages] =
    useState(0)

  const [currentPage, setCurrentPage] =
    useState(1)

  const [zoom, setZoom] =
    useState(1)

  const [shellWidth, setShellWidth] =
    useState(900)

  const [isFullscreen, setIsFullscreen] =
    useState(false)

  useEffect(() => {
    if (!apiUrl) {
      setError(
        'The publication API URL is missing.',
      )
      setLoading(false)
      return undefined
    }

    const controller =
      new AbortController()

    async function loadPublication() {
      try {
        setLoading(true)
        setError('')

        const response = await fetch(
          apiUrl,
          {
            headers: {
              Accept: 'application/json',
            },
            signal: controller.signal,
          },
        )

        if (!response.ok) {
          throw new Error(
            `Request failed with status ${response.status}.`,
          )
        }

        const data = await response.json()

        if (!data.pdf_url) {
          throw new Error(
            'The publication PDF URL is missing.',
          )
        }

        setPublication(data)
      } catch (requestError) {
        if (
          requestError.name
          === 'AbortError'
        ) {
          return
        }

        setError(
          requestError.message
          || 'The publication could not be loaded.',
        )
      } finally {
        if (!controller.signal.aborted) {
          setLoading(false)
        }
      }
    }

    loadPublication()

    return () => {
      controller.abort()
    }
  }, [apiUrl])

  useEffect(() => {
    const shell = shellRef.current

    if (!shell) {
      return undefined
    }

    const updateWidth = () => {
      setShellWidth(
        shell.clientWidth,
      )
    }

    updateWidth()

    const observer =
      new ResizeObserver(
        updateWidth,
      )

    observer.observe(shell)

    return () => {
      observer.disconnect()
    }
  }, [])

  useEffect(() => {
    function updateFullscreenState() {
      setIsFullscreen(
        document.fullscreenElement
        === shellRef.current,
      )
    }

    document.addEventListener(
      'fullscreenchange',
      updateFullscreenState,
    )

    return () => {
      document.removeEventListener(
        'fullscreenchange',
        updateFullscreenState,
      )
    }
  }, [])

  const isPortrait = shellWidth < 820

  const basePageWidth = useMemo(() => {
    if (isPortrait) {
      return clamp(
        shellWidth - 36,
        250,
        620,
      )
    }

    return clamp(
      (shellWidth - 72) / 2,
      300,
      560,
    )
  }, [
    isPortrait,
    shellWidth,
  ])

  const pageWidth = Math.round(
    basePageWidth * zoom,
  )

  const pageHeight = Math.round(
    pageWidth * PAGE_RATIO,
  )

  const renderTextLayer =
    zoom >= 0.9

  const pageNumbers = useMemo(
    () => (
      Array.from(
        {
          length: numPages,
        },
        (_, index) => index + 1,
      )
    ),
    [numPages],
  )

  const goPrevious = useCallback(() => {
    bookRef.current
      ?.pageFlip()
      ?.flipPrev()
  }, [])

  const goNext = useCallback(() => {
    bookRef.current
      ?.pageFlip()
      ?.flipNext()
  }, [])

  const goToPage = useCallback(
    (pageNumber) => {
      const target = clamp(
        pageNumber,
        1,
        Math.max(numPages, 1),
      )

      bookRef.current
        ?.pageFlip()
        ?.flip(target - 1)
    },
    [numPages],
  )

  useEffect(() => {
    function handleKeyDown(event) {
      const target = event.target

      const isTyping =
        target instanceof HTMLInputElement
        || target instanceof HTMLTextAreaElement
        || target instanceof HTMLSelectElement

      if (isTyping) {
        return
      }

      if (
        event.key === 'ArrowLeft'
        || event.key === 'PageUp'
      ) {
        event.preventDefault()
        goPrevious()
      }

      if (
        event.key === 'ArrowRight'
        || event.key === 'PageDown'
      ) {
        event.preventDefault()
        goNext()
      }

      if (event.key === 'Home') {
        event.preventDefault()
        goToPage(1)
      }

      if (event.key === 'End') {
        event.preventDefault()
        goToPage(numPages)
      }
    }

    window.addEventListener(
      'keydown',
      handleKeyDown,
    )

    return () => {
      window.removeEventListener(
        'keydown',
        handleKeyDown,
      )
    }
  }, [
    goNext,
    goPrevious,
    goToPage,
    numPages,
  ])

  function handleDocumentLoadSuccess({
    numPages: loadedPages,
  }) {
    setNumPages(loadedPages)
    setCurrentPage(1)
  }

  function handleDocumentLoadError(
    pdfError,
  ) {
    setError(
      pdfError?.message
      || 'The PDF could not be rendered.',
    )
  }

  function handleFlip(event) {
    setCurrentPage(
      event.data + 1,
    )
  }

  function zoomOut() {
    setZoom((currentZoom) => (
      clamp(
        Number(
          (
            currentZoom
            - ZOOM_STEP
          ).toFixed(2),
        ),
        MIN_ZOOM,
        MAX_ZOOM,
      )
    ))
  }

  function zoomIn() {
    setZoom((currentZoom) => (
      clamp(
        Number(
          (
            currentZoom
            + ZOOM_STEP
          ).toFixed(2),
        ),
        MIN_ZOOM,
        MAX_ZOOM,
      )
    ))
  }

  function resetZoom() {
    setZoom(1)
  }

  async function toggleFullscreen() {
    const shell = shellRef.current

    if (!shell) {
      return
    }

    try {
      if (
        document.fullscreenElement
        === shell
      ) {
        await document.exitFullscreen()
        return
      }

      await shell.requestFullscreen()
    } catch (fullscreenError) {
      setError(
        'Fullscreen mode is not available in this browser.',
      )
    }
  }

  if (loading) {
    return (
      <div className="digital-flipbook-state">
        <div className="digital-flipbook-spinner" />
        <strong>
          Loading Digital Publication
        </strong>
        <span>
          Preparing the reader…
        </span>
      </div>
    )
  }

  if (error || !publication) {
    return (
      <div className="digital-flipbook-state digital-flipbook-state--error">
        <strong>
          Digital reader unavailable
        </strong>
        <span>
          {error || 'The publication could not be loaded.'}
        </span>

        {publication?.pdf_url && (
          <a
            href={publication.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open the PDF directly
          </a>
        )}
      </div>
    )
  }

  const fileSizeLabel =
    formatFileSize(
      publication.file_size,
    )

  return (
    <div
      ref={shellRef}
      className={[
        'digital-flipbook',
        isFullscreen
          ? 'is-fullscreen'
          : '',
      ].join(' ')}
    >
      <div className="digital-flipbook-toolbar">

        <div className="digital-flipbook-toolbar__group">
          <button
            type="button"
            onClick={goPrevious}
            disabled={currentPage <= 1}
            aria-label="Previous page"
            title="Previous page"
          >
            ←
            <span>
              Previous
            </span>
          </button>

          <button
            type="button"
            onClick={goNext}
            disabled={
              numPages > 0
              && currentPage >= numPages
            }
            aria-label="Next page"
            title="Next page"
          >
            <span>
              Next
            </span>
            →
          </button>
        </div>


        <div className="digital-flipbook-page-jump">

          <label htmlFor="digital-flipbook-page-input">
            Page
          </label>

          <input
            id="digital-flipbook-page-input"
            type="number"
            min="1"
            max={numPages || 1}
            value={currentPage}
            onChange={(event) => {
              const value =
                Number(event.target.value)

              if (
                Number.isInteger(value)
                && value >= 1
                && value <= numPages
              ) {
                goToPage(value)
              }
            }}
          />

          <span>
            / {numPages || '—'}
          </span>

        </div>


        <div className="digital-flipbook-toolbar__group">

          <button
            type="button"
            onClick={zoomOut}
            disabled={zoom <= MIN_ZOOM}
            aria-label="Zoom out"
            title="Zoom out"
          >
            −
          </button>

          <button
            type="button"
            onClick={resetZoom}
            className="digital-flipbook-zoom-value"
            title="Reset zoom"
          >
            {Math.round(zoom * 100)}%
          </button>

          <button
            type="button"
            onClick={zoomIn}
            disabled={zoom >= MAX_ZOOM}
            aria-label="Zoom in"
            title="Zoom in"
          >
            +
          </button>

          <button
            type="button"
            onClick={toggleFullscreen}
            aria-label={
              isFullscreen
                ? 'Exit fullscreen'
                : 'Enter fullscreen'
            }
            title={
              isFullscreen
                ? 'Exit fullscreen'
                : 'Enter fullscreen'
            }
          >
            {isFullscreen ? '⤢' : '⛶'}
          </button>

        </div>

      </div>


      <div className="digital-flipbook-meta">

        <div>
          <strong>
            {publication.title}
          </strong>

          <span>
            {[
              publication.volume,
              publication.issue_number,
            ].filter(Boolean).join(' • ')}
          </span>
        </div>

        <div className="digital-flipbook-meta__right">
          <span>
            {publication.page_count || numPages}
            {' '}
            pages
          </span>

          {fileSizeLabel && (
            <span>
              {fileSizeLabel}
            </span>
          )}

          <a
            href={publication.pdf_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open PDF
          </a>
        </div>

      </div>


      <div className="digital-flipbook-stage">

        <Document
          file={publication.pdf_url}
          onLoadSuccess={
            handleDocumentLoadSuccess
          }
          onLoadError={
            handleDocumentLoadError
          }
          loading={
            <div className="digital-flipbook-state">
              <div className="digital-flipbook-spinner" />
              <strong>
                Rendering PDF
              </strong>
              <span>
                Large publications may take a moment.
              </span>
            </div>
          }
        >

          {numPages > 0 && (
            <HTMLFlipBook
              key={[
                isPortrait
                  ? 'portrait'
                  : 'landscape',
                pageWidth,
                pageHeight,
                numPages,
              ].join('-')}
              ref={bookRef}
              width={pageWidth}
              height={pageHeight}
              size="fixed"
              minWidth={pageWidth}
              maxWidth={pageWidth}
              minHeight={pageHeight}
              maxHeight={pageHeight}
              showCover
              usePortrait={isPortrait}
              mobileScrollSupport
              maxShadowOpacity={0.35}
              drawShadow
              flippingTime={650}
              clickEventForward
              useMouseEvents
              swipeDistance={25}
              showPageCorners
              disableFlipByClick={false}
              onFlip={handleFlip}
              className="digital-flipbook-book"
            >
              {pageNumbers.map(
                (pageNumber) => (
                  <FlipPage
                    key={pageNumber}
                    pageNumber={pageNumber}
                    pageWidth={pageWidth}
                    renderTextLayer={
                      renderTextLayer
                    }
                  />
                ),
              )}
            </HTMLFlipBook>
          )}

        </Document>

      </div>


      <div className="digital-flipbook-footer">

        <span>
          Use ← → keys to turn pages.
        </span>

        <span>
          {isPortrait
            ? 'Single-page view'
            : 'Two-page spread'}
        </span>

      </div>

    </div>
  )
}

export default DigitalPublicationViewer
