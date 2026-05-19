import { useEffect, useRef, useState } from 'react';
import { fetchPrCiStatus, type CiCheck } from '../api';

const POLL_INTERVAL = 60_000;

export function usePrCiStatus(prNumber: number | null) {
  const [checks, setChecks] = useState<CiCheck[]>([]);
  const timerRef = useRef<number | null>(null);

  useEffect(() => {
    if (prNumber === null) {
      setChecks([]);
      return;
    }
    let cancelled = false;
    const load = () => {
      if (cancelled) return;
      void fetchPrCiStatus(prNumber).then((res) => {
        if (cancelled) return;
        setChecks(res.checks || []);
      }).catch(() => {
        if (cancelled) return;
        setChecks([]);
      });
    };
    load();
    timerRef.current = window.setInterval(load, POLL_INTERVAL);
    return () => {
      cancelled = true;
      if (timerRef.current !== null) {
        window.clearInterval(timerRef.current);
        timerRef.current = null;
      }
    };
  }, [prNumber]);

  return checks;
}