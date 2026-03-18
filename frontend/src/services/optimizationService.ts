/**
 * Optimization Service
 * 
 * Handles API calls for prompt optimization.
 */

import { postRequest } from './apiClient';
import type { OptimizationRequest, OptimizationResponse } from '@/types';

/**
 * Generate optimized prompt variants.
 * 
 * @param request - Optimization request payload
 * @returns Optimization response with three variants
 */
export async function optimizePrompt(
  request: OptimizationRequest
): Promise<OptimizationResponse> {
  return postRequest<OptimizationResponse, OptimizationRequest>(
    '/optimize',
    request
  );
}
