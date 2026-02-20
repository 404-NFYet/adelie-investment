import { useState, useEffect, useCallback } from 'react';
import { API_BASE_URL } from '../config';
import { authFetch } from '../api/client';

const readResponseError = async (response) => {
  const data = await response.json().catch(() => ({}));
  return data.detail || data.message || `HTTP ${response.status}: ${response.statusText}`;
};

/**
 * Generic fetch hook for GET requests
 * @param {string} endpoint - API endpoint (e.g., '/api/v1/briefing/today')
 * @param {Object} options - Fetch options
 * @returns {Object} { data, error, isLoading, refetch }
 */
export function useFetch(endpoint, options = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(true);

  const { enabled = true, params = {}, dependencies = [] } = options;

  const fetchData = useCallback(async () => {
    if (!enabled) {
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      // Build URL with query params
      const url = new URL(`${API_BASE_URL}${endpoint}`);
      Object.entries(params).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          url.searchParams.append(key, value);
        }
      });

      const response = await authFetch(url.toString(), {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });

      if (!response.ok) {
        throw new Error(await readResponseError(response));
      }

      const result = await response.json();
      setData(result);
    } catch (err) {
      setError(err.message);
      console.error(`Fetch error for ${endpoint}:`, err);
    } finally {
      setIsLoading(false);
    }
  }, [endpoint, enabled, JSON.stringify(params)]);

  useEffect(() => {
    fetchData();
  }, [fetchData, ...dependencies]);

  return { data, error, isLoading, refetch: fetchData };
}

/**
 * Mutation hook for POST/PUT/DELETE requests
 * @param {string} endpoint - API endpoint
 * @param {Object} options - Mutation options
 * @returns {Object} { mutate, data, error, isLoading }
 */
export function useMutation(endpoint, options = {}) {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [isLoading, setIsLoading] = useState(false);

  const { method = 'POST', onSuccess, onError } = options;

  const mutate = useCallback(
    async (body) => {
      setIsLoading(true);
      setError(null);

      try {
        const response = await authFetch(`${API_BASE_URL}${endpoint}`, {
          method,
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(body),
        });

        if (!response.ok) {
          throw new Error(await readResponseError(response));
        }

        const result = await response.json();
        setData(result);
        onSuccess?.(result);
        return result;
      } catch (err) {
        setError(err.message);
        onError?.(err);
        throw err;
      } finally {
        setIsLoading(false);
      }
    },
    [endpoint, method, onSuccess, onError]
  );

  return { mutate, data, error, isLoading };
}

export default useFetch;
