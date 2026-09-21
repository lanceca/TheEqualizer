import {
  useEffect,
  useLayoutEffect,
  useRef,
  useState,
} from 'react'
import './StaffSidebarToggle.css'

function MenuIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M4 7h16M4 12h16M4 17h16" />
    </svg>
  )
}

function CollapseIcon({ collapsed }) {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <rect x="3.5" y="4" width="17" height="16" rx="2.5" />
      <path d="M9 4v16" />
      <path
        d={
          collapsed
            ? 'm13 9 3 3-3 3'
            : 'm16 9-3 3 3 3'
        }
      />
    </svg>
  )
}

function BellIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9" />
      <path d="M10 21h4" />
    </svg>
  )
}

function ExternalIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M14 5h5v5" />
      <path d="m10 14 9-9" />
      <path d="M19 13v6H5V5h6" />
    </svg>
  )
}

function ChevronIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="m7 10 5 5 5-5" />
    </svg>
  )
}

function UserIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <circle cx="12" cy="8" r="4" />
      <path d="M4.5 20c.8-4 3.3-6 7.5-6s6.7 2 7.5 6" />
    </svg>
  )
}

function LogoutIcon() {
  return (
    <svg viewBox="0 0 24 24" aria-hidden="true">
      <path d="M10 5H5v14h5" />
      <path d="m13 8 4 4-4 4M17 12H9" />
    </svg>
  )
}

const NAV_ICON_PATHS = {
  dashboard:
    '<rect x="3" y="3" width="7" height="7" rx="1.5"/><rect x="14" y="3" width="7" height="7" rx="1.5"/><rect x="3" y="14" width="7" height="7" rx="1.5"/><rect x="14" y="14" width="7" height="7" rx="1.5"/>',
  accounts:
    '<circle cx="9" cy="8" r="3"/><path d="M3.5 19c.5-3.5 2.4-5.5 5.5-5.5s5 2 5.5 5.5"/><path d="M16 7h5M18.5 4.5v5"/>',
  people:
    '<circle cx="9" cy="8" r="3"/><circle cx="17" cy="9" r="2.5"/><path d="M3.5 19c.5-3.5 2.4-5.5 5.5-5.5s5 2 5.5 5.5"/><path d="M14.5 14.5c3.4-.4 5.5 1.1 6 4.5"/>',
  analytics:
    '<path d="M4 20V10M10 20V4M16 20v-7M22 20V7"/>',
  directory:
    '<rect x="4" y="3" width="16" height="18" rx="2"/><path d="M8 8h8M8 12h8M8 16h5"/>',
  create:
    '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L8 18l-4 1 1-4Z"/>',
  drafts:
    '<path d="M6 3h9l3 3v15H6Z"/><path d="M14 3v4h4M9 12h6M9 16h4"/>',
  submissions:
    '<path d="M4 12h12"/><path d="m12 8 4 4-4 4"/><path d="M20 5v14"/>',
  published:
    '<circle cx="12" cy="12" r="9"/><path d="m8 12 2.6 2.6L16.5 9"/>',
  edit:
    '<path d="M4 20h4l11-11-4-4L4 16Z"/><path d="m13.5 6.5 4 4"/>',
  delete:
    '<path d="M4 7h16M9 7V4h6v3M7 7l1 14h8l1-14"/><path d="M10 11v6M14 11v6"/>',
  reports:
    '<path d="M6 3h9l3 3v15H6Z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
  archive:
    '<rect x="3" y="5" width="18" height="4" rx="1"/><path d="M5 9v11h14V9M10 13h4"/>',
  publications:
    '<path d="M4 5.5C6 4.5 8 4 11 5v15c-3-1-5-.5-7 .5Z"/><path d="M20 5.5c-2-1-4-1.5-7-.5v15c3-1 5-.5 7 .5Z"/>',
  ads:
    '<path d="M4 13v-2l12-5v12Z"/><path d="M7 14v5h4v-6"/><path d="M19 9v6"/>',
  about:
    '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7h.01"/>',
  activity:
    '<path d="M3 12h4l2-5 4 10 2-5h6"/>',
  logout:
    '<path d="M10 5H5v14h5"/><path d="M13 8l4 4-4 4M17 12H9"/>',
  default:
    '<circle cx="12" cy="12" r="8"/><path d="M12 8v8M8 12h8"/>',
}

function iconKeyForLabel(label) {
  const value = label.toLowerCase()

  if (value.includes('dashboard')) return 'dashboard'
  if (value.includes('admin account') || value.includes('staff account')) return 'accounts'
  if (value.includes('people')) return 'people'
  if (value.includes('analytics')) return 'analytics'
  if (value.includes('directory')) return 'directory'
  if (value.includes('create article')) return 'create'
  if (value.includes('draft')) return 'drafts'
  if (value.includes('submission')) return 'submissions'
  if (value.includes('published')) return 'published'
  if (value.includes('edit request')) return 'edit'
  if (value.includes('deletion')) return 'delete'
  if (value.includes('report')) return 'reports'
  if (value.includes('archive')) return 'archive'
  if (value.includes('digital publication')) return 'publications'
  if (value.includes('advertisement')) return 'ads'
  if (value.includes('about')) return 'about'
  if (value.includes('action log')) return 'activity'
  return 'default'
}

function enhanceNavigation(sidebar) {
  if (!sidebar) return

  sidebar
    .querySelectorAll('.staff-nav a[href]')
    .forEach((link) => {
      if (link.querySelector('.staff-nav-icon')) return

      const label = (
        link.textContent || ''
      ).replace(/\s+/g, ' ').trim()

      const icon = document.createElement('span')
      icon.className = 'staff-nav-icon'
      icon.setAttribute('aria-hidden', 'true')
      icon.innerHTML = `
        <svg viewBox="0 0 24 24" focusable="false">
          ${NAV_ICON_PATHS[iconKeyForLabel(label)]}
        </svg>
      `

      link.prepend(icon)
      link.title = label
    })

}

function StaffSidebarToggle({
  username,
  role,
  homeUrl,
  notificationUrl,
  profileUrl,
  logoutUrl,
  notificationCount = 0,
  csrfToken,
}) {
  const [isOpen, setIsOpen] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(() => {
    try {
      return localStorage.getItem(
        'equalizerWorkspaceSidebarCollapsed',
      ) === 'true'
    } catch {
      return false
    }
  })
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const [pageTitle, setPageTitle] = useState('Workspace')
  const [avatarUrl, setAvatarUrl] = useState('')

  const userMenuRef = useRef(null)

  useEffect(() => {
    const sidebar = document.getElementById('staff-sidebar')

    if (!sidebar) return undefined

    enhanceNavigation(sidebar)

    const heading = document.querySelector('.page-container h1')
    if (heading?.textContent?.trim()) {
      setPageTitle(heading.textContent.trim())
    }

    const avatarImage = sidebar.querySelector(
      '.staff-identity-avatar img',
    )
    if (avatarImage?.src) {
      setAvatarUrl(avatarImage.src)
    }

    return undefined
  }, [])

  useLayoutEffect(() => {
    const sidebar = document.getElementById('staff-sidebar')

    if (!sidebar) return undefined

    function applyLayoutState() {
      const isDesktop = window.innerWidth > 860
      const desktopCollapsed = isDesktop && isCollapsed
      const mobileOpen = !isDesktop && isOpen

      /*
       * Keep all three layers synchronized:
       * 1) root class = first-paint persistence across Django loads
       * 2) sidebar class = existing workspace CSS
       * 3) body class = existing layout helpers
       */
      document.documentElement.classList.toggle(
        'eq-staff-sidebar-collapsed',
        desktopCollapsed,
      )

      sidebar.classList.toggle(
        'is-collapsed',
        desktopCollapsed,
      )

      sidebar.classList.toggle(
        'is-mobile-open',
        mobileOpen,
      )

      document.body.classList.toggle(
        'staff-sidebar-collapsed',
        desktopCollapsed,
      )

      document.body.classList.toggle(
        'staff-sidebar-open',
        mobileOpen,
      )

      /*
       * The root class and the real sidebar class now agree.
       * Releasing the boot guard cannot animate the sidebar because
       * there is no width difference left to transition between.
       */
      document.documentElement.classList.remove(
        'eq-staff-sidebar-booting',
      )

      if (isDesktop && isOpen) {
        setIsOpen(false)
      }
    }

    applyLayoutState()
    window.addEventListener('resize', applyLayoutState)

    return () => {
      window.removeEventListener('resize', applyLayoutState)

      /*
       * A full Django navigation destroys this React tree while the
       * current document may still be visible. Never clear the desktop
       * collapsed classes during cleanup; the next document restores
       * the same state in <head> before first paint.
       */
      sidebar.classList.remove('is-mobile-open')
      document.body.classList.remove('staff-sidebar-open')
    }
  }, [isCollapsed, isOpen])

  useEffect(() => {
    const sidebar = document.getElementById('staff-sidebar')

    if (!sidebar) return undefined

    function handleSidebarClick(event) {
      const link = event.target.closest('a')

      if (link) {
        setIsOpen(false)
      }
    }

    function handleKeyDown(event) {
      if (event.key === 'Escape') {
        setIsOpen(false)
        setUserMenuOpen(false)
      }
    }

    function handlePointerDown(event) {
      if (
        userMenuRef.current
        && !userMenuRef.current.contains(event.target)
      ) {
        setUserMenuOpen(false)
      }
    }

    sidebar.addEventListener('click', handleSidebarClick)
    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('pointerdown', handlePointerDown)

    return () => {
      sidebar.removeEventListener('click', handleSidebarClick)
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('pointerdown', handlePointerDown)
    }
  }, [])

  function toggleCollapsed() {
    setIsCollapsed((current) => {
      const next = !current
      const isDesktop = window.innerWidth > 860
      const desktopCollapsed = isDesktop && next

      /*
       * Update the persistent first-paint class immediately in the
       * click handler. This prevents a gap between the click and the
       * React layout effect.
       */
      document.documentElement.classList.toggle(
        'eq-staff-sidebar-collapsed',
        desktopCollapsed,
      )

      const sidebar =
        document.getElementById('staff-sidebar')

      sidebar?.classList.toggle(
        'is-collapsed',
        desktopCollapsed,
      )

      document.body.classList.toggle(
        'staff-sidebar-collapsed',
        desktopCollapsed,
      )

      try {
        localStorage.setItem(
          'equalizerWorkspaceSidebarCollapsed',
          String(next),
        )
      } catch {
        // Local storage is optional progressive enhancement.
      }

      return next
    })
  }

  const initial = (
    username?.trim()?.slice(0, 1) || 'E'
  ).toUpperCase()

  return (
    <>
      <header className="staff-workspace-toolbar">
        <div className="staff-workspace-toolbar-start">
          <button
            type="button"
            className="staff-workspace-menu-button is-mobile"
            aria-label={
              isOpen
                ? 'Close workspace navigation'
                : 'Open workspace navigation'
            }
            aria-expanded={isOpen}
            aria-controls="staff-sidebar"
            onClick={() => setIsOpen((current) => !current)}
          >
            <MenuIcon />
          </button>

          <button
            type="button"
            className="staff-workspace-menu-button is-desktop"
            aria-label={
              isCollapsed
                ? 'Expand workspace navigation'
                : 'Collapse workspace navigation'
            }
            aria-expanded={!isCollapsed}
            aria-controls="staff-sidebar"
            onClick={toggleCollapsed}
          >
            <CollapseIcon collapsed={isCollapsed} />
          </button>

          <div className="staff-workspace-heading">
            <span>Editorial workspace</span>
            <strong>{pageTitle}</strong>
          </div>
        </div>

        <div className="staff-workspace-toolbar-actions">
          <a
            href={homeUrl || '/'}
            className="staff-workspace-action is-site-link"
            title="View public website"
          >
            <ExternalIcon />
            <span>View site</span>
          </a>

          <a
            href={notificationUrl || '#'}
            className="staff-workspace-action is-icon-only"
            aria-label={
              notificationCount > 0
                ? `${notificationCount} unread notifications`
                : 'Notifications'
            }
            title="Notifications"
          >
            <BellIcon />
            {notificationCount > 0 && (
              <span className="staff-workspace-notification-count">
                {notificationCount > 99 ? '99+' : notificationCount}
              </span>
            )}
          </a>

          <div
            className="staff-workspace-user-menu"
            ref={userMenuRef}
          >
            <button
              type="button"
              className="staff-workspace-user-trigger"
              aria-expanded={userMenuOpen}
              aria-haspopup="menu"
              onClick={() => {
                setUserMenuOpen((current) => !current)
              }}
            >
              <span className="staff-workspace-user-avatar">
                {avatarUrl ? (
                  <img src={avatarUrl} alt="" />
                ) : (
                  <span>{initial}</span>
                )}
              </span>

              <span className="staff-workspace-user-copy">
                <strong>{username}</strong>
                <small>{role}</small>
              </span>

              <span className="staff-workspace-user-chevron">
                <ChevronIcon />
              </span>
            </button>

            {userMenuOpen && (
              <div
                className="staff-workspace-user-popover"
                role="menu"
              >
                <div className="staff-workspace-user-popover-header">
                  <strong>{username}</strong>
                  <span>{role}</span>
                </div>

                <a
                  href={profileUrl || '#'}
                  role="menuitem"
                  onClick={() => setUserMenuOpen(false)}
                >
                  <UserIcon />
                  <span>Profile settings</span>
                </a>

                                <form
                  method="post"
                  action={logoutUrl || '#'}
                  className="staff-workspace-logout-form"
                  onSubmit={() => setUserMenuOpen(false)}
                >
                  <input
                    type="hidden"
                    name="csrfmiddlewaretoken"
                    value={csrfToken || ''}
                  />

                  <button
                    type="submit"
                    className="staff-workspace-logout-button"
                    role="menuitem"
                  >
                    <LogoutIcon />
                    <span>Logout</span>
                  </button>
                </form>

              </div>
            )}
          </div>
        </div>
      </header>

      {isOpen && (
        <button
          type="button"
          className="staff-sidebar-scrim"
          aria-label="Close workspace navigation"
          onClick={() => setIsOpen(false)}
        />
      )}
    </>
  )
}

export default StaffSidebarToggle
