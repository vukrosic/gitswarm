const ANSI_PATTERN = /(?:\x1b\][^\x07]*(?:\x07|\x1b\\)|\x1b\[[0-?]*[ -/]*[@-~]|\x1b[@-Z\\-_])/g;
const CONTROL_PATTERN = /[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g;

export function cleanTerminalText(value: string) {
  return value
    .replace(ANSI_PATTERN, '')
    .replace(/\x07/g, '')
    .replace(/\r\n/g, '\n')
    .replace(/\r/g, '\n')
    .replace(CONTROL_PATTERN, '');
}
