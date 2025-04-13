import { useState, useCallback, useEffect } from 'react';
import { useAppContext } from '../context/AppContext';

/**
 * Custom hook for making API calls with loading state and error handling
 * Integrated with the app context for global notifications and state management
 * 
 * @param {Function} apiMethod - The API method to call
 * @param {Array} dependencies - Dependencies to watch for automatic API calls
 * @param {Boolean} loadOnMount - Whether to load data on component mount
 * @param {Boolean} showErrorToast - Whether to show error notifications
 * @returns {Object} - API state and control functions
 */
const useApi = (
  apiMethod,
  dependencies = [],
  loadOnMount = false,
  showErrorToast = true
) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const { actions } = useAppContext();

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiMethod(...args);
      
      if (!result.success && result.error) {
        setError(result.error);
        
        if (showErrorToast) {
          actions.addNotification({
            type: 'error',
            title: 'API Error',
            message: result.error,
            autoDismiss: true
          });
        }
        
        setData(null);
      } else {
        setData(result);
      }
      
      return result;
    } catch (err) {
      setError(err.message);
      
      if (showErrorToast) {
        actions.addNotification({
          type: 'error',
          title: 'API Error',
          message: err.message,
          autoDismiss: true
        });
      }
      
      setData(null);
      return { success: false, error: err.message };
    } finally {
      setLoading(false);
    }
  }, [apiMethod, actions, showErrorToast]);

  // Auto-execute if loadOnMount is true
  useEffect(() => {
    if (loadOnMount) {
      execute();
    }
  }, [loadOnMount, execute, ...dependencies]);

  return {
    data,
    loading,
    error,
    execute,
    setData
  };
};

export default useApi;