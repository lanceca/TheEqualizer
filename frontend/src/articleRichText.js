const allowed = new Set(['STRONG', 'B', 'EM', 'I', 'U', 'S', 'STRIKE', 'P', 'BR'])

// Rebuild nodes instead of trusting attributes or pasted HTML. Server sanitization
// remains authoritative; this also protects unsaved previews in the browser.
export function cleanArticleHTML(value) {
  const source = document.createElement('template')
  if (!/<\/?[a-z][^>]*>/i.test(value)) {
    source.content.append(document.createTextNode(value))
    return source.innerHTML.replace(/\n/g, '<br>')
  }
  source.innerHTML = value
  const output = document.createElement('div')
  function copy(node, parent) {
    if (node.nodeType === Node.TEXT_NODE) {
      parent.append(document.createTextNode(node.textContent))
    } else if (node.nodeType === Node.ELEMENT_NODE) {
      const tag = node.tagName === 'DIV' ? 'P' : node.tagName
      const target = allowed.has(tag) ? document.createElement(tag.toLowerCase()) : parent
      if (target !== parent) parent.append(target)
      Array.from(node.childNodes).forEach(child => copy(child, target))
    }
  }
  Array.from(source.content.childNodes).forEach(node => copy(node, output))
  return output.innerHTML
}

export function articleText(value) {
  const source = document.createElement('template')
  source.innerHTML = cleanArticleHTML(value).replace(/<br\s*\/?\s*>|<\/p>/gi, '\n')
  return source.content.textContent || ''
}
