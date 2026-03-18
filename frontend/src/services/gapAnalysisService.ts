/**
 * Gap Analysis Service
 * 
 * Handles API calls for TCRTE coverage gap analysis.
 */

import { postRequest } from './apiClient';
import type { GapAnalysisRequest, GapAnalysisResponse } from '@/types';

/**
 * Analyze a prompt for TCRTE coverage gaps.
 * 
 * @param request - Gap analysis request payload
 * @returns Gap analysis response with TCRTE scores and questions
 */
export async function analyzePromptGaps(
  request: GapAnalysisRequest
): Promise<GapAnalysisResponse> {
  return postRequest<GapAnalysisResponse, GapAnalysisRequest>(
    '/gap-analysis',
    request
  );
}
