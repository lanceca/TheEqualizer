import { useEffect, useRef, useState } from 'react'
import { articleText, cleanArticleHTML } from './articleRichText'
import './PublicationInteractions.css'

const EMPTY_FORMATS = {
  bold: false,
  italic: false,
  underline: false,
  strikeThrough: false,
  bulletList: false,
  numberedList: false,
  dashList: false,
}

function selectionElement(root) {
  const selection = window.getSelection()

  if (!selection || !selection.rangeCount) return null

  let node = selection.anchorNode

  if (!node) return null

  if (node.nodeType !== Node.ELEMENT_NODE) {
    node = node.parentElement
  }

  if (!node || !root.contains(node)) return null

  return node
}

function closestList(root) {
  let node = selectionElement(root)

  while (node && node !== root) {
    if (node.tagName === 'UL' || node.tagName === 'OL') {
      return node
    }

    node = node.parentElement
  }

  return null
}

export default function ArticleRichTextEditor({ fieldId }) {
  const editor = useRef(null)
  const sync = useRef(() => {})
  const refreshToolbar = useRef(() => {})

  const [error, setError] = useState('')
  const [count, setCount] = useState(0)
  const [maximum, setMaximum] = useState(30000)
  const [formats, setFormats] = useState(EMPTY_FORMATS)

  useEffect(() => {
    const textarea = document.getElementById(fieldId)
    const editable = editor.current

    if (!textarea || !editable) return

    const required = textarea.required
    const maxLength = textarea.maxLength > 0
      ? textarea.maxLength
      : 30000

    const originalHidden = textarea.hidden
    const originalDisplay = textarea.style.display

    setMaximum(maxLength)

    textarea.hidden = true
    textarea.style.display = 'none'
    textarea.required = false

    editable.innerHTML = cleanArticleHTML(
      textarea.value,
    )

    let lastHTML = editable.innerHTML
    let lastValue = textarea.value
    let syncing = false

    const readToolbarState = () => {
      if (!selectionElement(editable)) {
        return
      }

      const list = closestList(editable)

      let bold = false
      let italic = false
      let underline = false
      let strikeThrough = false

      try {
        bold = document.queryCommandState('bold')
        italic = document.queryCommandState('italic')
        underline = document.queryCommandState('underline')
        strikeThrough = document.queryCommandState(
          'strikeThrough',
        )
      } catch {
        // queryCommandState is best-effort only.
      }

      const dashList = (
        list?.tagName === 'UL'
        && list.dataset.listStyle === 'dash'
      )

      setFormats({
        bold,
        italic,
        underline,
        strikeThrough,
        bulletList: (
          list?.tagName === 'UL'
          && !dashList
        ),
        numberedList: list?.tagName === 'OL',
        dashList,
      })
    }

    refreshToolbar.current = readToolbarState

    const validate = () => {
      const length = articleText(
        textarea.value,
      ).length

      const message = length > maxLength
        ? `Article content cannot exceed ${maxLength.toLocaleString()} characters.`
        : (
          required
          && !articleText(textarea.value).trim()
            ? 'Article content is required.'
            : ''
        )

      setCount(length)
      setError(message)

      textarea.setCustomValidity(message)
      textarea.dataset.visibleLength = String(length)

      editable.setAttribute(
        'aria-invalid',
        message ? 'true' : 'false',
      )

      return message
    }

    const update = () => {
      /*
       * Keep the editing selection stable while typing. The browser-facing
       * sanitizer rebuilds the allowed HTML, while the server sanitizer
       * remains authoritative when the form is saved.
       */
      const html = cleanArticleHTML(
        editable.innerHTML,
      )

      if (html !== lastHTML) {
        textarea.value = html
        lastHTML = html
        lastValue = html
      }

      validate()

      syncing = true

      textarea.dispatchEvent(
        new Event(
          'input',
          { bubbles: true },
        ),
      )

      syncing = false
      readToolbarState()
    }

    sync.current = update

    const restore = () => {
      if (
        syncing
        || textarea.value === lastValue
      ) {
        return
      }

      editable.innerHTML = cleanArticleHTML(
        textarea.value,
      )

      lastHTML = editable.innerHTML
      lastValue = textarea.value

      validate()
      readToolbarState()
    }

    const submit = (event) => {
      update()

      if (validate()) {
        event.preventDefault()
        event.stopImmediatePropagation()
        editable.focus()
      }
    }

    const invalid = (event) => {
      event.preventDefault()
      editable.focus()
    }

    const preview = () => {
      const target = document.getElementById(
        'staff-preview-content',
      )

      if (target) {
        target.innerHTML = cleanArticleHTML(
          textarea.value,
        )
      }
    }

    const observer = new MutationObserver(() => {
      const target = document.getElementById(
        'staff-preview-content',
      )

      const safe = cleanArticleHTML(
        textarea.value,
      )

      if (
        target
        && target.innerHTML !== safe
      ) {
        target.innerHTML = safe
      }
    })

    const previewTarget = document.getElementById(
      'staff-preview-content',
    )

    if (previewTarget) {
      observer.observe(
        previewTarget,
        { childList: true },
      )
    }

    const form = textarea.form

    form?.addEventListener(
      'submit',
      submit,
      true,
    )

    textarea.addEventListener(
      'input',
      restore,
    )

    textarea.addEventListener(
      'change',
      restore,
    )

    textarea.addEventListener(
      'invalid',
      invalid,
    )

    document.addEventListener(
      'selectionchange',
      readToolbarState,
    )

    document
      .querySelectorAll(
        '[data-article-preview-button]',
      )
      .forEach(
        (button) => (
          button.addEventListener(
            'click',
            preview,
          )
        ),
      )

    update()

    return () => {
      observer.disconnect()

      form?.removeEventListener(
        'submit',
        submit,
        true,
      )

      textarea.removeEventListener(
        'input',
        restore,
      )

      textarea.removeEventListener(
        'change',
        restore,
      )

      textarea.removeEventListener(
        'invalid',
        invalid,
      )

      document.removeEventListener(
        'selectionchange',
        readToolbarState,
      )

      document
        .querySelectorAll(
          '[data-article-preview-button]',
        )
        .forEach(
          (button) => (
            button.removeEventListener(
              'click',
              preview,
            )
          ),
        )

      textarea.hidden = originalHidden
      textarea.style.display = originalDisplay
      textarea.required = required
      textarea.setCustomValidity('')

      refreshToolbar.current = () => {}
      sync.current = () => {}
    }
  }, [fieldId])

  const runCommand = (name) => {
    const editable = editor.current

    if (!editable) return

    editable.focus()

    document.execCommand(
      'styleWithCSS',
      false,
      false,
    )

    document.execCommand(
      name,
      false,
      null,
    )

    sync.current()
    refreshToolbar.current()
  }

  const runListCommand = (kind) => {
    const editable = editor.current

    if (!editable) return

    editable.focus()

    const current = closestList(editable)

    if (kind === 'dash') {
      if (
        current?.tagName === 'UL'
        && current.dataset.listStyle === 'dash'
      ) {
        document.execCommand(
          'insertUnorderedList',
          false,
          null,
        )
      } else if (current?.tagName === 'UL') {
        current.dataset.listStyle = 'dash'
      } else {
        document.execCommand(
          'insertUnorderedList',
          false,
          null,
        )

        const created = closestList(editable)

        if (created?.tagName === 'UL') {
          created.dataset.listStyle = 'dash'
        }
      }
    }

    if (kind === 'bullet') {
      if (current?.tagName === 'UL') {
        if (
          current.dataset.listStyle === 'dash'
        ) {
          delete current.dataset.listStyle
        } else {
          document.execCommand(
            'insertUnorderedList',
            false,
            null,
          )
        }
      } else {
        document.execCommand(
          'insertUnorderedList',
          false,
          null,
        )

        const created = closestList(editable)

        if (created?.tagName === 'UL') {
          delete created.dataset.listStyle
        }
      }
    }

    if (kind === 'numbered') {
      document.execCommand(
        'insertOrderedList',
        false,
        null,
      )
    }

    sync.current()
    refreshToolbar.current()
  }

  const insertText = (event, text) => {
    event.preventDefault()

    document.execCommand(
      'insertText',
      false,
      text,
    )

    sync.current()
  }

  const inlineTools = [
    {
      name: 'bold',
      label: 'B',
      title: 'Bold',
      className: 'is-bold',
    },
    {
      name: 'italic',
      label: 'I',
      title: 'Italic',
      className: 'is-italic',
    },
    {
      name: 'underline',
      label: 'U',
      title: 'Underline',
      className: 'is-underline',
    },
    {
      name: 'strikeThrough',
      label: 'S',
      title: 'Strikethrough',
      className: 'is-strike',
    },
  ]

  const listTools = [
    {
      name: 'bulletList',
      kind: 'bullet',
      label: '• List',
      title: 'Bulleted list',
    },
    {
      name: 'numberedList',
      kind: 'numbered',
      label: '1. List',
      title: 'Numbered list',
    },
    {
      name: 'dashList',
      kind: 'dash',
      label: '— List',
      title: 'Dash list',
    },
  ]

  return (
    <div className="article-rich-editor">
      <div
        role="toolbar"
        aria-label="Article formatting"
        className="article-rich-toolbar"
      >
        <div
          className="article-rich-toolbar-group"
          role="group"
          aria-label="Text formatting"
        >
          <span
            className="article-rich-toolbar-group-label"
            aria-hidden="true"
          >
            Text
          </span>

          {inlineTools.map(
            ({
              name,
              label,
              title,
              className,
            }) => (
              <button
                key={name}
                type="button"
                title={title}
                aria-label={title}
                aria-pressed={formats[name]}
                className={
                  `article-rich-toolbar-button ${className} ${
                    formats[name] ? 'is-active' : ''
                  }`
                }
                onMouseDown={
                  (event) => (
                    event.preventDefault()
                  )
                }
                onClick={
                  () => runCommand(name)
                }
              >
                {label}
              </button>
            ),
          )}
        </div>

        <span
          className="article-rich-toolbar-divider"
          aria-hidden="true"
        />

        <div
          className="article-rich-toolbar-group article-rich-toolbar-group--lists"
          role="group"
          aria-label="List formatting"
        >
          <span
            className="article-rich-toolbar-group-label"
            aria-hidden="true"
          >
            Lists
          </span>

          {listTools.map(
            ({
              name,
              kind,
              label,
              title,
            }) => (
              <button
                key={name}
                type="button"
                title={title}
                aria-label={title}
                aria-pressed={formats[name]}
                className={
                  `article-rich-toolbar-button article-rich-toolbar-list ${
                    formats[name] ? 'is-active' : ''
                  }`
                }
                onMouseDown={
                  (event) => (
                    event.preventDefault()
                  )
                }
                onClick={
                  () => runListCommand(kind)
                }
              >
                {label}
              </button>
            ),
          )}
        </div>
      </div>

      <div
        ref={editor}
        contentEditable
        suppressContentEditableWarning
        className="article-rich-surface"
        role="textbox"
        aria-label="Article Content"
        aria-multiline="true"
        aria-describedby={`${fieldId}-rich-status`}
        data-placeholder="Write the article body here…"
        onInput={() => sync.current()}
        onFocus={() => refreshToolbar.current()}
        onMouseUp={() => refreshToolbar.current()}
        onKeyUp={() => refreshToolbar.current()}
        onKeyDown={(event) => {
          const modifier = (
            event.ctrlKey
            || event.metaKey
          )

          if (
            modifier
            && event.shiftKey
            && event.code === 'Digit7'
          ) {
            event.preventDefault()
            runListCommand('numbered')
            return
          }

          if (
            modifier
            && event.shiftKey
            && event.code === 'Digit8'
          ) {
            event.preventDefault()
            runListCommand('bullet')
            return
          }

          if (modifier) {
            const name = {
              b: 'bold',
              i: 'italic',
              u: 'underline',
            }[
              event.key.toLowerCase()
            ]

            if (name) {
              event.preventDefault()
              runCommand(name)
            }
          }
        }}
        onPaste={
          (event) => (
            insertText(
              event,
              event.clipboardData.getData(
                'text/plain',
              ),
            )
          )
        }
        onDrop={
          (event) => (
            insertText(
              event,
              event.dataTransfer.getData(
                'text/plain',
              ),
            )
          )
        }
      />

      <div
        id={`${fieldId}-rich-status`}
        className={
          `article-rich-status ${
            error ? 'has-error' : ''
          }`
        }
        aria-live="polite"
      >
        <span className="article-rich-status-copy">
          {error || (
            'Formatting: bold, italic, underline, strikethrough, bullets, numbers and dashes.'
          )}
        </span>

        <span className="article-rich-character-count">
          {count.toLocaleString()}
          {' / '}
          {maximum.toLocaleString()}
        </span>
      </div>
    </div>
  )
}
