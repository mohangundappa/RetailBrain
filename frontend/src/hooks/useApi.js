import { useState, useCallback } from 'react';
import { useAppContext } from '../context/AppContext';
import apiService from '../api/apiService';

/**
 * Custom hook for making API calls with built-in state management
 * 
 * @returns {Object} API utilities and state
 */
const useApi = () => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { addNotification } = useAppContext();

  /**
   * Makes an API call using the provided function and parameters
   * 
   * @param {Function} apiFunction - API function to call
   * @param {Array} params - Parameters to pass to the API function
   * @param {Object} options - Additional options
   * @returns {Object} - API response data
   */
  const makeRequest = useCallback(async (apiFunction, params = [], options = {}) => {
    const { 
      skipLoading = false,
      showSuccessNotification = false,
      showErrorNotification = true,
      successMessage = 'Operation completed successfully',
      errorMessage = 'An error occurred. Please try again.'
    } = options;

    if (!skipLoading) {
      setLoading(true);
    }
    setError(null);

    try {
      const response = await apiService.apiCall(apiFunction, ...params);
      setData(response);

      if (showSuccessNotification) {
        addNotification({
          title: 'Success',
          message: successMessage,
          type: 'success'
        });
      }

      return response;
    } catch (err) {
      setError(err.message || errorMessage);
      
      if (showErrorNotification) {
        addNotification({
          title: 'Error',
          message: err.message || errorMessage,
          type: 'error'
        });
      }
      
      return { success: false, error: err.message };
    } finally {
      if (!skipLoading) {
        setLoading(false);
      }
    }
  }, [addNotification]);

  /**
   * Resets the hook state
   */
  const reset = useCallback(() => {
    setData(null);
    setLoading(false);
    setError(null);
  }, []);

  return {
    makeRequest,
    reset,
    data,
    loading,
    error,
    setData
  };
};

export default useApi;