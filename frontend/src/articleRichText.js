const allowed = new Set([
  'STRONG',
  'B',
  'EM',
  'I',
  'U',
  'S',
  'STRIKE',
  'P',
  'BR',
  'UL',
  'OL',
  'LI',
])

// Rebuild nodes instead of trusting arbitrary attributes or pasted HTML.
// Server sanitization remains authoritative; this also protects unsaved
// previews in the browser.
export function cleanArticleHTML(value) {
  const source = document.createElement(
    'template',
  )

  if (
    !/<\/?[a-z][^>]*>/i.test(value)
  ) {
    source.content.append(
      document.createTextNode(value),
    )

    return source.innerHTML.replace(
      /\n/g,
      '<br>',
    )
  }

  source.innerHTML = value

  const output = document.createElement(
    'div',
  )

  function copy(node, parent) {
    if (
      node.nodeType === Node.TEXT_NODE
    ) {
      parent.append(
        document.createTextNode(
          node.textContent,
        ),
      )

      return
    }

    if (
      node.nodeType !== Node.ELEMENT_NODE
    ) {
      return
    }

    const tag = node.tagName === 'DIV'
      ? 'P'
      : node.tagName

    const target = allowed.has(tag)
      ? document.createElement(
        tag.toLowerCase(),
      )
      : parent

    if (target !== parent) {
      if (
        tag === 'UL'
        && node.getAttribute(
          'data-list-style',
        ) === 'dash'
      ) {
        target.setAttribute(
          'data-list-style',
          'dash',
        )
      }

      parent.append(target)
    }

    Array
      .from(node.childNodes)
      .forEach(
        (child) => (
          copy(child, target)
        ),
      )
  }

  Array
    .from(source.content.childNodes)
    .forEach(
      (node) => copy(node, output),
    )

  return output.innerHTML
}

export function articleText(value) {
  const source = document.createElement(
    'template',
  )

  source.innerHTML = cleanArticleHTML(
    value,
  )

  function extract(node) {
    if (
      node.nodeType === Node.TEXT_NODE
    ) {
      return node.textContent || ''
    }

    if (
      node.nodeType !== Node.ELEMENT_NODE
    ) {
      return ''
    }

    if (node.tagName === 'BR') {
      return '\n'
    }

    let result = Array
      .from(node.childNodes)
      .map(extract)
      .join('')

    if (
      node.tagName === 'P'
      || node.tagName === 'LI'
    ) {
      result += '\n'
    }

    if (
      node.tagName === 'UL'
      || node.tagName === 'OL'
    ) {
      result += '\n'
    }

    return result
  }

  return Array
    .from(source.content.childNodes)
    .map(extract)
    .join('')
    .replace(/\n{3,}/g, '\n\n')
}
