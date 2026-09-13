import {
  useEffect,
  useRef,
  useState,
} from 'react'

import './HeaderActions.css'

function GlobeIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <circle
        cx="12"
        cy="12"
        r="9"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <path
        d="M3.5 12h17M12 3c2.35 2.45 3.55 5.45 3.55 9S14.35 18.55 12 21M12 3C9.65 5.45 8.45 8.45 8.45 12S9.65 18.55 12 21"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.6"
        strokeLinecap="round"
      />
    </svg>
  )
}

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

function InstagramIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <rect
        x="3.5"
        y="3.5"
        width="17"
        height="17"
        rx="5"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle
        cx="12"
        cy="12"
        r="4"
        fill="none"
        stroke="currentColor"
        strokeWidth="1.8"
      />
      <circle
        cx="17.5"
        cy="6.7"
        r="1.1"
        fill="currentColor"
      />
    </svg>
  )
}

function XIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
      focusable="false"
    >
      <path
        fill="currentColor"
        d="M5.1 4h3.6l3.95 5.28L17.2 4H19l-5.52 6.6L19.3 20h-3.6l-4.31-5.76L6.45 20H4.6l5.96-7.08L5.1 4Zm3.02 1.5H7.9l8.55 13h.22l-8.55-13Z"
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
  instagramUrl,
  xUrl,
  installUrl,
}) {
  const [noticeOpen, setNoticeOpen] =
    useState(false)
  const [socialOpen, setSocialOpen] =
    useState(false)

  const wrapperRef = useRef(null)

  const hasInstallUrl =
    Boolean(installUrl?.trim())

  const socialLinks = [
    {
      key: 'facebook',
      label: 'Facebook',
      url: facebookUrl,
      Icon: FacebookIcon,
    },
    {
      key: 'instagram',
      label: 'Instagram',
      url: instagramUrl,
      Icon: InstagramIcon,
    },
    {
      key: 'x',
      label: 'X / Twitter',
      url: xUrl,
      Icon: XIcon,
    },
  ].filter(
    ({ url }) => Boolean(url?.trim()),
  )

  const hasSocialLinks =
    socialLinks.length > 0

  useEffect(() => {
    if (!noticeOpen && !socialOpen) {
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
        setSocialOpen(false)
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setNoticeOpen(false)
        setSocialOpen(false)
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
  }, [noticeOpen, socialOpen])

  return (
    <div
      className="header-actions"
      ref={wrapperRef}
    >
      {hasSocialLinks && (
        <div className="header-social-wrapper">
          <button
            type="button"
            className="header-action-button header-social-trigger"
            aria-label="Open The Equalizer social media links"
            aria-expanded={socialOpen}
            aria-controls="header-social-menu"
            onClick={() => {
              setNoticeOpen(false)
              setSocialOpen(
                (current) => !current,
              )
            }}
          >
            <span className="header-action-icon">
              <GlobeIcon />
            </span>
          </button>

          {socialOpen && (
            <div
              id="header-social-menu"
              className="header-social-menu"
              role="menu"
              aria-label="The Equalizer social media"
            >
              <div className="header-social-menu-title">
                Follow The Equalizer
              </div>

              {socialLinks.map(
                ({
                  key,
                  label,
                  url,
                  Icon,
                }) => (
                  <a
                    key={key}
                    href={url}
                    target="_blank"
                    rel="noopener noreferrer"
                    className={`header-social-link header-social-link-${key}`}
                    role="menuitem"
                    onClick={() => setSocialOpen(false)}
                  >
                    <span className="header-social-link-icon">
                      <Icon />
                    </span>

                    <span>{label}</span>
                  </a>
                ),
              )}
            </div>
          )}
        </div>
      )}

      {hasInstallUrl ? (
        <a
          href={installUrl}
          className="header-action-button header-action-install"
          aria-label="Install The Equalizer Android app"
          onClick={() => setSocialOpen(false)}
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
            setSocialOpen(false)
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
