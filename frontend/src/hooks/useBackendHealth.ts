/**
 * useBackendHealth Hook
 *
 * Polls backend health and returns status metadata for compact indicators.
 */

import { useEffect, useMemo, useRef, useState } from 'react';
import { ApiError, getRequest } from '@/services';

type BackendHealthStatus = 'checking' | 'online' | 'degraded' | 'offline';

interface BackendHealthResponse {
  status: string;
  version?: string;
}

interface HealthState {
  status: BackendHealthStatus;
  latencyMs?: number;
  lastCheckedAt?: number;
  consecutiveFailures: number;
  source?: 'live' | 'diagnostics';
}

const REQUEST_TIMEOUT_MS = 5000;
const HIGH_LATENCY_THRESHOLD_MS = 1200;
const OFFLINE_FAILURE_THRESHOLD = 2;
const OFFLINE_BASE_RETRY_MS = 2000;
const OFFLINE_MAX_RETRY_MS = 30000;
const DEGRADED_POLL_INTERVAL_MS = 8000;

function withTimeout<T>(promise: Promise<T>, timeoutMs: number): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const timeoutId = window.setTimeout(() => {
      reject(new Error('Backend health check timed out'));
    }, timeoutMs);

    promise
      .then((value) => {
        window.clearTimeout(timeoutId);
        resolve(value);
      })
      .catch((error) => {
        window.clearTimeout(timeoutId);
        reject(error);
      });
  });
}

function normalizeBackendStatus(status: string, latencyMs: number): BackendHealthStatus {
  const normalized = status.trim().toLowerCase();

  if (normalized === 'healthy' || normalized === 'ok' || normalized === 'up' || normalized === 'ready') {
    return latencyMs > HIGH_LATENCY_THRESHOLD_MS ? 'degraded' : 'online';
  }

  if (normalized === 'degraded' || normalized === 'partial') {
    return 'degraded';
  }

  return 'offline';
}

function getBackoffDelayMs(consecutiveFailures: number): number {
  const exponent = Math.max(0, consecutiveFailures - 1);
  const baseDelay = OFFLINE_BASE_RETRY_MS * 2 ** exponent;
  const clampedDelay = Math.min(OFFLINE_MAX_RETRY_MS, baseDelay);
  const jitterMultiplier = 0.85 + Math.random() * 0.3;
  return Math.round(clampedDelay * jitterMultiplier);
}

export function useBackendHealth(pollIntervalMs = 15000) {
  const [state, setState] = useState<HealthState>({ status: 'checking', consecutiveFailures: 0 });
  const timerRef = useRef<number | null>(null);
  const fallbackToDiagnosticsRef = useRef(false);
  const consecutiveFailuresRef = useRef(0);

  useEffect(() => {
    let isMounted = true;

    const clearScheduledCheck = () => {
      if (timerRef.current !== null) {
        window.clearTimeout(timerRef.current);
        timerRef.current = null;
      }
    };

    const scheduleNextCheck = (delayMs: number) => {
      clearScheduledCheck();
      timerRef.current = window.setTimeout(() => {
        void checkHealth();
      }, delayMs);
    };

    const runDiagnosticsProbe = async (): Promise<{ response: BackendHealthResponse; source: 'diagnostics' }> => {
      const response = await withTimeout(getRequest<BackendHealthResponse>('/health'), REQUEST_TIMEOUT_MS);
      return { response, source: 'diagnostics' };
    };

    const probeBackend = async (): Promise<{ response: BackendHealthResponse; source: 'live' | 'diagnostics' }> => {
      if (fallbackToDiagnosticsRef.current) {
        return runDiagnosticsProbe();
      }

      try {
        const response = await withTimeout(getRequest<BackendHealthResponse>('/health/live'), REQUEST_TIMEOUT_MS);
        return { response, source: 'live' };
      } catch (error) {
        if (error instanceof ApiError && error.statusCode === 404) {
          fallbackToDiagnosticsRef.current = true;
          return runDiagnosticsProbe();
        }
        throw error;
      }
    };

    const checkHealth = async () => {
      const startedAt = performance.now();
      try {
        const { response, source } = await probeBackend();
        const latencyMs = Math.round(performance.now() - startedAt);

        if (!isMounted) {
          return;
        }

        const status = normalizeBackendStatus(response.status, latencyMs);
        consecutiveFailuresRef.current = 0;

        setState({
          status,
          latencyMs,
          lastCheckedAt: Date.now(),
          consecutiveFailures: 0,
          source,
        });

        const nextDelayMs =
          status === 'degraded'
            ? Math.min(pollIntervalMs, DEGRADED_POLL_INTERVAL_MS)
            : pollIntervalMs;
        scheduleNextCheck(nextDelayMs);
      } catch {
        if (isMounted) {
          const nextFailureCount = consecutiveFailuresRef.current + 1;
          consecutiveFailuresRef.current = nextFailureCount;

          setState((current) => ({
            ...current,
            status:
              nextFailureCount >= OFFLINE_FAILURE_THRESHOLD
                ? 'offline'
                : 'degraded',
            lastCheckedAt: Date.now(),
            consecutiveFailures: nextFailureCount,
            source: fallbackToDiagnosticsRef.current ? 'diagnostics' : 'live',
          }));

          scheduleNextCheck(getBackoffDelayMs(nextFailureCount));
        }
      }
    };

    const runImmediateCheck = () => {
      clearScheduledCheck();
      void checkHealth();
    };

    const handleBrowserOnline = () => runImmediateCheck();
    const handleBrowserOffline = () => {
      consecutiveFailuresRef.current = Math.max(
        consecutiveFailuresRef.current,
        OFFLINE_FAILURE_THRESHOLD,
      );
      setState((current) => ({
        ...current,
        status: 'offline',
        lastCheckedAt: Date.now(),
        consecutiveFailures: consecutiveFailuresRef.current,
      }));
      scheduleNextCheck(getBackoffDelayMs(consecutiveFailuresRef.current));
    };
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        runImmediateCheck();
      }
    };

    runImmediateCheck();
    window.addEventListener('online', handleBrowserOnline);
    window.addEventListener('offline', handleBrowserOffline);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      isMounted = false;
      clearScheduledCheck();
      window.removeEventListener('online', handleBrowserOnline);
      window.removeEventListener('offline', handleBrowserOffline);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [pollIntervalMs]);

  return useMemo(() => {
    const lastPing = state.latencyMs ? `${state.latencyMs}ms` : 'n/a';
    const checked = state.lastCheckedAt
      ? new Date(state.lastCheckedAt).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
      : 'n/a';

    if (state.status === 'online') {
      return {
        ...state,
        label: 'Connected',
        color: 'var(--success)',
        tooltip: `Backend connected. Last ping ${lastPing}. Checked ${checked}. Source: ${state.source ?? 'live'}.`,
      };
    }

    if (state.status === 'degraded') {
      return {
        ...state,
        label: 'Degraded',
        color: 'var(--warning)',
        tooltip: `Backend reachable but degraded. Last ping ${lastPing}. Checked ${checked}.`,
      };
    }

    if (state.status === 'offline') {
      return {
        ...state,
        label: 'Offline',
        color: 'var(--danger)',
        tooltip: `Backend is unreachable. Last check ${checked}. Consecutive failures: ${state.consecutiveFailures}.`,
      };
    }

    return {
      ...state,
      label: 'Checking',
      color: 'var(--warning)',
      tooltip: 'Checking backend health...',
    };
  }, [state]);
}
