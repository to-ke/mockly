// Very small markdown-to-HTML helper for chat bubbles.
// Supports: headings (#..###), bold **..**, italics *..*, inline code `..`,
// code blocks ```...```, unordered lists (- ...), and paragraphs.
// Escapes HTML first and performs conservative replacements to avoid XSS.

function escapeHtml(input: string): string {
  return input
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/\"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

export function renderMarkdown(md: string): string {
  if (!md) return ''

  // Normalize newlines
  let text = md.replace(/\r\n?/g, '\n')

  // Protect code blocks first
  const codeBlocks: string[] = []
  text = text.replace(/```([\s\S]*?)```/g, (_m, p1) => {
    const idx = codeBlocks.push(p1) - 1
    return `@@CODEBLOCK_${idx}@@`
  })

  // Escape remaining HTML
  text = escapeHtml(text)

  // Headings (simple) -> strong blocks
  text = text.replace(/^###\s*(.+)$/gm, '<strong>$1</strong>')
             .replace(/^##\s*(.+)$/gm, '<strong>$1</strong>')
             .replace(/^#\s*(.+)$/gm, '<strong>$1</strong>')

  // Bold and italics (non-greedy)
  text = text.replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
             .replace(/\*(.+?)\*/g, '<em>$1</em>')

  // Inline code
  text = text.replace(/`([^`]+?)`/g, '<code class="px-1 py-0.5 rounded bg-muted/50">$1</code>')

  // Unordered lists: group consecutive - lines
  text = text.replace(/(?:^(?:- |\* ).+\n?)+/gm, (block) => {
    const items = block.trim().split(/\n+/).map((line) => line.replace(/^(?:- |\* )/, '').trim())
    const lis = items.map((it) => `<li class="ml-4 list-disc">${it}</li>`).join('')
    return `<ul class="my-1">${lis}</ul>`
  })

  // Paragraphs: split on blank lines and wrap if not already a block element
  const parts = text.split(/\n\n+/).map((seg) => {
    const s = seg.trim()
    if (!s) return ''
    if (s.startsWith('<ul') || s.startsWith('<pre') || s.startsWith('<strong') || s.startsWith('<code')) {
      return s
    }
    return `<p>${s.replace(/\n/g, '<br/>')}</p>`
  })

  let html = parts.join('\n')

  // Restore code blocks (already escaped before capture)
  html = html.replace(/@@CODEBLOCK_(\d+)@@/g, (_m, i) => {
    const raw = codeBlocks[Number(i)] ?? ''
    const esc = escapeHtml(raw)
    return `<pre class="my-1 overflow-x-auto rounded bg-muted/40 p-2"><code>${esc}</code></pre>`
  })

  return html
}

export default renderMarkdown

