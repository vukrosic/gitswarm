interface TerminalRenderOptions {
  rows?: number;
  cols?: number;
  maxScrollback?: number;
}

const DEFAULT_ROWS = 30;
const DEFAULT_COLS = 100;
const DEFAULT_SCROLLBACK = 1000;

function clampInt(value: unknown, fallback: number, min: number, max: number) {
  const n = typeof value === 'number' && Number.isFinite(value) ? Math.floor(value) : fallback;
  return Math.max(min, Math.min(max, n));
}

function blankLine(cols: number) {
  return Array.from({ length: cols }, () => ' ');
}

function trimRight(line: string[]) {
  return line.join('').replace(/\s+$/g, '');
}

function csiNumbers(params: string, defaultValue = 1) {
  const clean = params.replace(/[?<>=]/g, '');
  if (!clean) return [defaultValue];
  return clean.split(';').map((part) => {
    const n = Number.parseInt(part, 10);
    return Number.isFinite(n) && n > 0 ? n : defaultValue;
  });
}

function findOscEnd(value: string, start: number) {
  const bell = value.indexOf('\x07', start);
  const st = value.indexOf('\x1b\\', start);
  if (bell === -1) return st === -1 ? -1 : st + 2;
  if (st === -1) return bell + 1;
  return Math.min(bell + 1, st + 2);
}

function trimTrailingBlankLines(lines: string[]) {
  let end = lines.length;
  while (end > 0 && !lines[end - 1]) end -= 1;
  return lines.slice(0, end);
}

export function renderTerminalText(value: string, options: TerminalRenderOptions = {}) {
  const rows = clampInt(options.rows, DEFAULT_ROWS, 6, 80);
  const cols = clampInt(options.cols, DEFAULT_COLS, 20, 220);
  const maxScrollback = clampInt(options.maxScrollback, DEFAULT_SCROLLBACK, 100, 5000);
  let screen = Array.from({ length: rows }, () => blankLine(cols));
  const scrollback: string[] = [];
  let row = 0;
  let col = 0;
  let savedRow = 0;
  let savedCol = 0;
  let alternateScreen = false;
  let touchedScreen = false;

  function clampCursor() {
    row = Math.max(0, Math.min(rows - 1, row));
    col = Math.max(0, Math.min(cols - 1, col));
  }

  function pushScrollback(line: string[]) {
    const text = trimRight(line);
    if (text || scrollback.length) {
      scrollback.push(text);
      if (scrollback.length > maxScrollback) {
        scrollback.splice(0, scrollback.length - maxScrollback);
      }
    }
  }

  function scrollUp(count = 1) {
    for (let i = 0; i < count; i += 1) {
      if (!alternateScreen) pushScrollback(screen[0]);
      screen.shift();
      screen.push(blankLine(cols));
    }
    touchedScreen = true;
  }

  function newline() {
    row += 1;
    if (row >= rows) {
      row = rows - 1;
      scrollUp();
    }
  }

  function clearScreen() {
    screen = Array.from({ length: rows }, () => blankLine(cols));
    row = 0;
    col = 0;
    touchedScreen = true;
  }

  function eraseDisplay(mode: number) {
    touchedScreen = true;
    if (mode === 2 || mode === 3) {
      screen = Array.from({ length: rows }, () => blankLine(cols));
      if (mode === 3) scrollback.length = 0;
      return;
    }
    if (mode === 1) {
      for (let r = 0; r < row; r += 1) screen[r] = blankLine(cols);
      screen[row].fill(' ', 0, col + 1);
      return;
    }
    screen[row].fill(' ', col);
    for (let r = row + 1; r < rows; r += 1) screen[r] = blankLine(cols);
  }

  function eraseLine(mode: number) {
    touchedScreen = true;
    if (mode === 2) {
      screen[row] = blankLine(cols);
      return;
    }
    if (mode === 1) {
      screen[row].fill(' ', 0, col + 1);
      return;
    }
    screen[row].fill(' ', col);
  }

  function putChar(ch: string) {
    if (col >= cols) {
      col = 0;
      newline();
    }
    screen[row][col] = ch;
    col += 1;
    touchedScreen = true;
  }

  function putText(ch: string) {
    if (ch === '\t') {
      const spaces = 8 - (col % 8);
      for (let i = 0; i < spaces; i += 1) putChar(' ');
      return;
    }
    putChar(ch);
  }

  function handleCsi(params: string, final: string) {
    const nums = csiNumbers(params);
    const n = nums[0] || 1;
    switch (final) {
      case 'A':
        row -= n;
        break;
      case 'B':
        row += n;
        break;
      case 'C':
        col += n;
        break;
      case 'D':
        col -= n;
        break;
      case 'E':
        row += n;
        col = 0;
        break;
      case 'F':
        row -= n;
        col = 0;
        break;
      case 'G':
        col = n - 1;
        break;
      case 'H':
      case 'f':
        row = (nums[0] || 1) - 1;
        col = (nums[1] || 1) - 1;
        break;
      case 'd':
        row = n - 1;
        break;
      case 'J':
        eraseDisplay(Number.parseInt(params.replace(/[?<>=]/g, ''), 10) || 0);
        break;
      case 'K':
        eraseLine(Number.parseInt(params.replace(/[?<>=]/g, ''), 10) || 0);
        break;
      case 'S':
        scrollUp(n);
        break;
      case 'T':
        for (let i = 0; i < n; i += 1) {
          screen.pop();
          screen.unshift(blankLine(cols));
        }
        touchedScreen = true;
        break;
      case 'L':
        for (let i = 0; i < n; i += 1) {
          screen.splice(row, 0, blankLine(cols));
          screen.pop();
        }
        touchedScreen = true;
        break;
      case 'M':
        for (let i = 0; i < n; i += 1) {
          screen.splice(row, 1);
          screen.push(blankLine(cols));
        }
        touchedScreen = true;
        break;
      case 'P':
        screen[row].splice(col, n);
        screen[row].push(...Array.from({ length: n }, () => ' '));
        touchedScreen = true;
        break;
      case '@':
        screen[row].splice(col, 0, ...Array.from({ length: n }, () => ' '));
        screen[row] = screen[row].slice(0, cols);
        touchedScreen = true;
        break;
      case 'X':
        screen[row].fill(' ', col, Math.min(cols, col + n));
        touchedScreen = true;
        break;
      case 's':
        savedRow = row;
        savedCol = col;
        break;
      case 'u':
        row = savedRow;
        col = savedCol;
        break;
      case 'h':
        if (params.includes('?1049') || params.includes('?1047') || params.includes('?47')) {
          alternateScreen = true;
          scrollback.length = 0;
          clearScreen();
        }
        break;
      case 'l':
        if (params.includes('?1049') || params.includes('?1047') || params.includes('?47')) {
          alternateScreen = false;
          clearScreen();
        }
        break;
      default:
        break;
    }
    clampCursor();
  }

  for (let i = 0; i < value.length; i += 1) {
    const ch = value[i];
    if (ch === '\x1b') {
      const next = value[i + 1];
      if (next === '[') {
        let end = i + 2;
        while (end < value.length && !/[@-~]/.test(value[end])) end += 1;
        if (end < value.length) {
          handleCsi(value.slice(i + 2, end), value[end]);
          i = end;
          continue;
        }
      }
      if (next === ']') {
        const end = findOscEnd(value, i + 2);
        if (end !== -1) {
          i = end - 1;
          continue;
        }
      }
      if (next === 'P' || next === '^' || next === '_') {
        const end = findOscEnd(value, i + 2);
        if (end !== -1) {
          i = end - 1;
          continue;
        }
      }
      if (next === 'c') {
        clearScreen();
        i += 1;
        continue;
      }
      i += next ? 1 : 0;
      continue;
    }
    if (ch === '\x07') continue;
    if (ch === '\r') {
      col = 0;
      continue;
    }
    if (ch === '\n') {
      newline();
      continue;
    }
    if (ch === '\b' || ch === '\x7f') {
      col = Math.max(0, col - 1);
      continue;
    }
    if (ch < ' ' && ch !== '\t') continue;

    const code = ch.charCodeAt(0);
    if (code >= 0xd800 && code <= 0xdbff && i + 1 < value.length) {
      putText(value.slice(i, i + 2));
      i += 1;
    } else {
      putText(ch);
    }
  }

  const screenLines = screen.map(trimRight);
  const visibleScreen = trimTrailingBlankLines(screenLines);
  if (alternateScreen) return visibleScreen.join('\n');

  const lines = trimTrailingBlankLines([...scrollback, ...visibleScreen]);
  if (!lines.length && touchedScreen) return visibleScreen.join('\n');
  return lines.join('\n');
}

export function cleanTerminalText(value: string) {
  return renderTerminalText(value);
}
