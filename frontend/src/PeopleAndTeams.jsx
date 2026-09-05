import { useEffect, useMemo, useRef, useState } from 'react'
import './PeopleAndTeams.css'

function splitLines(value) {
  return String(value || '')
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
}

function ProfileDetails({ profile }) {
  const details = [
    ['Position', profile.school_position],
    ['Institute / Department', profile.institute_department],
    ['Courses Handled', profile.courses_handled],
    ['Achievements / Contributions', profile.achievements],
    ['Additional Information', profile.additional_information],
  ].filter(([, value]) => String(value || '').trim())

  if (!details.length) {
    return (
      <p className="pt-profile-empty-copy">
        More profile details will be added soon.
      </p>
    )
  }

  return (
    <dl className="pt-profile-details">
      {details.map(([label, value]) => (
        <div key={label}>
          <dt>{label}</dt>
          <dd>
            {splitLines(value).map((line, index) => (
              <span key={`${label}-${index}`}>{line}</span>
            ))}
          </dd>
        </div>
      ))}
    </dl>
  )
}

function ProfileModal({ profile, onClose }) {
  const closeButtonRef = useRef(null)
  const contentRef = useRef(null)

  useEffect(() => {
    const html = document.documentElement
    const body = document.body
    const scrollY = window.scrollY

    const previousHtmlOverflow = html.style.overflow
    const previousBodyOverflow = body.style.overflow
    const previousBodyPosition = body.style.position
    const previousBodyTop = body.style.top
    const previousBodyWidth = body.style.width

    html.style.overflow = 'hidden'
    body.style.overflow = 'hidden'
    body.style.position = 'fixed'
    body.style.top = `-${scrollY}px`
    body.style.width = '100%'

    closeButtonRef.current?.focus()

    function onKeyDown(event) {
      if (event.key === 'Escape') {
        onClose()
      }
    }

    window.addEventListener('keydown', onKeyDown)

    return () => {
      html.style.overflow = previousHtmlOverflow
      body.style.overflow = previousBodyOverflow
      body.style.position = previousBodyPosition
      body.style.top = previousBodyTop
      body.style.width = previousBodyWidth
      window.scrollTo(0, scrollY)
      window.removeEventListener('keydown', onKeyDown)
    }
  }, [onClose])

  return (
    <div
      className="pt-modal-backdrop"
      role="presentation"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) {
          onClose()
        }
      }}
    >
      <section
        className="pt-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="pt-modal-name"
        onWheel={(event) => {
          const content = contentRef.current
          if (!content) return

          if (!content.contains(event.target)) {
            event.preventDefault()
            content.scrollTop += event.deltaY
          }
        }}
      >
        <button
          ref={closeButtonRef}
          type="button"
          className="pt-modal-close"
          onClick={onClose}
          aria-label="Close profile"
        >
          <span aria-hidden="true">×</span>
        </button>

        <div className="pt-modal-portrait-wrap">
          {profile.image_url ? (
            <img
              src={profile.image_url}
              alt={profile.name}
              className="pt-modal-portrait"
            />
          ) : (
            <div className="pt-modal-portrait pt-image-placeholder" aria-hidden="true">
              {profile.name?.slice(0, 1) || '?'}
            </div>
          )}
          <div className="pt-modal-image-glow" aria-hidden="true" />
        </div>

        <div
          ref={contentRef}
          className="pt-modal-content"
        >
          <p className="pt-kicker">Profile Spotlight</p>
          <h2 id="pt-modal-name">{profile.name}</h2>
          {profile.role_title && (
            <p className="pt-modal-role">{profile.role_title}</p>
          )}
          <ProfileDetails profile={profile} />
        </div>
      </section>
    </div>
  )
}

function GroupTile({ group, index, active, onSelect }) {
  const tileRef = useRef(null)

  function handlePointerMove(event) {
    if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
      return
    }

    const tile = tileRef.current
    if (!tile) return

    const rect = tile.getBoundingClientRect()
    const x = (event.clientX - rect.left) / rect.width
    const y = (event.clientY - rect.top) / rect.height
    const rotateY = (x - 0.5) * 7
    const rotateX = (0.5 - y) * 7

    tile.style.setProperty('--pt-rx', `${rotateX}deg`)
    tile.style.setProperty('--pt-ry', `${rotateY}deg`)
    tile.style.setProperty('--pt-glow-x', `${x * 100}%`)
    tile.style.setProperty('--pt-glow-y', `${y * 100}%`)
  }

  function resetTilt() {
    const tile = tileRef.current
    if (!tile) return
    tile.style.setProperty('--pt-rx', '0deg')
    tile.style.setProperty('--pt-ry', '0deg')
  }

  return (
    <button
      ref={tileRef}
      type="button"
      className={`pt-group-tile${active ? ' is-active' : ''}`}
      onClick={() => onSelect(group.slug)}
      onPointerMove={handlePointerMove}
      onPointerLeave={resetTilt}
      aria-pressed={active}
      style={{ '--pt-delay': `${index * 90}ms` }}
    >
      <span className="pt-tile-orbit" aria-hidden="true" />
      <span className="pt-tile-index" aria-hidden="true">
        {String(index + 1).padStart(2, '0')}
      </span>
      <span className="pt-tile-eyebrow">{group.eyebrow || 'Explore'}</span>
      <strong>{group.title}</strong>
      <span className="pt-tile-footer">
        <span>
          {group.profiles.length} profile{group.profiles.length === 1 ? '' : 's'}
        </span>
        <span className="pt-tile-arrow" aria-hidden="true">↗</span>
      </span>
    </button>
  )
}

function ProfileCard({ profile, index, onOpen }) {
  return (
    <button
      type="button"
      className="pt-profile-card"
      onClick={() => onOpen(profile)}
      style={{ '--pt-profile-delay': `${index * 65}ms` }}
    >
      <span className="pt-profile-image-wrap">
        {profile.image_url ? (
          <img src={profile.image_url} alt={profile.name} />
        ) : (
          <span className="pt-image-placeholder" aria-hidden="true">
            {profile.name?.slice(0, 1) || '?'}
          </span>
        )}
        <span className="pt-profile-sheen" aria-hidden="true" />
        <span className="pt-profile-open">View profile</span>
      </span>

      <span className="pt-profile-copy">
        <span className="pt-profile-name">{profile.name}</span>
        {profile.role_title && (
          <span className="pt-profile-role">{profile.role_title}</span>
        )}
        <span className="pt-profile-more">
          Discover more <span aria-hidden="true">→</span>
        </span>
      </span>
    </button>
  )
}

function PeopleAndTeams({ apiUrl }) {
  const [groups, setGroups] = useState([])
  const [activeSlug, setActiveSlug] = useState('')
  const [selectedProfile, setSelectedProfile] = useState(null)
  const [isGroupTransitioning, setIsGroupTransitioning] = useState(false)
  const [status, setStatus] = useState('loading')
  const [errorMessage, setErrorMessage] = useState('')
  const sectionRef = useRef(null)

  useEffect(() => {
    const controller = new AbortController()

    async function loadPeople() {
      try {
        setStatus('loading')
        const response = await fetch(apiUrl, {
          headers: { Accept: 'application/json' },
          signal: controller.signal,
        })

        if (!response.ok) {
          throw new Error(`Request failed with status ${response.status}`)
        }

        const data = await response.json()
        const nextGroups = Array.isArray(data.groups) ? data.groups : []
        setGroups(nextGroups)
        setActiveSlug(nextGroups[0]?.slug || '')
        setStatus('ready')
      } catch (error) {
        if (error.name === 'AbortError') return
        setErrorMessage('The People & Teams showcase could not be loaded right now.')
        setStatus('error')
      }
    }

    if (apiUrl) {
      loadPeople()
    } else {
      setErrorMessage('The People & Teams data endpoint is not configured.')
      setStatus('error')
    }

    return () => controller.abort()
  }, [apiUrl])

  const activeGroup = useMemo(
    () => groups.find((group) => group.slug === activeSlug) || groups[0],
    [groups, activeSlug],
  )

  function selectGroup(slug) {
    if (!slug || slug === activeSlug || isGroupTransitioning) return

    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches

    if (reduceMotion) {
      setActiveSlug(slug)
      window.requestAnimationFrame(() => {
        sectionRef.current?.scrollIntoView({ behavior: 'auto', block: 'start' })
      })
      return
    }

    setIsGroupTransitioning(true)

    window.setTimeout(() => {
      setActiveSlug(slug)

      window.requestAnimationFrame(() => {
        sectionRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })

        window.setTimeout(() => {
          setIsGroupTransitioning(false)
        }, 70)
      })
    }, 180)
  }

  return (
    <main className="pt-page">
      <section className="pt-hero">
        <div className="pt-hero-noise" aria-hidden="true" />
        <div className="pt-hero-glow pt-hero-glow-one" aria-hidden="true" />
        <div className="pt-hero-glow pt-hero-glow-two" aria-hidden="true" />

        <div className="pt-hero-content">
          <p className="pt-kicker">The People Behind The Work</p>
          <h1>
            People <span>&amp;</span> Teams
          </h1>
          <p className="pt-hero-copy">
            Meet the developers, academic mentors, faculty, and publication staff
            whose work shapes The Equalizer.
          </p>
          <div className="pt-hero-meta" aria-label="People and Teams overview">
            <span>{groups.length || 4} groups</span>
            <span className="pt-meta-dot" aria-hidden="true" />
            <span>One publication</span>
          </div>
        </div>

        <div className="pt-scroll-cue" aria-hidden="true">
          <span />
          Explore
        </div>
      </section>

      {status === 'loading' && (
        <section className="pt-state-card" aria-live="polite">
          <span className="pt-loader" aria-hidden="true" />
          <p>Gathering the people behind The Equalizer...</p>
        </section>
      )}

      {status === 'error' && (
        <section className="pt-state-card pt-state-error" role="alert">
          <p>{errorMessage}</p>
        </section>
      )}

      {status === 'ready' && (
        <>
          <section className="pt-group-showcase" aria-labelledby="pt-group-heading">
            <div className="pt-section-heading">
              <div>
                <p className="pt-kicker">Choose a circle</p>
                <h2 id="pt-group-heading">Explore the teams</h2>
              </div>
              <p>Move through each group, then open a profile for the full spotlight.</p>
            </div>

            <div className="pt-group-grid">
              {groups.map((group, index) => (
                <GroupTile
                  key={group.slug}
                  group={group}
                  index={index}
                  active={group.slug === activeGroup?.slug}
                  onSelect={selectGroup}
                />
              ))}
            </div>
          </section>

          {activeGroup && (
            <section
              ref={sectionRef}
              className={`pt-active-group${isGroupTransitioning ? ' is-switching' : ''}`}
              aria-labelledby="pt-active-group-title"
              key={activeGroup.slug}
            >
              <div className="pt-active-group-head">
                <div>
                  <p className="pt-kicker">{activeGroup.eyebrow || 'People & Teams'}</p>
                  <h2 id="pt-active-group-title">{activeGroup.title}</h2>
                  <p>{activeGroup.description}</p>
                </div>
                <div className="pt-count-badge" aria-label={`${activeGroup.profiles.length} profiles`}>
                  <strong>{String(activeGroup.profiles.length).padStart(2, '0')}</strong>
                  <span>Profiles</span>
                </div>
              </div>

              {activeGroup.profiles.length ? (
                <div className="pt-profile-grid">
                  {activeGroup.profiles.map((profile, index) => (
                    <ProfileCard
                      key={profile.id}
                      profile={profile}
                      index={index}
                      onOpen={setSelectedProfile}
                    />
                  ))}
                </div>
              ) : (
                <div className="pt-empty-state">
                  <span aria-hidden="true">◇</span>
                  <h3>No public profiles yet</h3>
                  <p>This group is ready for profiles to be published from the CMS.</p>
                </div>
              )}
            </section>
          )}
        </>
      )}

      {selectedProfile && (
        <ProfileModal
          profile={selectedProfile}
          onClose={() => setSelectedProfile(null)}
        />
      )}
    </main>
  )
}

export default PeopleAndTeams
