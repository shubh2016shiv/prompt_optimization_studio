/**
 * useBackendHealth Hook
 *
 * Polls backend health and returns status metadata for compact indicators.
 */

import { useEffect, useMemo, useState } from 'react';
import { getRequest } from '@/services';

type BackendHealthStatus = 'checking' | 'online' | 'degraded' | 'offline';

interface BackendHealthResponse {
  status: string;
  version: string;
}

interface HealthState {
  status: BackendHealthStatus;
  latencyMs?: number;
  lastCheckedAt?: number;
}

export function useBackendHealth(pollIntervalMs = 15000) {
  const [state, setState] = useState<HealthState>({ status: 'checking' });

  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      const startedAt = performance.now();

      try {
        const response = await getRequest<BackendHealthResponse>('/health');
        const latencyMs = Math.round(performance.now() - startedAt);

        if (!isMounted) {
          return;
        }

        const isHealthy = response.status === 'healthy';
        const status: BackendHealthStatus = !isHealthy
          ? 'offline'
          : latencyMs > 1200
          ? 'degraded'
          : 'online';

        setState({
          status,
          latencyMs,
          lastCheckedAt: Date.now(),
        });
      } catch {
        if (isMounted) {
          setState({
            status: 'offline',
            lastCheckedAt: Date.now(),
          });
        }
      }
    };

    checkHealth();
    const intervalId = window.setInterval(checkHealth, pollIntervalMs);

    return () => {
      isMounted = false;
      window.clearInterval(intervalId);
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
        tooltip: `Backend connected. Last ping ${lastPing}. Checked ${checked}.`,
      };
    }

    if (state.status === 'degraded') {
      return {
        ...state,
        label: 'Degraded',
        color: 'var(--warning)',
        tooltip: `Backend responsive but slow. Last ping ${lastPing}. Checked ${checked}.`,
      };
    }

    if (state.status === 'offline') {
      return {
        ...state,
        label: 'Offline',
        color: 'var(--danger)',
        tooltip: `Backend is offline. Last check ${checked}.`,
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
