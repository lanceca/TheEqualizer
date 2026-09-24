import { useEffect, useMemo, useState } from 'react'
import { articleText } from './articleRichText'

function textValue(selector) {
  const element = document.querySelector(selector)

  if (!element) {
    return ''
  }

  return (selector === '#content' ? articleText(element.value || '') : String(element.value || '')).trim()
}

function selectedLabel(selector) {
  const element = document.querySelector(selector)

  if (!element || !element.options) {
    return ''
  }

  const option =
    element.options[element.selectedIndex]

  return String(option?.textContent || '').trim()
}

function contributorCount() {
  const rows = Array.from(
    document.querySelectorAll(
      '.contributor-row',
    ),
  )

  return rows.filter((row) => {
    const role =
      row.querySelector(
        '[name="contributor_roles"]',
      )

    const user =
      row.querySelector(
        '[name="contributor_users"]',
      )

    return Boolean(
      role?.value && user?.value,
    )
  }).length
}

function selectedTagCount() {
  const checked =
    document.querySelectorAll(
      'input[name="tags"]:checked',
    ).length

  const custom = textValue('#custom_tags')
    .split(/[\n,]+/)
    .map((value) => value.trim())
    .filter(Boolean)
    .length

  return checked + custom
}

function selectedMediaCount(
  hasExistingFeatured,
) {
  const featured =
    document.querySelector('#featured_image')

  const images =
    document.querySelector('#attachments')

  const videos =
    document.querySelector(
      '#video_attachments',
    )

  const featuredCount =
    featured?.files?.length
      ? 1
      : (hasExistingFeatured ? 1 : 0)

  return (
    featuredCount
    + (images?.files?.length || 0)
    + (videos?.files?.length || 0)
  )
}

function readComposerState(
  hasExistingFeatured,
) {
  const title = textValue('#title')
  const category = textValue('#category')
  const content = textValue('#content')

  const required = [
    {
      id: 'title',
      label: 'Headline',
      complete: Boolean(title),
    },
    {
      id: 'category',
      label: 'Category',
      complete: Boolean(category),
    },
    {
      id: 'content',
      label: 'Story body',
      complete: Boolean(content),
    },
  ]

  const completed =
    required.filter(
      (item) => item.complete,
    ).length

  return {
    required,
    progress:
      Math.round(
        (completed / required.length)
        * 100,
      ),
    titleLength: title.length,
    contentLength: content.length,
    categoryLabel:
      category
        ? selectedLabel('#category')
        : 'Not selected',
    contributors: contributorCount(),
    tags: selectedTagCount(),
    media:
      selectedMediaCount(
        hasExistingFeatured,
      ),
  }
}

function CheckIcon({ complete }) {
  if (complete) {
    return (
      <svg
        viewBox="0 0 24 24"
        aria-hidden="true"
      >
        <path d="m5 12 4 4L19 6" />
      </svg>
    )
  }

  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <circle
        cx="12"
        cy="12"
        r="7"
      />
    </svg>
  )
}

function JumpIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      aria-hidden="true"
    >
      <path d="M7 17 17 7" />
      <path d="M8 7h9v9" />
    </svg>
  )
}

export default function EditorialWorkspaceEnhancer({
  mode = 'create',
  role = '',
  statusLabel = 'Draft',
  version = '',
  hasFeaturedImage = false,
}) {
  const hasExistingFeatured =
    hasFeaturedImage === true
    || hasFeaturedImage === 'true'

  const [state, setState] = useState(
    () => readComposerState(
      hasExistingFeatured,
    ),
  )

  useEffect(() => {
    const form =
      document.querySelector(
        '.editorial-composer-form',
      )

    if (!form) {
      return undefined
    }

    const update = () => {
      setState(
        readComposerState(
          hasExistingFeatured,
        ),
      )
    }

    update()

    form.addEventListener(
      'input',
      update,
    )

    form.addEventListener(
      'change',
      update,
    )

    form.addEventListener(
      'click',
      update,
    )

    const contributorList =
      form.querySelector(
        '#contributor-list',
      )

    const observer =
      contributorList
        ? new MutationObserver(update)
        : null

    if (observer && contributorList) {
      observer.observe(
        contributorList,
        {
          childList: true,
          subtree: true,
        },
      )
    }

    return () => {
      form.removeEventListener(
        'input',
        update,
      )

      form.removeEventListener(
        'change',
        update,
      )

      form.removeEventListener(
        'click',
        update,
      )

      observer?.disconnect()
    }
  }, [hasExistingFeatured])

  const roleCopy = useMemo(() => {
    if (mode === 'published') {
      return (
        'Saving creates the next '
        + 'official published version.'
      )
    }

    if (mode === 'revision') {
      return (
        'Complete the requested edits '
        + 'before resubmitting for review.'
      )
    }

    if (role === 'EIC') {
      return (
        'Save a working draft or publish '
        + 'directly when the story is ready.'
      )
    }

    return (
      'Save a working draft or submit '
      + 'the story to the Editor in Chief.'
    )
  }, [mode, role])

  const readinessCopy =
    state.progress === 100
      ? 'Core story fields complete'
      : `${state.progress}% core completion`

  const jumpItems = [
    {
      label: 'Story',
      target: '#title',
    },
    {
      label: 'Contributors',
      target: '#contributor-list',
    },
    {
      label: 'Body',
      target: '#content',
    },
    {
      label: 'Media',
      target: '#featured_image',
    },
  ].filter(
    (item) => (
      document.querySelector(item.target)
    ),
  )

  return (
    <div className="editorial-inspector">
      <div className="editorial-inspector-topline">
        <span>
          Story status
        </span>

        <span className="editorial-inspector-status">
          {statusLabel}
        </span>
      </div>

      <div className="editorial-readiness">
        <div
          className="editorial-readiness-ring"
          style={{
            '--editorial-progress':
              `${state.progress * 3.6}deg`,
          }}
          aria-label={readinessCopy}
        >
          <span>
            {state.progress}%
          </span>
        </div>

        <div>
          <strong>
            {state.progress === 100
              ? 'Core fields ready'
              : 'Complete the essentials'}
          </strong>

          <p>
            {readinessCopy}
          </p>
        </div>
      </div>

      <div className="editorial-inspector-checklist">
        <span className="editorial-inspector-section-label">
          Required
        </span>

        {state.required.map(
          (item) => (
            <a
              key={item.id}
              href={`#${item.id}`}
              className={
                item.complete
                  ? 'is-complete'
                  : ''
              }
            >
              <span className="editorial-check-icon">
                <CheckIcon
                  complete={item.complete}
                />
              </span>

              <span>
                {item.label}
              </span>
            </a>
          ),
        )}
      </div>

      <div className="editorial-inspector-facts">
        <div>
          <span>Category</span>
          <strong>
            {state.categoryLabel}
          </strong>
        </div>

        <div>
          <span>Contributors</span>
          <strong>
            {state.contributors}
          </strong>
        </div>

        <div>
          <span>Tags</span>
          <strong>
            {state.tags}
          </strong>
        </div>

        <div>
          <span>Media selected</span>
          <strong>
            {state.media}
          </strong>
        </div>
      </div>

      <div className="editorial-inspector-jumps">
        <span className="editorial-inspector-section-label">
          Jump to
        </span>

        <div>
          {jumpItems.map(
            (item) => (
              <a
                key={item.label}
                href={item.target}
              >
                <span>
                  {item.label}
                </span>
                <JumpIcon />
              </a>
            ),
          )}
        </div>
      </div>

      <div className="editorial-inspector-footer">
        {version && (
          <span>
            Version {version}
          </span>
        )}

        <p>
          {roleCopy}
        </p>
      </div>
    </div>
  )
}
