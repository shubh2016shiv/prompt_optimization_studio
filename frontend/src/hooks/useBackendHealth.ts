/**
 * useBackendHealth Hook
 *
 * Polls the backend health endpoint so the header can reflect
 * whether the API is online during local development.
 */

import { useEffect, useMemo, useState } from 'react';
import { getRequest } from '@/services';

type BackendHealthStatus = 'checking' | 'online' | 'offline';

interface BackendHealthResponse {
  status: string;
  version: string;
}

export function useBackendHealth(pollIntervalMs = 15000) {
  const [status, setStatus] = useState<BackendHealthStatus>('checking');

  useEffect(() => {
    let isMounted = true;

    const checkHealth = async () => {
      try {
        const response = await getRequest<BackendHealthResponse>('/health');

        if (!isMounted) {
          return;
        }

        setStatus(response.status === 'healthy' ? 'online' : 'offline');
      } catch {
        if (isMounted) {
          setStatus('offline');
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
    if (status === 'online') {
      return {
        status,
        label: 'Backend online',
        color: 'var(--success)',
        background: 'var(--success-soft)',
      };
    }

    if (status === 'offline') {
      return {
        status,
        label: 'Backend offline',
        color: 'var(--danger)',
        background: 'var(--danger-soft)',
      };
    }

    return {
      status,
      label: 'Checking backend',
      color: 'var(--warning)',
      background: 'var(--warning-soft)',
    };
  }, [status]);
}
