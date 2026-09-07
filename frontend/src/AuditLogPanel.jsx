import {
  useEffect,
  useMemo,
  useRef,
  useState,
} from 'react'

import './AuditLogPanel.css'


const EMPTY_FILTERS = {
  q: '',
  role: '',
  module: '',
  action: '',
  date_from: '',
  date_to: '',
}


function humanizeAction(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(
      /\b\w/g,
      (letter) => letter.toUpperCase(),
    )
}


function roleLabel(value) {
  const labels = {
    SUPER_ADMIN: 'Super Admin',
    ADMIN: 'Admin',
    ADVISER: 'Adviser',
    EIC: 'Editor in Chief',
    EDITOR: 'Editor',
    STAFF: 'Staff',
    SYSTEM: 'System',
  }

  return labels[value] || value || 'System'
}


function moduleLabel(value) {
  return String(value || '')
    .replaceAll('_', ' ')
    .toLowerCase()
    .replace(
      /\b\w/g,
      (letter) => letter.toUpperCase(),
    )
}


function buildQuery(filters, page) {
  const params =
    new URLSearchParams()

  Object.entries(filters).forEach(
    ([key, value]) => {
      if (String(value || '').trim()) {
        params.set(key, value)
      }
    },
  )

  if (page > 1) {
    params.set(
      'page',
      String(page),
    )
  }

  return params
}


function ActionBadge({ action }) {
  const normalized =
    String(action || '').toUpperCase()

  let tone = 'neutral'

  if (
    normalized.includes('CREATED')
    || normalized.includes('PUBLISHED')
    || normalized.includes('APPROVED')
    || normalized.includes('ACTIVATED')
    || normalized.includes('RESTORED')
    || normalized.includes('LOGGED_IN')
  ) {
    tone = 'positive'
  } else if (
    normalized.includes('DELETED')
    || normalized.includes('REJECTED')
    || normalized.includes('DEACTIVATED')
    || normalized.includes('UNPUBLISHED')
  ) {
    tone = 'negative'
  } else if (
    normalized.includes('REVISION')
    || normalized.includes('ARCHIVED')
    || normalized.includes('PENDING')
  ) {
    tone = 'warning'
  }

  return (
    <span
      className={[
        'audit-react-action-badge',
        `is-${tone}`,
      ].join(' ')}
      title={action}
    >
      {humanizeAction(action)}
    </span>
  )
}


function RoleBadge({ role }) {
  return (
    <span className="audit-react-role-badge">
      {roleLabel(role)}
    </span>
  )
}


function ModuleBadge({ module }) {
  return (
    <span className="audit-react-module-badge">
      {moduleLabel(module)}
    </span>
  )
}


function MetadataBlock({ metadata }) {
  const entries =
    Object.entries(metadata || {})

  if (!entries.length) {
    return null
  }

  return (
    <div className="audit-react-metadata">
      <h4>
        Safe metadata
      </h4>

      <dl>
        {entries.map(
          ([key, value]) => (
            <div key={key}>
              <dt>
                {humanizeAction(key)}
              </dt>

              <dd>
                {Array.isArray(value)
                  ? value.join(', ')
                  : typeof value === 'object'
                    ? JSON.stringify(value)
                    : String(value)}
              </dd>
            </div>
          ),
        )}
      </dl>
    </div>
  )
}


function LogRow({
  row,
  expanded,
  onToggle,
}) {
  return (
    <article
      className={[
        'audit-react-log-card',
        expanded ? 'is-expanded' : '',
      ].join(' ')}
    >
      <button
        type="button"
        className="audit-react-log-summary"
        onClick={onToggle}
        aria-expanded={expanded}
      >
        <div className="audit-react-log-time">
          <span>
            {row.created_at_display}
          </span>

          <small>
            #{row.id}
          </small>
        </div>

        <div className="audit-react-log-actor">
          <span className="audit-react-avatar">
            {(row.actor || 'S')
              .slice(0, 1)
              .toUpperCase()}
          </span>

          <div>
            <strong>
              {row.actor || 'System'}
            </strong>

            <RoleBadge
              role={row.actor_role}
            />
          </div>
        </div>

        <div className="audit-react-log-action">
          <ActionBadge
            action={row.action}
          />

          <ModuleBadge
            module={row.module}
          />
        </div>

        <div className="audit-react-log-target">
          <strong>
            {row.target_label || '—'}
          </strong>

          <small>
            {row.target_type || 'System action'}
          </small>
        </div>

        <span
          className="audit-react-expand-icon"
          aria-hidden="true"
        >
          {expanded ? '−' : '+'}
        </span>
      </button>

      {expanded && (
        <div className="audit-react-log-detail">
          <div className="audit-react-detail-grid">
            <div>
              <span>
                Description
              </span>

              <p>
                {row.description || '—'}
              </p>
            </div>

            <div>
              <span>
                Target reference
              </span>

              <p>
                {row.target_type || '—'}
                {row.target_id
                  ? ` #${row.target_id}`
                  : ''}
              </p>
            </div>

            <div>
              <span>
                Raw action code
              </span>

              <p>
                <code>
                  {row.action}
                </code>
              </p>
            </div>

            <div>
              <span>
                Visibility
              </span>

              <p>
                {row.sensitive
                  ? 'Sensitive audit event'
                  : 'Standard audit event'}
              </p>
            </div>
          </div>

          <MetadataBlock
            metadata={row.metadata}
          />
        </div>
      )}
    </article>
  )
}


function AuditLogPanel({
  apiUrl,
  pageUrl,
}) {
  const [filters, setFilters] =
    useState(EMPTY_FILTERS)

  const [appliedFilters, setAppliedFilters] =
    useState(EMPTY_FILTERS)

  const [data, setData] =
    useState({
      results: [],
      filter_options: {
        roles: [],
        modules: [],
        actions: [],
      },
      pagination: {
        page: 1,
        pages: 1,
        count: 0,
        has_next: false,
        has_previous: false,
      },
      full_visibility: false,
    })

  const [page, setPage] =
    useState(1)

  const [loading, setLoading] =
    useState(true)

  const [error, setError] =
    useState('')

  const [expandedId, setExpandedId] =
    useState(null)

  const [reloadKey, setReloadKey] =
    useState(0)

  const initialized =
    useRef(false)

  const query = useMemo(
    () => buildQuery(
      appliedFilters,
      page,
    ),
    [
      appliedFilters,
      page,
    ],
  )

  useEffect(() => {
    if (initialized.current) {
      return
    }

    initialized.current = true

    const params =
      new URLSearchParams(
        window.location.search,
      )

    const initialFilters = {
      q: params.get('q') || '',
      role: params.get('role') || '',
      module:
        params.get('module') || '',
      action:
        params.get('action') || '',
      date_from:
        params.get('date_from') || '',
      date_to:
        params.get('date_to') || '',
    }

    const initialPage =
      Math.max(
        1,
        Number(
          params.get('page') || 1,
        ) || 1,
      )

    setFilters(initialFilters)
    setAppliedFilters(
      initialFilters,
    )
    setPage(initialPage)
  }, [])

  useEffect(() => {
    if (!apiUrl) {
      setLoading(false)
      setError(
        'The Action Log data endpoint is unavailable.',
      )
      return undefined
    }

    const controller =
      new AbortController()

    async function loadLogs() {
      setLoading(true)
      setError('')

      try {
        const response = await fetch(
          `${apiUrl}?${query.toString()}`,
          {
            credentials: 'same-origin',
            signal: controller.signal,
            headers: {
              Accept: 'application/json',
            },
          },
        )

        if (!response.ok) {
          throw new Error(
            `Request failed with status ${response.status}.`,
          )
        }

        const payload =
          await response.json()

        setData(payload)
        setExpandedId(null)

        if (pageUrl) {
          const visibleQuery =
            buildQuery(
              appliedFilters,
              page,
            )

          const nextUrl =
            visibleQuery.toString()
              ? `${pageUrl}?${visibleQuery.toString()}`
              : pageUrl

          window.history.replaceState(
            {},
            '',
            nextUrl,
          )
        }
      } catch (requestError) {
        if (
          requestError.name
          === 'AbortError'
        ) {
          return
        }

        console.error(
          'Action Log request failed.',
          requestError,
        )

        setError(
          'The Action Log could not be loaded. Please try again.',
        )
      } finally {
        if (
          !controller.signal.aborted
        ) {
          setLoading(false)
        }
      }
    }

    loadLogs()

    return () => {
      controller.abort()
    }
  }, [
    apiUrl,
    pageUrl,
    query,
    appliedFilters,
    page,
    reloadKey,
  ])

  function updateFilter(
    key,
    value,
  ) {
    setFilters(
      (current) => ({
        ...current,
        [key]: value,
      }),
    )
  }

  function applyFilters(event) {
    event.preventDefault()

    setPage(1)

    setAppliedFilters({
      ...filters,
    })
  }

  function clearFilters() {
    setFilters(EMPTY_FILTERS)
    setAppliedFilters(
      EMPTY_FILTERS,
    )
    setPage(1)
  }

  const options =
    data.filter_options
    || {
      roles: [],
      modules: [],
      actions: [],
    }

  const pagination =
    data.pagination
    || {
      page: 1,
      pages: 1,
      count: 0,
      has_next: false,
      has_previous: false,
    }

  return (
    <section className="audit-react-shell">
      <div className="profile-page-header">
        <div>
          <p className="workflow-eyebrow">
            Activity Center
          </p>

          <h1>
            Action Log
          </h1>

          <p className="section-description">
            Search and review meaningful CMS,
            workflow, management, account,
            and security activity across
            The Equalizer.
          </p>
        </div>
      </div>

      <form
        className="audit-react-filter-panel"
        onSubmit={applyFilters}
      >
        <div className="audit-react-search-field">
          <label htmlFor="audit-react-search">
            Search activity
          </label>

          <div className="audit-react-search-box">
            <span aria-hidden="true">
              ⌕
            </span>

            <input
              type="search"
              id="audit-react-search"
              value={filters.q}
              onChange={
                (event) => updateFilter(
                  'q',
                  event.target.value,
                )
              }
              placeholder="Username, article, action..."
            />
          </div>
        </div>

        <div>
          <label htmlFor="audit-react-role">
            Role
          </label>

          <select
            id="audit-react-role"
            value={filters.role}
            onChange={
              (event) => updateFilter(
                'role',
                event.target.value,
              )
            }
          >
            <option value="">
              All roles
            </option>

            {options.roles?.map(
              (role) => (
                <option
                  key={role}
                  value={role}
                >
                  {roleLabel(role)}
                </option>
              ),
            )}
          </select>
        </div>

        <div>
          <label htmlFor="audit-react-module">
            Module
          </label>

          <select
            id="audit-react-module"
            value={filters.module}
            onChange={
              (event) => updateFilter(
                'module',
                event.target.value,
              )
            }
          >
            <option value="">
              All modules
            </option>

            {options.modules?.map(
              (module) => (
                <option
                  key={module}
                  value={module}
                >
                  {moduleLabel(module)}
                </option>
              ),
            )}
          </select>
        </div>

        <div>
          <label htmlFor="audit-react-action">
            Action
          </label>

          <select
            id="audit-react-action"
            value={filters.action}
            onChange={
              (event) => updateFilter(
                'action',
                event.target.value,
              )
            }
          >
            <option value="">
              All actions
            </option>

            {options.actions?.map(
              (action) => (
                <option
                  key={action}
                  value={action}
                >
                  {humanizeAction(action)}
                </option>
              ),
            )}
          </select>
        </div>

        <div>
          <label htmlFor="audit-react-from">
            From
          </label>

          <input
            id="audit-react-from"
            type="date"
            value={filters.date_from}
            onChange={
              (event) => updateFilter(
                'date_from',
                event.target.value,
              )
            }
          />
        </div>

        <div>
          <label htmlFor="audit-react-to">
            To
          </label>

          <input
            id="audit-react-to"
            type="date"
            value={filters.date_to}
            onChange={
              (event) => updateFilter(
                'date_to',
                event.target.value,
              )
            }
          />
        </div>

        <div className="audit-react-filter-actions">
          <button
            type="submit"
            className="audit-react-primary-button"
          >
            Apply Filters
          </button>

          <button
            type="button"
            className="audit-react-secondary-button"
            onClick={clearFilters}
          >
            Clear
          </button>
        </div>
      </form>

      {!data.full_visibility && !loading && (
        <div className="audit-react-privacy-note">
          <strong>
            Protected security details
          </strong>

          <span>
            Account and security events remain
            visible for transparency, but protected
            target information and metadata are
            redacted for this role.
          </span>
        </div>
      )}

      <div className="audit-react-list-panel">
        <div className="audit-react-list-heading">
          <div>
            <span>
              Activity History
            </span>

            <h2>
              Recent CMS actions
            </h2>
          </div>

          <small>
            Page {pagination.page || 1}
            {' '}
            of {pagination.pages || 1}
          </small>
        </div>

        {loading && (
          <div className="audit-react-state">
            <span className="audit-react-spinner" />

            <strong>
              Loading activity…
            </strong>
          </div>
        )}

        {!loading && error && (
          <div className="audit-react-state is-error">
            <strong>
              {error}
            </strong>

            <button
              type="button"
              onClick={
                () => setReloadKey(
                  (value) => value + 1,
                )
              }
            >
              Try again
            </button>
          </div>
        )}

        {!loading
          && !error
          && !data.results?.length && (
            <div className="audit-react-state">
              <strong>
                No matching activity
              </strong>

              <span>
                Try changing or clearing the
                current filters.
              </span>
            </div>
          )}

        {!loading
          && !error
          && data.results?.length > 0 && (
            <div className="audit-react-log-list">
              {data.results.map(
                (row) => (
                  <LogRow
                    key={row.id}
                    row={row}
                    expanded={
                      expandedId === row.id
                    }
                    onToggle={
                      () => setExpandedId(
                        (current) => (
                          current === row.id
                            ? null
                            : row.id
                        ),
                      )
                    }
                  />
                ),
              )}
            </div>
          )}

        {!loading
          && !error
          && pagination.pages > 1 && (
            <nav
              className="audit-react-pagination"
              aria-label="Action log pages"
            >
              <button
                type="button"
                disabled={
                  !pagination.has_previous
                }
                onClick={
                  () => setPage(
                    Math.max(
                      1,
                      page - 1,
                    ),
                  )
                }
              >
                ← Previous
              </button>

              <span>
                {pagination.page}
                {' '}
                / {pagination.pages}
              </span>

              <button
                type="button"
                disabled={
                  !pagination.has_next
                }
                onClick={
                  () => setPage(
                    page + 1,
                  )
                }
              >
                Next →
              </button>
            </nav>
          )}
      </div>
    </section>
  )
}


export default AuditLogPanel
