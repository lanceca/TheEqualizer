import { useEffect, useState } from 'react'
import './StaffSidebarToggle.css'

function StaffSidebarToggle({
  username,
  role,
}) {
  const [isOpen, setIsOpen] = useState(false)

  useEffect(() => {
    const sidebar =
      document.getElementById('staff-sidebar')

    if (!sidebar) {
      return undefined
    }

    sidebar.classList.toggle(
      'is-mobile-open',
      isOpen,
    )

    document.body.classList.toggle(
      'staff-sidebar-open',
      isOpen,
    )

    return () => {
      sidebar.classList.remove(
        'is-mobile-open',
      )

      document.body.classList.remove(
        'staff-sidebar-open',
      )
    }
  }, [isOpen])

  useEffect(() => {
    const sidebar =
      document.getElementById('staff-sidebar')

    if (!sidebar) {
      return undefined
    }

    function handleSidebarClick(event) {
      const link =
        event.target.closest('a')

      const button =
        event.target.closest(
          '.logout-link',
        )

      if (link || button) {
        setIsOpen(false)
      }
    }

    function handleKeyDown(event) {
      if (
        event.key === 'Escape'
        && isOpen
      ) {
        setIsOpen(false)
      }
    }

    function handleResize() {
      if (window.innerWidth > 860) {
        setIsOpen(false)
      }
    }

    sidebar.addEventListener(
      'click',
      handleSidebarClick,
    )

    document.addEventListener(
      'keydown',
      handleKeyDown,
    )

    window.addEventListener(
      'resize',
      handleResize,
    )

    return () => {
      sidebar.removeEventListener(
        'click',
        handleSidebarClick,
      )

      document.removeEventListener(
        'keydown',
        handleKeyDown,
      )

      window.removeEventListener(
        'resize',
        handleResize,
      )
    }
  }, [isOpen])

  return (
    <>
      <div className="staff-mobile-toolbar">
        <div className="staff-mobile-user">
          <span className="staff-mobile-user-label">
            Signed in as
          </span>

          <strong>
            {username}
          </strong>

          <span className="staff-mobile-user-role">
            {role}
          </span>
        </div>

        <button
          type="button"
          className="staff-mobile-sidebar-toggle"
          aria-label={
            isOpen
              ? 'Close dashboard menu'
              : 'Open dashboard menu'
          }
          aria-expanded={isOpen}
          aria-controls="staff-sidebar"
          onClick={() => {
            setIsOpen(
              (current) => !current,
            )
          }}
        >
          {isOpen ? (
            <span
              className="staff-mobile-close-icon"
              aria-hidden="true"
            >
              ×
            </span>
          ) : (
            <span
              className="staff-mobile-menu-icon"
              aria-hidden="true"
            >
              <span />
              <span />
              <span />
            </span>
          )}
        </button>
      </div>

      {isOpen && (
        <button
          type="button"
          className="staff-sidebar-scrim"
          aria-label="Close dashboard menu"
          onClick={() => {
            setIsOpen(false)
          }}
        />
      )}
    </>
  )
}

export default StaffSidebarToggle