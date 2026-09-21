// Browser smoke tests using installed Chrome and its DevTools protocol.
// Run after npm run build: node tests/interactions.mjs
import assert from 'node:assert/strict'
import { spawn } from 'node:child_process'
import { createServer } from 'node:http'
import { mkdtemp, readFile, rm } from 'node:fs/promises'
import { tmpdir } from 'node:os'
import { dirname, resolve, sep } from 'node:path'
import { fileURLToPath } from 'node:url'

const root = resolve(dirname(fileURLToPath(import.meta.url)), '../..')
const fixture = `<!doctype html><html><head><meta charset="utf-8"><link rel="stylesheet" href="/static/react-dist/assets/equalizer-react.css"></head><body>
<input type="hidden" name="csrfmiddlewaretoken" value="test-token">
<div data-react-component="SystemUpdatePopup" data-api-url="/popup"></div>
<span data-update-count>1</span>
<div id="email-one" data-react-component="AccountEmailToggle" data-email="one@example.test"></div>
<div id="email-two" data-react-component="AccountEmailToggle" data-email="two@example.test"></div>
<form id="article-form"><textarea id="content" name="content" maxlength="30000" required>Original &amp; plain text</textarea><div data-react-component="ArticleRichTextEditor" data-field-id="content"></div><button type="submit">Save</button></form>
<div id="staff-preview-content"></div><button data-article-preview-button>Preview</button>
<div data-react-component="InlineDownloadButton" data-url="/pdf" data-filename="fallback.pdf"></div>
<script>
window.acks = 0;
const originalFetch = window.fetch;
window.fetch = async (url, options) => {
  if (url === '/popup') return Response.json({update: {id:1,title:'Editorial improvements',summary:'Publication tools',changeNotes:'NEW\\nPublic Archive\\nIMPROVED\\nArticle formatting',version:'v1.5',type:'Improved',published:'Sep. 21, 2026',required:true,url:'/full',ackUrl:'/ack'}});
  if (url === '/ack') { window.acks++; return Response.json({ok:true}); }
  if (url === '/pdf') { await new Promise(resolve=>setTimeout(resolve,150)); return new Response('%PDF-1.4 test', {headers: {'Content-Type':'application/pdf', 'Content-Length':'13', 'Content-Disposition':"attachment; filename*=UTF-8''Equalizer%20story.pdf"}}); }
  return originalFetch(url, options);
};
// Avoid saving a synthetic test PDF; capture the browser download attributes.
const originalClick = HTMLAnchorElement.prototype.click;
HTMLAnchorElement.prototype.click = function() { if(this.download) window.downloadName = this.download; else originalClick.call(this); };
</script><script type="module" src="/static/react-dist/assets/equalizer-react.js"></script></body></html>`

const server = createServer(async (request, response) => {
  try {
    if (request.url === '/') { response.setHeader('Content-Type', 'text/html'); response.end(fixture); return }
    const path = resolve(root, '.' + decodeURIComponent(request.url.split('?')[0]))
    const staticRoot = resolve(root, 'static/react-dist') + sep
    if (!path.startsWith(staticRoot)) { response.writeHead(404); response.end(); return }
    response.setHeader('Content-Type', path.endsWith('.css') ? 'text/css' : 'text/javascript')
    response.end(await readFile(path))
  } catch { response.writeHead(404); response.end() }
})
await new Promise(resolve => server.listen(0, '127.0.0.1', resolve))
const profile = await mkdtemp(resolve(tmpdir(), 'equalizer-browser-test-'))
const chromePath = process.env.CHROME_PATH || 'C:/Program Files/Google/Chrome/Application/chrome.exe'
const browser = spawn(chromePath, ['--headless=new', '--disable-gpu', '--no-first-run', '--no-default-browser-check', '--remote-debugging-port=0', `--user-data-dir=${profile}`, 'about:blank'], { windowsHide: true, stdio: ['ignore', 'ignore', 'pipe'] })
let socket
try {
  const endpoint = await new Promise((resolve, reject) => {
    const timeout = setTimeout(() => reject(new Error('Chrome startup timed out')), 15000)
    let output = ''
    browser.on('error', reject)
    browser.stderr.on('data', chunk => {
      output += chunk
      const match = output.match(/DevTools listening on (ws:\/\/[^\s]+)/)
      if (match) { clearTimeout(timeout); resolve(match[1]) }
    })
  })
  socket = new WebSocket(endpoint)
  await new Promise((resolve, reject) => { socket.onopen = resolve; socket.onerror = reject })
  let sequence = 0
  const pending = new Map()
  const errors = []
  socket.onmessage = event => {
    const data = JSON.parse(event.data)
    if (data.method === 'Runtime.exceptionThrown') errors.push(data.params.exceptionDetails.text)
    if (pending.has(data.id)) {
      const { resolve, reject } = pending.get(data.id)
      pending.delete(data.id)
      if (data.error) reject(new Error(JSON.stringify(data.error)))
      else resolve(data.result)
    }
  }
  function command(method, params = {}, sessionId) {
    return new Promise((resolve, reject) => {
      const id = ++sequence
      pending.set(id, { resolve, reject })
      socket.send(JSON.stringify({ id, method, params, sessionId }))
    })
  }
  const { targetId } = await command('Target.createTarget', { url: 'about:blank' })
  const { sessionId } = await command('Target.attachToTarget', { targetId, flatten: true })
  await command('Runtime.enable', {}, sessionId)
  await command('Page.enable', {}, sessionId)
  const evaluate = async expression => {
    const value = await command('Runtime.evaluate', { expression, returnByValue: true, awaitPromise: true }, sessionId)
    if (value.exceptionDetails) throw new Error(value.exceptionDetails.exception?.description || value.exceptionDetails.text)
    return value.result.value
  }
  async function until(expression) {
    for (let i = 0; i < 80; i++) {
      if (await evaluate(expression)) return
      await new Promise(resolve => setTimeout(resolve, 100))
    }
    throw new Error(`Timed out: ${expression}`)
  }
  await command('Page.navigate', { url: `http://127.0.0.1:${server.address().port}/` }, sessionId)
  await until('!!document.querySelector(".system-update-dialog[open]")')
  assert.equal(await evaluate('document.querySelector(".system-update-dialog").contains(document.activeElement)'), true)
  await evaluate('document.querySelector(".system-update-dialog button").click()')
  await until('!document.querySelector(".system-update-dialog")')
  assert.equal(await evaluate('window.acks'), 1)
  assert.equal(await evaluate('document.querySelector("[data-update-count]").hidden'), true)
  await until('!!document.querySelector(".article-rich-surface")')
  assert.equal(await evaluate('document.querySelector(".article-rich-surface").textContent'), 'Original & plain text')
  assert.equal(await evaluate('document.querySelector("#email-one span span").textContent.includes("••")'), true)
  await evaluate('document.querySelector("#email-one button").click()')
  assert.equal(await evaluate('document.querySelector("#email-one span span").textContent'), 'one@example.test')
  assert.equal(await evaluate('document.querySelector("#email-two span span").textContent.includes("••")'), true)
  await evaluate('document.querySelector("#email-one button").click()')
  assert.equal(await evaluate('document.querySelector("#email-one button").getAttribute("aria-pressed")'), 'false')
  for (const label of ['Bold', 'Italic', 'Underline', 'Strikethrough']) {
    await evaluate(`(() => { const editor=document.querySelector('.article-rich-surface'); editor.focus(); window.getSelection().selectAllChildren(editor); document.querySelector('[aria-label="${label}"]').click(); })()`)
  }
  const content = await evaluate('document.querySelector("#content").value')
  for (const tag of ['b', 'i', 'u', 'strike']) assert.match(content, new RegExp(`<${tag}>`))
  await evaluate('document.querySelector("#staff-preview-content").textContent = document.querySelector("#content").value')
  await until('!!document.querySelector("#staff-preview-content b")')
  await evaluate('document.querySelector("#content").value = "<b>Restored</b><img src=x onerror=alert(1)>"; document.querySelector("#content").dispatchEvent(new Event("change", {bubbles:true}))')
  assert.equal(await evaluate('document.querySelector(".article-rich-surface").innerHTML'), '<b>Restored</b>')
  await evaluate('const editor=document.querySelector(".article-rich-surface"); editor.textContent="x".repeat(30001); editor.dispatchEvent(new InputEvent("input", {bubbles:true}))')
  assert.equal(await evaluate('document.querySelector("#article-form").checkValidity()'), false)
  assert.equal(await evaluate('document.activeElement.classList.contains("article-rich-surface")'), true)
  await evaluate('document.querySelector(".inline-pdf-download button").click()')
  assert.equal(await evaluate('document.querySelector(".inline-pdf-download").textContent.includes("Preparing PDF")'), true)
  await until('window.downloadName === "Equalizer story.pdf"')
  assert.equal(await evaluate('document.querySelector(".inline-pdf-download").textContent.includes("Downloaded")'), true)
  assert.equal(await evaluate('!!document.querySelector(".reader-pdf-download-overlay")'), false)
  assert.deepEqual(errors, [])
  console.log('PASS: popup acknowledgement/focus, per-card email toggles, four rich-text styles, preview, retry restoration, maxlength validity, and inline PDF filename/status.')
  await command('Browser.close')
} finally {
  socket?.close()
  browser.kill()
  await new Promise(resolve => server.close(resolve))
  // The generated Chrome profile is the only recursively removed directory.
  const safeRoot = resolve(tmpdir()) + sep
  if (resolve(profile).startsWith(safeRoot) && dirname(profile) === resolve(tmpdir())) {
    await rm(profile, { recursive: true, force: true, maxRetries: 5, retryDelay: 200 })
  }
}
