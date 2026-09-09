import { createPortal } from 'react-dom'
import './AdviserAnalytics.css'

const CHART_COLORS = [
  '#184536',
  '#d6ad32',
  '#5f7480',
  '#9a5d4b',
  '#4f8b63',
  '#7a6a98',
]

function readJson(id, fallback = []) {
  const element =
    document.getElementById(id)

  if (!element) {
    return fallback
  }

  try {
    return JSON.parse(
      element.textContent || '[]',
    )
  } catch {
    return fallback
  }
}

function numberValue(value) {
  const next = Number(value)

  return Number.isFinite(next)
    ? next
    : 0
}

function formatNumber(value) {
  return new Intl.NumberFormat(
    'en-US',
  ).format(numberValue(value))
}

function sumValues(items) {
  return items.reduce(
    (total, item) => (
      total
      + numberValue(item.value)
    ),
    0,
  )
}

function valueFor(items, label) {
  const item = items.find(
    (entry) => entry.label === label,
  )

  return numberValue(item?.value)
}

function readTopArticles() {
  const container =
    document.getElementById(
      'adviser-top-articles-data',
    )

  if (!container) {
    return []
  }

  return Array.from(
    container.querySelectorAll(
      '[data-top-article]',
    ),
  )
    .map(
      (element) => ({
        title:
          element.dataset.title || '',
        category:
          element.dataset.category || '',
        views:
          numberValue(
            element.dataset.views,
          ),
        reactions:
          numberValue(
            element.dataset.reactions,
          ),
        shares:
          numberValue(
            element.dataset.shares,
          ),
      }),
    )
    .sort(
      (left, right) => (
        right.views - left.views
        || right.reactions - left.reactions
        || right.shares - left.shares
      ),
    )
    .slice(0, 5)
}

function MetricCard({
  eyebrow,
  value,
  description,
}) {
  return (
    <article className="aa-metric-card">
      <span className="aa-metric-eyebrow">
        {eyebrow}
      </span>

      <strong className="aa-metric-value">
        {formatNumber(value)}
      </strong>

      <p>
        {description}
      </p>
    </article>
  )
}

function SectionHeading({
  kicker,
  title,
  copy,
}) {
  return (
    <div className="aa-section-heading">
      <div>
        <span>
          {kicker}
        </span>

        <h3>
          {title}
        </h3>
      </div>

      {copy && (
        <p>
          {copy}
        </p>
      )}
    </div>
  )
}

function DonutChart({
  items,
  centerLabel,
}) {
  const total =
    Math.max(sumValues(items), 1)

  let position = 0

  const stops = items.map(
    (item, index) => {
      const start = position
      const portion =
        numberValue(item.value)
        / total
        * 100

      position += portion

      return [
        `${CHART_COLORS[index % CHART_COLORS.length]} ${start}%`,
        `${CHART_COLORS[index % CHART_COLORS.length]} ${position}%`,
      ].join(' ')
    },
  )

  const gradient =
    `conic-gradient(${stops.join(', ')})`

  return (
    <div className="aa-donut-layout">
      <div
        className="aa-donut"
        style={{
          background: gradient,
        }}
        role="img"
        aria-label={items
          .map(
            (item) => (
              `${item.label}: ${formatNumber(item.value)}`
            ),
          )
          .join(', ')}
      >
        <div className="aa-donut-center">
          <strong>
            {formatNumber(
              sumValues(items),
            )}
          </strong>

          <span>
            {centerLabel}
          </span>
        </div>
      </div>

      <div className="aa-donut-legend">
        {items.map(
          (item, index) => (
            <div
              key={item.label}
              className="aa-legend-row"
            >
              <span
                className="aa-legend-dot"
                style={{
                  background:
                    CHART_COLORS[
                      index
                      % CHART_COLORS.length
                    ],
                }}
              />

              <span>
                {item.label}
              </span>

              <strong>
                {formatNumber(
                  item.value,
                )}
              </strong>
            </div>
          ),
        )}
      </div>
    </div>
  )
}

function HorizontalBars({
  items,
  valueKey = 'value',
  labelKey = 'label',
}) {
  const maxValue = Math.max(
    1,
    ...items.map(
      (item) => (
        numberValue(item[valueKey])
      ),
    ),
  )

  if (!items.length) {
    return (
      <p className="aa-empty-state">
        No tracked data is available for this period.
      </p>
    )
  }

  return (
    <div className="aa-bars">
      {items.map(
        (item, index) => {
          const value =
            numberValue(item[valueKey])

          const percent =
            value / maxValue * 100

          return (
            <div
              className="aa-bar-row"
              key={`${item[labelKey]}-${index}`}
            >
              <div className="aa-bar-meta">
                <span>
                  {item[labelKey]}
                </span>

                <strong>
                  {formatNumber(value)}
                </strong>
              </div>

              <div
                className="aa-bar-track"
                aria-hidden="true"
              >
                <span
                  style={{
                    width: `${percent}%`,
                    background:
                      CHART_COLORS[
                        index
                        % CHART_COLORS.length
                      ],
                  }}
                />
              </div>
            </div>
          )
        },
      )}
    </div>
  )
}

function buildLinePath(
  values,
  width,
  height,
  maximum,
  padding,
) {
  if (!values.length) {
    return ''
  }

  const innerWidth =
    width - padding.left - padding.right

  const innerHeight =
    height - padding.top - padding.bottom

  const step =
    values.length > 1
      ? innerWidth / (values.length - 1)
      : 0

  return values
    .map(
      (value, index) => {
        const x =
          padding.left
          + step * index

        const y =
          padding.top
          + innerHeight
          - (
            numberValue(value)
            / maximum
            * innerHeight
          )

        return `${index === 0 ? 'M' : 'L'} ${x.toFixed(2)} ${y.toFixed(2)}`
      },
    )
    .join(' ')
}

function EngagementTrend({
  labels,
  fullDates,
  views,
  reactions,
  shares,
}) {
  const width = 900
  const height = 300

  const padding = {
    top: 22,
    right: 24,
    bottom: 40,
    left: 54,
  }

  const maximum = Math.max(
    1,
    ...views,
    ...reactions,
    ...shares,
  )

  const gridFractions = [
    0,
    0.25,
    0.5,
    0.75,
    1,
  ]

  const series = [
    {
      label: 'Views',
      values: views,
      color: CHART_COLORS[0],
    },
    {
      label: 'Reactions',
      values: reactions,
      color: CHART_COLORS[1],
    },
    {
      label: 'Shares',
      values: shares,
      color: CHART_COLORS[2],
    },
  ]

  const labelIndexes = Array.from(
    new Set([
      0,
      Math.floor(
        (labels.length - 1) / 2,
      ),
      Math.max(
        labels.length - 1,
        0,
      ),
    ]),
  ).filter(
    (index) => index >= 0,
  )

  const innerWidth =
    width - padding.left - padding.right

  const innerHeight =
    height - padding.top - padding.bottom

  function xFor(index) {
    if (labels.length <= 1) {
      return padding.left
    }

    return (
      padding.left
      + innerWidth
      * index
      / (labels.length - 1)
    )
  }

  function yFor(value) {
    return (
      padding.top
      + innerHeight
      - numberValue(value)
      / maximum
      * innerHeight
    )
  }

  if (!labels.length) {
    return (
      <p className="aa-empty-state">
        No historical engagement data is available yet.
      </p>
    )
  }

  const showPoints =
    labels.length <= 45

  return (
    <div className="aa-line-chart-wrap">
      <svg
        viewBox={`0 0 ${width} ${height}`}
        className="aa-line-chart"
        role="img"
        aria-label="Daily views, reactions, and shares"
      >
        {gridFractions.map(
          (fraction) => {
            const y =
              padding.top
              + innerHeight
              * (1 - fraction)

            const value = Math.round(
              maximum * fraction,
            )

            return (
              <g key={fraction}>
                <line
                  x1={padding.left}
                  x2={width - padding.right}
                  y1={y}
                  y2={y}
                  className="aa-chart-grid-line"
                />

                <text
                  x={padding.left - 10}
                  y={y + 4}
                  className="aa-chart-axis-label"
                  textAnchor="end"
                >
                  {formatNumber(value)}
                </text>
              </g>
            )
          },
        )}

        {labelIndexes.map(
          (index) => (
            <text
              key={index}
              x={xFor(index)}
              y={height - 12}
              className="aa-chart-axis-label"
              textAnchor={
                index === 0
                  ? 'start'
                  : index
                    === labels.length - 1
                    ? 'end'
                    : 'middle'
              }
            >
              {labels[index] || ''}
            </text>
          ),
        )}

        {series.map(
          (item) => (
            <path
              key={item.label}
              d={buildLinePath(
                item.values,
                width,
                height,
                maximum,
                padding,
              )}
              fill="none"
              stroke={item.color}
              strokeWidth="4"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          ),
        )}

        {showPoints
          && series.map(
            (item) => (
              <g key={`${item.label}-points`}>
                {item.values.map(
                  (value, index) => (
                    <circle
                      key={index}
                      cx={xFor(index)}
                      cy={yFor(value)}
                      r="4"
                      fill={item.color}
                    >
                      <title>
                        {`${item.label} — ${fullDates[index] || labels[index]}: ${formatNumber(value)}`}
                      </title>
                    </circle>
                  ),
                )}
              </g>
            ),
          )}
      </svg>

      <div className="aa-chart-legend">
        {series.map(
          (item) => (
            <span key={item.label}>
              <i
                style={{
                  background: item.color,
                }}
              />
              {item.label}
            </span>
          ),
        )}
      </div>
    </div>
  )
}

function CategoryPerformance({
  items,
}) {
  if (!items.length) {
    return (
      <p className="aa-empty-state">
        No published category data is currently available.
      </p>
    )
  }

  const maxViews = Math.max(
    1,
    ...items.map(
      (item) => numberValue(item.views),
    ),
  )

  return (
    <div className="aa-category-list">
      {items.slice(0, 8).map(
        (item, index) => (
          <article
            className="aa-category-row"
            key={item.label}
          >
            <div className="aa-category-copy">
              <strong>
                {item.label}
              </strong>

              <span>
                {formatNumber(item.articles)} published
              </span>
            </div>

            <div className="aa-category-visual">
              <div className="aa-category-track">
                <span
                  style={{
                    width:
                      `${numberValue(item.views) / maxViews * 100}%`,
                    background:
                      CHART_COLORS[
                        index
                        % CHART_COLORS.length
                      ],
                  }}
                />
              </div>

              <div className="aa-category-stats">
                <span>
                  <b>{formatNumber(item.views)}</b> views
                </span>
                <span>
                  <b>{formatNumber(item.reactions)}</b> reactions
                </span>
                <span>
                  <b>{formatNumber(item.shares)}</b> shares
                </span>
              </div>
            </div>
          </article>
        ),
      )}
    </div>
  )
}

function EditorPerformance({
  items,
}) {
  if (!items.length) {
    return (
      <p className="aa-empty-state">
        No Editor accounts are currently available.
      </p>
    )
  }

  const maxPublished = Math.max(
    1,
    ...items.map(
      (item) => numberValue(item.published),
    ),
    ...items.map(
      (item) => numberValue(item.approved),
    ),
  )

  return (
    <div className="aa-editor-list">
      {items.map(
        (editor) => (
          <article
            className="aa-editor-row"
            key={editor.username}
          >
            <div className="aa-editor-name">
              <span>
                {editor.username
                  ?.slice(0, 1)
                  .toUpperCase()}
              </span>

              <div>
                <strong>
                  {editor.username}
                </strong>

                <small>
                  {formatNumber(editor.submissions)} submissions
                </small>
              </div>
            </div>

            <div className="aa-editor-bars">
              <div>
                <span>
                  Published
                </span>
                <div className="aa-mini-track">
                  <i
                    style={{
                      width:
                        `${numberValue(editor.published) / maxPublished * 100}%`,
                    }}
                  />
                </div>
                <b>
                  {formatNumber(editor.published)}
                </b>
              </div>

              <div>
                <span>
                  Approved
                </span>
                <div className="aa-mini-track aa-mini-track--gold">
                  <i
                    style={{
                      width:
                        `${numberValue(editor.approved) / maxPublished * 100}%`,
                    }}
                  />
                </div>
                <b>
                  {formatNumber(editor.approved)}
                </b>
              </div>
            </div>

            <div className="aa-editor-flags">
              <span>
                {formatNumber(editor.rejected)} rejected
              </span>
              <span>
                {formatNumber(editor.revision)} revision
              </span>
            </div>
          </article>
        ),
      )}
    </div>
  )
}

function TopArticles({
  items,
}) {
  if (!items.length) {
    return (
      <p className="aa-empty-state">
        No published articles are currently available.
      </p>
    )
  }

  return (
    <div className="aa-top-articles">
      {items.map(
        (article, index) => (
          <article
            className="aa-top-article"
            key={`${article.title}-${index}`}
          >
            <span className="aa-rank">
              {String(index + 1).padStart(2, '0')}
            </span>

            <div className="aa-top-article-copy">
              <strong>
                {article.title}
              </strong>

              <small>
                {article.category}
              </small>
            </div>

            <div className="aa-top-article-stats">
              <span>
                <b>{formatNumber(article.views)}</b>
                views
              </span>
              <span>
                <b>{formatNumber(article.reactions)}</b>
                reacts
              </span>
              <span>
                <b>{formatNumber(article.shares)}</b>
                shares
              </span>
            </div>
          </article>
        ),
      )}
    </div>
  )
}

function AdviserDashboard({
  mountPoint,
}) {
  const articleStatus = readJson(
    'adviser-article-status-data',
  )

  const submissions = readJson(
    'adviser-submission-data',
  )

  const editRequests = readJson(
    'adviser-edit-request-data',
  )

  const deletionRequests = readJson(
    'adviser-deletion-request-data',
  )

  const contentReports = readJson(
    'adviser-content-report-data',
  )

  const engagement = readJson(
    'adviser-reader-engagement-data',
  )

  const categories = readJson(
    'adviser-category-data',
  )

  const editors = readJson(
    'adviser-editor-data',
  )

  const historyLabels = readJson(
    'adviser-history-labels',
  )

  const historyFullDates = readJson(
    'adviser-history-full-dates',
  )

  const historyViews = readJson(
    'adviser-history-views',
  )

  const historyReactions = readJson(
    'adviser-history-reactions',
  )

  const historyShares = readJson(
    'adviser-history-shares',
  )

  const topArticles =
    readTopArticles()

  const periodLabel =
    mountPoint.dataset.periodLabel
    || 'Selected Period'

  const startDate =
    mountPoint.dataset.startDate || ''

  const endDate =
    mountPoint.dataset.endDate || ''

  const timezone =
    mountPoint.dataset.timezone
    || 'Asia/Manila'

  const totalViews =
    valueFor(engagement, 'Views')

  const totalReactions =
    valueFor(
      engagement,
      'Reactions',
    )

  const totalShares =
    valueFor(engagement, 'Shares')

  const pendingEditRequests =
    valueFor(editRequests, 'Pending')

  const pendingDeletionRequests =
    valueFor(
      deletionRequests,
      'Pending',
    )

  const activeReports =
    valueFor(contentReports, 'Open')
    + valueFor(
      contentReports,
      'Revision Required',
    )

  const revisionReports =
    valueFor(
      contentReports,
      'Revision Required',
    )

  const workflowItems = [
    {
      label: 'Pending Edit Requests',
      value: pendingEditRequests,
    },
    {
      label: 'Pending Deletion Requests',
      value: pendingDeletionRequests,
    },
    {
      label: 'Active Content Reports',
      value: activeReports,
    },
    {
      label: 'Revision Required Reports',
      value: revisionReports,
    },
  ]

  return (
    <section className="adviser-analytics-shell">
      <header className="aa-hero">
        <div>
          <span className="aa-hero-kicker">
            Analytics Workspace
          </span>

          <h2>
            Publication intelligence at a glance
          </h2>

          <p>
            One consolidated view of reader activity,
            editorial workflow, content performance,
            and Editor output.
          </p>
        </div>

        <div className="aa-period-card">
          <span>
            Reporting period
          </span>

          <strong>
            {periodLabel}
          </strong>

          <small>
            {startDate && endDate
              ? `${startDate} → ${endDate}`
              : timezone}
          </small>
        </div>
      </header>

      <div className="aa-metrics-grid">
        <MetricCard
          eyebrow="Period Views"
          value={totalViews}
          description="Tracked article views"
        />

        <MetricCard
          eyebrow="Period Reactions"
          value={totalReactions}
          description="Reader reactions recorded"
        />

        <MetricCard
          eyebrow="Period Shares"
          value={totalShares}
          description="Tracked article shares"
        />

        <MetricCard
          eyebrow="Submissions"
          value={sumValues(submissions)}
          description="Submitted during this period"
        />
      </div>

      <div className="aa-primary-grid">
        <article className="aa-panel aa-panel--wide">
          <SectionHeading
            kicker="Reader Engagement"
            title="Engagement Trend"
            copy={`Daily tracked interactions for ${periodLabel}.`}
          />

          <EngagementTrend
            labels={historyLabels}
            fullDates={historyFullDates}
            views={historyViews}
            reactions={historyReactions}
            shares={historyShares}
          />

          <p className="aa-panel-note">
            Historical analytics only represent dates captured by
            the daily analytics tracker; earlier lifetime totals are
            not backfilled into individual days.
          </p>
        </article>

        <article className="aa-panel">
          <SectionHeading
            kicker="Current Snapshot"
            title="Publication Status"
            copy="Current article-state distribution."
          />

          <DonutChart
            items={articleStatus}
            centerLabel="articles"
          />
        </article>
      </div>

      <div className="aa-secondary-grid">
        <article className="aa-panel">
          <SectionHeading
            kicker="Editorial Flow"
            title="Submission Distribution"
            copy={`Submission outcomes for ${periodLabel}.`}
          />

          <HorizontalBars
            items={submissions.map(
              (item) => ({
                ...item,
                label:
                  item.label === 'Revision'
                    ? 'Sent Back for Revision'
                    : item.label,
              }),
            )}
          />
        </article>

        <article className="aa-panel">
          <SectionHeading
            kicker="Live Attention"
            title="Workflow Health"
            copy="Current items that may need editorial attention."
          />

          <div className="aa-workflow-grid">
            {workflowItems.map(
              (item, index) => (
                <div
                  className="aa-workflow-card"
                  key={item.label}
                >
                  <span>
                    {item.label}
                  </span>

                  <strong>
                    {formatNumber(item.value)}
                  </strong>

                  <i
                    style={{
                      background:
                        CHART_COLORS[
                          index
                          % CHART_COLORS.length
                        ],
                    }}
                  />
                </div>
              ),
            )}
          </div>
        </article>
      </div>

      <article className="aa-panel aa-panel--full">
        <SectionHeading
          kicker="Content Performance"
          title="Category Reach"
          copy="Currently published articles grouped by category, with engagement limited to the selected period."
        />

        <CategoryPerformance
          items={categories}
        />
      </article>

      <div className="aa-secondary-grid aa-secondary-grid--performance">
        <article className="aa-panel">
          <SectionHeading
            kicker="Top Content"
            title="Top Performing Articles"
            copy="Ranked by total article views, with reactions and shares shown for context."
          />

          <TopArticles
            items={topArticles}
          />
        </article>

        <article className="aa-panel">
          <SectionHeading
            kicker="Staff Performance"
            title="Editor Performance"
            copy={`Published and approved output during ${periodLabel}.`}
          />

          <EditorPerformance
            items={editors}
          />
        </article>
      </div>

      <footer className="aa-footer-note">
        <span>
          Timezone: {timezone}
        </span>

        <span>
          Live workflow cards are current snapshots and are not filtered by date.
        </span>
      </footer>
    </section>
  )
}

function AdviserAnalytics() {
  const mountPoint =
    document.getElementById(
      'adviser-analytics-react-root',
    )

  if (!mountPoint) {
    return null
  }

  return createPortal(
    <AdviserDashboard
      mountPoint={mountPoint}
    />,
    mountPoint,
  )
}

export default AdviserAnalytics
