/**
 * API Client Configuration
 * 
 * Provides a configured HTTP client for making API requests to the backend.
 * Uses native fetch with TypeScript types for request/response handling.
 */

/** API error with status code and message */
export class ApiError extends Error {
  constructor(
    message: string,
    public statusCode: number,
    public details?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

/** Base URL for API requests - uses Vite's proxy in development */
const API_BASE_URL = '/api';

/** Default request options */
const DEFAULT_OPTIONS: RequestInit = {
  headers: {
    'Content-Type': 'application/json',
  },
};

/**
 * Make a typed POST request to the API.
 * 
 * @param endpoint - API endpoint path (without /api prefix)
 * @param body - Request body to send as JSON
 * @returns Parsed response body
 * @throws ApiError if the request fails
 */
export async function postRequest<TResponse, TRequest = unknown>(
  endpoint: string,
  body: TRequest
): Promise<TResponse> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...DEFAULT_OPTIONS,
      method: 'POST',
      body: JSON.stringify(body),
    });

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;
      let details: unknown;

      try {
        const errorBody = await response.json();
        errorMessage = errorBody.detail || errorBody.message || errorMessage;
        details = errorBody;
      } catch {
        // Response body wasn't JSON, use default message
      }

      throw new ApiError(errorMessage, response.status, details);
    }

    return await response.json() as TResponse;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    // Network errors or other issues
    throw new ApiError(
      error instanceof Error ? error.message : 'Network request failed',
      0
    );
  }
}

/**
 * Make a typed GET request to the API.
 * 
 * @param endpoint - API endpoint path (without /api prefix)
 * @returns Parsed response body
 * @throws ApiError if the request fails
 */
export async function getRequest<TResponse>(
  endpoint: string
): Promise<TResponse> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  try {
    const response = await fetch(url, {
      ...DEFAULT_OPTIONS,
      method: 'GET',
    });

    if (!response.ok) {
      let errorMessage = `Request failed with status ${response.status}`;
      let details: unknown;

      try {
        const errorBody = await response.json();
        errorMessage = errorBody.detail || errorBody.message || errorMessage;
        details = errorBody;
      } catch {
        // Response body wasn't JSON, use default message
      }

      throw new ApiError(errorMessage, response.status, details);
    }

    return await response.json() as TResponse;
  } catch (error) {
    if (error instanceof ApiError) {
      throw error;
    }

    throw new ApiError(
      error instanceof Error ? error.message : 'Network request failed',
      0
    );
  }
}
