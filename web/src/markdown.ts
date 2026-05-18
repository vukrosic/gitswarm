function escapeHtml(value: string): string {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}

export function renderMarkdown(input: string): string {
  const normalized = (input || '')
    .replace(/\r\n/g, '\n')
    .replace(/\\n/g, '\n');
  const lines = normalized.split('\n');
  const out: string[] = [];
  let inList = false;
  let inCode = false;
  let codeLines: string[] = [];

  const closeList = () => {
    if (inList) {
      out.push('</ul>');
      inList = false;
    }
  };

  const flushCode = () => {
    out.push(`<pre><code>${escapeHtml(codeLines.join('\n'))}</code></pre>`);
    codeLines = [];
  };

  for (const raw of lines) {
    const line = raw.trimEnd();
    if (line.startsWith('```')) {
      if (inCode) {
        flushCode();
        inCode = false;
      } else {
        closeList();
        inCode = true;
      }
      continue;
    }
    if (inCode) {
      codeLines.push(line);
      continue;
    }
    if (!line.trim()) {
      closeList();
      out.push('<p></p>');
      continue;
    }
    const heading = line.match(/^(#{1,3})\s+(.*)$/);
    if (heading) {
      closeList();
      const level = heading[1].length + 1;
      out.push(`<h${level}>${escapeHtml(heading[2])}</h${level}>`);
      continue;
    }
    const bullet = line.match(/^[-*]\s+(.*)$/);
    if (bullet) {
      if (!inList) {
        out.push('<ul>');
        inList = true;
      }
      out.push(`<li>${escapeHtml(bullet[1])}</li>`);
      continue;
    }
    closeList();
    out.push(`<p>${escapeHtml(line)}</p>`);
  }
  if (inCode) {
    flushCode();
  }
  closeList();
  return out.join('\n').replace(/<p><\/p>\n?/g, '<div class="md-gap"></div>');
}
