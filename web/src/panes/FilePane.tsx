import type { FileEntry } from '../types';
import { fmtTime } from '../lib/time';

interface FilePaneProps {
  file: FileEntry;
  text: string;
}

export function FilePane({ file, text }: FilePaneProps) {
  return (
    <section className="detail">
      <div className="detail-head">
        <div>
          <div className="eyebrow">State file</div>
          <h2>{file.name}</h2>
          <div className="meta-line">{Math.round(file.size / 1024)} KB · {fmtTime(file.mtime)}</div>
        </div>
      </div>
      <pre className="body">{text || 'Loading file...'}</pre>
    </section>
  );
}
