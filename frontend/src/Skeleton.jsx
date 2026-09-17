import './Skeleton.css'

export function SkeletonBlock({ className = '', style }) {
  return (
    <span
      className={['eq-skeleton-block', className].filter(Boolean).join(' ')}
      style={style}
      aria-hidden="true"
    />
  )
}

export function AuditLogSkeleton() {
  return (
    <div className="eq-skeleton-audit" role="status" aria-label="Loading activity">
      {Array.from({ length: 6 }, (_, index) => (
        <div className="eq-skeleton-audit-row" key={index}>
          <SkeletonBlock className="eq-skeleton-audit-time" />
          <div className="eq-skeleton-audit-user">
            <SkeletonBlock className="eq-skeleton-circle" />
            <SkeletonBlock className="eq-skeleton-audit-name" />
          </div>
          <SkeletonBlock className="eq-skeleton-audit-action" />
          <SkeletonBlock className="eq-skeleton-audit-target" />
        </div>
      ))}
    </div>
  )
}

export function PeopleAndTeamsSkeleton() {
  return (
    <div className="eq-skeleton-people" role="status" aria-label="Loading People and Teams">
      <div className="eq-skeleton-people-heading">
        <SkeletonBlock className="eq-skeleton-kicker" />
        <SkeletonBlock className="eq-skeleton-heading" />
        <SkeletonBlock className="eq-skeleton-copy" />
      </div>
      <div className="eq-skeleton-team-grid">
        {Array.from({ length: 4 }, (_, index) => (
          <div className="eq-skeleton-team-card" key={index}>
            <SkeletonBlock className="eq-skeleton-kicker" />
            <SkeletonBlock className="eq-skeleton-title-line" />
            <SkeletonBlock className="eq-skeleton-copy is-short" />
          </div>
        ))}
      </div>
      <div className="eq-skeleton-profile-grid">
        {Array.from({ length: 6 }, (_, index) => (
          <div className="eq-skeleton-profile-card" key={index}>
            <SkeletonBlock className="eq-skeleton-profile-photo" />
            <div className="eq-skeleton-profile-copy">
              <SkeletonBlock className="eq-skeleton-title-line" />
              <SkeletonBlock className="eq-skeleton-copy is-short" />
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function DigitalPublicationSkeleton({ stageOnly = false }) {
  if (stageOnly) {
    return (
      <div className="eq-skeleton-pdf-stage" role="status" aria-label="Rendering publication">
        <SkeletonBlock className="eq-skeleton-pdf-sheet" />
        <SkeletonBlock className="eq-skeleton-pdf-sheet is-secondary" />
      </div>
    )
  }

  return (
    <div className="eq-skeleton-digital-reader" role="status" aria-label="Loading digital publication">
      <div className="eq-skeleton-digital-toolbar">
        <SkeletonBlock className="eq-skeleton-button" />
        <SkeletonBlock className="eq-skeleton-button" />
        <SkeletonBlock className="eq-skeleton-page-chip" />
        <SkeletonBlock className="eq-skeleton-button is-small" />
        <SkeletonBlock className="eq-skeleton-button is-small" />
      </div>
      <div className="eq-skeleton-digital-meta">
        <div>
          <SkeletonBlock className="eq-skeleton-title-line" />
          <SkeletonBlock className="eq-skeleton-copy is-short" />
        </div>
        <SkeletonBlock className="eq-skeleton-page-chip" />
      </div>
      <DigitalPublicationSkeleton stageOnly />
    </div>
  )
}

export function PdfPageSkeleton() {
  return (
    <div className="eq-skeleton-pdf-page-wrap" aria-hidden="true">
      <SkeletonBlock className="eq-skeleton-pdf-page" />
    </div>
  )
}
