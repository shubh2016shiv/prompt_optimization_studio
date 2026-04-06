/**
 * EndpointInput Component
 * 
 * Optional input for overriding the default API endpoint.
 */

import { Input } from '@/components/ui';
import { FieldLabel } from '@/components/layout';
import { useConfigurationStore, useCurrentProvider } from '@/store';

/**
 * Optional endpoint override input.
 */
export function EndpointInput() {
  const endpointOverride = useConfigurationStore((state) => state.endpointOverride);
  const setEndpointOverride = useConfigurationStore((state) => state.setEndpointOverride);
  const provider = useCurrentProvider();

  return (
    <div className="min-w-0">
      <FieldLabel hint="override">API Endpoint</FieldLabel>
      <Input
        value={endpointOverride}
        onChange={(e) => setEndpointOverride(e.target.value)}
        placeholder={provider?.defaultEndpoint}
        className="text-[10.5px] text-[var(--text-secondary)]"
      />
    </div>
  );
}
