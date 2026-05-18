import { useEffect, useRef, useState } from 'react';
import { readPtyStream } from '../api';

function isRetryableStreamError(err: unknown) {
  if (!(err instanceof Error)) return false;
  return /failed to fetch|load failed|networkerror/i.test(err.message);
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

export function usePtyStream(sid: string) {
  const [text, setText] = useState('');
  const [offset, setOffset] = useState(0);
  const [alive, setAlive] = useState(false);
  const sessionRef = useRef('');

  useEffect(() => {
    if (!sid) {
      setText('');
      setOffset(0);
      setAlive(false);
      return;
    }

    let cancelled = false;
    sessionRef.current = sid;
    setText('');
    setOffset(0);
    setAlive(true);

    const loop = async () => {
      let nextOffset = 0;
      let notifiedNetworkError = false;
      while (!cancelled && sessionRef.current === sid) {
        try {
          const result = await readPtyStream(sid, nextOffset, 10);
          if (cancelled || sessionRef.current !== sid) return;
          if (notifiedNetworkError) {
            setText((prev) => prev + '\n[stream reconnected]\n');
            notifiedNetworkError = false;
          }
          nextOffset = result.offset;
          setOffset(nextOffset);
          setAlive(result.alive);
          if (result.reset) {
            setText(result.text);
          } else if (result.text) {
            setText((prev) => prev + result.text);
          }
          if (!result.alive) break;
        } catch (err) {
          if (isRetryableStreamError(err)) {
            if (!notifiedNetworkError && !cancelled) {
              setText((prev) => prev + '\n[stream reconnecting...]\n');
              notifiedNetworkError = true;
            }
            await sleep(1200);
            continue;
          }
          if (!cancelled) {
            setText((prev) => prev + `\n[stream error] ${err instanceof Error ? err.message : String(err)}\n`);
          }
          break;
        }
      }
    };

    void loop();

    return () => {
      cancelled = true;
    };
  }, [sid]);

  return { text, offset, alive };
}
