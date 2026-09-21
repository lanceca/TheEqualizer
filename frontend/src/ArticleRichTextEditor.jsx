import { useEffect, useRef, useState } from 'react'
import { articleText, cleanArticleHTML } from './articleRichText'
import './PublicationInteractions.css'

export default function ArticleRichTextEditor({ fieldId }) {
  const editor = useRef(null)
  const sync = useRef(() => {})
  const [error, setError] = useState('')
  const [count, setCount] = useState(0)

  useEffect(() => {
    const textarea = document.getElementById(fieldId)
    const editable = editor.current
    if (!textarea || !editable) return
    const required = textarea.required
    const maximum = textarea.maxLength > 0 ? textarea.maxLength : 30000
    const originalHidden = textarea.hidden
    const originalDisplay = textarea.style.display
    textarea.hidden = true
    textarea.style.display = 'none'
    textarea.required = false
    editable.innerHTML = cleanArticleHTML(textarea.value)
    let lastHTML = editable.innerHTML
    let lastValue = textarea.value
    let syncing = false
    const validate = () => {
      const length = articleText(textarea.value).length
      const message = length > maximum ? `Article content cannot exceed ${maximum.toLocaleString()} characters.`
        : required && !articleText(textarea.value).trim() ? 'Article content is required.' : ''
      setCount(length)
      setError(message)
      textarea.setCustomValidity(message)
      textarea.dataset.visibleLength = String(length)
      editable.setAttribute('aria-invalid', message ? 'true' : 'false')
      return message
    }
    const update = () => {
      // Keep the selection stable while typing. Sanitize the submitted value;
      // paste and drop only insert text, and the toolbar creates allowed tags.
      const html = cleanArticleHTML(editable.innerHTML)
      if (html !== lastHTML) {
        textarea.value = html
        lastHTML = html
        lastValue = html
      }
      validate()
      syncing = true
      textarea.dispatchEvent(new Event('input', { bubbles: true }))
      syncing = false
    }
    sync.current = update
    const restore = () => {
      if (syncing || textarea.value === lastValue) return
      editable.innerHTML = cleanArticleHTML(textarea.value)
      lastHTML = editable.innerHTML
      lastValue = textarea.value
      validate()
    }
    const submit = event => {
      update()
      if (validate()) {
        event.preventDefault()
        event.stopImmediatePropagation()
        editable.focus()
      }
    }
    const invalid = event => { event.preventDefault(); editable.focus() }
    const preview = () => {
      const target = document.getElementById('staff-preview-content')
      if (target) target.innerHTML = cleanArticleHTML(textarea.value)
    }
    const observer = new MutationObserver(() => {
      const target = document.getElementById('staff-preview-content')
      const safe = cleanArticleHTML(textarea.value)
      if (target && target.innerHTML !== safe) target.innerHTML = safe
    })
    const target = document.getElementById('staff-preview-content')
    if (target) observer.observe(target, { childList: true })
    const form = textarea.form
    form?.addEventListener('submit', submit, true)
    textarea.addEventListener('input', restore)
    textarea.addEventListener('change', restore)
    textarea.addEventListener('invalid', invalid)
    document.querySelectorAll('[data-article-preview-button]').forEach(button => button.addEventListener('click', preview))
    update()
    return () => {
      observer.disconnect()
      form?.removeEventListener('submit', submit, true)
      textarea.removeEventListener('input', restore)
      textarea.removeEventListener('change', restore)
      textarea.removeEventListener('invalid', invalid)
      document.querySelectorAll('[data-article-preview-button]').forEach(button => button.removeEventListener('click', preview))
      textarea.hidden = originalHidden
      textarea.style.display = originalDisplay
      textarea.required = required
      textarea.setCustomValidity('')
    }
  }, [fieldId])

  const command = name => {
    editor.current.focus()
    document.execCommand('styleWithCSS', false, false)
    document.execCommand(name, false)
    sync.current()
  }
  const insertText = (event, text) => {
    event.preventDefault()
    document.execCommand('insertText', false, text)
    sync.current()
  }
  return <div className="article-rich-editor">
    <div role="toolbar" aria-label="Article formatting" className="article-rich-toolbar">
      {[['bold', 'B', 'Bold'], ['italic', 'I', 'Italic'], ['underline', 'U', 'Underline'], ['strikeThrough', 'S', 'Strikethrough']].map(([name, label, title]) =>
        <button key={name} type="button" title={title} aria-label={title} onMouseDown={event => event.preventDefault()} onClick={() => command(name)}>{label}</button>)}
    </div>
    <div ref={editor} contentEditable suppressContentEditableWarning className="article-rich-surface" role="textbox" aria-label="Article Content" aria-multiline="true" aria-describedby={`${fieldId}-rich-status`}
      onInput={() => sync.current()}
      onKeyDown={event => {
        if (event.ctrlKey || event.metaKey) {
          const name = { b: 'bold', i: 'italic', u: 'underline' }[event.key.toLowerCase()]
          if (name) { event.preventDefault(); command(name) }
        }
      }}
      onPaste={event => insertText(event, event.clipboardData.getData('text/plain'))}
      onDrop={event => insertText(event, event.dataTransfer.getData('text/plain'))}
    />
    <p id={`${fieldId}-rich-status`} aria-live="polite" className={error ? 'rich-editor-error' : ''}>{error || `${count.toLocaleString()} characters · Bold, italic, underline and strikethrough`}</p>
  </div>
}
