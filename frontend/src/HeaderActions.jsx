import {
  useEffect,
  useRef,
  useState,
} from 'react'

import './HeaderActions.css'

function FacebookIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="currentColor"
        d="M13.6 22v-8.8h3l.45-3.45H13.6V7.55c0-1 .28-1.68 1.72-1.68H17.2V2.79c-.32-.04-1.44-.14-2.73-.14-2.7 0-4.55 1.65-4.55 4.68v2.42H6.86v3.45h3.06V22h3.68Z"
      />
    </svg>
  )
}

function InstallIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="currentColor"
        d="M11 3h2v9.17l3.59-3.58L18 10l-6 6-6-6 1.41-1.41L11 12.17V3Zm-6 15h14v2H5v-2Z"
      />
    </svg>
  )
}

function HeaderActions({
  facebookUrl,
  installUrl,
}) {
  const [noticeOpen, setNoticeOpen] =
    useState(false)

  const wrapperRef = useRef(null)

  const hasInstallUrl =
    Boolean(installUrl?.trim())

  useEffect(() => {
    if (!noticeOpen) {
      return undefined
    }

    function handlePointerDown(event) {
      if (
        wrapperRef.current
        && !wrapperRef.current.contains(
          event.target,
        )
      ) {
        setNoticeOpen(false)
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setNoticeOpen(false)
      }
    }

    document.addEventListener(
      'pointerdown',
      handlePointerDown,
    )

    document.addEventListener(
      'keydown',
      handleKeyDown,
    )

    return () => {
      document.removeEventListener(
        'pointerdown',
        handlePointerDown,
      )

      document.removeEventListener(
        'keydown',
        handleKeyDown,
      )
    }
  }, [noticeOpen])

  return (
    <div
      className="header-actions"
      ref={wrapperRef}
    >
      {facebookUrl && (
        <a
          href={facebookUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="header-action-button header-action-facebook"
          aria-label="Open The Equalizer Facebook page"
        >
          <span className="header-action-icon">
            <FacebookIcon />
          </span>

          <span className="header-action-label">
            Facebook
          </span>
        </a>
      )}

      {hasInstallUrl ? (
        <a
          href={installUrl}
          className="header-action-button header-action-install"
          aria-label="Install The Equalizer Android app"
        >
          <span className="header-action-icon">
            <InstallIcon />
          </span>

          <span className="header-action-label">
            Install App
          </span>
        </a>
      ) : (
        <button
          type="button"
          className="header-action-button header-action-install"
          aria-expanded={noticeOpen}
          onClick={() => {
            setNoticeOpen(
              (current) => !current,
            )
          }}
        >
          <span className="header-action-icon">
            <InstallIcon />
          </span>

          <span className="header-action-label">
            Install App
          </span>

        </button>
      )}

      {!hasInstallUrl && noticeOpen && (
        <div
          className="header-install-notice"
          role="status"
        >
          <span
            className="header-install-notice-icon"
            aria-hidden="true"
          >
            <InstallIcon />
          </span>

          <span>
            <strong>
              Android app coming soon
            </strong>

            <small>
              The install link will become
              available here once the APK is ready.
            </small>
          </span>
        </div>
      )}
    </div>
  )
}

export default HeaderActions
